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

from PyQt4.QtCore import SIGNAL

from ufwi_rpcd.common.multisite import MULTISITE_MASTER, MULTISITE_SLAVE

from ufwi_rulesetqt.generic_links import GenericLinksDialog
from ufwi_rulesetqt.template_dialog import TemplateDialog

class Template:
    def __init__(self, window):
        self.window = window
        self.ruleset = window.ruleset
        self.generic_links = GenericLinksDialog(self.window, self.saveGenericLinks)
        self.connectSlots()
        self.dialog = TemplateDialog(window)

    def connectSlots(self):
        window = self.window
        ui = window.ui
        if ui.multisite_type != MULTISITE_SLAVE:
            window.connect(ui.action_manage_templates, SIGNAL("triggered()"), self.manageTemplates)
        window.connect(ui.action_generic_links, SIGNAL('triggered()'), self.editGenericLinks)

    def manageTemplates(self):
        self.dialog.exec_()

    def refresh(self, all_updates, updates):
        self.ruleset.readAttributes()

    def display(self, updates, highlight=False):
        pass

    def editGenericLinks(self):
        ui = self.window
        if ui.multisite_type == MULTISITE_MASTER and ui.eas_window is not None and 'ew4_multisite' in ui.eas_window.apps:
            multisite = ui.eas_window.apps['ew4_multisite']
            multisite.setupGenericLinks()
        else:
            links = self.ruleset('genericLinksGet')
            self.generic_links.modify(links)

    def saveGenericLinks(self):
        try:
            links = self.generic_links.getLinks()
            updates = self.ruleset('genericLinksSet', dict(links))
        except Exception, err:
            self.window.exception(err)
            return False
        self.window.refresh(updates)
        return True

