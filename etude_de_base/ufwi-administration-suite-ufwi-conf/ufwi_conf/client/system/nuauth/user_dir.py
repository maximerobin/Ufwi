# -*- coding: utf-8 -*-

# $Id$

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


from logging import info

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QFrame, QIcon, QLabel, QTabWidget, \
                        QVBoxLayout, QAction, QCheckBox, \
                        QSizePolicy

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.toolbar import ToolBar
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
from ufwi_conf.common.user_dir import (NuauthCfg,
    LDAP, LDAPOrg, SameAsOrgAuth,
    auth_protocols, org_protocols, auth_class, org_class)
from ufwi_conf.common.user_dir import NOT_CONFIGURED
from ufwi_conf.common.user_dir.protocols import NND

from .dir_chooser import VariableConfigFrontend, AUTH, GROUP
from .tests_dialog import DirectoryTest

class NuauthFrontEnd(FullFeaturedScrollArea):
    COMPONENT = 'nuauth'
    LABEL = tr('User directory')
    REQUIREMENTS = ('nuauth',)
    ICON = ':/icons/users.png'

    def __init__(self, client, parent):
        #Parent constructor
        self.config = None
        self.auth_page = None
        self.group_page = None
        self.auth_configs = {}
        self.group_configs = {}
        self.mainwindow = parent
        self._module_disabled = False
        FullFeaturedScrollArea.__init__(self, client, parent)

        self.selected_auth = LDAP
        self.auth_configs[self.selected_auth] = LDAPOrg()
        self.selected_group = LDAP
        self.group_configs[self.selected_group] = LDAPOrg()

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (( 'nuauth', 'getNuauthConfig'), ( 'nuauth', 'availableModules'))

    def buildInterface(self):
        available_modules = self.mainwindow.init_call('nuauth', 'availableModules')
        if available_modules is None:
            self._no_backend()
            return

        # This boolean to support server versions 4.0.12/13. The new fake
        # protocol NOT_CONFIGURED has been added recently, but other
        # protocols are unchanged
        option_no_directory_available = True

        server_auth_protocols = available_modules['auth']
        for module in auth_protocols:
            if not module in server_auth_protocols:
                if module == NOT_CONFIGURED:
                    option_no_directory_available = False
                    #we continue and simply won't show checkbox
                    continue
                info("[User directory] Unsupported auth module, server side: %s (got %s)" % (module, server_auth_protocols))
                self._ask_server_upgrade()
                return

        server_org_protocols = available_modules['group']
        for module in org_protocols:
            if not module in server_org_protocols:
                if module == NOT_CONFIGURED:
                    option_no_directory_available = False
                    #we continue and simply won't show checkbox
                    continue
                if module == NND:
                    continue
                info("[User directory] Unsupported org module, server side: %s (got %s)" % (module, server_org_protocols))
                self._ask_server_upgrade()
                return

        self.mkToolbar()

        for module in available_modules['auth']:
            if module not in auth_protocols:
                self.mainwindow.addToInfoArea(
                    tr("User authentication: cannot handle the following protocol: ") +
                    module
                )
        for module in available_modules['group']:
            if module not in org_protocols:
                self.mainwindow.addToInfoArea(
                    tr("Organization: cannot handle the following protocol: ") +
                    module
                )

        frame = QFrame()
        self.setWidget(frame)
        self.setWidgetResizable(True)
        v_box = QVBoxLayout(frame)

        title = u'<h1>%s</h1>' % self.tr('Directory Configuration')
        v_box.addWidget(QLabel(title))

        self.use_directory = QCheckBox(tr("Use a user directory"))
        self.mainwindow.writeAccessNeeded(self.use_directory)
        self.tabs = QTabWidget()
