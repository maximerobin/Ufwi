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
from PyQt4.QtGui import QDialog

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.tools import QListWidget_currentText
from ufwi_rulesetqt.template_dialog_ui import Ui_Dialog

class TemplateDialog(QDialog):
    def __init__(self, window):
        QDialog.__init__(self, window)
        self.window = window
        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.connectSlots()
        self.ruleset = window.ruleset

    def connectSlots(self):
        self.connect(self.ui.add_template, SIGNAL("clicked()"), self.addTemplate)
        self.connect(self.ui.remove_template, SIGNAL("clicked()"), self.removeTemplate)

#    def refresh(self):
#        ui.add_template_button.setEnabled(len(templates) == 0)
#        ui.remove_template_button.setEnabled(len(templates) == 1)

    def fillTemplates(self):
        if self.ruleset.is_template:
            current_template = self.ruleset.ruleset_name
        else:
            current_template = None

        widget = self.ui.ruleset_templates
        ruleset_templates = [template['name']
            for template in self.ruleset.templates.values()
            if template['direct']]
        widget.clear()
        widget.addItems(ruleset_templates)

        ruleset_templates = set(template['name']
            for template in self.ruleset.templates.values())
        templates = []
        for name, timestamp in self.ruleset('rulesetList', 'template'):
            if name in ruleset_templates:
                continue
            if name == current_template:
                continue
            templates.append(name)
        templates.sort()
        widget = self.ui.available_templates
        widget.clear()
        widget.addItems(templates)

    def exec_(self):
        self.fillTemplates()
        return QDialog.exec_(self)

    def addTemplate(self):
        name = QListWidget_currentText(self.ui.available_templates)
        try:
            updates = self.ruleset("addTemplate", name)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.accept()
        self.window.refresh(updates)
        self.window.setStatus(tr("Template %s added.") % name)

    def removeTemplate(self):
        name = QListWidget_currentText(self.ui.ruleset_templates)
        try:
            updates = self.ruleset("removeTemplate", name)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.accept()
        self.window.refresh(updates)
        self.window.setStatus(tr("Template %s deleted.") % name)

