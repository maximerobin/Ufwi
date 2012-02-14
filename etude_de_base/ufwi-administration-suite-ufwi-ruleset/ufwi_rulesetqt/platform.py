"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Victor Stinner <vstinner AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

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
from ufwi_rpcc_qt.html import Html, BR

from ufwi_rulesetqt.create_platform import CreatePlatform
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object

class Platform(Object):
    def __init__(self, *args, **kwargs):
        Object.__init__(self, *args, **kwargs)

    def getToolTip(self):
        # TODO
        return ""

    def getIcon(self):
        return ":/icons-32/platform.png"

    def getBackground(self):
        return ":/backgrounds/platform"

    def createInformation(self):
        window = self.library.window
        networks = window.object_libraries['resources']
        protocols = window.object_libraries['protocols']

        title = tr('Platform')
        items = []
        for item in self['items']:
            network = item['network']
            network = networks[network]
            protocol = item['protocol']
            protocol = protocols[protocol]
            html = '(%s, %s)' % (network.createHTML(tooltip=True, icon=False), protocol.createHTML(tooltip=True, icon=False))
            html = Html(html, escape=False)
            items.append(html)
        items = BR.join(items)
        interface = networks[self['interface']]
        options = [
            (tr('Identifier'), self['id']),
            (tr('Interface'), interface.createHTML(tooltip=True)),
            (tr('Items'), items),
            (tr('References'), self.createReferencesHTML()),
        ]
        return (title, options)

class Platforms(Library):
    REFRESH_DOMAIN = u"platforms"
    URL_FORMAT = u"platforms:%s"
    RULESET_ATTRIBUTE = "platforms"
    CHILD_CLASS = Platform

    def __init__(self, window):
        Library.__init__(self, window, "platform")
        self.dialog = CreatePlatform(window)
        self.setupWindow()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.platform_list)
        self.setMenu(LibraryMenu(self,
            tr("New platform"),
            tr("Edit this platform"),
            tr("Delete this platform")))

    def getTreeKey(self, platform):
        return u"platform"

    def createTreeKeyLabel(self, key):
        return tr("Platform")

    def setEditMode(self, edit):
        Library.setEditMode(self, edit)
        self.create_button.setEnabled(not edit)

