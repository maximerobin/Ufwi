
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

from M2Crypto.SSL.TwistedProtocolWrapper import listenSSL
from ufwi_rpcd.backend.logger import Logger

class ContextFactory(Logger):
    def __init__(self, ssl_config):
        Logger.__init__(self, "ssl")
        self.ssl_config = ssl_config
        self.info("Use protocol %s" % ssl_config.protocol)

    def getContext(self):
        return self.ssl_config.createContext(self)

def startListeningSSL(core, ssl):
    listenSSL(ssl.port, core.site, ContextFactory(ssl),
        interface=ssl.address, reactor=core.reactor)

