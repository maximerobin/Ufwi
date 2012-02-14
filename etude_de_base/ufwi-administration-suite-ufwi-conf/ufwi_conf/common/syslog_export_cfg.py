# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies

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


from ufwi_rpcd.common import tr
from ufwi_rpcd.common.abstract_cfg import AbstractConf
from ufwi_rpcd.common.validators import (
    check_hostname,
    check_ip_or_domain,
    )

class SyslogExportConf(AbstractConf):
    """
    Configuration for syslog_export component.
    """

    ATTRS = """
        ca
        certificate
        crl
        disable_crl
        enabled
        components
        key
        servers
        use_pki
        """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, ca="", certificate="", crl="", disable_crl=False,
                 enabled=False, components=None, key="", servers=None,
                 use_pki=""):
        if servers is None:
            servers = []
        if components is None:
            components = {
                "ulogd": {
                    "enabled": False,
                    "facility": "local4",
                    "level": "info"}}
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return SyslogExportConf()

    def isValidWithMsg(self):
        if not isinstance(self.servers, list):
            return False, tr("The servers parameter must be a list.")
        if not self.enabled:
            return True, ''

        # Syslog export is enabled, so we check the parameters.
        if not self.servers or not self.servers[0] or \
                self.servers[0].get("address", "") == "":
            return False, tr("You must enter the address of a syslog server.")
        component_enabled = False
        for component in self.components.values():
            if component.get("enabled", False):
                component_enabled = True
                break
        if not component_enabled:
            return False, tr("You must enable at least one component.")
        for server in self.servers:
            if not isinstance(server, dict):
                return False, tr(
                    "At least one of the configured servers does "
                    "not contain the expected type of information:") + \
                    " %s." % server
            if "address" not in server:
                return False, tr(
                    "The following server does not have an address:") + \
                    " %s." % server
            if "port" not in server:
                return False, tr(
                    "The following server does not have a port:") + \
                    " %s." % server
            if not (check_ip_or_domain(server["address"]) or
                    check_hostname(server["address"])):
                return False, tr(
                    "The syslog server must be an IP address or a FQDN.")
        if not isinstance(self.components, dict):
            return False, tr(
                "The components parameter must be a dictionary.")
        for name, component in self.components.items():
            if not component["facility"].startswith("local"):
                return False, tr("The component") + " %s " % name + \
                    tr("has an invalid facility:") + \
                    " %s. " % component["facility"] + tr(
                    "It should begin with \"local\".")
        return True, ''


    def setCertificate(self, filename):
        self.certificate = unicode(filename)

    def setKey(self, filename):
        self.key = unicode(filename)

    def setCA(self, filename):
        self.ca = unicode(filename)

    def setCRL(self, filename):
        self.crl = unicode(filename)

    def setEnabled(self, value):
        if value:
            self.enabled = True
        else:
            self.enabled = False

    def setComponents(self, value):
        self.components = value

    def setServers(self, value):
        self.servers = value

    def setUsePKI(self, value):
        if value:
            self.use_pki = unicode(value)
        else:
            self.use_pki = u''

    def setDisableCRL(self, value):
        if value:
            self.disable_crl = True
        else:
            self.disable_crl = False

