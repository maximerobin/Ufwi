#coding: utf-8
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


from IPy import IP

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.abstract_cfg import AbstractConf

OPEN_BY_DEFAULT = ('bind', 'nuauth', 'ufwi_rpcd_access')

CLOSED_NETWORKS = set((
    IP('0.0.0.0/0'),
    IP('2000::/3'),
))

class AccessConf(AbstractConf):
    """
    Configuration for Access component.

    Changelog:
    DATASTRUCTURE_VERSION 1: initial version
    DATASTRUCTURE_VERSION 2: unknown
    DATASTRUCTURE_VERSION 3: unknown
    DATASTRUCTURE_VERSION 4: nuauth (tcp/4129) is now handled by auth_cert
    """
    ATTRS = (
        # dict: service name => set of (interface name, network as IPy.IP object)
        "permissions",
        # list of (interface name, network address as string)
        "custom_networks",
    )

    DATASTRUCTURE_VERSION = 4

    def __init__(self, permissions={}, custom_networks=tuple()):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return AccessConf(
            {},
            tuple(),
        )

    def isValidWithMsg(self):
        if not self.permissions.get('ufwi_rpcd_access'):
            # no access to ufwi_rpcd!
            return False, tr("You have to allow at least one network for the Administrator access!")
        return True, ''

    # Compatibility code
    @classmethod
    def checkSerialVersion(cls, serialized):
        """nuauth now handled by auth_cert component, not by nuauth component"""
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = (1, 2, 3, 4)
        if datastructure_version not in supported_versions:
            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        else:
            if datastructure_version < 4:
                if 'nuauth' in serialized['permissions']:
                    state = serialized['permissions'].pop('nuauth')
                    serialized['permissions']['auth_cert'] = state

        return datastructure_version

    def downgradeFields(self, serialized, wanted_version):
        """nuauth now handled by auth_cert component, not by nuauth component"""
        if wanted_version == 3:
            if 'auth_cert' in serialized['permissions']:
                state = serialized['permissions'].pop('auth_cert')
                serialized['permissions']['nuauth'] = state
        return serialized

