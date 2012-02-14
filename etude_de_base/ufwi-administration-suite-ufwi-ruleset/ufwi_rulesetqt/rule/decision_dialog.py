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
from ufwi_rpcc_qt.tools import QComboBox_setCurrentText

from ufwi_rulesetqt.dialog import RulesetDialog
from ufwi_rulesetqt.default_decision_ui import Ui_Dialog
from ufwi_rulesetqt.rule.tools import fillDecisionCombo

class DecisionDialog(RulesetDialog, Ui_Dialog):
    def __init__(self, window, controler, chain):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.controler = controler
        self.default_decisions = chain.default_decisions
        self.chain_key = chain.key

        decision, use_log = self.default_decisions.get(self.chain_key)
        fillDecisionCombo(self.decision_combo)
        self.header_label.setText(tr("Change the default decision of the %s chain:") % unicode(chain))
        QComboBox_setCurrentText(self.decision_combo, decision)
        self.log_checkbox.setChecked(use_log)

    def save(self):
        decision = unicode(self.decision_combo.currentText())
        log = self.log_checkbox.isChecked()
        self.default_decisions.set(self.chain_key, decision, log)
        try:
            updates = self.default_decisions.save()
        except Exception, err:
            self.window.exception(err)
            return False
        self.window.refresh(updates)
        return True


