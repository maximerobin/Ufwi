
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

from M2Crypto.m2 import X509_PURPOSE_SSL_CLIENT
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.ssl import SSLConfig

class ClientSSLConfig(SSLConfig):
    EXPECTED_X509_PURPOSE = X509_PURPOSE_SSL_CLIENT
    def __init__(self):
        SSLConfig.__init__(self)

        # Prefer TLSv1 to SSLv3 because it's more recent and more secure.
        #
        # PyOpenSSL server using SSLv23 accepts TLSv1 client.
        # M2Crypt server using SSLv23 or TLSv1 accepts TLSv1 client.
        self.protocol = 'tlsv1'   # only understand TLSv1

        # Disable cert authentication by default
        self.send_cert = False

    def validate(self):
        if self.cert and (not self.key):
            return tr('Please specify a private key.')
        if self.key and (not self.cert):
            return tr('Please specify a certificate.')
        m2validate = SSLConfig.validate(self)
        if m2validate is not None:
            return m2validate
        return None

