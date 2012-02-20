# -*- coding: utf-8 -*-
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

from sys import exit

from PyQt4.QtCore import SIGNAL

from ufwi_rpcc_qt.central_window import CentralWindow
from ufwi_rpcc_qt.central_window import STANDALONE
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.logger import Logger

from nufaceqt.generic_links import GenericLinksDialog

from .ui.main_window_ui import Ui_MainWindow
from .edit_categories import EditCategories
from .register_firewall import RegisterFirewallWindow
from .edw import Edw
from .main_tab import MainTab
from .status_tab import StatusTab
from .templates_tab import TemplatesTab
from .nuconf_update_tab import NuConfUpdateTab
from .schedule_tab import ScheduleTab
from .monitoring_tab import MonitoringTab
from .permissions_tab import PermissionsTab
from .groups_header import GroupsHeader
from .groups_list import GroupsList

class MultisiteMainWindow(CentralWindow):
    ROLES = set(('multisite_read',))

    TABS_TYPES = [ MainTab, MonitoringTab, StatusTab, TemplatesTab, NuConfUpdateTab, ScheduleTab, PermissionsTab ]
    def __init__(self, application, client, standalone=STANDALONE, parent=None, eas_window = None):
        CentralWindow.__init__(self, client, parent, eas_window)
        self.setupCentralWindow(application, standalone)
        self.ui = Ui_MainWindow()
        self.application = application
        self.ui.setupUi(self)
        self.client = client
        self.filter = u''
        self.filterby = ''
        self.edw_list = []
        self.tmpl_list = []
        self.categories = {}
        self.categories_order = []
        self.categories_inited = False
        self.status_window = None
        self.template_window = None
        self.tabs = []
        self.denied_fw = []
        self.log = Logger()
        self.EAS_MESSAGES['update_templates'] = self.updateTemplates

        if 'multisite_master' not in self.client.call('CORE', 'getComponentList'):
            #QMessageBox.critical(None, APP_TITLE, tr("Please install the 'multisite_master' component before using Nucentral Multisite"), QMessageBox.Ok)
            # TODO: add a log entry
            print tr("Please install the 'multisite_master' component before using Nucentral Multisite")
            exit(1)

        self.is_admin = ('multisite_admin' in self.getRoles())
        if not self.is_admin:
            self.ui.actionRegister_a_new_host.setEnabled(False)

        self.read_only = 'multisite_write' not in self.getRoles()
        if self.read_only:
            self.ui.actionEdit_categories.setEnabled(False)

        roles = set([])

        for grp in self.getGroups():
            roles |= set([acl[2] for acl in self.client.call('multisite_transport', 'getAcl', grp)])
        self.roles = list(roles)

        for no, tab in enumerate(self.TABS_TYPES):
            self.tabs.append(None)

            if ( (len(tab.ROLES) != 0 and set(tab.ROLES) - set(self.roles) != set([]) ) \
            or   (len(tab.LOCAL_ROLES) != 0 and set(tab.LOCAL_ROLES) - set(self.getRoles()) != set([]) )) \
            and not self.is_admin:
                self.ui.tabs.setTabEnabled(no, False)

        # TODO: rename scroll_areas into tab_widget
        self.scroll_areas = [ self.ui.main_scroll_area, self.ui.monitoring_scroll_area, self.ui.services_scroll_area, self.ui.firewall_scroll_area,
                            self.ui.nuconf_update_scroll_area, self.ui.scheduler_scroll_area, self.ui.permission_tab ]

        self.groups_header = GroupsHeader(self.ui.filter_frame)
        self.connect(self.ui.actionRefresh, SIGNAL('triggered()'), self.refresh)
        self.connect(self.ui.actionRegister_a_new_host, SIGNAL('triggered()'), self.displayRegisterFirewallWindow)
        #self.connect(self.ui.actionStart_Nulog, SIGNAL('triggered()'), self.startNulog)
        self.connect(self.ui.actionEdit_categories, SIGNAL('triggered()'), self.startEditCategories)
        self.connect(self.ui.actionEdit_templates, SIGNAL('triggered()'), lambda: self.EAS_SendMessage('eas', 'show_app', 'nufaceqt'))
        self.connect(self.ui.tabs, SIGNAL('currentChanged(int)'), self.changeTab)

        # Disable toolbar buttons of the other tabs
        self.ui.actionUpdate_templates.setVisible(False)
        self.ui.actionEdit_generic_links.setVisible(False)
        self.ui.actionUpload_updates.setVisible(False)
        self.ui.actionReschedule.setVisible(False)
        self.ui.actionDelete_task.setVisible(False)
        self.ui.actionEdit_templates.setVisible(False)

        # Header
        self.connect(self.groups_header.group_combo, SIGNAL("activated(int)"), self.refresh)
        self.connect(self.groups_header.filter_apply, SIGNAL("clicked()"), self.applyFilter)
        self.connect(self.groups_header.filter_lineedit, SIGNAL("returnPressed()"), self.applyFilter)

        #try:
        #    from console_edenwall.log_viewer import DockLogViewer
        #    log_viewer = DockLogViewer(self, self.client)
        #    self.addDockWidget(Qt.BottomDockWidgetArea, log_viewer)
        #    #self.connect(self.ui.actionRefresh, SIGNAL('triggered()'), log_viewer.widget().refresh)
        #except ImportError:
        #    print "Please install EAS to get the LogView"


        self.previous_tab = 0
        self.changeTab(0)
        self.refreshEdwList()

    def refreshEdwList(self):
        # refresh the edenwall list
        edw_list = self.client.call("multisite_master", "listFirewalls")

        # Erase deleted firewalls
        for del_edw in self.edw_list:
            for edw in edw_list:
                if del_edw.getID() == edw[0]:
                    break
            else:
                self.delHost(del_edw)
                self.edw_list.remove(del_edw)

        # Find new firewalls / update existing
        for new_edw in edw_list:
            found = False

            # find this edenwall in the list of edenwalls
            edw_obj = None
            for edw in self.edw_list:
                if edw.getID() == new_edw[0]:
                    edw_obj = edw
                    break

            # if it's a new edw, create an Edw object for it and notify other windows
            if edw_obj == None:
                # check permissions on this firewall
                roles = self.getFirewallRoles(new_edw[0])
                if not self.is_admin and roles == set():
                    continue

                edw_obj = Edw(self, new_edw[0], new_edw[4], self.client, roles)
                self.edw_list.append(edw_obj)
                self.newObj(edw_obj)

            edw_obj.setError(new_edw[2])
            edw_obj.setGlobalStatus(new_edw[1])
            edw_obj.setLastSeen(new_edw[3])

        if not self.categories_inited:
            self.categories_inited = True
            categories, categories_order = self.client.call("multisite_master", "getCategories")
            self.categories.update(categories)
            self.categories_order.__init__(categories_order)

    def refresh(self):
        if not self.currentTab() is None:
            self.currentTab().refresh()

    def displayRegisterFirewallWindow(self):
        if RegisterFirewallWindow(self.client, self.edw_list, parent=self).run():
            self.refresh()

    def newObj(self, edw):
        # Notify all windows of the new host
        for tab in self.tabs:
            if not tab is None:
                tab.newObj(edw)

    def delHost(self, edw):
        # Notify all windows of the new host
        for tab in self.tabs:
            if not tab is None:
                tab.delObj(edw)

    def startEditCategories(self):
        dialog = EditCategories(self.categories, self.categories_order)
        if dialog.modified:
            for deleted in set(self.categories_order) - set(dialog.categories_order):
                self.client.call("multisite_master", "delCategories", deleted)
                self.categories.pop(deleted)
                for edw in self.edw_list:
                    edw.categories.pop(deleted)
            self.categories.update(dialog.categories)
            self.categories_order.__init__(dialog.categories_order)
            self.client.call("multisite_master", "setCategories", self.categories, self.categories_order)

            self.groups_header.refreshHeaders(self.currentTab())
            for tab in self.tabs:
                if not tab is None:
                    tab.refresh()

    def changeTab(self, new):
        if new >= len(self.TABS_TYPES):
            return
        if self.tabs[new] is None:
            if issubclass(self.TABS_TYPES[new], GroupsList):
                self.tabs[new] = self.TABS_TYPES[new](self.client, self.scroll_areas[new], self, self.edw_list, self.categories, self.categories_order)
                self.tabs[new].setGroupHeaders(self.groups_header)
                self.connect(self.tabs[new], SIGNAL('refresh_edw_list'), self.refreshEdwList)
            else:
                self.tabs[new] = self.TABS_TYPES[new](self)
            self.tabs[new].refresh()

        if issubclass(self.TABS_TYPES[new], GroupsList):
            self.groups_header.refreshHeaders(self.tabs[new])
            self.tabs[new].applyFilter(self.filterby, self.filter)
        self.tabs[self.previous_tab].unsetTab()
        self.tabs[new].setTab()
        self.previous_tab = new

    def currentTab(self):
        if self.ui.tabs.currentIndex() < 0:
            return None
        return self.tabs[self.ui.tabs.currentIndex()]

    def applyFilter(self):
        self.filterby = self.groups_header.getFilteredBy()
        self.filter = unicode(self.groups_header.filter_lineedit.text())

        filterby_title = u''
        if not self.currentTab() is None:
            self.currentTab().applyFilter(self.filterby, self.filter)
            if self.filterby != '':
                filterby_title = self.currentTab().getColumnTitle(self.filterby)

        # Display the current filter:
        self.groups_header.setFilterLabel(self.filter, filterby_title)

    def setupGenericLinks(self, fw = None):
        self.generic_links = GenericLinksDialog(self, self.saveGenericLinks)

        links = {}
        for edw in self.edw_list:
            links[edw.getID()] = edw.generic_links
            for type, missing in edw.missing_links.iteritems():
                if type not in links[edw.getID()]:
                    links[edw.getID()][type] = {}
                for id in missing:
                    links[edw.getID()][type][id] = ''
        self.generic_links.modify(links, fw)
        for edw in self.edw_list:
            edw.updateMissingLinks()

    def saveGenericLinks(self):
        try:
            links = self.generic_links.getLinks()
        except:
            return False

        for edw in self.edw_list:
            edw.setGenericLinks(links[edw.getID()])
            self.client.call('multisite_nuface', 'setGenericLinks', edw.getID(), links[edw.getID()])
        return True

    def getFirewallRoles(self, name):
        if name in self.denied_fw:
            return set()

        roles = set()
        for grp in self.getGroups():
            roles |= set([acl[2] for acl in self.client.call('multisite_transport', 'getAcl', grp, '', name)])

        if roles == set():
            self.denied_fw.append(name)

        return roles

    def updateTemplates(self, from_app):
        index = self.TABS_TYPES.index(TemplatesTab)
        if self.tabs[index] is not None:
            self.tabs[index].refreshCells()

