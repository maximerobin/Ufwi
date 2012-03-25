
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
from .groups_list import GroupsList
from .start_task import StartTask
from .edw_list import EdwList
from multisite_tab import MultisiteTab

class NuConfUpdateTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'name', 'edenwall_type', 'revision', 'nuconf_update_filepath', 'nuconf_update_browse', 'nuconf_update_status', 'nuconf_update_send' ]
    FILTER_BY = [ 'name', 'edenwall_type', 'revision', 'nuconf_update_filepath', 'nuconf_update_status' ]
    GROUPS_BY_ID = [ 'edenwall_type', 'revision', 'nuconf_update_status' ]
    ROLES = [ 'nuconf_write' ]
    LOCAL_ROLES = [ 'multisite_write' ]
    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        GroupsList.__init__(self, client, scroll_area, main_window.ui, EdwList, edw_list, categories, categories_order)
        self.start_task = StartTask(':/icons/apply_updates.png', 'Apply updates', self.sendUpdates, self, 'nuconf_update_send')
        self.ui = main_window.ui
        self.connect(self.ui.actionUpload_updates, SIGNAL('triggered()'), lambda: self.start_task.start(False))

    def setTab(self):
        self.ui.actionUpload_updates.setVisible(True)

    def unsetTab(self):
        self.ui.actionUpload_updates.setVisible(False)

    def sendUpdates(self, sched_options):
        for edw in self.edw_list:
            edw.applyNuconfUpdates(sched_options)

    def refreshCells(self):
        for edw in self.edw_list:
            edw.refreshNuconfUpdateData()
