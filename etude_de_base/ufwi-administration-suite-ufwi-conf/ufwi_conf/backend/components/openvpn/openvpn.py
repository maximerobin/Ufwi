#coding: utf-8
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           François Toussenel <ftoussenel AT edenwall.com>
           Feth Arezki <farezki AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

This file is part of NuFirewall.

 NuFirewall is free software: you can redistribute it and/or modify
 it under the terms of the GNU General Public License as published by
 the Free Software Foundation, version 3 of the License.

 NuFirewall is distributed in the hope that it will be useful,
 but WITHOUT ANY WARRANTY; without even the implied warranty of
 MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
 GNU General Public License for more details.

 You should have received a copy of the GNU General Public License
 along with NuFirewall.  If not, see <http://www.gnu.org/licenses/>
"""

from __future__ import with_statement

import IPy
from IPy import IP
from os import unlink
from os.path import exists, join
from twisted.internet.defer import inlineCallbacks, returnValue

from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.use_cert_component import UseCertificateComponent
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.core.config.responsible import CONFIG_AUTOCONFIGURATION, \
    CONFIG_MODIFICATION
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.netcfg import deserializeNetCfg
from ufwi_conf.common.net_objects import Net
from ufwi_conf.common.openvpn_cfg import (OpenVpnConf, OPENVPN_CLIENT_CONF_UNAVAILABLE,
    OPENVPN_CLIENT_TOO_OLD, OPENVPN_INVALID_CONFIGURATION)

from ufwi_conf.common.resolvcfg import deserialize as deserializeResolv

from .error import OpenVpnError

def split_net(network):
    net = IPy.IP(network)
    return net.net().strNormal(), net.strNetmask()

def _pushRoute(network):
    """
    Accepts
     - ufwi_conf.common.net_objects.Net objects
     - IPy.IP
    and formats a datastructure for the template
    """
    if isinstance(network, IP):
        net = network
    elif isinstance(network, Net):
        net = network.net
    else:
        raise ValueError("Invalid type: %s" % type(network))

    route_def = {
        'net_addr': net.net().strNormal(),
        'netmask': net.netmask().strNormal()
        }
    return route_def

def _acceptclient(context):
    if not context.isUserContext():
        #accept components
        return True
    if not context.user.client_name:
        return True
    if context.user.client_name.lower() not in ('eas', 'nfas'):
        #ufwi_rpcd_client and anything accepted
        return True
    if context.user.client_release is None:
        return False
    #For 4.0.13, client_release is None
    #For 4.0.14, client_release == '4.0.14'. For now we accept future clients
    return True

def _includeNet(network, default_gateways):
    """
    User comes from internet. It is unlikely that he'd be going back to the
    lan containing the default gateway (and internet).

    It is very likely, on the other hand, that the EdenWall has more than
    one LAN and that we export at least one LAN.
    """
    for default_gateway in default_gateways:
        if network.net.overlaps(default_gateway):
            return False
    return True

class OpenvpnComponent(ConfigServiceComponent, UseCertificateComponent):
    """
    Manage a Openvpn server
    """
    NAME = "openvpn"
    MASTER_KEY = NAME
    VERSION = "1.0"

    ACLS = {
        'resolv': set(('getResolvConfig',)),
        'network': set(('getNetconfig',)),
        'nupki': set(('copyPKI', 'copyCRL', )),
        'config': set(('apply', 'reset', )),
    }

    REQUIRES = ('config', 'network')
    CONFIG_DEPENDS = frozenset(('network', 'resolv'))

    ROLES = {
        'conf_read': set(('getClientConfig', 'getOpenVpnConfig',
                            'runtimeFiles', 'getCertificatesInfo')),
        'conf_write': set(('setOpenVpnConfig',)),
        'dpi_read': set(('getOpenVpnConfig',)),
    }

    PIDFILE = "/var/run/openvpn.server.pid"
    #<feth>I'd rather not use the exe name because it is not specific of a client or a particular server.
    #(many openvpn instances can coexist)
    #EXE_NAME="openvpn"

    INIT_SCRIPT = "openvpn"
    INITRANK_S = 16
    INITRANK_K = 80

    check_vpn_port = ConfigServiceComponent.check_port
    check_vpn_address = ConfigServiceComponent.check_ip
    # TODO check the vpn_netmask

    OPENVPN_BASE = '/etc/openvpn'
    CERT_PATH = join(OPENVPN_BASE, 'server.crt')
    KEY_PATH = join(OPENVPN_BASE, 'server.key')
    CRL_PATH = join(OPENVPN_BASE, 'server.crl')
    CA_PATH = join(OPENVPN_BASE, 'ca.crt')

    CLIENT_CONF = join(OPENVPN_BASE, 'client.ovpn')
    SERVER_CONF = join(OPENVPN_BASE, 'server.conf')
    CONF_FILES = CLIENT_CONF, SERVER_CONF

    #override UseCertificateComponent value
    CERT_OWNER_AND_GROUP = "openvpn", "openvpn"

    #apply_config is inherited

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        UseCertificateComponent.__init__(self)
        self.openvpn_cfg = self.context = self.core = None

    def init(self, core):
        UseCertificateComponent.init(self, core)
        self.context = Context.fromComponent(self)
        for filename in self.CONF_FILES:
            self.addConfFile(filename, 'root:root', '0644')
        ConfigServiceComponent.init(self, core)

    @inlineCallbacks
    def init_done(self):
        config_version = self.openvpn_cfg.getReceivedSerialVersion()
        if config_version < 4:
            if not self.openvpn_cfg.manual_pushed_routes and self.should_run(None):
                self.critical(
                    "A configuration with version %d was read, and no pushed "
                    "routes were defined in it. Adding all routes. and saving" %
                    config_version
                    )
                if self._append_all_routes():
                    yield self.core.callService(self.context, 'config', 'reset')
                    self.save_config(
                        "openvpn : Adding pushed routes",
                        context=self.context,
                        action=CONFIG_AUTOCONFIGURATION
                        )
                    yield self.core.callService(self.context, 'config', 'apply')
                else:
                    self.critical("Could'nt find a route to add")
        else:
            self.debug("Not need to add any routes.")

    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
        except (ConfigError, KeyError):
            self.warning('Openvpn not configured, default values loaded.')
            self.openvpn_cfg = OpenVpnConf()
            return

        try:
            self.openvpn_cfg = OpenVpnConf.deserialize(serialized)
        except DatastructureIncompatible:
            self.openvpn_cfg = OpenVpnConf.deserialize(serialized)

    def should_run(self, responsible):
        if not self.openvpn_cfg.enabled:
            if responsible:
                responsible.feedback(tr("Explicitely disabled."))
            return False
        if not self.openvpn_cfg.client_network:
            if responsible:
                responsible.feedback(
                    tr("No client network was defined, disabling server.")
                    )
            return False
        return True

    def _template_variables(self, responsible, resolvcfg):
        # The server will listen on 0.0.0.0.
        net, mask = split_net(
            self.openvpn_cfg.client_network
        )
        yield 'client_network', net
        yield 'netmask_long_format', mask

        #For client.ovpn.
        yield 'server_address', self.openvpn_cfg.server

        yield 'port', self.openvpn_cfg.port
        yield 'protocol', self.openvpn_cfg.protocol
        yield 'redirect', self.openvpn_cfg.redirect
        yield 'disable_crl', self.openvpn_cfg.disable_crl

        yield 'domain', resolvcfg.domain
        yield 'nameserver1', resolvcfg.nameserver1
        yield 'nameserver2', resolvcfg.nameserver2

        routes = []

        for network in self.openvpn_cfg.manual_pushed_routes:
            routes.append(_pushRoute(network))
        yield 'routes', routes

    @inlineCallbacks
    def _fetchResolv(self):
        context = Context.fromComponent(self)

        serialized_resolvcfg = yield self.core.callService(
            context, 'resolv', 'getResolvConfig'
        )

        resolvcfg = deserializeResolv(serialized_resolvcfg)
        returnValue(resolvcfg)


    @inlineCallbacks
    def genConfigFiles(self, responsible):
        #FIXME: id 'read_config' call really useful?
        self.read_config()

        if not self.should_run(responsible):
            for filename in self.CONF_FILES:
                if exists(filename):
                    unlink(filename)
            return

        resolvcfg = yield self._fetchResolv()

        template_variables = dict(
            self._template_variables(responsible, resolvcfg)
            )

        self.generate_configfile(template_variables)

        #svn commit r19729:
        #auth_cert, openvpn: don't set SSL in apply_config() in a restoration
        #To avoid nupki.copyPKI() error if the PKI doesn't exist anymore.
        if not responsible.isRestoring():
            ssl_conf = self.openvpn_cfg.getSSLDict()
            yield self._setSSLConfig(ssl_conf)

        self.setCertsOwnership()

    def save_config(self, message, context=None, action=None):
        with self.core.config_manager.begin(self, context, action=action) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.openvpn_cfg.serialize())
            cm.commit(message)

    def get_ports(self):
        return [{'proto': self.openvpn_cfg.protocol,
                 'port': self.openvpn_cfg.port}]

    def check_vpn_proto(self, value):
        return value in ('tcp', 'udp')

    # Services:
    def service_getOpenVpnConfig(self, context):
        serialized = self.openvpn_cfg.serialize()

        if _acceptclient(context):
            return serialized

        #sending for v3
        self.debug("Downgrading openvpn conf - will be read only for that client")
        return self.openvpn_cfg.downgradeFields(serialized, 2)

    def service_setOpenVpnConfig(self, context, serialized, message):
        if not _acceptclient(context):
            raise OpenVpnError(OPENVPN_CLIENT_TOO_OLD, tr('Impossible to '
                'configure openvpn with this frontend version; '
                'please upgrade'))
        openvpn_cfg = OpenVpnConf.deserialize(serialized)
        is_valid, msg = openvpn_cfg.isValidWithMsg()
        if is_valid:
            self.openvpn_cfg = openvpn_cfg
            self.save_config(message, context=context, action=CONFIG_MODIFICATION)
        else:
            raise OpenVpnError(OPENVPN_INVALID_CONFIGURATION, msg)

    def service_sendFile(self, context, type_, encoded_bin):
        # deprecated
        raise RpcdError(tr('Your EAS is too old to change the certificate configuration, please upgrade it.'))

    def service_copyPKI(self, context, pkiname, cname):
        # deprecated
        raise RpcdError(tr('Your EAS is too old to change the certificate configuration, please upgrade it.'))

    def service_getClientConfig(self, context):
        """
        Return a string containing a configuration for a client.
        """
        try:
            with open(self.CLIENT_CONF) as fd:
                return encodeFileContent(fd.read())
        except IOError:
            raise OpenVpnError(OPENVPN_CLIENT_CONF_UNAVAILABLE,
                tr('The client configuration for VPN client is not available. '
                    'Have you configured the VPN client service, '
                    'then saved and applied the configuration?'))

    # TODO : factorize with auth_cert, aka authentication, aka nuauth
    def service_runtimeFiles(self, context):
        cert_files = (self.CERT_PATH, self.KEY_PATH, self.CRL_PATH, self.CA_PATH)
        cert_tuples = [(cert, 'bin') for cert in cert_files]
        return {'added': cert_tuples}

    def service_runtimeFilesModified(self, context):
        #Nothing to do because the config module will reload us
        pass

    # TODO : factorize with auth_cert, aka authentication, aka nuauth
    def _getSSLConfig(self):
        return self.openvpn_cfg.getSSLDict()

    def _append_all_routes(self):
        """
        When importing an old config without any manual pushed routes
        """
        changed = False

        #fetch net config
        netconfig = self.core.config_manager.get('network')
        netcfg = deserializeNetCfg(netconfig)

        #fetch default routes and gateways
        default_routes = tuple(netcfg.iterRoutes(default_only=True))
        #default_gateways: IPy.IP
        default_gateways = tuple(route.router for route in default_routes)

        #add everything into config
        for network in netcfg.iterNetworks(include_ha=False):
            if _includeNet(network, default_gateways):
                self.openvpn_cfg.manual_pushed_routes += (network.net, )
                changed = True

        return changed

