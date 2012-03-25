
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

from PyQt4.QtCore import SIGNAL, Qt, QDateTime, QDate
from PyQt4.QtGui import QLabel, QComboBox, QCheckBox, QWidget, QProgressBar, QPalette, QVBoxLayout, QFrame, QColor, QPushButton, QSizePolicy
from ufwi_rpcd.common import tr

class Cell():
    def __init__(self):
        return
    def refresh(self):
        return

class EdwBlankCell(QWidget, Cell):
    def __init__(self):
        QWidget.__init__(self)

    def setPalette(self, palette):
        self.setAutoFillBackground(True)
        QWidget.setPalette(self, palette)

class EdwCell(QLabel, Cell):
    def __init__(self, string, image = None):
        string = unicode(string)
        if image:
            QLabel.__init__(self,'''
            <table>
            <td><img src="%s" valign="middle"/></td>
            <td valign="middle">%s</td>
            </table>''' % (image, string))
        else:
            QLabel.__init__(self, string)

    def mousePressEvent(self, event):
        event.ignore()

    def setPalette(self, palette):
        self.setAutoFillBackground(True)
        QLabel.setPalette(self, palette)

class EdwStatusCell(EdwCell):
    def __init__(self, name, status = None):
        image = self.DEFAULT_ICON
        if status in self.STATUS_TO_ICON:
            image = self.STATUS_TO_ICON[status]
        EdwCell.__init__(self, name, image)

class EdwCheckBoxCell(QFrame, Cell):
    def __init__(self, initial_state, callback):
        QFrame.__init__(self)
        Cell.__init__(self)
        layout = QVBoxLayout()
        self.checkbox = QCheckBox(self)
        self.setContentsMargins(0, 0, 0, 0)
        self.setAutoFillBackground(True)
        self.callback = None

        layout.addWidget(self.checkbox)
        self.setLayout(layout)

        self.state = False
        self.connect(self.checkbox, SIGNAL('clicked(bool)'), self.setState)

        self.setState(initial_state)
        self.callback = callback

    def setState(self, state):
        self.state = state
        if self.callback:
            self.callback(state)

    def getState(self):
        return self.state

    def refresh(self):
        if self.state:
            self.checkbox.setCheckState(Qt.Checked)
        else:
            self.checkbox.setCheckState(Qt.Unchecked)

    def setPalette(self, palette):
        QFrame.setPalette(self, palette)
        palette = QPalette(palette)
        palette.setColor(QPalette.Window, palette.color(QPalette.Base))
        palette.setColor(QPalette.Background, palette.color(QPalette.Base))
        palette.setColor(QPalette.Foreground, palette.color(QPalette.Base))
        palette.setColor(QPalette.AlternateBase, palette.color(QPalette.Base))
        palette.setColor(QPalette.Button, palette.color(QPalette.Base))
        self.checkbox.setPalette(palette)
        return

    def sizeHint(self):
        return QFrame.sizeHint(self) * 1.1

class EdwComboBoxCell(Cell, QComboBox):
    def __init__(self, lst, current, callback):
        QComboBox.__init__(self)
        Cell.__init__(self)
        self.clear()

        for tmpl in lst:
            self.addItem(tmpl)
        self.setCurrentIndex(0)
        if current < len(lst):
            self.setCurrentIndex(current)

        self.connect(self, SIGNAL('currentIndexChanged ( int )'), callback)

class EdwDateCell(EdwCell):
    def __init__(self, date):
        if date:
            d = QDateTime(QDate(0,0,0))
            d.setTime_t(int(date))
            EdwCell.__init__(self, d.toString('yyyy-MM-dd hh:mm'))
        else:
            EdwCell.__init__(self, tr('Never'))

class EdwProgressBarCell(Cell, QProgressBar):
    def __init__(self, val, max, color = None, format = '%v'):
        QProgressBar.__init__(self)
        Cell.__init__(self)
        self.setFormat(format)
        self.setMinimum(0)
        self.setMaximum(max)
        self.setValue(val)
        if color:
            palette = self.palette()
            palette.setColor(QPalette.Highlight, QColor(color))
            self.setPalette(palette)

class EdwButtonCell(EdwBlankCell):
    def __init__(self, text, callback):
        EdwBlankCell.__init__(self)
        self.button = QPushButton(text, self)
        self.button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        #self.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.connect(self.button, SIGNAL("clicked()"), callback)

    def setMaximumSize(self, size):
        self.button.setMaximumSize(size)

    def sizeHint(self):
        return self.button.size()
