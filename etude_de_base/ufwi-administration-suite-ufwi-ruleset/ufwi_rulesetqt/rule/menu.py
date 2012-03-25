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
from ufwi_rulesetqt.rule.actions import RuleActions
from ufwi_rulesetqt.menu import Menu

class RuleMenu(Menu):
    def __init__(self, rules):
        Menu.__init__(self)
        window = rules.window
        self.debug = window.debug
        self.create_before = self.add(":/icons/add.png",
            tr("Create before"), self.createAclBefore)
        self.create_after = self.add(":/icons/add.png",
            tr("Create after"), self.createAclAfter)
        self.edit = self.add(":/icons/edit.png",
            tr("Edit"), self.editAcl)
        self.up = self.add(":/icons/up.png",
            tr("Move up"), self.moveUp)
        if window.compatibility.has_move_rule:
            self.move_at = self.add(":/icons/updown.png",
                tr("Move to line..."), self.moveAt)
        else:
            self.move_at = None
        self.down = self.add(":/icons/down.png",
            tr("Move down"), self.moveDown)
        self.clone = self.add(":/icons/copy.png",
            tr("Clone"), self.cloneAcl)
        self.delete = self.add(":/icons/delete.png",
            tr("Delete"), self.deleteAcl)
        self.iptables = self.add(":/icons/apply_rules.png",
            tr("Iptables rules"), self.iptablesRules)
        self.ldap = self.add(":/icons/apply_rules.png",
            tr("LDAP rules"), self.ldapRules)
        self.rules = rules
        self.rule_id = None
        self.identifiers = None

    def display(self, event, identifiers, is_nat):
        self.identifiers = tuple(identifiers)
        if self.identifiers:
            self.rule_id = self.identifiers[0]
        else:
            self.rule_id = None
        actions = RuleActions(self.rules, self.identifiers)
        self.create_before.setEnabled(actions.create_before)
        self.create_after.setEnabled(actions.create_after)
        self.edit.setEnabled(actions.edit)
        self.up.setEnabled(actions.move_up)
        self.down.setEnabled(actions.move_down)
        if self.move_at:
            self.move_at.setEnabled(actions.move_at)
        self.clone.setEnabled(actions.clone)
        self.delete.setEnabled(actions.delete)
        if self.debug:
            self.iptables.setEnabled(actions.iptables)
            self.ldap.setEnabled(actions.ldap)
        self.exec_(event.globalPos())

    def cloneAcl(self):
        self.rules.cloneAcl(self.rule_id)

    def deleteAcl(self):
        self.rules.delete(self.identifiers)

    def _create(self, position_delta):
        if self.rule_id is not None:
            rule = self.rules[self.rule_id]
            position = rule.getOrder() + position_delta
        else:
            position = None
        self.rules.create(position)

    def createAclBefore(self):
        self._create(0)

    def createAclAfter(self):
        self._create(1)

    def editAcl(self):
        self.rules.edit(self.rule_id)

    def moveUp(self):
        self.rules.moveUp(self.rule_id)

    def moveDown(self):
        self.rules.moveDown(self.rule_id)

    def moveAt(self):
        self.rules.moveAt(self.rule_id)

    def iptablesRules(self):
        self.rules.iptablesRules(self.identifiers)

    def ldapRules(self):
        self.rules.ldapRules(self.identifiers)

