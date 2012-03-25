
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

from PyQt4.QtCore import Qt, QRegExp, SIGNAL
from PyQt4.QtGui import QValidator, QComboBox

INT32_MIN = -2**31
INT32_MAX = 2**31 - 1

NON_EMPTY_REGEXP = QRegExp(".+")

def acceptableInput(widget):
    if isinstance(widget, QComboBox):
        text = widget.currentText()
    else:
        try:
            return widget.acceptableInput()
        except AttributeError:
            # WTF?
            pass
        text = widget.text()
    validator = widget.validator()
    state, pos = validator.validate(text, 0)
    return (state == QValidator.Acceptable)

class ValidatorWrapper:
    def __init__(self, dialog, widget):
        self.dialog = dialog
        self.widget = widget
        self.orig_set_enabled = widget.setEnabled
        widget.connect(widget, SIGNAL("textChanged(const QString&)"), self.textChanged)
        widget.setEnabled = self.setEnabled

    def reset(self):
        widget = self.widget
        widget.setValidator(None)
        widget.disconnect(widget, SIGNAL("textChanged(const QString&)"), self.textChanged)
        widget.setEnabled = self.orig_set_enabled

    def textChanged(self, text):
        self.dialog.updateWidget(self.widget)

    def setEnabled(self, enabled):
        self.dialog.widgetSetEnabled(self.widget, enabled)

class QComboBoxValidator(QValidator):
    """
    Validate the input of an editable QComboBox: only accept strings already
    defined in the model.
    """
    def __init__(self, widget):
        QValidator.__init__(self, widget)
        self.model = widget.model()

    def validate(self, input, pos):
        # FIXME: Don't call findItems() twice?
        items = self.model.findItems(input, Qt.MatchExactly)
        if items:
            return QValidator.Acceptable, pos
        items = self.model.findItems(input, Qt.MatchStartsWith)
        if items:
            return QValidator.Intermediate, pos
        else:
            return QValidator.Invalid, pos

