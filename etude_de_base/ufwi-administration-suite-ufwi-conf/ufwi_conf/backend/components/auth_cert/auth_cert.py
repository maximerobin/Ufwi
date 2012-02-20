#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by François Toussenel <ftoussenel AT edenwall.com>
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

import os
from os.path import join
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.use_cert_component import UseCertificateComponent
from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.core.context import Context

from ufwi_ruleset.localfw.wrapper import LocalFW

from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.backend.unix_service import RunCommandError
from ufwi_conf.common.auth_cert_cfg import AuthCertConf

DEFAULT_SHAREDIR = '/usr/share/ufwi_rpcd'
IPSET_EXE = '/usr/sbin/ipset'

_NUAUTH_CONF = '/etc/nufw/nuauth.conf'

class AuthCertComponent(ConfigServiceComponent, UseCertificateComponent):
    """
    Manage the authentication server's certificates and certificate
    configuration.
    """
    NAME = "auth_cert"
    MASTER_KEY = NAME
    VERSION = "1.0"

    ACLS = {
        'localfw': frozenset(('addFilterIptable', 'addNatIptable', 'apply', 'clear',
                        'close', 'open')),
        'network': frozenset(('getNetconfig',)),
        'ufwi_ruleset': frozenset(('open', 'reapplyLastRuleset',)),
        'nupki': frozenset(('copyPKI', 'copyCRL', )),
        'nuauth_command': frozenset(('refreshCRL', )),
    }

    # We need to restart nuauth when nuauth component, actually the user_directory component,
    # is modified.
    CONFIG_DEPENDS = ("nuauth",)

    REQUIRES = ('config', )
    if EDENWALL:
        REQUIRES += ('license',)
        ACLS['license'] = frozenset(('getMaxClients',))

    ROLES = {
        'conf_read': set(('getAuthCertConfig', 'runtimeFiles', 'getCertificatesInfo')),
        'conf_write': set(('setAuthCertConfig',)),
    }

    EXE_NAME = "nuauth"
    INIT_SCRIPT = "nuauth"

    CERT_BASE = '/etc/nufw/certs'
    CERT_PATH = join(CERT_BASE, 'nuauth-cert.pem')
    KEY_PATH = join(CERT_BASE, 'nuauth-key.pem')
    CRL_PATH = join(CERT_BASE, 'nuauth-crl.pem')
    CA_PATH = join(CERT_BASE, 'nuauth-cacert.pem')

    def __init__(self):
        ConfigServiceComponent.__init__(self)
        UseCertificateComponent.__init__(self)

    def init(self, core):
        ConfigServiceComponent.init(self, core)
        UseCertificateComponent.init(self, core)
        self.core = core
        try:
            self.sharedir = self.core.config.get('CORE', 'sharedir')
        except:
            self.sharedir = DEFAULT_SHAREDIR
        self.script_dir = os.path.join(self.sharedir, 'scripts')
        self.addConfFile(_NUAUTH_CONF, 'root:root', '0644')
        self.addConfFile('/etc/nufw/nuauth.d/nuauth_tls.conf', 'root:root',
                         '0644')
        self.addConfFile('/etc/nufw/user-down.sh', 'root:root', '0755')
        self.addConfFile('/etc/nufw/user-up.sh', 'root:root', '0755')

    def read_config(self, *args, **kwargs):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
        except (ConfigError, KeyError):
            self.warning(tr('Authentication server (certificates) not configured, default values loaded.'))
            self.auth_cert_cfg = AuthCertConf()
        else:
            try:
                self.auth_cert_cfg = AuthCertConf.deserialize(serialized)
            except DatastructureIncompatible:
                self.upgradeFields(serialized)
                self.auth_cert_cfg = AuthCertConf.deserialize(serialized)

    def apply_config(self, responsible, arg, modified_paths):
        return self._apply_conf(responsible)

    @inlineCallbacks
    def _apply_conf(self, responsible):
        #Ensure always enabled on boot.
        yield deferToThread(self.setEnabledOnBoot, True)

        self.read_config()
        yield self.genConfigFiles(responsible)

        #RunCommandError may happen here if nuauth was not started.
        yield deferToThread(self.startstopManager, 'restart')

        if EDENWALL:
            yield self.setup_portal(responsible)

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        template_variables = {
            'auth_by_cert': self.auth_cert_cfg.auth_by_cert,
            'portal_enabled': self.auth_cert_cfg.portal_enabled,
            'strict': self.auth_cert_cfg.strict,
            'disable_crl': self.auth_cert_cfg.disable_crl,
        }

        if EDENWALL:
            context = Context.fromComponent(self)
            nuauth_tls_max_clients = \
                yield self.core.callService(context, 'license', 'getMaxClients')
            template_variables['nuauth_tls_max_clients'] = nuauth_tls_max_clients

        self.generate_configfile(template_variables)

        if not responsible.isRestoring():
            ssl_config = self.auth_cert_cfg.getSSLDict()
            yield self._setSSLConfig(ssl_config)

        # TODO: move in ufwi_rpcd.backend.use_cert_component
        for cert_file in self.CERT_ATTR_TO_PATH.values():
            self.chownWithNames(cert_file, 'nuauth', 'nuauth')

    @inlineCallbacks
    def setup_portal(self, responsible):
        try:
            yield deferToThread(
                self.runCommandAsRootAndCheck,
                os.path.join(
                    self.script_dir,
                    "portal_ipset"
                    )
                )
        except RunCommandError:
            self.error("Could not create captive portal IP set.")

        localfw = LocalFW('portal')
        if self.auth_cert_cfg.portal_enabled:
            try:
                os.chmod(IPSET_EXE, 04755)
            except Exception, err:
                self.critical('Could not add setuid on %s (%s).' %
                              (IPSET_EXE, err))

            localfw.call('addNatIptable', False, '-N PORTAL')
            for network in self.auth_cert_cfg.portal_nets:
                localfw.call('addNatIptable', False,
                        '-A PREROUTING -p tcp --dport 80 -s %s -j PORTAL' %
                        network)
                localfw.call('addFilterIptable', False,
                        '-A INPUT -p tcp --dport 80 -s %s -j ACCEPT' %
                        network)
            localfw.call('addNatIptable', False,
                    '-A PORTAL -m set --set nuauth src,src -j RETURN')
            localfw.call('addNatIptable', False,
                    '-A PORTAL -j REDIRECT')
        # else: just clear existing rules

        context = Context.fromComponent(self)
        try:
            yield localfw.execute(self.core, context)
        except Exception, err:
            self.writeError(err,
                'Error while handling firewall NAT rules for the captive portal')
            raise

        if self.auth_cert_cfg.portal_enabled:
            responsible.feedback(tr("Captive portal has been setup"))
        else:
            responsible.feedback(tr("Captive portal has been disabled"))

    def save_config(self, message, context=None):
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except ConfigError:
                pass
            cm.set(self.MASTER_KEY, self.auth_cert_cfg.serialize())
            cm.commit(message)

    def get_ports(self):
        return [{'proto': 'tcp', 'port': 4129}]

    # Services:
    def service_getAuthCertConfig(self, context):
        return self.auth_cert_cfg.serialize()

    def service_setAuthCertConfig(self, context, serialized, message):
        self.auth_cert_cfg = AuthCertConf.deserialize(serialized)
        self.save_config(message, context)

    def service_sendFile(self, context, type_, encoded_bin):
        # deprecated
        raise RpcdError(tr('Your EAS is too old to change the certificate configuration, please upgrade it.'))

    def service_copyPKI(self, context, pkiname, cname):
        # deprecated
        raise RpcdError(tr('Your EAS is too old to change the certificate configuration, please upgrade it.'))

    # TODO : factorize with openvpn
    def service_runtimeFiles(self, context):
        cert_files = (self.CERT_PATH, self.KEY_PATH, self.CRL_PATH, self.CA_PATH)
        cert_tuples = [(cert, 'bin') for cert in cert_files]
        return {'added': cert_tuples}

    def service_runtimeFilesModified(self, context):
        #Nothing to do because the config module will reload us
        pass

    # TODO : factorize with openvpn
    def _getSSLConfig(self):
        return self.auth_cert_cfg.getSSLDict()

    def _onCRLUpdated(self):
        component_context = Context.fromComponent(self)
        return self.core.callService(component_context, 'nuauth_command', 'refreshCRL')

