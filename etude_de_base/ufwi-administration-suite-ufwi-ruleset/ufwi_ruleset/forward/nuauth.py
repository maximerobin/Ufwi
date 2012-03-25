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

from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.logger import LoggerChild

from nuauth_command import Client

SOCKET = "/var/run/nuauth/nuauth-command.socket"

class RunNuauthCommand(Transaction, LoggerChild):
    def __init__(self, logger):
        LoggerChild.__init__(self, logger)

    def apply(self):
        try:
            client = Client(SOCKET)
            self.info("Connect to %s" % SOCKET)
            client.connect()
            self.info("Run command: reload periods")
            client.execute("reload periods")
            self.info("Run command: refresh cache")
            client.execute("refresh cache")
        except Exception, err:
            self.writeError(err, "nuauth_command error")

