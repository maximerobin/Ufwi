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

from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.validate_widgets import ValidateWidgets

class EditRule(ValidateWidgets):
    def __init__(self, window, rules, widget_prefix):
        ValidateWidgets.__init__(self)
        self.window = window
        self.ui = window
        self.ruleset = window.ruleset
        self.rule = None
        self.rules = rules
        self.position = None
        self.widget_prefix = widget_prefix
        self.object_list = {}
        self.enabled = None
        self.old_fullscreen = None
        self.setupWindow()

        # Create the EditList for each list of objects
        for lst_name in self.OBJECT_CLASS.OBJECT_ATTR.iterkeys():
            widget = self.getWidget(lst_name)
            libraries = self.getLibrary(lst_name)
            editor_builder = self.OBJECT_CLASS.OBJECT_ATTR[lst_name]['editor']
            editor = editor_builder(self, widget, False, self.object_list, True, *libraries)
            if lst_name in self.OBJECT_CLASS.MANDATORY_ATTR:
                # Mandatory attribute
                editor.use_validator = True
                widget.acceptableInput = editor.acceptableInput
                self.addInputWidget(widget)
            self.object_list[lst_name] = editor

        self.highlight_list = self.object_list.copy()
        self.groupbox = self.getWidget("groupbox")

    def getLibrary(self, lst_name):
        lst_type = self.OBJECT_CLASS.OBJECT_ATTR[lst_name]['name']
        library = self.window.object_libraries[lst_type]
        return [library]

    def getWidget(self, name):
        name = self.widget_prefix + '_' + name
        return getattr(self.window, name)

    def setupEdit(self, enabled, mandatory, comment):
        self.enabled = enabled
        self.mandatory = mandatory
        self.comment = comment
        self.comment.setAcceptRichText(False)
        self.comment.setAcceptDrops(False)

    def setupWindow(self):
        window = self.window
        window.connect(self.getWidget('cancel_button'), SIGNAL("clicked()"), self.cancelEdit)

    def startEdit(self):
        self.old_fullscreen = self.window.setFullScreen(False)
        self.window.setEditMode(True)

    def stopEdit(self):
        self.window.setFullScreen(self.old_fullscreen)
        self.window.setEditMode(False)
        self.window.acl_stack.setCurrentIndex(0)

    def cancelEdit(self):
        self.stopEdit()
        if self.rule:
            self.rule.highlight()

    def checkRuleAttributes(self, attr):
        return True

    def _save(self, attr):
        attr['enabled'] = self.enabled.isChecked()
        attr['mandatory'] = self.mandatory.isChecked()
        attr['comment'] = unicode(self.comment.toPlainText())
        if self.position is not None:
            attr['position'] = self.position

        if not self.checkRuleAttributes(attr):
            return
        try:
            if self.rule:
                updates = self.ruleset('ruleChange', self.rules.rule_type, self.rule['id'], attr)
            else:
                updates = self.ruleset('ruleCreate', self.rules.rule_type, attr)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)
        self.stopEdit()

    def _prepareForm(self, rule, position):
        self.rule = rule
        self.position = position
        self.mandatory.setEnabled(self.ruleset.is_template)

    def _create(self, rules):
        pass

    def create(self, rules, position=None):
        self.rules = rules
        self._prepareForm(None, position)
        for lst in self.object_list.values():
            lst.clear()
        self.enabled.setChecked(True)
        self.mandatory.setChecked(True)
        self.comment.setPlainText(u'')
        self._create(rules)
        self.startEdit()

    def highlight(self, key, identifier):
        if key == 'comment':
            self.comment.setFocus()
        else:
            widget = self.highlight_list[key]
            widget.highlight(identifier)

    def _editRule(self, rule):
        pass

    def editRule(self, rules, rule, highlight=None):
        self.rules = rules
        self._prepareForm(rule, None)
        for (lst_name, lst) in self.object_list.items():
            lst.fill(rule[lst_name])
        self.enabled.setChecked(rule['enabled'])
        self.mandatory.setChecked(rule['mandatory'])
        self.comment.setPlainText(rule.get('comment', u''))
        self._editRule(rule)
        if highlight:
            self.highlight(highlight[0], highlight[1])
        self.startEdit()

    @abstractmethod
    def save(self):
        pass

