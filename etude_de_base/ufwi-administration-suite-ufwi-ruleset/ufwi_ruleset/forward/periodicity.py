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

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.attribute import Integer
from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.library import Library

class WeekDay(Integer):
    def __init__(self):
        Integer.__init__(self, min=0, max=6)

class Periodicity(Object):
    XML_TAG = u"periodicity"
    UPDATE_DOMAIN = u'periodicities'
    day_from = WeekDay()
    day_to = WeekDay()
    hour_from = Integer(min=0, max=23)
    hour_to = Integer(min=1, max=24)

    def __init__(self, periodicities, values, loader_context=None):
        self.ruleset = periodicities.ruleset
        Object.__init__(self, values, loader_context)

    def checkConsistency(self, loader_context=None):
        if self.day_to < self.day_from:
            raise RulesetError(
                tr("Invalid day range: %s..%s"),
                self.day_from, self.day_to)
        if self.hour_to <= self.hour_from:
            raise RulesetError(
                tr("Invalid hour range: %sh00..%sh59"),
                self.hour_from, (self.hour_to - 1))

    def __unicode__(self):
        return tr('The %s time criterion') % self.formatID()

    def _exportDay(self, day):
        # Convert Ruleset day number to NuFW day number:
        #  - ufwi_ruleset: monday=0, ..., saturday=5, sunday=6
        #  - nufw: sunday=0, monday=1, ..., saturday=6
        day = (day + 1) % 7
        return unicode(day)

    def exportTimeRangeXML(self, parent):
        # Export to periods.xml
        etree.SubElement(parent, "days",
            start=self._exportDay(self.day_from),
            end=self._exportDay(self.day_to))
        if self.hour_from != 0 or self.hour_to != 24:
            etree.SubElement(parent, "hours",
                start=unicode(self.hour_from),
                end=unicode(self.hour_to))

class Periodicities(Library):
    NAME = 'periodicities'
    ACL_ATTRIBUTE = 'periodicities'
    XML_TAG = u"periodicities"
    CHILD_CLASSES = (Periodicity,)

    def createGroup(self, attr):
        raise RulesetError(
            tr("Impossible to create a group of time criteria!"))

