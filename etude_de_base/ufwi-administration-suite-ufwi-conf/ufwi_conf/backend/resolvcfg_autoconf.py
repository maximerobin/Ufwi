
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

from __future__ import with_statement

import re

from socket import getfqdn
from ufwi_conf.common.resolvcfg import ResolvCfg

class ResolvREs(object):
    nameserver = re.compile(r'nameserver (.+).*')

class ResolvCfgAutoconf(ResolvCfg):
    def __init__(self):
        useless1, useless2, domain = getfqdn().partition('.')
        ResolvCfg.__init__(self, domain, '', '')
        self.autoconf()

    def autoconf(self):
        with open('/etc/resolv.conf') as fd:
            for line in fd:
                self.interprete(line)

    def interprete(self, line):
        match = ResolvREs.nameserver.search(line)
        if match is not None:
            nameserver = match.group(1)
            if not self.nameserver1:
                self.nameserver1 = nameserver
            elif not self.nameserver2:
                self.nameserver2 = nameserver
                return

