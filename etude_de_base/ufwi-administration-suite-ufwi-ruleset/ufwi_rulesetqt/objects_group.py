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

from PyQt4.QtCore import SIGNAL, QObject
from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.validate_widgets import ValidateWidgets

from ufwi_rulesetqt.rule.edit_list import EditList
from ufwi_rulesetqt.dialog import IDENTIFIER_REGEX

class ObjectsGroupWidget(QObject, ValidateWidgets):
    def __init__(self, window):
        QObject.__init__(self)
        ValidateWidgets.__init__(self)
        self.connectOkButton(window.objgroup_apply_button)
        cancel = window.objgroup_cancel_button
        cancel.connect(cancel, SIGNAL("clicked()"), self.stopEdit)

        self.window = window
        self.identifier = self.window.objgroup_id_text
        self.list = self.window.objgroup_list
        self.current_group = None

        self.setRegExpValidator(self.identifier, IDENTIFIER_REGEX)
        self.edit_list = EditList(self, self.list, True, {}, False, None)
        self.list.acceptableInput = self.edit_list.acceptableInput
        self.addInputWidget(self.list)

        self.edit_list.setDeleteButton(window.objgroup_delete_button)

    def editGroup(self, group_obj, *libraries):
        if self.window.acl_stack.currentIndex() != 0:
            QMessageBox.critical(self.window,
                tr("Can not create a group"),
                tr("You can not create a group while editing a rule. "
                   "Please close the current rule before proceeding."))
            return

        self.edit_list.clear()
        self.edit_list.libraries = libraries
        self.current_group = group_obj

        if group_obj:
            self.edit_list.fill(group_obj.getObjectList())
            self.identifier.setText(group_obj['id'])
        else:
            self.identifier.setText(u'')
        self.updateWidget(self.list)

        self.window.setEditMode(True)
        self.window.acl_stack.setCurrentIndex(2)

    def save(self):
        identifier = unicode(self.identifier.text())
        library = self.edit_list.libraries[0].RULESET_ATTRIBUTE
        is_new = (self.current_group is None)
        if is_new:
            arguments = ('groupCreate', identifier, library, self.edit_list.getAll())
        else:
            attr = {
                'id': identifier,
                'objects': self.edit_list.getAll(),
            }
            fusion = self.window.useFusion()
            arguments = ('objectModify', library,
                self.current_group['id'], attr, fusion)
        try:
            updates = self.window.ruleset(*arguments)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)
        self.stopEdit()

    def stopEdit(self):
        self.window.setEditMode(False)