#        self.tabs.setTabPosition(QTabWidget.West)

        #signature: QWidget * page, const QIcon & icon, const QString & label
        self.tabs.addTab(*self.mkUsersTab(available_modules['auth']))
        self.tabs.addTab(*self.mkGroupsTab(available_modules['group']))
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.connect(self.use_directory, SIGNAL("stateChanged (int)"), self.use_directory_state)

        v_box.addWidget(self.use_directory)
        v_box.addWidget(self.tabs)
        self.use_directory.setVisible(option_no_directory_available)

        self.message_area = MessageArea()
        v_box.addWidget(self.message_area)

    def use_directory_state(self, state):
        noconf = (state != Qt.Checked)
        if noconf:
            self.config = NuauthCfg()
            self.auth_page.setViewData(self.config)
            self.group_page.setViewData(self.config)
        elif not self.config.isConfigured():
            self.config = NuauthCfg(auth=SameAsOrgAuth(), org=LDAPOrg())
            self.auth_page.setViewData(self.config)
            self.group_page.setViewData(self.config)
        self.tabs.setEnabled(not noconf)
        self.setModified()

    def mkToolbar(self):
        self.test_action = QAction(
            QIcon(":/icons-32/auth_protocol.png"),
            tr("Test current configuration"),
            self
            )
        self.contextual_toolbar = ToolBar((self.test_action,), self, 'User directory')

        self.connect(self.test_action, SIGNAL('triggered(bool)'), self.testdialog)

    def testdialog(self):
        dialog = DirectoryTest(self.client, self)
        dialog.exec_()

    def reemit(self, *args):
        self.setModified()

    def mkUsersTab(self, available_modules):
        self.auth_page = VariableConfigFrontend(
            available_modules,
            self.config,
            self.auth_configs,
            AUTH,
            self.mainwindow
            )
        icon = QIcon(':/icons/one_user')
        self.connect(self.auth_page, SIGNAL('modified'), self.reemit)
        self.auth_page = self.auth_page
        self.mainwindow.writeAccessNeeded(self.auth_page)
        return self.auth_page, icon, tr('Authentication')

    def mkGroupsTab(self, available_modules):
        self.group_page = VariableConfigFrontend(
            available_modules,
            self.config,
            self.group_configs,
            GROUP,
            self.mainwindow
            )
        icon = QIcon(':/icons/users')
        self.connect(self.group_page, SIGNAL('modified'), self.reemit)
        self.mainwindow.writeAccessNeeded(self.group_page)
        return self.group_page, icon, tr('Groups')

    def _ask_server_upgrade(self):
        self._disable(
            tr("Client-server version mismatch"),
            tr(
                "This version of the user interface cannot handle the current "
                 "software version of the appliance. The appliance may need upgrading."
            ),
            tr("User directory interface disabled because of a version mismatch.")
        )

    def _no_backend(self):
        self._disable(
            tr("Could not fetch user directory parameters"),
            tr(
                "Problem while fetching the server configuration "
                "for user directory"
            ),
            tr(
                "The user directory interface is disabled because the configuration "
                "could not be fetched properly."
            )
        )

    def _disable(self, title, message, main_message):
        if self._module_disabled:
            #already done
            return
        self._module_disabled = True
        msg = MessageArea()
        msg.setMessage(
            title,
            message,
            "critical"
            )
        msg.setWidth(65)
        self.setWidget(msg)
        self.mainwindow.addToInfoArea(
            main_message
            )
        self.setWidgetResizable(True)

    def fetchConfig(self):
        serialized = self.mainwindow.init_call('nuauth', 'getNuauthConfig')
        if serialized is None:
            self._no_backend()
            return

        #DON'T REMOVE: 3 is a major turn in this module conception
        if serialized['DATASTRUCTURE_VERSION'] < 3:
            self._ask_server_upgrade()
            return

        self.config = NuauthCfg.deserialize(serialized)
        self.selected_auth = self.config.auth.protocol
        self.selected_group = self.config.org.protocol

        #instantiate all data structures
        if len(self.auth_configs) == 0:
            for protocol in auth_protocols:
                if protocol == self.selected_auth:
                    self.auth_configs[protocol] = self.config.auth
                else:
                    self.auth_configs[protocol] = auth_class(protocol)()
        self.auth_configs[self.selected_auth] = self.config.auth

        if len(self.group_configs) == 0:
            for protocol in org_protocols:
                if protocol == self.selected_group:
                    continue
                self.group_configs[protocol] = org_class(protocol)()
        self.group_configs[self.selected_group] = self.config.org

    def setViewData(self):
        if self._module_disabled:
            return
        configured = self.config.isConfigured()
        self.use_directory_state(Qt.Checked if configured else Qt.Unchecked)
        self.use_directory.setChecked(configured)
        for page in (self.auth_page, self.group_page):
            if page is not None:
                page.setViewData(self.config)

    def sendConfig(self, message):
        if not self.config.isValidWithMsg(use_state=True)[0]:
            return
        serialized = self.config.serialize(downgrade=True)
        self.client.call('nuauth', 'setNuauthConfig', serialized, message)

    def isValid(self):
        ok, msg = self.config.isValidWithMsg(use_state=True)

        if not ok:
            self.error_message = msg    # used by main_window
        return ok

