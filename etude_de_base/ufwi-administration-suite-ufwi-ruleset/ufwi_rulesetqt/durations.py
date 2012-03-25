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

from ufwi_rulesetqt.create_duration import CreateDuration
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object

class Duration(Object):
    def getText(self):
        seconds = self['seconds']
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        days, hours = divmod(hours, 24)
        text = "%s:%02u:%02u" % (hours, minutes, seconds)
        if days:
            text = tr("%s day(s)", "", days) % days + u" " + text
        return text

    def getToolTip(self):
        return tr("Duration: %s") % self.getText()

    def getIcon(self):
        return ":/icons-32/chrono.png"

    def getBackground(self):
        return ":/backgrounds/periodicity.png"

    def createInformation(self):
        options = [
            (tr('Identifier'), self['id']),
            (tr('Duration'), self.getText()),
            (tr('References'), self.createReferencesHTML()),
        ]
        return tr('Duration'), options

class Durations(Library):
    REFRESH_DOMAIN = u"durations"
    URL_FORMAT = u"duration:%s"
    RULESET_ATTRIBUTE = "durations"
    CHILD_CLASS = Duration

    def __init__(self, window):
        Library.__init__(self, window, "duration")
        self.dialog = CreateDuration(window)
        self.setupWindow()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.duration_list)
        self.setMenu(LibraryMenu(self,
            tr("New duration"),
            tr("Edit this duration"),
            tr("Delete this duration")))

    def getTreeKey(self, duration):
        return u"duration"

