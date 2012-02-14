
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

from PyQt4.QtCore import QRegExp, SIGNAL
from PyQt4.QtGui import QIntValidator, QRegExpValidator
from math import log10, ceil
from ufwi_rpcc_qt.colors import COLOR_INVALID
from ufwi_rpcc_qt.validation import (
    acceptableInput, ValidatorWrapper,
    INT32_MIN, INT32_MAX, NON_EMPTY_REGEXP)
from ufwi_rpcd.common.tools import abstractmethod

class ValidateWidgets:
    def __init__(self, accept=None):
        # widget => ValidatorWrapper or None, see addInputWidget()
        self.input_widgets = {}
        self.ok_button = None
        if accept is None:
            accept = self.save
        self._accept = accept

    def acceptableInput(self):
        for widget in self.input_widgets:
            if not widget.isEnabled():
                continue
            if not acceptableInput(widget):
                return False
        return True

    def checkAccept(self):
        if not self.acceptableInput():
            return
        self._accept()

    def connectOkButton(self, button):
        button.connect(button, SIGNAL("clicked()"), self.checkAccept)
        self.ok_button = button

    def updateWidget(self, widget):
        if widget.isEnabled():
            valid = acceptableInput(widget)
        else:
            valid = True
        if valid:
            # Don't use empty string to avoid a strange bug:
            # setStyleSheet(u'') does not always update the style
            style = u';'
        else:
            style = u'.%s { background: %s; }' % (widget.metaObject().className(), COLOR_INVALID)
        widget.setStyleSheet(style)
        if self.ok_button:
            all_valid = valid
            if all_valid:
                all_valid = self.acceptableInput()
            self.ok_button.setEnabled(all_valid)

    def setValidator(self, widget, validator):
        widget.setValidator(validator)
        if widget not in self.input_widgets:
            wrapper = ValidatorWrapper(self, widget)
            self.addInputWidget(widget, wrapper)
        else:
            self.updateWidget(widget)

    def addInputWidget(self, widget, wrapper=None):
        self.input_widgets[widget] = wrapper
        self.updateWidget(widget)

    def resetValidator(self, widget):
        try:
            wrapper = self.input_widgets.pop(widget)
        except KeyError:
            return
        if wrapper:
            wrapper.reset()
        widget.setStyleSheet('')
        acceptable = self.acceptableInput()
        self.ok_button.setEnabled(acceptable)

    def setNonEmptyValidator(self, widget):
        validator = QRegExpValidator(NON_EMPTY_REGEXP, widget)
        self.setValidator(widget, validator)

    def setRegExpValidator(self, widget, regex):
        validator = QRegExpValidator(regex, widget)
        self.setValidator(widget, validator)

    def setIntValidator(self, widget, first, last):
        if (INT32_MIN <= first) and (last <= INT32_MAX):
            validator = QIntValidator(first, last, widget)
            self.setValidator(widget, validator)
        else:
            # Create an approximative regex matching the integer
            # range first..last
            # eg. 0..100 => [0-9]{1,3}
            nb_digits = 1
            if first:
                nb_digits = max(log10(abs(first)), nb_digits)
            if last:
                nb_digits = max(log10(abs(last)), nb_digits)
            nb_digits = int(ceil(nb_digits))
            regex = "[0-9]{1,%s}" % nb_digits
            if (first < 0) or (last < 0):
                regex = "-" + regex
            self.setRegExpValidator(widget, QRegExp(regex))

    def widgetSetEnabled(self, widget, enabled):
        cls = widget.__class__
        cls.setEnabled(widget, enabled)
        self.updateWidget(widget)

    #--- abstract methods ---------------

    @abstractmethod
    def save(self):
        pass

