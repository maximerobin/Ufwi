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

from ufwi_rpcd.common.xml_etree import etree
from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.attribute import Integer
from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.error import RulesetError

class Seconds(Integer):
    def __init__(self, optional=False):
        Integer.__init__(self, min=1)

class Duration(Object):
    XML_TAG = u"duration"
    UPDATE_DOMAIN = u'durations'
    seconds = Seconds()

    def __init__(self, durations, values, loader_context=None):
        self.ruleset = durations.ruleset
        Object.__init__(self, values, loader_context)

    def __unicode__(self):
        return tr('The duration %s') % self.formatID()

    def exportTimeRangeXML(self, parent):
        # Export to periods.xml
        etree.SubElement(parent, "duration",
            length=unicode(self.seconds))

class Durations(Library):
    NAME = 'durations'
    ACL_ATTRIBUTE = 'durations'
    XML_TAG = u"durations"
    CHILD_CLASSES = (Duration,)

    def createGroup(self, attr):
        raise RulesetError(
            tr("It is not possible to create a group of durations!"))

