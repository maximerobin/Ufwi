# -*- coding: utf-8 -*-

# $Id$

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
from ufwi_rpcd.common.abstract_cfg import AbstractConf
from ufwi_rpcd.common.validators import check_ip_or_domain, check_port, check_network
from ufwi_rpcd.common import tr

from ufwi_conf.common.cert import CertConf

INTERFACE_NAME = 'tunp'

# Error codes:
OPENVPN_CLIENT_CONF_UNAVAILABLE = 1
OPENVPN_CLIENT_COULD_NOT_START_SERVICE = 2
OPENVPN_CLIENT_COULD_NOT_STOP_SERVICE = 3
OPENVPN_CLIENT_COULD_NOT_ENABLE_SERVICE_ON_BOOT = 4
OPENVPN_CLIENT_COULD_NOT_DISABLE_SERVICE_ON_BOOT = 5
OPENVPN_CLIENT_TOO_OLD = 6
OPENVPN_INVALID_CONFIGURATION = 7

class OpenVpnConf(AbstractConf, CertConf):
    """
    Configuration for openvpn component.

    Changelog:
    DATASTRUCTURE_VERSION 1: initial version, by ft
    DATASTRUCTURE_VERSION 2: add 'manual_pushed_routes' attr, by feth
    DATASTRUCTURE_VERSION 3: cf. cert.py (checkSerialVersionA)
    DATASTRUCTURE_VERSION 4: upgrade august '10. A conf without routes is invalid
    """

    ATTRS = """
        client_network
        enabled
        manual_pushed_routes
        port
        protocol
        redirect
        server
        """.split() + CertConf.ATTRS

    DATASTRUCTURE_VERSION = 4

    def __init__(self, client_network='', enabled=False, port='1194', protocol='udp',
            redirect=False, server='', manual_pushed_routes = (), ca='', cert='', crl='',
            key='', nupki_pki='', nupki_cert='', use_nupki=False, disable_crl=False):


        AbstractConf.__init__(self)
        CertConf.__init__(self, ca=ca, cert=cert, crl=crl,
            key=key, nupki_pki=nupki_pki, nupki_cert=nupki_cert, use_nupki=use_nupki, disable_crl=disable_crl)
        self.client_network = client_network
        self.enabled = bool(enabled)
        self.port = port
        self.protocol = protocol
        self.redirect = redirect
        self.server = server
        self.manual_pushed_routes = manual_pushed_routes

    @classmethod
    def checkSerialVersion(cls, serialized):
        datastructure_version = serialized.get('DATASTRUCTURE_VERSION')
        supported_versions = range(1, cls.DATASTRUCTURE_VERSION + 1)
        if datastructure_version not in supported_versions:
            #This will raise relevant errors
            cls.raise_version_error(datastructure_version)
        if datastructure_version < 2:
            #upgrade
            #1 -> 2: add manual_pushed_routes
            serialized['manual_pushed_routes'] = ()

        # 2 -> 3: pass
        # 3 -> 4: pass

        CertConf.checkSerialVersionA(datastructure_version, serialized)
        return datastructure_version

    @classmethod
    def downgradeFields(cls, serialized, wanted_version):
        if wanted_version < 4 and serialized['DATASTRUCTURE_VERSION'] >= 4:
            #4 -> 3:
            CertConf.downgradeFieldsA(serialized)
            serialized['DATASTRUCTURE_VERSION'] = 3

        if wanted_version < 3 and serialized['DATASTRUCTURE_VERSION'] >= 3:
            #3 -> 2:
            CertConf.downgradeFieldsA(serialized)
            serialized['DATASTRUCTURE_VERSION'] = 2

        if wanted_version < 2 and serialized['DATASTRUCTURE_VERSION'] >= 2:
            #2 -> 1: remove manual_pushed_routes
            del serialized['manual_pushed_routes']
            serialized['DATASTRUCTURE_VERSION'] = 1

        if wanted_version != serialized['DATASTRUCTURE_VERSION']:
            raise NotImplementedError()

        return serialized

    @staticmethod
    def defaultConf():
        """
        create an empty object, rely on __init__ default values
        """
        return OpenVpnConf()

    def isValidWithMsg(self):
        if not self.enabled and not self.server:
            # allow empty server if not enabled
            pass
        elif not check_ip_or_domain(self.server):
            return (False,
                    tr('Invalid server IP (IPv4 or IPv6 are allowed): ') \
                        + self.server)

        if not check_port(self.port):
            return False, tr('Invalid port (%s): must be greater than 0 and lower than 65536.') % self.port


        # allow empty client_network if not enabled
        if self.enabled or self.client_network:
            if not check_network(self.client_network):
                return False, tr('Invalid client network: ') + self.client_network

            if IP(self.client_network).len() > 65536L:
                return False, tr('The client network cannot be broader than a /16 network (netmask 255.255.0.0 at most).')
            elif IP(self.client_network).len() < 8:
                return False, tr('The client network cannot be narrower than a /29 network (netmask 255.255.255.248 at least).')

        if self.protocol not in ['tcp', 'udp']:
            return False, tr("Unknown protocol (choose 'tcp' or 'udp'): ") + self.protocol

        # should be done inside checkSerialVersion
        if self.enabled is None and self.hasCertWithMsg()[0]:
            self.enabled = False

        if self.enabled and not self.redirect and not self.manual_pushed_routes:
            return False, tr("You need to add routed networks for the VPN or\
                to redirect the default gateway through the VPN.")

        return True, ''

    def hasCertWithMsg(self):
        for key, value in (('CA', self.ca), ('cert', self.cert),
                           ('key', self.key)):
            missing = []
            if not value:
                missing.append(key)
            if missing:
                return False, tr('The following is missing: ') + ','.join(missing)
        return True, ''

    def setClientNetwork(self, value):
        self.client_network = unicode(value)

    def setEnabled(self, value):
        if value:
            self.enabled = True
        else:
            self.enabled = False

    def setPort(self, value):
        self.port = unicode(value)

    def setProtocol(self, value):
        self.protocol = unicode(value)

    def setRedirect(self, value):
        if value:
            self.redirect = True
        else:
            self.redirect = False

    def setServer(self, value):
        self.server = unicode(value)

