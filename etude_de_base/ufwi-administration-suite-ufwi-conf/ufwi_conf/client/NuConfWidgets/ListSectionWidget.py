
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

from PyQt4.QtGui import QWidget, QVBoxLayout, QGridLayout, QHBoxLayout, QLineEdit, QPushButton, QLabel, QSizePolicy
from PyQt4.QtCore import QCoreApplication, SIGNAL
translate = QCoreApplication.translate

class ListSectionWidget(QWidget):
    __pyqtSignals__ = ("itemToAdd", "itemToDelete", 'stateChanged')

    def __init__(self, parent, list, validator = None):
        QWidget.__init__(self, parent)

        self.counter = 1
        self.labels = {}
        self.buttons = {}

        layout = QVBoxLayout(self)

        self.layout = layout
        self.list = list

        self.createTable()
        self.createButton()

        self.layout.addStretch(100)


    def createTable(self):
        list_table = QWidget(self)
        self.layout.addWidget(list_table)

        layout = QGridLayout(list_table)
        list_table.setLayout(layout)
        self.table_layout = layout

        self.createAllRows()

    def createButton(self, validator=None):
        # TODO correct the layout problem
        # button should not be below, but after the lineedit
        # TODO connect lineedit to add button

        w = QWidget(self)

        layout = QHBoxLayout(w)

        self.lineedit = QLineEdit(w)

        if validator:
            self.lineedit.setValidator(validator(w))

        layout.addWidget(self.lineedit)

        text = translate('MainWindow', 'Add')
        new_site_button = QPushButton(text, w)
        new_site_button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)


        self.connect(new_site_button, SIGNAL('clicked()'),  lambda: self.emit(SIGNAL("itemToAdd")))
        layout.addWidget(new_site_button)
        self.layout.addWidget(w)

    def createAllRows(self):
        for site in self.list:
                self.addRowList(site)



    def addRowList(self, content):

        label = QLabel(content)
        self.labels[self.counter] = label

        text = translate('MainWindow', 'Delete')

        button = QPushButton(text)
        button.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self.buttons[self.counter] = button

        self.table_layout.addWidget(button, self.counter, 1)
        self.table_layout.addWidget(label, self.counter, 0)

        # we should not use reference to self, in a lambda, as this doesn't behave nicely
        counter = self.counter
        self.connect(button, SIGNAL('clicked()'), lambda: self.emit(SIGNAL("itemToDelete"), counter))

        self.counter += 1

        self.emit(SIGNAL("stateChanged"))

    def getInputText(self):
        return unicode(self.lineedit.text())

    def clearInputText(self):
        self.lineedit.setText('')

    def getValueRow(self, col):
        site_label = self.labels[col]
        return unicode(site_label.text())

    def getValueList(self):
        for i in self.labels:
            yield self.getValueRow(i)

    def clearList(self):
        self.list = []
        self.deleteAllRows()

    def deleteAllRows(self):
        # we cannot use self.label while we remove element from it
        a = self.labels.keys()[:]
        for i in a:
            self.deleteRowList(i)

    def setList(self, list):
        self.clearList()
        self.list = list
        self.createAllRows()

    def deleteRowList(self, col):
        button = self.buttons[col]
        self.table_layout.removeWidget(button)
        button.hide()
        del self.buttons[col]

        label = self.labels[col]
        self.table_layout.removeWidget(label)
        label.hide()
        del self.labels[col]

        self.emit(SIGNAL("stateChanged"))

