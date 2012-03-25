#coding: utf-8
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


from PyQt4.QtCore import Qt
from PyQt4.QtCore import QTime
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QPlainTextEdit

class AbstractEditor(QDialog):
    """
    A little short of time for doc:
    see ufwi_conf.client.services.site2site.editor.VPNEditor for an example
    """
    def __init__(self, cfg, parent=None):
        QDialog.__init__(self, parent)
        self._cfg = cfg
        self._setup_ui()
        self._import_data()

    def accept(self):
        if not self._validate():
            return False
        self._report_data()
        QDialog.accept(self)

    def reject(self):
        QDialog.reject(self)

    def _validate(self):
        return True

    def _setup_ui(self):
        raise NotImplementedError()

    def _import_data(self):
        raise NotImplementedError()

    def _report_data(self):
        raise NotImplementedError()

    def _import(self, attr_type, attr):
        """
        Your attribute in self.cfg has the same name as the Qt widget controlling it

        Supported attr_type:
         * 'bool' for booleans
         * 'string' for string, unicode... <--> QString in lineEdit
         * 'time' for time in seconds <--> QTime in timeEdit
        """
        value = getattr(self._cfg, attr)
        control = getattr(self, attr)
        if attr_type == 'bool':
            if value:
                check_state = Qt.Checked
            else:
                check_state = Qt.Unchecked
            control.setChecked(check_state)
        elif attr_type == 'string':
            if isinstance(control, QLineEdit):
                method = control.setText
            elif isinstance(control, QPlainTextEdit):
                method = control.setPlainText
            method(value)
        elif attr_type == 'time':
            time = QTime(0, 0, 0, 0)
            control.setTime(time.addSecs(value))

    def _export(self, attr_type, attr):
        """
        Your attribute in self.cfg has the same name as the Qt widget controlling it

        Supported attr_type:
         * 'bool' for booleans
         * 'string' for string, unicode... <--> QString in lineEdit
         * 'time' for time in seconds <--> QTime in timeEdit
        """
        control = getattr(self, attr)
        if attr_type == 'bool':
            value = control.isChecked()
        elif attr_type == 'string':
            if isinstance(control, QLineEdit):
                method = control.text
            elif isinstance(control, QPlainTextEdit):
                method = control.plainText
            value = unicode(method())
        elif attr_type == 'time':
            value = QTime(0, 0, 0, 0).secsTo(control.time())
        setattr(self._cfg, attr, value)

