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

from ufwi_rulesetqt.create_os import CreateOS
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object

class OperatingSystem(Object):
    ICONS = {
        u"Linux":   ":/icons-32/linux",
        u"Darwin":  ":/icons-32/apple",
        u"Windows": ":/icons-32/windows",
    }
    BACKGROUNDS = {
        u"Linux":   ":/backgrounds/linux",
        u"Darwin":  ":/backgrounds/apple",
        u"Windows": ":/backgrounds/windows",
    }
    DEFAULT_ICON = ":/icons-32/application.png"
    DEFAULT_BACKGROUND = ":/backgrounds/computer"

    def getToolTip(self):
        text = tr('Operating system "%s"' % self['name'])
        if 'version' in self:
            text += u' (%s)' % self['version']
        if 'release' in self:
            text += u' (%s)' % self['release']
        return text

    def getIcon(self):
        name = self['name'].title()
        return self.ICONS.get(name, self.DEFAULT_ICON)

    def getBackground(self):
        name = self['name'].title()
        return self.BACKGROUNDS.get(name, self.DEFAULT_BACKGROUND)

    def createInformation(self):
        title = tr('Operating System')
        options = [
            (tr('Identifier'), self['id']),
            (tr('Name'), self['name']),
        ]
        if "version" in self:
            options.append((tr('Version'), self['version']))
        if "release" in self:
            options.append((tr('Release'), self['release']))
        options.append((tr('References'), self.createReferencesHTML()))
        return title, options

class OperatingSystems(Library):
    REFRESH_DOMAIN = u"operating_systems"
    URL_FORMAT = u"operating_system:%s"
    RULESET_ATTRIBUTE = "operating_systems"
    CHILD_CLASS = OperatingSystem

    def __init__(self, window):
        Library.__init__(self, window, "os")
        self.dialog = CreateOS(window)
        self.setupWindow()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.os_list)
        self.setMenu(LibraryMenu(self,
            tr("New operating system"),
            tr("Edit this operating system"),
            tr("Delete this operating system")))

    def getTreeKey(self, os):
        return os['name'].title()

