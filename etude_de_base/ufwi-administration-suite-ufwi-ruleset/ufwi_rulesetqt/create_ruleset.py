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
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common.multisite import MULTISITE_SLAVE

from ufwi_rulesetqt.create_ruleset_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog
from ufwi_rulesetqt.tools import formatWarnings

class CreateRuleset(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.connect(self.base_checkbox,
            SIGNAL("toggled(bool)"),
            self.toggleBase)
        self.toggleBase(self.base_checkbox.isChecked())

    def toggleBase(self, enabled):
        self.base_combo.setEnabled(enabled)

    def run(self):
        if self.window.multisite_type == MULTISITE_SLAVE:
            return self.create('ruleset', '')

        # Read templates
        try:
            templates = self.window.ruleset('rulesetList', 'template')
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        templates = [name for name, timestamp in templates]
        templates.sort()

        self.ruleset_radio.setChecked(True)
        self.base_checkbox.setChecked(False)
        self.base_combo.setEnabled(False)
        self.base_combo.clear()
        self.base_combo.addItems(templates)

        self.execLoop()

    def create(self, filetype, base_template):
        while True:
            try:
                self.window.config.getConfig()
                result = self.window.ruleset.create(filetype, base_template)
            except RpcdError, err:
                if err.type == 'AlreadyAcquired':
                    try:
                        self.window.sessionDialog()
                    except RpcdError, sess_dial_err:
                        self.window.exception(sess_dial_err)
                    else:
                        continue
                self.window.reset()
                self.window.ufwi_rpcdError(err)
                return False
            break
        self.window.reset(result['undoState'])
        message = tr("New rule set created.")
        message = formatWarnings(message, result.get('warnings'))
        self.window.information(message, escape=False)
        return True

    def save(self):
        if not self.window.rulesetClose(refresh=True):
            return
        if self.template_radio.isChecked():
            filetype = "template"
        else:
            filetype = "ruleset"
        use_base = self.base_checkbox.isChecked()
        if use_base:
            base = unicode(self.base_combo.currentText())
        else:
            base = u''
        return self.create(filetype, base)

