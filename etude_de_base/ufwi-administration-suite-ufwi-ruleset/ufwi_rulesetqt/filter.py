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

from unicodedata import normalize as normalize_unicode
from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS
from ufwi_rulesetqt.objects import Group

def normalizeTextPattern(text):
    text = unicode(text)
    # Convert to lower case
    text = text.lower()
    # Remove diacritics
    text = u''.join(normalize_unicode("NFKD", char)[0]
        for char in text)
    return text

class Filter:
    def __init__(self):
        self.pattern = None

    def normalize(self, text):
        return normalizeTextPattern(text)

    def setText(self, pattern):
        if not pattern:
            pattern = None
        else:
            pattern = self.normalize(pattern)
        changed = (self.pattern != pattern)
        self.pattern = pattern
        return changed

    def match(self, object):
        if self.pattern is None:
            return True
        text = self.normalize(object['id'])
        if self.pattern in text:
            return True
        if isinstance(object, Group):
            return any(self.match(item) for item in object.getObjectList())
        return False

class AddressTypeFilter(Filter):
    def __init__(self):
        Filter.__init__(self)
        self.address_type = None
        self.setIPv6(False)

    def setIPv6(self, use_ipv6):
        if use_ipv6:
            address_type = IPV6_ADDRESS
        else:
            address_type = IPV4_ADDRESS
        changed = (self.address_type != address_type)
        self.address_type = address_type
        return changed

    def matchAddressType(self, object):
        return (self.address_type in object['address_types'])

def _splitgroupname(fullname):
    parsed = fullname.split("@", 1)
    if len(parsed) == 2:
        return parsed
    else:
        return parsed[0], ""

def unescapegroupname(fullname):
    grouppart, domainpart = _splitgroupname(fullname)

    if grouppart[-1] != "#":
        return fullname

    return "%s@%s" % (grouppart.replace("#", ",") , domainpart)

