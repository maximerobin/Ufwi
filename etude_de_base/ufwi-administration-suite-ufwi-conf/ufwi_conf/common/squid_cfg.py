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
    check_ip_or_domain, check_port
    )
import IPy

class SquidConf(AbstractConf):
    """
    configuration for squid component (and services/proxy frontend).
    """
    ATTRS = """
        antivirus_enabled
        auth
        authorized_ips
        blacklist_enabled
        categories_blacklist
        categories_whitelist
        enabled
        parent_enabled
        parent_host
        parent_password
        parent_port
        parent_user
        transparent
        whitelist_mode
        """.split()

    DATASTRUCTURE_VERSION = 3

    def __init__(self,
                 antivirus_enabled=False,
                 auth='ip',
                 authorized_ips=None,
                 blacklist_enabled=False,
                 categories_blacklist=None,
                 categories_whitelist=None,
                 enabled=False,
                 parent_enabled=False,
                 parent_host='',
                 parent_password='',
                 parent_port=3128,
                 parent_user='',
                 transparent=False,
                 whitelist_mode=False):
        if authorized_ips is None:
            authorized_ips = []
        if categories_blacklist is None:
            categories_blacklist = []
        if categories_whitelist is None:
            categories_whitelist = []
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2, 3)
        if datastructure_version not in supported_versions:
            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        else:
            if datastructure_version < 3:
                # Upgrade (1 or 2) -> 3:
                serialized['whitelist_mode'] = False
            if datastructure_version < 2:
                # Upgrade 1 -> 2:
                serialized['blacklist_enabled'] = False
                serialized['categories_blacklist'] = []
                serialized['categories_whitelist'] = []
        return datastructure_version

    def downgradeFields(self, serialized, wanted_version):
        if wanted_version == 3:
            return serialized
        if wanted_version == 2:
            del serialized["whitelist_mode"]
            serialized["DATASTRUCTURE_VERSION"] = wanted_version
            return serialized
        if wanted_version == 1:
            # 1 -> 2:
            for attribute in ("blacklist_enabled",
                              "categories_blacklist",
                              "categories_whitelist"):
                del serialized[attribute]
            serialized['DATASTRUCTURE_VERSION'] = wanted_version
            return serialized
        raise NotImplementedError()

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        use_proxy = False
        return SquidConf(False, 'ip', [], False, [], [], False, False, '', '',
                         3128, '', False, False)

    def isValidWithMsg(self):
        for ip in self.authorized_ips:
            if not ip: continue
            try:
                IPy.IP(ip)  # For test only, so discard the result.
            except Exception, e:
                return False, tr('Invalid IP in authorized IPs (%s).') % ip
        if self.parent_enabled:
            if not check_ip_or_domain(self.parent_host):
                return False, tr('The parent proxy host (%s) is not a valid host or IP.') % self.parent_host
            if not check_port(self.parent_port):
                return False, tr('The parent proxy port (%s) is invalid.') % self.parent_port
        return True, ''

    def setAntivirusEnabled(self, antivirus_enabled):
        if antivirus_enabled:
            self.antivirus_enabled = True
        else:
            self.antivirus_enabled = False

    def setAuth(self, auth):
        self.auth = auth

    def setAuthorizedIPs(self, authorized_ips):
        self.authorized_ips = [unicode(ip) for ip in authorized_ips]

    def setCategoriesBlacklist(self, categories_blacklist):
        self.categories_blacklist = categories_blacklist

    def setCategoriesWhitelist(self, categories_whitelist):
        self.categories_whitelist = categories_whitelist

    def setBlacklistEnabled(self, enabled):
        if enabled:
            self.blacklist_enabled = True
        else:
            self.blacklist_enabled = False

    def setEnabled(self, enabled):
        if enabled:
            self.enabled = True
        else:
            self.enabled = False

    def setParentEnabled(self, parent_enabled):
        if parent_enabled:
            self.parent_enabled = True
        else:
            self.parent_enabled = False

    def setParentPassword(self, parent_password):
        self.parent_password = parent_password

    def setParentPort(self, parent_port):
        self.parent_port = parent_port

    def setParentHost(self, parent_host):
        self.parent_host = parent_host

    def setParentUser(self, parent_user):
        self.parent_user = parent_user

    def setTransparent(self, transparent):
        if transparent:
            self.transparent = True
        else:
            self.transparent = False

    def setWhitelistMode(self, enabled):
        if enabled:
            self.whitelist_mode = True
        else:
            self.whitelist_mode = False

