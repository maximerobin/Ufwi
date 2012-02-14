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

from ufwi_rulesetqt.create_application import CreateApplication
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object

class Application(Object):
    def getToolTip(self):
        return tr('"%s" application' % self['path'])

    def getIcon(self):
        return ":/icons-32/application.png"

    def getBackground(self):
        return ":/backgrounds/application"

    def createInformation(self):
        title = tr('Application')
        options = [
            (tr('Identifier'), self['id']),
            (tr('Path'), self['path']),
            (tr('References'), self.createReferencesHTML()),
        ]
        return (title, options)

class Applications(Library):
    REFRESH_DOMAIN = u"applications"
    URL_FORMAT = u"application:%s"
    RULESET_ATTRIBUTE = "applications"
    CHILD_CLASS = Application

    def __init__(self, window):
        Library.__init__(self, window, "app")
        self.dialog = CreateApplication(window)
        self.setupWindow()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.app_list)
        self.setMenu(LibraryMenu(self,
            tr("New application"),
            tr("Edit this application"),
            tr("Delete this application")))

    def getTreeKey(self, app):
        if "\\" in app['path']:
            return u"win"
        else:
            return u"unix"

    def createTreeKeyLabel(self, osname):
        if osname == u"win":
            return tr("Windows")
        else:
            return tr("UNIX/BSD")

