"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

$Id$
"""

from __future__ import with_statement
from datetime import datetime

from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.common import tr
from ufwi_rpcd.common import is_pro
from ufwi_rpcd.common.tools import readDocumentation, getPrototype

from ufwi_rpcd.backend import Component
from ufwi_rpcd.backend.use_cert_component import UseCertificateComponent
from ufwi_rpcd.backend.error import CoreError

from ufwi_rpcd.core.conf_files import RPCD_CUSTOM_CONF
from ufwi_rpcd.core.version import VERSION as nucentral_version, PROTOCOL_VERSION
from ufwi_rpcd.core.getter import getUnicode
from ufwi_rpcd.core.tools import writeConfig

class CoreComponent(Component, UseCertificateComponent):
    """
    Rpcd core: store and manage all components and services
    """

    NAME = "CORE"
    VERSION = "1.0"
    API_VERSION = 2
    ROLES = {
        'nucentral_admin': set(("getSSLConfig", "setSSLConfig", "getCertificatesInfo")),
        # Create nucentral_debug role
        'nucentral_debug': set(),
    }
    ACLS = {
        'nupki': set(("copyPKI", "copyCRL")),
    }

    CERT_PATH = '/etc/ufwi-rpcd/cert.pem'
    KEY_PATH =  '/etc/ufwi-rpcd/key.pem'
    CA_PATH =   '/etc/ufwi-rpcd/ca.pem'
    CRL_PATH =  '/etc/ufwi-rpcd/crl.pem'

    def __init__(self):
        Component.__init__(self)
        UseCertificateComponent.__init__(self)

    def init(self, core):
        UseCertificateComponent.init(self, core)
        self.core = core

    # deprecated: replaced by createSession() service
    def service_clientHello(self, context, client_name, protocol_version):
        """
        Very first client request: announce the client software name and version.
        The server answers with its version (str) and a session key (str).

        Eg. ("0.1", "ld6aU7ZjdtJK5E8hU2sPMA==")
        """
        return self.service_createSession(context,
            {'client_name': client_name, 'protocol_version': protocol_version})

    def service_createSession(self, context, data):
        """
        Very first client request: announce the client software name and version.
        The server answers with its version (str) and a session key (str).

        Eg. ("0.1", "ld6aU7ZjdtJK5E8hU2sPMA==")
        """
        cookie = self.core.session_manager.create(context, data)
        return (PROTOCOL_VERSION, cookie)

    def service_getStatus(self, context):
        """
        Get current Rpcd status.

        Eg. 'Rpcd 0.2 up and running'
        """
        uptime = datetime.now() - self.core.start_time
        uptime = unicode(uptime).split(".")[0]
        return "Rpcd %s up and running since %s" \
            % (nucentral_version, uptime)

    def service_getComponentList(self, context):
        """
        Get the list of all components.
        """
        components = list(self.core.getComponentList(context))
        components.sort()
        return components

    def service_hasComponent(self, context, component_name):
        """
        Check if a component exists. Return False if the component doesn't
        exist or if you are not allowed to use it, and True otherwise.
        """
        return self.core.hasComponent(context, component_name)

    def service_hasService(self, context, component_name, service_name):
        try:
            self.core.getService(context, component_name, service_name)
            return True
        except CoreError:
            return False

    def service_getServiceList(self, context, component_name):
        """
        Get the list of all services of a component.

        Eg. ['getComponentVersion', 'getGroups', 'login']
        """
        services = self.core.getServiceList(context, component_name)
        services.sort()
        return services

    def service_help(self, context, *arguments):
        """
        Display help of a component or a service.
        Usage: "help component" or "help component service"
        """
        component_name = None
        service_name = 'getComponentVersion'
        prototype = None
        if len(arguments) == 1:
            component_name = getUnicode("component", arguments[0], 1, 100)
            obj = self.core.getComponent(context, component_name)
        elif len(arguments) == 2:
            component_name = getUnicode("component", arguments[0], 1, 100)
            service_name = getUnicode("service", arguments[1], 1, 100)
            component, obj = self.core.getService(context,
                component_name, service_name, component_check=False)
            prototype = getPrototype(obj, skip=1)
            if prototype.startswith("service_"):
                prototype = prototype[8:]
        else:
            return u'Usage: "help component" or "help component service"'
        doc = readDocumentation(obj)
        if prototype:
            doc = list(doc)
            if doc:
                doc = [prototype+':', ''] + list(doc)
            else:
                doc = [prototype]
        return doc

    def service_getMultisiteType(self, context):
        """
        Returns the type of firewall in the multisite context.
        """
        return self.core.getMultisiteType()

    def service_useEdenWall(self, context):
        """
        Return True if the nucentral is running on EdenWall.
        """
        return is_pro()

    def service_runtimeFiles(self, context):
        files = (
            (RPCD_CUSTOM_CONF, 'text'),
            (self.CERT_PATH, 'text'),
            (self.KEY_PATH, 'text'),
            (self.CA_PATH, 'text'),
            (self.CRL_PATH, 'text'),
        )
        return  {'added': files}

    def service_runtimeFilesModified(self, context):
        """
        nothing to do
        """
        pass

    def _checkSSL(self):
        if not self.core.ssl_config:
            raise CoreError(tr("SSL is disabled"))

    def _getSSLConfig(self):
        self._checkSSL()
        config = self.core.config
        ssl_config = self.core.ssl_config
        return {
            'check_clients': ssl_config.check,
            'use_nupki': config.getboolean('ssl', 'use_nupki'),
            'nupki_pki': config.get('ssl', 'nupki_pki'),
            'nupki_cert': config.get('ssl', 'nupki_cert'),
            'disable_crl' : not bool(config.get('ssl', 'crl')),
        }

    def service_getSSLConfig(self, context):
        return self._getSSLConfig()

    @inlineCallbacks
    def service_setSSLConfig(self, ctx, config):
        self._checkSSL()

        # Write certificates files
        yield self._setSSLConfig(config)

        # Prepare new configuration file
        use_nupki = config.get('use_nupki', False)
        ssl = {'use_nupki': use_nupki}

        if use_nupki:
            ssl.update({
                'use_nupki':    True,
                'nupki_pki':    config.get('nupki_pki', u''),
                'nupki_cert':   config.get('nupki_cert', u''),
                'ca':           self.CA_PATH,
                'cert':         self.CERT_PATH,
                'key':          self.KEY_PATH,
                'crl':          self.CRL_PATH,
            })
        else:
            for attr in self.CERT_ATTR_TO_PATH.keys():
                if attr in config.keys():
                    ssl[attr] = self.CERT_ATTR_TO_PATH[attr]

        if 'check_clients' in config:
            ssl['check_clients'] = config['check_clients']

        if 'disable_crl' not in config or config['disable_crl']:
            ssl['crl'] = u''

        self.critical("Writing new config file.")
        writeConfig(self.core, {'ssl': ssl})
        self.critical("Restart ufwi-rpcd to use the new configuration.")

