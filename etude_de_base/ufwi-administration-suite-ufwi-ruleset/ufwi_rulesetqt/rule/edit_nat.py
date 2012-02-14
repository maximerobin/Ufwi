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

from ufwi_ruleset.common.rule import NAT_TRANSLATE, NAT_PREROUTING_ACCEPT, NAT_POSTROUTING_ACCEPT
from ufwi_rulesetqt.rule.edit import EditRule
from ufwi_rulesetqt.rule.nat import Nat, NAT_TYPE_LABELS

TYPES = [NAT_TRANSLATE, NAT_PREROUTING_ACCEPT, NAT_POSTROUTING_ACCEPT]
TYPE_INDEX = dict((type, index) for index, type in enumerate(TYPES))

class EditNAT(EditRule):
    OBJECT_CLASS = Nat
    def __init__(self, window, rules):
        EditRule.__init__(self, window, rules, "nat")
        ui = self.ui
        self.setupEdit(
            ui.nat_enabled,
            ui.nat_mandatory,
            ui.nat_comment)

        for widget in ['nated_sources', 'nated_destinations', 'nated_filters']:
            editor = self.object_list[widget]
            editor.accept_groups = False
            window.connect(editor.widget, SIGNAL('objectDrop()'), self.switchNatEnabled)
            window.connect(editor.menu.delete_action, SIGNAL('triggered()'), self.switchNatEnabled)

        if self.window.compatibility.nat_support_accept:
            self.type = self.ui.nat_type
            self.type.clear()
            labels = [NAT_TYPE_LABELS[type] for type in TYPES]
            self.type.addItems(labels)
            window.connect(
                ui.nat_type,
                SIGNAL("currentIndexChanged(int)"),
                self.changeDecision)
        else:
            self.ui.nat_type.hide()
            self.type = None

        self.connectOkButton(self.getWidget('save_button'))

    def changeDecision(self, index):
        self.switchNatEnabled()

    def save(self):
        attr = {
            'comment': unicode(self.comment.toPlainText()),
        }
        if self.type:
            type_index = self.type.currentIndex()
            attr['type'] = TYPES[type_index]

        for lst_name in self.OBJECT_CLASS.OBJECT_ATTR.keys():
            attr[lst_name] = self.object_list[lst_name].getAll()

        self._save(attr)

    def startEdit(self):
        self.switchNatEnabled()
        EditRule.startEdit(self)

    def _create(self, rules):
        title = tr("Create a new NAT rule")
        self.groupbox.setTitle(title)
        if self.type:
            self.type.setCurrentIndex(TYPE_INDEX[NAT_TRANSLATE])

    def _editRule(self, nat):
        title = unicode(nat)
        self.groupbox.setTitle(title)
        if self.type:
            type_index = TYPE_INDEX[nat['type']]
            self.type.setCurrentIndex(type_index)

    def switchNatEnabled(self):
        if self.type:
            enabled = (self.ui.nat_type.currentIndex() == TYPE_INDEX[NAT_TRANSLATE])
        else:
            enabled = True

        if enabled:
            accept_src = self.object_list['nated_destinations'].widget.count() == 0 and self.object_list['nated_filters'].widget.count() == 0
        else:
            accept_src = False
        self.object_list['nated_sources'].setEnabled(accept_src)

        if enabled:
            accept_dst = self.object_list['nated_sources'].widget.count() == 0
        else:
            accept_dst = False
        self.object_list['nated_destinations'].setEnabled(accept_dst)
        self.object_list['nated_filters'].setEnabled(accept_dst)

