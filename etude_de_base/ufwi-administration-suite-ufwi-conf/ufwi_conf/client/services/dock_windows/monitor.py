#!/usr/bin/env python2.5
#encoding: utf-8 -*-

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


from __future__ import with_statement
from PyQt4.QtGui import (
QFrame, QToolButton, QIcon, QDialog, QAbstractItemView,
QHBoxLayout, QVBoxLayout, QTableWidget
)
from PyQt4.QtCore import SIGNAL, Qt
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcc_qt.service_status_item import ServiceStatusItem
from ufwi_rpcc_qt.services_name import ComponentToName
from ufwi_rpcc_qt.tools import QTableWidget_resizeWidgets
from monitor_config_dialog_ui import Ui_MonitorConfigDialog

class ButtonBar(QFrame):
    def __init__(self, parent, monitor):
        QFrame.__init__(self, parent)
        self.setContentsMargins(0, 0, 0, 0)

        self.monitor = monitor

        layout = QVBoxLayout(self)
        layout.setSpacing(0)

        refresh_btn = QToolButton(self)
        refresh_btn.setIcon(QIcon(":/icons/refresh"))
        refresh_btn.setAutoRaise(True)
        self.connect(refresh_btn, SIGNAL('clicked()'), monitor.refreshClick)

        config_btn = QToolButton(self)
        config_btn.setIcon(QIcon(":/icons/settings"))
        config_btn.setAutoRaise(True)
        self.connect(config_btn, SIGNAL('clicked()'), self.configDialog)

        layout.addWidget(refresh_btn)
        layout.addWidget(config_btn)
        layout.addStretch()

        self.setLayout(layout)

    def configDialog(self):
        MonitorConfigDialog(self.monitor, self)

class MonitorConfigDialog(QDialog, Ui_MonitorConfigDialog):
    def __init__(self, monitor, parent = None):
        QDialog.__init__(self, parent)
        self.monitor = monitor
        self.setupUi(self)

        show_run, show_stop = (ServiceStatusValues.RUNNING in self.monitor.showable_states,
            ServiceStatusValues.STOPPED in self.monitor.showable_states)
        self.running_checkBox.setChecked(show_run)
        self.stopped_checkBox.setChecked(show_stop)

        self.show()

    def accept(self, *args):
        show_run, show_stop = [box.isChecked() for box in
            self.running_checkBox,
            self.stopped_checkBox]
        showable_states = set()
        if show_run:
            showable_states.add(ServiceStatusValues.RUNNING)
        if show_stop:
            showable_states.add(ServiceStatusValues.STOPPED)
        self.monitor.showStates(showable_states)
        self.hide()
    def reject(self, *args):
        self.hide()


class MonitorWindow(QFrame):
    def __init__(self, client, parent, main_window, reload_frequency=30):
        QFrame.__init__(self, parent)

        self.setContentsMargins(0, 0, 0, 0)
        layout = QHBoxLayout(self)
        layout.setSpacing(0)
        self.monitor = MonitorWidget(client, self, main_window, reload_frequency)
        layout.addWidget(self.monitor)
        layout.addWidget(ButtonBar(self, self.monitor))

        self.setLayout(layout)

class NuConfServiceStatusItem(ServiceStatusItem):
    def __init__(self, component_name, on_off, parent):
        component_to_name = ComponentToName()
        ServiceStatusItem.__init__(self, component_to_name.display_name(component_name), on_off, parent)
        self.component_name = component_name

