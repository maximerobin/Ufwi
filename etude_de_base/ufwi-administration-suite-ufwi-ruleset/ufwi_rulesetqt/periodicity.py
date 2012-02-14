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

from ufwi_rpcd.common import tr

from ufwi_rulesetqt.create_periodicity import CreatePeriodicity
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object

class Periodicity(Object):
    def formatFrom(self, time):
        return tr('%sh00') % time

    def formatTo(self, time):
        return tr('%sh59') % (time - 1)

    def dayName(self, day):
        day = int(day)
        days = [tr("Monday"), tr("Tuesday"), tr("Wednesday"), tr("Thursday"), tr("Friday"), tr("Saturday"), tr("Sunday")]
        return days[day]

    def getToolTip(self):
        start = u"%s %s" % (self.dayName(self['day_from']), self.formatFrom(self['hour_from']))
        stop = u"%s %s" % (self.dayName(self['day_to']), self.formatTo(self['hour_to']))
        return tr("Time Criterion: %s - %s") % (start, stop)

    def getIcon(self):
        return ":/icons-32/chrono.png"

    def getBackground(self):
        return ":/backgrounds/periodicity"

    def createInformation(self):
        title = tr('Time Criterion')
        options = [
            (tr('Identifier'), self['id']),
            (tr('from'),    self.dayName(self['day_from'])),
            (tr('to'),      self.dayName(self['day_to'])),
            (tr('from'),    self.formatFrom(self['hour_from'])),
            (tr('to'),      self.formatTo(self['hour_to'])),
            (tr('References'), self.createReferencesHTML()),
        ]
        return (title, options)

class Periodicities(Library):
    REFRESH_DOMAIN = u"periodicities"
    URL_FORMAT = u"periodicities:%s"
    RULESET_ATTRIBUTE = "periodicities"
    CHILD_CLASS = Periodicity

    def __init__(self, window):
        Library.__init__(self, window, "period")
        self.dialog = CreatePeriodicity(window)
        self.setupWindow()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.period_list)
        self.setMenu(LibraryMenu(self,
            tr("New time criterion"),
            tr("Edit this time criterion"),
            tr("Delete this time criterion")))

    def getTreeKey(self, user_group):
        return u"periodicity"

    def createTreeKeyLabel(self, key):
        return tr("Time Criterion")

