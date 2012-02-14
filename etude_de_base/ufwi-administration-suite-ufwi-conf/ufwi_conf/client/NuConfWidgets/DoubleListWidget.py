
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
from PyQt4.QtGui import QAbstractItemView, QFrame, QHBoxLayout, QListWidget, QPushButton, QVBoxLayout, QWidget

class DoubleListWidget(QWidget):
    __pyqtSignals__ = ('stateChanged')

    def __init__(self, parent, list, active_list):
        QWidget.__init__(self, parent)
        self.list = list
        self.list_active = active_list
        self.item_list = {}

        layout = QHBoxLayout(self)

        self.setLayout(layout)
        self.layout = layout

        self.addActiveListView()
        self.addButtons()
        self.addInactiveListView()
        self.fillListView()

    def addButtons(self):
        frame = QFrame(self)
        layout_v = QVBoxLayout(frame)
        frame.setLayout(layout_v)

        button_left = QPushButton('<- Left')
        self.connect(button_left, SIGNAL('clicked()'), lambda: self.MoveToActive())
        layout_v.addWidget(button_left)

        button_right = QPushButton('Right ->')
        self.connect(button_right, SIGNAL('clicked()'), lambda: self.MoveToInactive())
        layout_v.addWidget(button_right)

        layout_v.addStretch(100)

        self.layout.addWidget(frame)


    def addActiveListView(self):
        self.listview_active = QListWidget(self)
        self.listview_active.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.layout.addWidget(self.listview_active)


    def addInactiveListView(self):
        self.listview_inactive = QListWidget(self)
        self.listview_inactive.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.layout.addWidget(self.listview_inactive)


    def fillListView(self):

        self.listview_active.clear()
        self.listview_inactive.clear()

        for i in self.list_active:
            self.listview_active.addItem(i)

        for i in self.list:
            if not i in self.list_active:
                self.listview_inactive.addItem(i)

        self.listview_inactive.sortItems()
        self.listview_active.sortItems()


    def MoveToActive(self):
        for i in self.listview_inactive.selectedItems():
            self.list_active.append(i.text())
        self.fillListView()

        self.emit(SIGNAL("stateChanged"))


    def MoveToInactive(self):
        for i in self.listview_active.selectedItems():
            self.list_active.remove(i.text())
        self.fillListView()

        self.emit(SIGNAL("stateChanged"))

    def getActiveList(self):
        return self.list_active



