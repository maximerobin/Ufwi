"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT inl.fr>

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

$Id$
"""

from IPy import IP
from re import compile
from ufwi_rpcd.common.validators import check_domain, check_ip

class ResolvError(Exception):
    pass

_REGEX = compile(r'^0x[0-9a-fA-F]+$')

class ResolvCfg(object):
    def __init__(self, domain, nameserver1, nameserver2):
        """
        This class makes resolv.conf objects accessible
        """
        self.domain = unicode(domain).strip()
        self.nameserver1 = unicode(nameserver1).strip()
        self.nameserver2 = unicode(nameserver2).strip()

    def setDomain(self, domain):
         self.domain = unicode(domain).strip()

    def setNameserver1(self, dns):
        self.nameserver1 = unicode(dns).strip()

    def setNameserver2(self, dns):
        self.nameserver2 = unicode(dns).strip()

    def iterNameServers(self):
        for nameserver in (self.nameserver1, self.nameserver2):
            if nameserver:
                yield nameserver

    def serialize(self):
        serialized = {}
        serialized['domain'] = self.domain
        serialized['nameserver1'] = self.nameserver1
        serialized['nameserver2'] = self.nameserver2
        return serialized

    def isValidWithMsg(self):
        intermediate = self.isInvalid()
        if intermediate is False:
            return True, ''
        else:
            return False, intermediate

    def isValid(self):
        return self.isValidWithMsg()[0]

    def isInvalid(self):
        if self.domain and not check_domain(self.domain):
            return "domain is invalid"

        if not self.nameserver1 and not self.nameserver2:
            return "one name server required"

        if self.nameserver1 == self.nameserver2:
            return "nameservers 1 and 2 are identical"

        for value in (self.nameserver1, self.nameserver2):
            if value:
                error = "invalid IP: '%s'" % value
                if not check_ip(value):
                    return error

                try:
                    dns = IP(value)
                except:
                    return error

        return False

def deserialize(serialized):
    domain = serialized['domain'].strip()
    nameserver1 = serialized['nameserver1'].strip()
    nameserver2 = serialized['nameserver2'].strip()
    if not nameserver1 and nameserver2:
        swap = nameserver2
        nameserver2 = nameserver1
        nameserver1 = swap
    return ResolvCfg(domain, nameserver1, nameserver2)

