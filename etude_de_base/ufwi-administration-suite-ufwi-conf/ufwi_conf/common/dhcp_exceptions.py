
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

class DHCPError(Exception):
    pass

class MissingData(DHCPError):
    pass

class DHCPRangeNotInNet(DHCPError):
    pass

class _IPNotInNet(DHCPRangeNotInNet):
    def __init__(self, ip):
        DHCPRangeNotInNet.__init__(self, "IP not in network")
        self.ip = ip

class RouterNotInNet(_IPNotInNet):
    pass

class StartIPNotInNet(_IPNotInNet):
    pass

class EndIpNotInNet(_IPNotInNet):
    pass

