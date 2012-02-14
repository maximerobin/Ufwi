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

from ufwi_rpcd.common.abstract_cfg import AbstractConf

from ufwi_conf.common.cert import CertConf

FORBIDDEN = 0
ALLOWED = 1
MANDATORY = 2

class AuthCertConf(AbstractConf, CertConf):
    """
    Configuration for authentication.
    """
    # In version 2, 2 new variables: portal_enabled, portal_nets
    # In version 3 cf. cert.py (checkSerialVersionA)

    ATTRS = """
        auth_by_cert
        portal_enabled
        portal_nets
        strict
        """.split() + CertConf.ATTRS

    DATASTRUCTURE_VERSION = 3

    def __init__(self,
        auth_by_cert=FORBIDDEN,
        portal_enabled=False,
        portal_nets=None,
        strict=False,
        ca='', #certconf
        cert='', #certconf
        crl='', #certconf
        key='', #certconf
        nupki_pki='', #certconf
        nupki_cert='', #certconf
        use_nupki=False, #certconf
        disable_crl=True #certconf
        ):

        if portal_nets is None:
            portal_nets = set()

        AbstractConf.__init__(self)
        CertConf.__init__(
            self,
            ca=ca,
            cert=cert,
            crl=crl,
            key=key,
            nupki_pki=nupki_pki,
            nupki_cert=nupki_cert,
            use_nupki=use_nupki,
            disable_crl=disable_crl
            )

        self.auth_by_cert = auth_by_cert
        self.portal_enabled = portal_enabled
        self.portal_nets = portal_nets
        self.strict = strict

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = range(1, cls.DATASTRUCTURE_VERSION + 1)

        if datastructure_version not in supported_versions:
            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        if datastructure_version < 2:
            # Upgrade 1 -> 2:
            serialized['portal_enabled'] = False
            serialized['portal_nets'] = set()
        CertConf.checkSerialVersionA(datastructure_version, serialized)
        return datastructure_version

    @classmethod
    def downgradeFields(cls, serialized, wanted_version):
        if wanted_version < 3 and serialized['DATASTRUCTURE_VERSION'] >= 3:
            serialized['DATASTRUCTURE_VERSION'] = 2
            # Downgrade 3 -> 2:
            #delegate CertConf
            cls.downgradeFieldsA(serialized)
        if wanted_version < 2 and serialized['DATASTRUCTURE_VERSION'] >= 2:
            # 2 -> 1:
            del serialized['portal_enabled']
            del serialized['portal_nets']
            serialized['DATASTRUCTURE_VERSION'] = 1

        if wanted_version != serialized['DATASTRUCTURE_VERSION']:
            raise NotImplementedError()

        return serialized

    @staticmethod
    def defaultConf():
        """
        create an empty object
        """
        return AuthCertConf()

    def isValidWithMsg(self):
        return True, ''

    def setPortalEnabled(self, value):
        if value:
            self.portal_enabled = True
        else:
            self.portal_enabled = False

    def setPortalNets(self, nets):
        self.portal_nets = nets

    def setStrict(self, value):
        if value:
            self.strict = True
        else:
            self.strict = False

