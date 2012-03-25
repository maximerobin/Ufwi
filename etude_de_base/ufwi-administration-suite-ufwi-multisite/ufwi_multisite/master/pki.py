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


from twisted.internet.defer import succeed
from ufwi_rpcd.core.context import Context

PKI_NAME = u'__edenwall_multisite'
PKI_ORGUNIT = u'edenwall'
PKI_ORG = u'com'
PKI_LOCATION = u'Paris'
PKI_STATE = u'France'
PKI_COUNTRY = u'FR'
PKI_EMAIL = u'edenwall@edenwall.com'

NUPKI_SERVICES = set(('listPKI', 'createPKI', 'listServerCerts', 'listClientCerts', 'createCert', 'getCert', 'getCertPath',
                        'getPrivateCert', 'getPrivateCertPath', 'getCACert', 'getCACertPath', 'signRequest', 'newCert', 'updateCertSettings'))

class PKI:
    def __init__(self, component, core):
        self.core = core
        self.ctx = Context.fromComponent(component)
        self.ca_path = {}
        self.key_path = {}
        self.cert_path = {}
        self.ca = {}
        self.key = {}
        self.cert = {}

    def createPki(self, pki_list):
        for pki in pki_list:
            if pki[1] == PKI_NAME:
                break
        else:
            return self.core.callService(self.ctx, 'nupki', 'createPKI', PKI_NAME, PKI_ORGUNIT, PKI_ORG, PKI_LOCATION, PKI_STATE, PKI_COUNTRY)

    def loadPki(self, *args):
        d = self.core.callService(self.ctx, 'nupki', 'listPKI')
        d.addCallback(self.createPki)
        return d

    def getServerCerts_create_cert(self, cert_list, cert_name, type):
        for cert in cert_list:
            if cert[2] == cert_name:
                break
        else:
            return self.core.callService(self.ctx, 'nupki', 'createCert', PKI_NAME, cert_name, type, '01', PKI_EMAIL, PKI_ORGUNIT, PKI_ORG, PKI_LOCATION, PKI_STATE, PKI_COUNTRY)
        return succeed("done")

    ## Certificate, private key, CA path and creation
    def loadServerCertsPaths(self, cert_name, type):
        if type == 'server':
            d = self.core.callService(self.ctx, 'nupki', 'listServerCerts', PKI_NAME)
        else:
            d = self.core.callService(self.ctx, 'nupki', 'listClientCerts', PKI_NAME)
        d.addCallback(self.getServerCerts_create_cert, cert_name, type)
        d.addCallback(self.getServerCertsPaths_get_cert, cert_name)
        d.addCallback(self.getServerCertsPaths_get_key, cert_name)
        d.addCallback(self.getServerCertsPaths_get_ca, cert_name)
        d.addCallback(self.getServerCertsPaths_done, cert_name)
        return d

    def getServerCertsPaths_get_cert(self, done, cert_name):
        return self.core.callService(self.ctx, 'nupki', 'getCertPath', PKI_NAME, cert_name)

    def getServerCertsPaths_get_key(self, cert_path, cert_name):
        self.cert_path[cert_name] = cert_path
        return self.core.callService(self.ctx, 'nupki', 'getPrivateCertPath', PKI_NAME, cert_name)

    def getServerCertsPaths_get_ca(self, key_path, cert_name):
        self.key_path[cert_name] = key_path
        return self.core.callService(self.ctx, 'nupki', 'getCACertPath', PKI_NAME)

    def getServerCertsPaths_done(self, ca_path, cert_name):
        self.ca_path[cert_name] = ca_path
        return succeed("done")

    def getServerCertsPaths(self, cert_name):
        return self.cert_path[cert_name], self.key_path[cert_name], self.ca_path[cert_name]

    ## Certificate, private key, CA blob and creation
    def loadServerCerts(self, cert_name, type):
        if type == 'server':
            d = self.core.callService(self.ctx, 'nupki', 'listServerCerts', PKI_NAME)
        else:
            d = self.core.callService(self.ctx, 'nupki', 'listClientCerts', PKI_NAME)
        d.addCallback(self.getServerCerts_create_cert, cert_name, type)
        d.addCallback(self.getServerCerts_get_cert, cert_name)
        d.addCallback(self.getServerCerts_get_key, cert_name)
        d.addCallback(self.getServerCerts_get_ca, cert_name)
        d.addCallback(self.getServerCerts_done, cert_name)
        return d

    def getServerCerts_get_cert(self, done, cert_name):
        return self.core.callService(self.ctx, 'nupki', 'getCert', PKI_NAME, cert_name)

    def getServerCerts_get_key(self, cert_path, cert_name):
        self.cert[cert_name] = cert_path
        return self.core.callService(self.ctx, 'nupki', 'getPrivateCert', PKI_NAME, cert_name)

    def getServerCerts_get_ca(self, key_path, cert_name):
        self.key[cert_name] = key_path
        return self.core.callService(self.ctx, 'nupki', 'getCACert', PKI_NAME)

    def getServerCerts_done(self, key_path, cert_name):
        self.ca[cert_name] = key_path
        return succeed("done")

    def getServerCerts(self, cert_name):
        return self.cert[cert_name], self.key[cert_name], self.ca[cert_name]


    ## Cetificate signing
    def signCertRequest(self, req, hostname, type):
        d = self.core.callService(self.ctx, 'nupki', 'newCert', PKI_NAME, hostname, type)
        d.addCallback(lambda x:self.core.callService(self.ctx, 'nupki', 'updateCertSettings', PKI_NAME, hostname, '01', PKI_EMAIL, PKI_ORGUNIT, PKI_ORG, PKI_LOCATION, PKI_STATE, PKI_COUNTRY))
        d.addCallback(lambda x:self.core.callService(self.ctx, 'nupki', 'signRequest', PKI_NAME, hostname, req, type))
        d.addCallback(lambda x:self.core.callService(self.ctx, 'nupki', 'getCert', PKI_NAME, hostname))
        d.addCallback(self.signRequest_get_ca, hostname)
        d.addCallback(self.signRequest_done, hostname)
        return d

    def signRequest_get_ca(self, cert, hostname):
        self.cert[hostname] = cert
        return self.core.callService(self.ctx, 'nupki', 'getCACert', PKI_NAME)

    def signRequest_done(self, ca, hostname):
        self.ca[hostname] = ca
        return succeed("done")

    def getSignedCert(self, hostname):
        return self.cert[hostname], self.ca[hostname]

