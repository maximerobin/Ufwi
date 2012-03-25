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

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QTableWidgetItem, QFrame

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.tools import unsetFlag

from ufwi_ruleset.common.rule import NAT_TRANSLATE
from ufwi_rulesetqt.rule.list import RulesList
from ufwi_rulesetqt.rule.filter import RuleFilter, AttributeFilter
from ufwi_rulesetqt.rule.edit_nat import EditNAT
from ufwi_rulesetqt.rule.attr import AclNetworks, AclFilters, AclComment
from ufwi_rulesetqt.rule.chain import DECISION_COLORS
from ufwi_rulesetqt.nat_wizard import NatWizard
from ufwi_rulesetqt.rule.model import NatRulesModel

ACCEPT_ICON = ":/icons-32/go-next.png"

class NatFilter(RuleFilter):
    def __init__(self, rules):
        RuleFilter.__init__(self, rules,
            tr("Drag & drop networks and protocols here"))
        getLibrary = rules.window.getLibrary
        self.filters.extend((
            AttributeFilter(self,
                getLibrary('resources'),
                'sources', 'destinations',
                'nated_sources', 'nated_destinations'),
            AttributeFilter(self,
                getLibrary('protocols'),
                'filters', 'nated_filters'),
        ))

class NatList(RulesList):
    RULES_STACK_INDEX = 2
    EDIT_STACK_INDEX = 3

    def __init__(self, window):
        edit = EditNAT(window, self)
        model = NatRulesModel(window)
        RulesList.__init__(self, window, model, window.table_nats, "nats", "nat", edit)
        self.filter = NatFilter(self)
        self.window.nat_wizard_button.connect(self.window.nat_wizard_button, SIGNAL('clicked()'), self.showWizard)
        self.table.connect(self.table, SIGNAL('cellClicked(int, int)'), self.setButtonsEnabled)

    def setButtonsEnabled(self, row = -1, col = -1):
        nat_ids = self.currentAcls()
        only_one = (len(nat_ids) == 1)

        self.window.nat_delete_button.setEnabled(only_one)
        self.window.nat_edit_button.setEnabled(only_one)
        self.window.nat_clone_button.setEnabled(only_one)

        move_up = False
        move_down = False
        if only_one:
            nat_id = nat_ids[0]
            nat = self[nat_id]
            index = self.getChain(nat).index(nat)

            if index > 0:
                move_up = True
            if index < len(self.getChain(nat)) - 1:
                move_down = True
        self.window.nat_up_button.setEnabled(move_up)
        self.window.nat_down_button.setEnabled(move_down)

    def showWizard(self):
        NatWizard(self.window)

    def refreshChain(self, all_updates, updates):
        self.model.refresh(all_updates, updates)

    def fillAclRow(self, row, acl):
        rule_id = acl['id']
        sources = AclNetworks(self, rule_id, "sources", acl["sources"], True)
        destinations = AclNetworks(self, rule_id, "destinations", acl["destinations"], False)
        protocols = AclFilters(self, rule_id, "filters", acl["filters"], ACCEPT_ICON)

        if acl.get('type', NAT_TRANSLATE) == NAT_TRANSLATE:
            line = QFrame()
            line.setFrameShape(QFrame.VLine)

            # if an attribute of the acl is not translated, display the original one
            if len(acl["nated_sources"]) != 0:
                nated_sources = AclNetworks(self, rule_id, "nated_sources", acl["nated_sources"], True)
            else:
                nated_sources = AclNetworks(self, rule_id, None, acl["sources"], True)

            if len(acl["nated_filters"]) != 0:
                nated_protocols  = AclFilters(self, rule_id, "nated_filters", acl["nated_filters"], ACCEPT_ICON)
            else:
                nated_protocols  = AclFilters(self, rule_id, None, acl["filters"], ACCEPT_ICON)

            if len(acl["nated_destinations"]) != 0:
                nated_destinations  = AclNetworks(self, rule_id, "nated_destinations", acl["nated_destinations"], False)
            else:
                nated_destinations  = AclNetworks(self, rule_id, None, acl["destinations"], False)
        else:
            line = None
            nated_sources = None
            nated_protocols  = None
            nated_destinations  = None

        comment = AclComment(self, acl)
        widgets = (
            sources,
            protocols,
            destinations,
            line,
            nated_sources,
            nated_protocols,
            nated_destinations,
            comment,
        )
        for column, widget in enumerate(widgets):
            if widget:
                if not acl['enabled']:
                    widget.setEnabled(False)
                if acl['editable']:
                    widget.setStyleSheet(u'font-weight: bold;')
            self.table.setCellWidget(row, column, widget)


    def getColumns(self):
        return [tr("Source"), tr("Protocol"), tr("Destination"), '', tr("Source"), tr("Protocol"), tr("Destination"), tr("Comment")]

    def setReadOnly(self, read_only):
        RulesList.setReadOnly(self, read_only)
        button = self.getButton("wizard")
        if read_only:
            button.hide()
        else:
            button.show()

    def fillHeader(self, row, chain):
        item = chain.createTableWidgetItem()
        self.table.setSpan(row, 0, 1, 3)
        self.table.setItem(row, 0, item)

        item = QTableWidgetItem()
        unsetFlag(item, Qt.ItemIsEditable)
        item.setText(tr("Translated to"))
        item.setTextAlignment(Qt.AlignHCenter)
        item.setBackgroundColor(DECISION_COLORS['ACCEPT'])
        self.table.setSpan(row, 4, 1, 3)
        self.table.setItem(row, 4, item)