class MonitorWidget(QTableWidget):
    u"""
    Panel meant to display the status of services, for instance Apache, Squid…
    """

    REFRESH_INTERVAL = 30000 #(msec)
    COLUMNS_COUNT = 3

    def __init__(self, client, parent, main_window, reload_frequency):
        QTableWidget.__init__(self, parent)
        self.main_window = main_window
        self.msg_no_services = False
        self.msg_no_connexion = False

        self.setContentsMargins(0, 0, 0, 0)
        self.horizontalHeader().hide()
        self.verticalHeader().hide()
        self.setGridStyle(Qt.NoPen)
        self.setSelectionMode(QAbstractItemView.NoSelection)
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.setWhatsThis(
            tr("This panel lists the services configured in ufwi_conf "
               "and tells whether they are running or not."))
        self.client = client

        self.services_list = []
        self.services_status = {}
        self.showable_states = set(ServiceStatusValues.monitor_status)

        #initial filling
        self.data = {} # key : component name, value : status
        self.refresh()

    def showStates(self, showable_states):
        self.showable_states = showable_states
        self.refreshView()

    def refreshClick(self):
        self.refresh(on_click=True)

    def refresh(self, on_click=False):
        try:
            services, services_local = self.main_window.init_call('status', 'getStatus')
            services.update(services_local)
            self.data = services
        except Exception:
            self.setEnabled(False)
            if (not self.msg_no_connexion) or on_click:
                self.main_window.addToInfoArea(tr("Status monitor could not fetch server status, server is unreachable"))
                self.msg_no_connexion = True
            self.services_status.clear()
            self.clearContents()
            return
        if self.msg_no_connexion:
            self.main_window.addToInfoArea(tr("Connection restored, resuming monitoring"))
            self.msg_no_connexion = False
        self.refreshView()

    def refreshView(self):
        self.setEnabled(True)
        shown_data = self._select_showable_data(self.data)
        self._refresh_services(shown_data)
        self.doLayout()

    def _refresh_services(self, data):
        #3 sets of names we will act upon
        obsolete = set()
        update = set()
        new = set()

        #triage into sets
        for name in self.services_list:
            if not name in data.keys():
                obsolete.add(name)
            else:
                state = data[name]
                if state in self.showable_states:
                    update.add(name)
                else:
                    obsolete.add(name)

        for name, state in data.iteritems():
            if name not in self.services_list:
                new.add(name)

        #action
        for name in obsolete:
            self.removeItem(name)
        for name in update:
            self.services_status[name] = data[name]
        for name in new:
            self.addItem(name, data[name])

        #in case there was nothing left to display
        if not self.services_status:
            self._refresh_no_services()
        else:
            self.msg_no_services = False

    def removeItem(self, name):
        self.services_list.remove(name)

    def addItem(self, name, state):
        self.services_list.append(name)
        self.services_list.sort()
        self.services_status[name] = state

    def _select_showable_data(self, data):
        shown_data = {}
        for key, value in self.data.iteritems():
            if value in self.showable_states:
                shown_data[key] = value
        return shown_data

    def _refresh_no_services(self):
        del self.services_list[:]
        self.services_status.clear()
        self.clearContents()
        if not self.msg_no_services:
            self.main_window.addToInfoArea(tr("No services are running on the server."))
            self.msg_no_services = True

    def doLayout(self):
        self.clear()
        max_len = 0
        status_widgets = []

        if not self.services_list:
            self.setRowCount(0)
            return

        for service_name in self.services_list:
            status = self.services_status.get(service_name)
            if status is None:
                continue
            status_widgets.append(NuConfServiceStatusItem(service_name, status, None))
            cur_len = len(status_widgets[-1].name)
            if max_len < cur_len:
                max_len = cur_len

        cell_width = self.fontMetrics().averageCharWidth() * max_len

        if self.size().width() < cell_width:
            columns_count = 1
        else:
            if cell_width != 0:
                columns_count = self.size().width() / cell_width
            else:
                columns_count = 1
        self.setColumnCount(columns_count)

        self.setRowCount((len(self.services_list) / columns_count) + 1)
        if status_widgets:
            for cell_no, service_name in enumerate(self.services_list):
                x = cell_no % columns_count
                y = cell_no / columns_count

                self.setCellWidget(y, x, status_widgets[cell_no])
        QTableWidget_resizeWidgets(self)

    def resizeEvent(self, event):
        self.doLayout()
