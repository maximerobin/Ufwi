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

from ufwi_ruleset.forward.attribute import Unicode
from ufwi_ruleset.forward.object import Object, REGEX_ID
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.error import RulesetError
from ufwi_rpcd.backend import tr

class OSAttr(Unicode):
    def getter(self, os, name, value):
        value = unicode(value)
        if not value:
            return None
        if not REGEX_ID.match(value):
            raise RulesetError(
                tr("Invalid value for the %s operating system field: %s"),
                name, repr(value))
        return value

class OperatingSystem(Object):
    XML_TAG = u"operating_system"
    UPDATE_DOMAIN = u'operating_systems'
    name = OSAttr()
    version = OSAttr(optional=True)
    release = OSAttr(optional=True)

    def __init__(self, operating_systems, values, loader_context=None):
        self.ruleset = operating_systems.ruleset
        Object.__init__(self, values, loader_context)

    def __unicode__(self):
        return tr('The operating system %s') % self.formatID()

class OperatingSystems(Library):
    NAME = 'operating_systems'
    ACL_ATTRIBUTE = 'operating_systems'
    XML_TAG = u"operating_systems"
    CHILD_CLASSES = (OperatingSystem,)

