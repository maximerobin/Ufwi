# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Laurent Defert <lds AT inl.fr>

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

$Id$
"""

from PyQt4.QtGui import QTableView, QHeaderView, QAction, QMenu
from PyQt4.QtCore import Qt, SIGNAL

from ufwi_rpcd.common import tr

class HeaderView(QHeaderView):
    def __init__(self, orientation, parent):
        QHeaderView.__init__(self, orientation, parent)
        self.setStyleSheet("font: bold 12px")
        self.setResizeMode(QHeaderView.Stretch)

    def mousePressEvent(self, event):
        if event.buttons() & Qt.RightButton:
            self.emit(SIGNAL("right_clicked"), event)
            return
        QHeaderView.mousePressEvent(self, event)

    def mouseMoveEvent(self, event):
        QHeaderView.mouseMoveEvent(self, event)
        if self.cursor().shape() == Qt.OpenHandCursor:
            self.setCursor(Qt.ArrowCursor)


class TableView(QTableView):

    def __init__(self, parent):
        QTableView.__init__(self, parent)

        # Set the title header
        self.header_column_count = 0
        self.header = HeaderView(Qt.Horizontal, self)
        self.header.setClickable(True)
        self.connect(self.header, SIGNAL("right_clicked"), self.displayHeadersActionsMenu)
        self.setHorizontalHeader(self.header)
        self.setMouseTracking(True)
        self.header_menu = QMenu(self)

        self.setAlternatingRowColors(True)

    def updateHeadersActions(self):
        # clean the current actions list:

        if self.header_column_count == self.header.count():
            #column didn't change
            return

        self.header_column_count = self.header.count()

        for action in self.header_menu.actions():
            self.removeAction(action)

        for col in xrange(self.header.count()):
            col_label = self.model().headerData(col, Qt.Horizontal).toString()
            action = QAction(col_label, self.header)
            action.setCheckable(True)
            action.setChecked(not self.header.isSectionHidden(col))
            self.connect(action, SIGNAL("triggered()"), self.updateDisplayedColumns)
            self.header_menu.addAction(action)

    def displayHeadersActionsMenu(self, event):
        self.header_menu.exec_(event.globalPos())

    def updateDisplayedColumns(self):

        for menu_item_no, menu_item in enumerate(self.header_menu.actions()):
            if menu_item.isChecked():
                self.header.showSection(menu_item_no)
            else:
                self.header.hideSection(menu_item_no)

        print self.sizeHint()

    def parentResizeEvent(self, event):
        pass

