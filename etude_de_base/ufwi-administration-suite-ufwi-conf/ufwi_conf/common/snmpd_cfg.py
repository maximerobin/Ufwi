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
import IPy

V2C_LIST_FIELD_COUNT = 2
V3_LIST_FIELD_COUNT = 5
INDEX_V2C_SOURCE = 0
INDEX_V2C_COMMUNITY = 1
INDEX_V3_USERNAME = 0
INDEX_V3_AUTHENTICATION_PASS = 1
INDEX_V3_AUTHENTICATION_PROTO = 2
INDEX_V3_ENCRYPTION_PASS = 3
INDEX_V3_ENCRYPTION_ALGO = 4

class SnmpdConf(AbstractConf):
    """
    Configuration for snmpd component.
    """
    ATTRS = """
        enabled
        super_password
        v2c_list
        v3_list
        """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self,
                 enabled=False,
                 super_password="",
                 v2c_list=None,
                 v3_list=None):
        if v2c_list is None:
            v2c_list = []
        if v3_list is None:
            v3_list = []
        AbstractConf.__init__(self)
        self._setLocals(locals())

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return SnmpdConf(False, "", [], [])

    def isValidWithMsg(self):
        # Always check given entries.
        # v2c_list:
        for el in self.v2c_list:
            field_count = len(el)
            if field_count != 2:
                return False, \
                    tr("Invalid number of fields for the v2c access list.")
            if not el[INDEX_V2C_SOURCE]:
                return False, tr("The source address must not be empty.")
            try:
                IPy.IP(el[INDEX_V2C_SOURCE])
            except Exception:
                return False, tr("Invalid source address.")
            if not el[INDEX_V2C_COMMUNITY]:
                return False, tr("Community must not be empty.")

        # v3_list:
        for el in self.v3_list:
            if not el[INDEX_V3_AUTHENTICATION_PROTO]:
                return False, tr(
                    "You must select an authentication protocol from the list.")
            if el[INDEX_V3_AUTHENTICATION_PROTO] not in ("MD5", "SHA"):
                return False, tr("Invalid protocol") + \
                    " (%s). " % el[INDEX_V3_AUTHENTICATION_PROTO] + \
                    tr("Available protocols: MD5 and SHA.")
            if not el[INDEX_V3_ENCRYPTION_ALGO]:
                return False, tr("You must select an algorithm from the list.")
            if el[INDEX_V3_ENCRYPTION_ALGO] not in ("AES", "DES"):
                return False, tr("Invalid algorithm") + \
                    " (%s). " % el[INDEX_V3_ENCRYPTION_ALGO] + \
                    tr("Available algorithms: AES and DES.")
            if not (el[INDEX_V3_USERNAME] and el[INDEX_V3_AUTHENTICATION_PASS]
                    and el[INDEX_V3_ENCRYPTION_PASS]):
                return False, tr(
                    "No field may be left empty in the SNMPv3 access list.")

        # No more checks if the service is disabled.
        if not self.enabled:
            return True, ""

        # Require some configuration if the service is enabled.
        if not (self.v2c_list or self.v3_list):
            return False, tr("You must add an entry in an access list.")

        return True, ''

    def setEnabled(self, enabled):
        if enabled:
            self.enabled = True
        else:
            self.enabled = False

    def setSuperPassword(self, value):
        self.super_password = value

    def setV2cList(self, value):
        self.v2c_list = value

    def setV3List(self, value):
        self.v3_list = value

