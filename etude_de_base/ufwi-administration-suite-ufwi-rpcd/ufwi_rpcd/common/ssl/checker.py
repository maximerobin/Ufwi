"""
SSL peer certificate checking routines

Copyright (c) 2004-2007 Open Source Applications Foundation.
All rights reserved.

Copyright 2008 Heikki Toivonen. All rights reserved.
"""

__all__ = ['SSLVerificationError', 'NoCertificate', 'WrongCertificate',
           'WrongHost', 'Checker']

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


from M2Crypto.m2 import NID_commonName
from M2Crypto.EVP import MessageDigest
from M2Crypto.util import octx_to_num

from M2Crypto.SSL.Checker import SSLVerificationError, NoCertificate, WrongCertificate, WrongHost, Checker as M2Checker

class Checker(M2Checker):
    def __init__(self, ssl_config):
        M2Checker.__init__(self)
        self.ssl_config = ssl_config

    def __call__(self, peerCert, host=None):
        if peerCert is None:
            raise NoCertificate('peer did not return certificate')

        if host is not None:
            self.host = host

        if self.fingerprint:
            if self.digest not in ('sha1', 'md5'):
                raise ValueError('unsupported digest "%s"' %(self.digest))

            if (self.digest == 'sha1' and len(self.fingerprint) != 40) or \
               (self.digest == 'md5' and len(self.fingerprint) != 32):
                raise WrongCertificate('peer certificate fingerprint length does not match')

            der = peerCert.as_der()
            md = MessageDigest(self.digest)
            md.update(der)
            digest = md.final()
            if octx_to_num(digest) != int(self.fingerprint, 16):
                raise WrongCertificate('peer certificate fingerprint does not match')

        if self.host and self.ssl_config.fqdn_check and self.ssl_config.check:
            hostValidationPassed = False
            self.useSubjectAltNameOnly = False

            # subjectAltName=DNS:somehost[, ...]*
            try:
                subjectAltName = peerCert.get_ext('subjectAltName').get_value()
                if self._splitSubjectAltName(self.host, subjectAltName):
                    hostValidationPassed = True
                elif self.useSubjectAltNameOnly:
                    raise WrongHost(expectedHost=self.host,
                                    actualHost=subjectAltName,
                                    fieldName='subjectAltName')
            except LookupError:
                pass

            # commonName=somehost[, ...]*
            if not hostValidationPassed:
                hasCommonName = False
                commonNames = ''
                for entry in peerCert.get_subject().get_entries_by_nid(NID_commonName):
                    hasCommonName = True
                    commonName = entry.get_data().as_text()
                    if not commonNames:
                        commonNames = commonName
                    else:
                        commonNames += ',' + commonName
                    if self._match(self.host, commonName):
                        hostValidationPassed = True
                        break

                if not hasCommonName:
                    raise WrongCertificate('no commonName in peer certificate')

                if not hostValidationPassed:
                    raise WrongHost(expectedHost=self.host,
                                    actualHost=commonNames,
                                    fieldName='commonName')

        return True

