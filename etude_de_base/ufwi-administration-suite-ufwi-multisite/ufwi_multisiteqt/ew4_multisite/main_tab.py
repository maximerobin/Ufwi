
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
from .edw_list import EdwList
from .multisite_tab import MultisiteTab

class MainTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'name', 'global_status', 'last_seen', 'revision', 'edenwall_type', 'nuauth_users', 'dropped_packets', 'current_template', 'error' ]
    FILTER_BY = [ 'name', 'global_status', 'revision', 'edenwall_type', 'current_template', 'error' ]
    GROUPS_BY_ID = [ 'global_status', 'revision', 'edenwall_type' ]

    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        GroupsList.__init__(self, client, scroll_area, main_window.ui, EdwList, edw_list, categories, categories_order)

    def refreshCells(self):
        for edw in self.edw_list:
            if edw.global_status == 'online':
                edw.refreshNulogData()
                edw.refreshNuFaceData()
