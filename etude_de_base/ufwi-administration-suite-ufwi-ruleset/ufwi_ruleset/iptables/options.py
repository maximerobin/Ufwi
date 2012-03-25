"""
Copyright (C) 2009-2011 EdenWall Technologies

Written by Victor Stinner <vstinner AT edenwall.com>
Modified by Pierre-Louis Bonicoli <bonicoli@edenwall.com>

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

class IptablesOptions(object):
    def __init__(self):
        self.ipv6 = False
        self.nufw = True
        # "iptables" (debug), "iptables-restore" (write files to disk)
        self.format = "iptables-restore"
        self.dispatch = True
        # 'LOG', 'ULOG' or 'NFLOG'
        self.log_type = 'ULOG'
        self.gateway = True

        # option used when IPv6 is completly disabled: don't generate any rule,
        # only set default policies to DROP
        self.deny_all = False

    def getProgram(self):
        if self.format == "iptables":
            if self.ipv6:
                return "ip6tables"
            else:
                return "iptables"
        else:
            return None

