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


from __future__ import with_statement

from os.path import exists

from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import SLOT
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QDialogButtonBox

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.input_widgets import FileSelector

class UploadDialog(QDialog):
    def __init__(
        self,
        selector_label=tr("File to upload"),
        filter=tr("Any file (*)"),
        parent=None
        ):
        QDialog.__init__(self, parent)
        form = QFormLayout(self)
        self.file_selector = FileSelector(
            filter=filter
            )
        form.addRow(selector_label, self.file_selector)

        self.message_area = MessageArea()
        form.addRow(self.message_area)
        self.message_area.hide()

        button_box = QDialogButtonBox(
            QDialogButtonBox.Open | QDialogButtonBox.Cancel,
            Qt.Horizontal,
            self
        )
        form.addRow(button_box)

        self.connect(button_box, SIGNAL('accepted()'), SLOT('accept()'));
        self.connect(button_box, SIGNAL('rejected()'), SLOT('reject()'))
        self.connect(self.file_selector.edit, SIGNAL('textChanged(QString)'), self.message_area.hide)

    def accept(self):
        filename = unicode(self.file_selector.edit.text())
        if not exists(filename):
            self.message_area.show()
            self.message_area.setMessage(
            tr("Error"),
            tr("File not found, or cannot read directory of: '") + filename + "'"
            )
            return

        try:
            with open(filename, 'r'):
                pass
        except Exception:
            self.message_area.show()
            self.message_area.setMessage(
            tr("Error"),
            tr("Unable to read file: '") + filename + "'"
            )
            return

        #It's all Ok.
        self.filename = filename
        self.hide()
        self.setResult(QDialog.Accepted)

