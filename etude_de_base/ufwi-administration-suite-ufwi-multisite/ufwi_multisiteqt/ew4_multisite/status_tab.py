
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

from .groups_list import GroupsList
from .strings import MULTISITE_COLUMNS
from .edw_list import EdwList
from .multisite_tab import MultisiteTab

class StatusTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'name', 'global_status' ]
    FILTER_BY = [ 'name', 'global_status' ]
    GROUPS_BY_ID = [ 'global_status' ]
    ROLES = [ 'conf_read' ]
    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        GroupsList.__init__(self, client, scroll_area, main_window.ui, EdwList, edw_list, categories, categories_order)
        self.sorted_services = []

    def refreshHeaders(self):
        services = set()
        for edw in self.edw_list:
            services.update(edw.getServices())

        self.sorted_services = list(services)
        self.sorted_services.sort()

        for table in self.grouped_tables.values():
            table.refreshHeaders(self.getTitles())
        self.groups_header.refreshHeaders(self)

    def refreshCells(self):
        for edw in self.edw_list:
            edw.refreshServicesStatus()

    def getColumns(self):
        return self.HEADERS_ID + self.sorted_services + self.categories_order

    def getTitles(self):
        return [MULTISITE_COLUMNS[col] for col in self.HEADERS_ID] + self.sorted_services + [self.categories[name] for name in self.categories_order]

