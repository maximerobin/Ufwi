
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

from .strings import MULTISITE_COLUMNS
from .groups_list import GroupsList
from .edw_list import EdwList
from .multisite_tab import MultisiteTab

class MonitoringTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'name', 'ha_mode', 'monitoring_load', 'monitoring_mem', 'bandwidth_in', 'bandwidth_out', 'hdd__', 'hdd__var', 'hdd__tmp', 'hdd__usr', 'hdd__var_lib_postgresql', 'hdd__var_lib_ldap', 'hdd__var_log', 'hdd__var_spool', 'hdd__var_tmp' ]
    FILTER_BY = [ 'name', ]
    GROUPS_BY_ID = [ ]
    ROLES = [ 'log_read' ]

    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        GroupsList.__init__(self, client, scroll_area, main_window.ui, EdwList, edw_list, categories, categories_order)
        self.ui = main_window.ui
        self.hdd_list = []

    def refreshCells(self):
        for edw in self.edw_list:
            edw.refreshMonitoring()

    def refreshHeaders(self):
        for edw in self.edw_list:
            for cell in edw.cell_classes.keys():
                if cell[:4] == 'hdd_' and cell not in self.hdd_list and cell not in self.HEADERS_ID:
                    self.hdd_list.append(cell)

        for table in self.grouped_tables.values():
            table.refreshHeaders(self.getTitles())
        self.groups_header.refreshHeaders(self)

    def getColumns(self):
        return self.HEADERS_ID + self.hdd_list + self.categories_order

    def getTitles(self):
        return [MULTISITE_COLUMNS[col] for col in self.HEADERS_ID + self.hdd_list] + [self.categories[name] for name in self.categories_order]

