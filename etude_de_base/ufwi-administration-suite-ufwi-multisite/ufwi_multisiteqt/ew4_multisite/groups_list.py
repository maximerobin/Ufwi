
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

from PyQt4.QtCore import SIGNAL, QRegExp, QObject, Qt
from PyQt4.QtGui import QWidget, QVBoxLayout
from .foldable_table import FoldableTable
from .strings import MULTISITE_COLUMNS
from copy import copy

class GroupsList(QObject):
    ROLES = []
    LOCAL_ROLES = []

    def __init__(self, client, widget, ui, obj_class, edw_list, categories, categories_order):
        QObject.__init__(self)
        self.client = client
        self.edw_list = edw_list
        self.filtered_edw_list = copy(edw_list)
        self.categories = categories
        self.categories_order = categories_order
        self.widget = widget
        self.table_count = 0
        self.content = QWidget()
        self.widget.setWidget(self.content)
        self.layout = QVBoxLayout()
        self.filter_by = ''
        self.filter = u''
        self.obj_class = obj_class

        # table widget by group
        self.grouped_tables = {}
        # list of edenwalls by group
        self.grouped_edw = {}
        self.tables = {}

    def setGroupHeaders(self, groups_header):
        # Header
        self.groups_header = groups_header

    def refreshCells(self):
        raise Exception("Not implemented")

    def refresh(self, selected_edw = None):
        self.emit(SIGNAL("refresh_edw_list"))

        for table in self.grouped_tables.itervalues():
            table.disable_display = True

        self.refreshCells()
        self.refreshGroups()

        # refresh the cell display
        for group in self.grouped_tables.itervalues():
            group.refresh(selected_edw)

        for table in self.grouped_tables.itervalues():
            table.disable_display = False
            table.refreshDisplay()

    def applyFilter(self, filterby, filter):
        self.filter = filter
        self.filter_by = filterby
        if filter == u'' or filterby == '':
            self.filtered_edw_list = copy(self.edw_list)
        else:
            self.filtered_edw_list = []
            rx = QRegExp(filter)
            rx.setCaseSensitivity(Qt.CaseInsensitive)

            for edw in self.edw_list:
                grp_name = unicode(edw.getVal(filterby))
                if rx.indexIn(grp_name) != -1:
                    self.filtered_edw_list.append(edw)
        self.refreshGroups()

        # refresh the cell display
        for table in self.grouped_tables.itervalues():
            table.refresh(None)
            table.disable_display = False
            table.refreshDisplay()

    def createGroup(self, grp_name):
        self.grouped_edw[grp_name] = []
        group_by = self.groups_header.getGroupedBy()

        table = FoldableTable()
        edw_table = self.obj_class(self.client, table.table, self.content, self.grouped_edw[grp_name], self)

        self.layout.addWidget(table)
        if group_by == '':
            table.label.hide()
        else:
            table.label.show()

        self.grouped_tables[grp_name] = edw_table
        self.tables[grp_name] = table
        self.table_count += 1

    def addEdwToGroup(self, grp_name, edw):
        if not grp_name in self.grouped_edw:
            self.createGroup(grp_name)
        self.grouped_edw[grp_name].append(edw)
        self.grouped_tables[grp_name].newObj(edw)

        text = ""
        group_by = self.groups_header.getGroupedBy()
        if group_by != '':
            text = ("%s : %s (%i %s(s))" % (self.getColumnTitle(group_by), grp_name, len(self.grouped_edw[grp_name]), self.obj_class.getObjectTypeName()))
        self.tables[grp_name].setLabel(text)

    def refreshGroups(self):
        self.content = QWidget()
        self.widget.setWidget(self.content)

        self.layout = QVBoxLayout()
        self.grouped_tables = {}
        self.grouped_edw = {}
        self.tables = {}
        self.old_table = self.table_count
        self.table_count = 0

        group_by = self.groups_header.getGroupedBy()

        if group_by == '':
            for edw in self.filtered_edw_list:
                self.addEdwToGroup('', edw)
        else:
            for edw in self.filtered_edw_list:
                col_title = self.getColumnTitle(group_by)
                grp_name = edw.getVal(group_by)
                self.addEdwToGroup(grp_name, edw)

        self.layout.addStretch()
        self.content.setLayout(self.layout)

    def newObj(self, edw):
        self.connect(edw, SIGNAL('refresh_headers'), self.refreshHeaders)

        group_by = self.groups_header.getGroupedBy()
        if group_by == '':
            self.filtered_edw_list.append(edw)
            self.addEdwToGroup('', edw)
        else:
            grp_name = edw.getVal(group_by)
            if self.filter == u'' or self.filter in grp_name.lower():
                self.filtered_edw_list.append(edw)
                self.addEdwToGroup(grp_name, edw)

    def delObj(self, edw):
        if edw in self.filtered_edw_list:
            self.filtered_edw_list.remove(edw)

    def getAllObjects(self):
        lst = []
        for objs in self.grouped_edw.values():
            lst += objs
        return lst

    def currentEdw(self):
        return None

    def getColumn(self, cell_id):
        if cell_id in self.getColumns():
            return self.getColumns().index(cell_id)
        if cell_id in self.categories_order:
            return len(self.getColumns()) + self.categories_order.index(cell_id)
        return -1

    def getColumns(self):
        return self.HEADERS_ID + self.categories_order

    def getTitles(self):
        return [MULTISITE_COLUMNS[col] for col in self.HEADERS_ID] + [self.categories[name] for name in self.categories_order]

    def getFilterBy(self):
        return self.FILTER_BY + self.categories_order
    def getGroupsBy(self):
        return self.GROUPS_BY_ID + self.categories_order

    def getColumnTitle(self, id):
        if id in self.getColumns():
            col_no = self.getColumns().index(id)
            return self.getTitles()[col_no]
        return ''

    def refreshHeaders(self):
        for table in self.grouped_tables.values():
            table.refreshHeaders(self.getTitles())
