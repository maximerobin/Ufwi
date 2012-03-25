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

from ufwi_rulesetqt.dialog import RulesetDialog
from ufwi_rulesetqt.move_rule_ui import Ui_Dialog

class MoveRuleDialog(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.ruleset = window.ruleset
        self.rule_id = None
        self.rule_order = None

    def moveRule(self, rule_type, rule):
        self.rule_type = rule_type
        self.rule_id = rule['id']
        self.label.setText(tr("Move %s to line:") % unicode(rule))
        chain = rule.getChain()
        first = chain.getFirstEditableOrder()
        self.rule_order = rule.getOrder()
        last = len(chain) - 1
        self.spinBox.setMinimum(1 + first)
        self.spinBox.setMaximum(1 + last)
        self.spinBox.setValue(1 + self.rule_order)
        self.execLoop()

    def save(self):
        order = self.spinBox.value() - 1
        if self.rule_order == order:
            # No change: do nothing
            return True
        try:
            updates = self.ruleset('moveRule', self.rule_type, self.rule_id, order)
        except Exception, err:
            self.window.exception(err)
            return False
        self.window.refresh(updates)
        return True


