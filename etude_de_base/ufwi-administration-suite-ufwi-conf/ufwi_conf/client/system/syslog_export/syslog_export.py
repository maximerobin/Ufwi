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


from __future__ import with_statement
from PyQt4.QtGui import (
    QLabel, QGroupBox, QCheckBox, QFormLayout, QLineEdit,
    QVBoxLayout, QFrame)
from PyQt4.QtCore import SIGNAL

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.syslog_export import QSyslogExportObject

_component = 'syslog_export'

class SyslogExportFrontend(ScrollArea):
    COMPONENT = 'syslog_export'
    LABEL = tr('Syslog export')
    REQUIREMENTS = ('syslog_export',)
    ICON = ':/icons/up.png'

    def __init__(self, client, parent):
        self.__loading = True
        ScrollArea.__init__(self)
        self.mainwindow = parent
        self.client = client
        self.modified = False

        self.qsyslogexportobject = QSyslogExportObject.getInstance()

        frame = QFrame(self)
        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel('<H1>%s</H1>' % tr('Syslog export')))

        enabled_box = QGroupBox(tr("Enable syslog export"))
        enabled_layout = QFormLayout(enabled_box)
        self.enabledCheckBox = QCheckBox()
        enabled_layout.addRow(QLabel(tr("Enable the syslog export service")),
                              self.enabledCheckBox)
        self.connect(self.enabledCheckBox, SIGNAL('toggled(bool)'),
                     self.setEnabled)

        servers_box = QGroupBox(tr("Syslog server to export to"))
        servers_layout = QFormLayout(servers_box)
        self.serverLineEdit = QLineEdit()
        servers_layout.addRow(QLabel(tr("Syslog server to export to")),
                              self.serverLineEdit)
        self.connect(self.serverLineEdit,
                     SIGNAL('textEdited(const QString&)'),
                     self.setModifiedCallback)

        components_box = QGroupBox(tr("Enabled components"))
        components_layout = QFormLayout(components_box)
        self.ulogdCheckBox = QCheckBox()
        components_layout.addRow(QLabel(tr(
            "Firewall logs (ulogd, facility local4, level info)")),
                                 self.ulogdCheckBox)
        self.connect(self.ulogdCheckBox, SIGNAL('toggled(bool)'),
                     self.setUlogd)

        self.mainwindow.writeAccessNeeded(
            self.enabledCheckBox, self.ulogdCheckBox, self.serverLineEdit)

        for widget in (enabled_box, servers_box, components_box):
            layout.addWidget(widget)
        layout.addStretch()
        self.setWidget(frame)
        self.setWidgetResizable(True)

        self.resetConf()
        self.__loading = False

    def setModified(self, isModified=True, message=""):
        if self.__loading:
            return
        if isModified:
            self.modified = True
            self.mainwindow.setModified(self, True)
            if message:
                self.mainwindow.addToInfoArea(message)
        else:
            self.modified = False

    def setModifiedCallback(self, *unused):
        self.setModified()

    def isModified(self):
        return self.modified

    def saveAbstractConf(self):
        self.qsyslogexportobject.syslog_export.setServers([{
                    "address": unicode(self.serverLineEdit.text()),
                    "port": 514}])

    def saveConf(self, message):
        serialized = self.qsyslogexportobject.syslog_export.serialize(downgrade=True)
        self.client.call(_component, 'setSyslogExportConfig', serialized, message)

    def resetConf(self):
        self.qsyslogexportobject.syslog_export = self.client.call(
            'syslog_export', 'getSyslogExportConfig')
        self.enabledCheckBox.setChecked(self.qsyslogexportobject.syslog_export.enabled)
        self._disable_fields(not self.qsyslogexportobject.syslog_export.enabled)
        self.ulogdCheckBox.setChecked(self.qsyslogexportobject.syslog_export.components[
                "ulogd"]["enabled"])
        try:
            self.serverLineEdit.setText(
                self.qsyslogexportobject.syslog_export.servers[0]["address"])
        except (KeyError, IndexError):
            pass

        self.setModified(False)

    def error(self, message):
        self.mainwindow.addToInfoArea(message, category=COLOR_ERROR)

    def _disable_fields(self, disabled):
        """Disable fields if argument disabled is True, enable otherwise."""
        for widget in (self.serverLineEdit, self.ulogdCheckBox):
            widget.setDisabled(disabled)

    def setEnabled(self, value):
        if value != self.qsyslogexportobject.syslog_export.enabled:
            self.qsyslogexportobject.syslog_export.setEnabled(value)
            self.setModified()
        self._disable_fields(not value)

    def setUlogd(self, value):
        if not "ulogd" in self.qsyslogexportobject.syslog_export.components:
            self.qsyslogexportobject.syslog_export.components["ulogd"] = {
                "enabled": False,
                "facility": "local4",
                "level": "info"}
        if value != self.qsyslogexportobject.syslog_export.components[
            "ulogd"]["enabled"]:
            self.qsyslogexportobject.syslog_export.components[
                "ulogd"]["enabled"] = bool(value)
            self.setModified()

    def isValid(self):
        self.saveAbstractConf()
        outcome, self.error_message = \
            self.qsyslogexportobject.syslog_export.isValidWithMsg()
        return outcome

