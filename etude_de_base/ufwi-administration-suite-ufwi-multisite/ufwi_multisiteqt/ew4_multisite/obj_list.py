
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

from PyQt4.QtGui import QTableWidgetItem
from PyQt4.QtCore import Qt, SIGNAL, QObject
from ufwi_rpcc_qt.tools import QTableWidget_resizeWidgets
from ufwi_rpcd.common import tr

class ObjList(QObject):
    def __init__(self, client, table, ui, obj_list, group):
        QObject.__init__(self)
        self.client = client
        self.widget = table
        self.obj_list = obj_list
        self.sort_column = 'name'
        self.sort_ascendant = True
        self.sorted_edw = []
        self.columns = {}
        self.group = group
        self.disable_display = True
        self.max_width = 0
        self.max_height = 0

        self.widget.verticalHeader().hide()
        self.widget.horizontalHeader().setSortIndicatorShown(True)

        self.connect(self.widget, SIGNAL("itemChanged ( QTableWidgetItem * )"), self.entryChanged)
        self.widget.horizontalHeader().connect(self.widget.horizontalHeader(), SIGNAL('sortIndicatorChanged(int, Qt::SortOrder)'), self.changeOrder)
        self.widget.horizontalHeader().setSortIndicator(0, Qt.AscendingOrder)
        self.sort_ascendant =  (self.widget.horizontalHeader().sortIndicatorOrder() == Qt.AscendingOrder)

    def changeOrder(self, col_no, order):
        self.disable_display = True
        self.sort_column = self.group.getColumns()[col_no]
        self.sort_ascendant =  (order == Qt.AscendingOrder)
        self.disable_display = False
        self.refreshDisplay()

    def refresh(self, selected_edw = None):
        #self.clear()
        self.group.refreshHeaders()
        row_count = len(self.obj_list)
        if self.getHeader() is not None:
            row_count += 1
        self.widget.setRowCount(row_count)
        if selected_edw != '' and selected_edw in self.sorted_edw:
            self.widget.setCurrentCell(self.rowFromEdw(selected_edw), 0)

    def refreshDisplay(self):
        self.refreshVals()
        self.refreshOrder()

        for edw in self.obj_list:
            for col in self.group.getColumns():
                self.displayCell(edw, col, True)

        if self.getHeader() is not None:
            for col in self.group.getColumns():
                self.displayCell(self.getHeader(), col, True)

        QTableWidget_resizeWidgets(self.widget)
        self.widget.setFixedHeight(self.widget.verticalHeader().length() + 50)

    def clear(self):
        # refresh data from ufwi_rpcd
        self.widget.clear()
        self.columns = {}
        self.refreshOrder()

    def refreshHeaders(self, header):
        self.widget.setColumnCount(len(header))
        self.widget.setHorizontalHeaderLabels(header)
        #self.widget.refreshSize()

    def refreshVals(self):
        self.columns = {}
        for edw in self.obj_list:
            self.columns[edw.getID()] = {}
            for col in self.group.getColumns():
                self.columns[edw.getID()][col] = edw.getVal(col)

    def displayCell(self, edw, col_id, full_display = False):
        # Add the host to the sorting list if it's not there yet
        #print "Displaying col %20s of edw %15s recursively: %i" % (col_id, edw.getID(), recurse)
        if not col_id in self.group.getColumns():
            return

        val = edw.getVal(col_id)

        if not edw.isHeader():
            self.columns[edw.getID()][col_id] = val

        old_row_no = self.rowFromEdw(edw.getID())
        selected_edw = self.currentEdw()

        if col_id == self.sort_column:
            self.refreshOrder()

        # Data are refreshed: exit if display is disabled
        if self.disable_display:
            return

        self.displayCellWidget(edw, col_id, full_display, old_row_no, selected_edw)

    def displayCellWidget(self, edw, col_id, full_display, old_row_no, selected_edw):
        col_no = self.group.getColumn(col_id)
        row_no = self.rowFromEdw(edw.getID())

        # Set the widget if one was returned
        val, cell = edw.getCell(col_id)
        if cell:
            self.widget.setCellWidget(row_no, col_no, cell)
            cell.refresh()
        else:
            item = QTableWidgetItem(val)
            self.widget.setItem(row_no, col_no, item)

        # If the sorting column was modified force a refresh
        # on all other cells beneath it
        if row_no != old_row_no:
            #first_row = min(row_no, old_row_no)
            for row in xrange(1, len(self.sorted_edw) + 1):
                changed_edw = self.edwFromName(self.edwFromRow(row))
                for col in self.group.getColumns():
                    if col == col_id and changed_edw == edw:
                        continue
                    if not full_display:
                        self.displayCell(changed_edw, col, True)
        if selected_edw != '' and selected_edw in self.sorted_edw:
            self.widget.setCurrentCell(self.rowFromEdw(selected_edw), 0)

        #if not full_display:
        #    self.refreshCellSize(row_no, col_no, cell)

        # Refresh the generic corresponding cell
        if edw != self.getHeader() and not full_display:
            self.displayCell(self.getHeader(), col_id)

    def refreshCellSize(self, row_no, col_no, widget):
        if self.max_width == 0:
            self.max_width = self.widget.horizontalHeader().sectionSizeHint(col_no)
        if self.max_height == 0:
            self.max_height = self.widget.verticalHeader().sectionSizeHint(col_no)

        if widget is not None:
            size = widget.size()
            if self.max_height < size.height():
                self.max_height = size.height()
                self.widget.setRowHeight(row_no, self.max_height)
            if self.max_width < size.width():
                self.max_width = size.width()
                self.widget.setColumnWidth(col_no, self.max_width)

    def refreshOrder(self):
        unsorted = {}
        for edw in self.columns.keys():
            if self.sort_column in self.columns[edw]:
                unsorted[edw] = self.columns[edw][self.sort_column]
            else:
                unsorted[edw] = ''

        items = unsorted.items()
        items.sort(lambda x,y: cmp(x[1],y[1]))
        if not self.sort_ascendant:
            items.reverse()
        self.sorted_edw = [i[0] for i in items]

    def edwFromName(self, id):
        edw_obj = None
        for edw in self.obj_list:
            if id == edw.id:
                edw_obj = edw
                break
        return edw_obj

    def rowFromEdw(self, edw):
        if self.getHeader() is not None and edw == self.getHeader().getID():
            return 0
        if edw not in self.sorted_edw:
            return -1
        sorted_pos = self.sorted_edw.index(edw)
        if self.getHeader() is not None:
            sorted_pos += 1
        return sorted_pos

    def edwFromRow(self, row):
        if self.getHeader() is not None:
            if row == 0:
                return self.getHeader()
            row -= 1
        return self.sorted_edw[row]

    def currentEdw(self):
        try:
            return self.widget.cellWidget(self.widget.currentRow(), 0).text()
        except:
            return ''

    def getList(self):
        return self.obj_list

    def entryChanged(self, item):
        edw = self.edwFromRow(item.row())
        edw = self.edwFromName(edw)
        edw = edw.getEdwObj()
        edw.setCategory(self.group.getColumns()[item.column()], unicode(item.text()))

    def newObj(self, obj):
        self.connect(obj, SIGNAL('display_cell'), self.displayCell)
        self.columns[obj.getID()] = {}
        self.sorted_edw.append(obj.getID())

    def getHeader(self):
        return None

    @staticmethod
    def getObjectTypeName():
        return tr('object(s)')

