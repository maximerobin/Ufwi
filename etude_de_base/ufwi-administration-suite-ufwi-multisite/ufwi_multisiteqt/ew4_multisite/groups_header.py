
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

from PyQt4.QtCore import SIGNAL, QSize, QObject
from PyQt4.QtGui import QComboBox, QLineEdit, QLabel, QPushButton, QSizePolicy, QIcon, QPixmap, QGridLayout, QSpacerItem
from ufwi_rpcd.common import tr

class GroupsHeader(QObject):
    def __init__(self, parent):
        QObject.__init__(self)
        self.group_combo = QComboBox()
        self.filter_combo = QComboBox()
        self.filter_combo.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.filter_lineedit = QLineEdit()
        filter_icon = QIcon()
        filter_icon.addPixmap(QPixmap(":/icons/apply.png"))
        self.filter_apply = QPushButton(filter_icon, tr("OK"))
        self.filter_apply.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        clear_icon = QIcon()
        clear_icon.addPixmap(QPixmap(":/icons/clear.png"))
        self.filter_clear = QPushButton(clear_icon, "")
        self.filter_clear.setMaximumSize(QSize(30,30))
        self.filter_clear.setToolTip(tr("Clear filter"))
        self.group_label = QLabel(tr("Group by"))
        self.group_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.filter_label = QLabel(tr("Filter by"))
        self.filter_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.current_filter_label = QLabel()
        self.current_filter_label.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum)
        self.setFilterLabel('', '')
        self.groups_list = []
        self.filter_list = []

        self.layout = QGridLayout()
        self.layout.addWidget(self.filter_label, 0, 0)
        self.layout.addWidget(self.filter_combo, 0, 1)
        self.layout.addWidget(self.filter_clear, 0, 2)
        self.layout.addWidget(self.filter_lineedit, 0, 3)
        self.layout.addWidget(self.filter_apply, 0, 4)
        self.layout.addItem(QSpacerItem(20,20, QSizePolicy.Expanding, QSizePolicy.Minimum), 0, 5)
        self.layout.addWidget(self.group_label, 0, 6)
        self.layout.addWidget(self.group_combo, 0, 7)
        self.layout.addWidget(self.current_filter_label, 1, 0, 1, 5)
        parent.setLayout(self.layout)
        parent.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

        self.connect(self.filter_clear, SIGNAL("clicked()"), self.clearFilter)

    def clearFilter(self):
        self.filter_lineedit.clear()
        self.filter_apply.emit(SIGNAL("clicked()"))

    def getGroupedBy(self):
        if self.group_combo.currentIndex() == self.group_combo.count() - 1:
            return ''
        return self.groups_list[self.group_combo.currentIndex()]

    def getFilteredBy(self):
        return self.filter_list[self.filter_combo.currentIndex()]

    def refreshHeaders(self, lst):
        self.groups_list = lst.getGroupsBy()
        self.filter_list = lst.getFilterBy()
        current_text = None
        current_filter = None
        if self.group_combo.currentIndex() != self.group_combo.count() - 1:
            current_text = self.group_combo.currentText()
        current_filter = self.filter_combo.currentText()
        self.group_combo.clear()
        self.filter_combo.clear()

        current_item = -1
        filter_item = -1
        #Try to find the current group/filter
        for item_no, header in enumerate(lst.getGroupsBy()):
            header = lst.getColumnTitle(header)
            if header == current_text:
                current_item = item_no

            self.group_combo.addItem(header)


        for item_no, header in enumerate(lst.getFilterBy()):
            header = lst.getColumnTitle(header)
            if header == current_filter:
                filter_item = item_no
            self.filter_combo.addItem(header)

        self.group_combo.addItem(tr("None"))

        # Set back the current group/filter
        if current_item != -1:
            self.group_combo.setCurrentIndex(current_item)
        else:
            self.group_combo.setCurrentIndex(self.group_combo.count() - 1)
        if filter_item != -1:
            self.filter_combo.setCurrentIndex(filter_item)

    def setFilterLabel(self, filter_val, filter_grp):
        if filter_val == "":
            self.current_filter_label.setText(tr("No filter applied"))
        else:
            self.current_filter_label.setText(tr("Current filter: %s filtered with %s") % (filter_grp, filter_val))

