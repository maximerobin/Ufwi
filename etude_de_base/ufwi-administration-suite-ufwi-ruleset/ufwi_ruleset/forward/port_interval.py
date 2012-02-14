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

from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.attribute import Attribute

PORT_MIN = 1
PORT_MAX = 65535

class PortIntervalObject:
    def __init__(self, value):
        if isinstance(value, (str, unicode)):
            if ":" in value:
                value = value.split(":", 1)
                first = int(value[0])
                last = int(value[1])
            else:
                first = int(value)
                last = first
        else:
            first = int(value)
            last = first
        self.first = first
        self.last = last
        if (first < PORT_MIN) or (PORT_MAX < last) or (last < first):
            raise RulesetError(tr("Invalid port interval: %s"), repr(self))

    def __unicode__(self):
        if self.first != self.last:
            return u"%s:%s" % (self.first, self.last)
        else:
            return unicode(self.first)
    __str__ = __unicode__

    def __repr__(self):
        return "<PortInterval %s>" % str(self)

    def match(self, other):
        return (self.first <= other.first) and (other.last <= self.last)

class PortInterval(Attribute):
    type = PortIntervalObject
    xmlrpc = unicode

    def getter(self, protocol, name, text):
        if not text:
            return None
        port = PortIntervalObject(text)
        if (port.first == PORT_MIN) and (port.last == PORT_MAX):
            return None
        return port

