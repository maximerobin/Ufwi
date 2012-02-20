
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

from copy import copy
from PyQt4.QtGui import QDialog, QListWidgetItem
from PyQt4.QtCore import SIGNAL, Qt
from ufwi_rpcd.common import tr
from .ui.edit_categories_ui import Ui_Dialog
from .strings import APP_TITLE

class EditCategories(QDialog):
    def __init__(self, categories, categories_order):
        QDialog.__init__(self)
        self.window = Ui_Dialog()
        self.window.setupUi(self)
        self.connect(self.window.categories_list, SIGNAL("itemChanged ( QListWidgetItem * )"), self.entryChanged)
        self.connect(self.window.add_button, SIGNAL("clicked()"), self.addEntry)
        self.connect(self.window.del_button, SIGNAL("clicked()"), self.delEntry)
        self.connect(self.window.up_button, SIGNAL("clicked()"), self.moveUp)
        self.connect(self.window.down_button, SIGNAL("clicked()"), self.moveDown)
        self.categories = copy(categories)
        self.categories_order = copy(categories_order)
        self.setWindowTitle(APP_TITLE)

        for entry in self.categories_order:
            item = QListWidgetItem(self.categories[entry])
            item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.window.categories_list.addItem(item)
        self.modified = False

        if self.exec_():
            self.modified = True

    def addEntry(self):
        item = QListWidgetItem(tr("New category"))
        item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
        self.window.categories_list.addItem(item)

        name = ""
        i = 0
        while name == "" or name in self.categories_order:
            name = "category%i" % i
            i += 1

        self.categories_order.append(name)
        self.categories[name] = tr("New category")

    def delEntry(self):
        row = self.window.categories_list.currentRow()
        if row != -1:
            name = self.categories_order[row]
            self.categories_order.remove(name)
            self.categories.pop(name)

            self.window.categories_list.model().removeRow(row)

    def entryChanged(self, new):
        row = self.window.categories_list.row(new)
        name = self.categories_order[row]
        self.categories[name] = unicode(new.text())

    def moveUp(self):
        item = self.window.categories_list.currentItem()
        row = self.window.categories_list.currentRow()
        name = self.categories_order[row]
        if row > 0:
            self.window.categories_list.model().removeRow(row)

            item = QListWidgetItem(self.categories[name])
            item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.window.categories_list.insertItem(row - 1, item)
            self.categories_order.remove(name)
            self.categories_order.insert(row - 1, name)
            self.window.categories_list.setCurrentRow(row - 1)

    def moveDown(self):
        item = self.window.categories_list.currentItem()
        row = self.window.categories_list.currentRow()
        name = self.categories_order[row]
        if row < len(self.categories_order) - 1:
            self.window.categories_list.model().removeRow(row)

            item = QListWidgetItem(self.categories[name])
            item.setFlags(Qt.ItemIsEditable | Qt.ItemIsEnabled | Qt.ItemIsSelectable)
            self.window.categories_list.insertItem(row + 1, item)
            self.categories_order.remove(name)
            self.categories_order.insert(row + 1, name)
            self.window.categories_list.setCurrentRow(row + 1)
