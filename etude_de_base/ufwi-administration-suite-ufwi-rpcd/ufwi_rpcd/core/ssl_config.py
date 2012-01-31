
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

from M2Crypto.m2 import X509_PURPOSE_SSL_SERVER
from ufwi_rpcd.common.ssl import SSLConfig
from ufwi_rpcd.backend.logger import Logger

class ServerSSLConfig(SSLConfig, Logger):
    EXPECTED_X509_PURPOSE = X509_PURPOSE_SSL_SERVER
    def __init__(self, core):
        Logger.__init__(self, "ssl")
        SSLConfig.__init__(self)
        config = core.config

        # Options
        self.check = config.getboolean('ssl', 'check_clients')
        self.fqdn_check = config.getboolean('ssl', 'fqdn_check')
        self.max_depth = config.getint('ssl', 'max_depth')
        self.protocol = config.get('ssl', 'protocol')

        # Filenames
        self.ca = config.get('ssl', 'ca')
        self.cert = config.get('ssl', 'cert')
        self.key = config.get('ssl', 'key')
        self.crl = config.get('ssl', 'crl')
        self.key_passwd = config.get('ssl', 'key_passwd')

        # TCP parameters
        self.address, self.port = core.getAddressPort("_ssl", 8443)

    def get_key_password(self, v):
        return str(self.key_passwd)

    def silent_get_password(self, v):
        return str(self.key_passwd)

    def user_verify(self, error):
        self.critical('Certificate verification of "%s" failed: %s'
            % (error.getSubject(), error.getMessage()))
        for line in error.getCertText().splitlines():
            self.debug(line)
        # deny invalid certificate
        return 0

    def sslInfo(self, info):
        info.logInto(self)

