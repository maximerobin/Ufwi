#coding: utf-8
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

import re
import time

from PyQt4.QtCore import QObject
from PyQt4.QtCore import QString
from PyQt4.QtCore import Qt
from PyQt4.QtCore import QTimer
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QFileDialog
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QGridLayout
from PyQt4.QtGui import QGroupBox
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QTextEdit
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.colors import (COLOR_CRITICAL, COLOR_ERROR,
    COLOR_WARNING, COLOR_SUCCESS)
from ufwi_rpcc_qt.html import htmlBold, htmlColor

from ufwi_conf.client import NuConfPageKit
from ufwi_conf.client.qt.widgets import (ScrollArea, SelectableLabel)
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.system.resolv.qhostname_object import QHostnameObject
from .save_restore_widget import SaveRestoreWidget

REFRESH_INTERVAL_MILLISECONDS = 5000
LAST_CONNECTIONS_RE = re.compile(
    r'^([^ ]+ [^ ]+ [^ ]+) .*\(sshd:session\): session (\w+) for')

_tr_strings = {
    'running': tr('running'),
    'not running': tr('not running'),
    'pending': tr('pending'),
    'disabled': tr('disabled')
}

def _tr_first_element(seq):
    try:
        return [_tr_strings.get(seq[0], seq[0])] + seq[1:]
    except:
        return seq

class ToolsFrontend(ScrollArea):
    COMPONENT = 'tools'
    LABEL = tr('Tools')
    REQUIREMENTS = ('tools',)
    ICON = ':/icons/run.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        self.tools_widget = ToolsWidget(client, parent, self)
        self.setWidget(self.tools_widget)
        self.setWidgetResizable(True)

    def isModified(self):
        return False

    def isValid(self):
        return True

    def resetConf(self):
        # nothing to do
        pass

class ToolsWidget(QFrame):
    def __init__(self, client, mainwindow, parent=None):
        QFrame.__init__(self, parent)
        self.client = client
        self.mainwindow = mainwindow
        self.timer = None

        form_layout = QGridLayout(self)
        title = QLabel("<H1>%s</H1>" % tr('Tools'))
        form_layout.addWidget(title)

        self.build()

    def build(self):
        """
        populate interface
        """
        ### diagnostic and support
        diag_grp = self.mk_diag_grp()

        ### ufwi_rpcd and services : restart
        software_grp = QGroupBox(tr('Restart services'))
        software_buttons = QGridLayout(software_grp)

        self.restart_ufwi_rpcd_button = QPushButton(tr('Restart'))
        self.mainwindow.writeAccessNeeded(self.restart_ufwi_rpcd_button)
        self.connect(self.restart_ufwi_rpcd_button, SIGNAL('clicked()'),
                     self.restart_ufwi_rpcd)
        software_buttons.addWidget(QLabel(tr("Restart the configuration service")), 0, 0)
        software_buttons.addWidget(self.restart_ufwi_rpcd_button, 0, 1)

        self.restart_winbind_button = QPushButton(tr('Restart'))
        self.mainwindow.writeAccessNeeded(self.restart_winbind_button)
        self.connect(self.restart_winbind_button, SIGNAL('clicked()'),
                     self.restart_winbind)
        software_buttons.addWidget(
            QLabel(tr("Restart the interface with Active Directory")), 1, 0)
        software_buttons.addWidget(self.restart_winbind_button, 1, 1)

        software_buttons.setColumnStretch(3, 10)

        ### appliance : restart / shutdown
        buttons = QGroupBox(tr('Shutdown or restart the system'))
        buttons_layout = QGridLayout(buttons)

        restart = QPushButton(tr('Restart'))
        halt = QPushButton(tr('Shutdown'))

        buttons_layout.addWidget(QLabel(tr('Restart the system')), 0, 0)
        buttons_layout.addWidget(restart, 0, 1)
        buttons_layout.addWidget(QLabel(tr('Shutdown the system')), 1, 0)
        buttons_layout.addWidget(halt, 1, 1)
        buttons_layout.setColumnStretch(3, 10)
        buttons_layout.setRowStretch(3, 10)

        self.mainwindow.writeAccessNeeded(restart)
        self.mainwindow.writeAccessNeeded(halt)

        self.connect(restart, SIGNAL('clicked()'), self.restart)
        self.connect(halt, SIGNAL('clicked()'), self.halt)

        ### The SaveRestoreWidget is defined in its own file.

        ### Purge button
        purge_grp = QGroupBox(tr(
                "Purge old logs (in case of low disk space)"))
        purge_layout = QGridLayout(purge_grp)
        self.purge_button = QPushButton(tr("Delete old logs"))
        purge_layout.addWidget(self.purge_button)
        purge_layout.setColumnStretch(2, 10)
        self.connect(self.purge_button, SIGNAL('clicked()'), self.purge_logs)
        self.mainwindow.writeAccessNeeded(self.purge_button)
        if "supervisor" not in self.mainwindow.available_backends:
            purge_grp.hide()

        ### Restore to factory default:
        try:
            is_factory_default_asked = self.client.call(
                'tools', 'isFactoryDefaultAsked')
            has_factory_default_functionality = True
        except Exception:
            has_factory_default_functionality = False
        if has_factory_default_functionality:
            self.factory_grp = QGroupBox(tr('Restore to factory default'))
            self.factory_layout = QGridLayout(self.factory_grp)

            self.factory_button = QPushButton(
                tr('Delete all data and restore to factory default'))
            self.cancel_factory_button = QPushButton(
                tr('Cancel factory default restoration request'))

            factory_text = tr('Restoration to factory default has been requested.')\
                            + htmlBold(tr('All data will be deleted at next boot.'))
            self.factory_default_asked_label = QLabel(
                htmlColor(factory_text, COLOR_WARNING).html)
            self.factory_default_asked_label.setTextFormat(Qt.RichText)
            self.factory_layout.addWidget(self.factory_default_asked_label, 0,
                0)
            if not is_factory_default_asked:
                self.factory_default_asked_label.hide()
            self.factory_layout.addWidget(
                QLabel(tr('Restore to factory default')), 1, 0)
            self.factory_layout.addWidget(self.factory_button, 1, 1)
            self.factory_layout.addWidget(
                QLabel(tr('Cancel factory default restoration request')), 2, 0)
            self.factory_layout.addWidget(self.cancel_factory_button, 2, 1)
            self.factory_layout.setColumnStretch(3, 10)
            self.factory_layout.setRowStretch(3, 10)

            self.mainwindow.writeAccessNeeded(self.factory_button, self.cancel_factory_button)

            self.connect(self.factory_button, SIGNAL('clicked()'),
                         self.ask_factory)
            self.connect(self.cancel_factory_button, SIGNAL('clicked()'),
                         self.cancel_factory)

        if diag_grp is not None:
            self.layout().addWidget(diag_grp)
        self.layout().addWidget(software_grp)
        self.layout().addWidget(buttons)
        self.layout().addWidget(SaveRestoreWidget(self.mainwindow))
        self.layout().addWidget(purge_grp)
        if has_factory_default_functionality:
            self.layout().addWidget(self.factory_grp)
        self.layout().setRowStretch(5, 10)
        self.layout().setColumnStretch(2, 10)
        if EDENWALL:
            self.refreshVpnSupport()

    def mk_diag_grp(self):
        if not EDENWALL:
            return None
        diag_grp = QGroupBox(tr('Diagnostic and support'), self)
        diag_buttons = QGridLayout(diag_grp)
        diagnostic = QPushButton(tr('Diagnostic'), self)
        self.connect(diagnostic, SIGNAL('clicked()'), self.diagnostic)

        diag_buttons.addWidget(QLabel(tr('Download the diagnostic file')), 0, 0)
        diag_buttons.addWidget(diagnostic, 0, 1)

        self.vpnSupportLabel = QLabel(tr('Connect to support VPN'))
        self.vpnSupportLabel.hide()
        diag_buttons.addWidget(self.vpnSupportLabel, 1, 0)

        self.startVpnSupportButton = QPushButton(tr('Start VPN support'))
        self.connect(self.startVpnSupportButton, SIGNAL('clicked()'),
                     self.startVpnSupport)
        self.startVpnSupportButton.hide()
        diag_buttons.addWidget(self.startVpnSupportButton, 1, 1)

        self.stopVpnSupportButton = QPushButton(tr('Stop VPN support'))
        self.connect(self.stopVpnSupportButton, SIGNAL('clicked()'),
                     self.stopVpnSupport)
        self.stopVpnSupportButton.hide()
        diag_buttons.addWidget(self.stopVpnSupportButton, 1, 2)

        self.vpnSupportStatusTextLabel = QLabel(
            tr('VPN support status and IP: '))
        self.vpnSupportStatusTextLabel.hide()
        diag_buttons.addWidget(self.vpnSupportStatusTextLabel, 2, 0)

        self.vpnSupportStatusLabel = SelectableLabel()
        self.vpnSupportStatusLabel.hide()
        diag_buttons.addWidget(self.vpnSupportStatusLabel, 2, 1)

        self.refreshVpnSupportButton = QPushButton(tr('Refresh'))
        self.connect(self.refreshVpnSupportButton, SIGNAL('clicked()'),
                     self.refreshVpnSupport)
        self.refreshVpnSupportButton.hide()
        diag_buttons.addWidget(self.refreshVpnSupportButton, 2, 2)

        self.lastConnectionsLabel = QLabel(
            tr('Display last connections from support'))
        self.lastConnectionsLabel.hide()
        diag_buttons.addWidget(self.lastConnectionsLabel, 3, 0)

        self.lastConnectionsButton = QPushButton(tr('Last connections'))
        self.connect(self.lastConnectionsButton, SIGNAL('clicked()'),
                     self.lastConnections)
        self.lastConnectionsButton.hide()
        diag_buttons.addWidget(self.lastConnectionsButton, 3, 1)

        diag_buttons.setColumnStretch(4, 10)

        return diag_grp

    def ask_factory(self):
        confirm = QMessageBox.warning(
            self, tr('Confirm'),
            tr("Do you really want to delete all your data on this appliance and restore to factory default?"),
            QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok == confirm:
            try:
                self.client.call('tools', 'askFactoryDefault')
                self.mainwindow.addToInfoArea(
                    tr('Asked to restore to factory default. Please reboot the appliance now. The system will be restored automatically and it will reboot on the restored system.'))
                self.factory_default_asked_label.show()
            except Exception, err:
                self.mainwindow.addToInfoArea(
                    tr('Could not ask to restore to factory default (%s).'
                       % err))

    def cancel_factory(self):
        try:
            self.client.call('tools', 'cancelFactoryDefault')
            self.mainwindow.addToInfoArea(
                tr('Canceled factory default restoration request.'))
            self.factory_default_asked_label.hide()
        except Exception:
            self.mainwindow.addToInfoArea(
                tr('Could not cancel factory default restoration request. All the data WILL be deleted at next boot.'),
                category=COLOR_CRITICAL)

    def purge_logs(self):
        msg = tr("Do you want to permanently delete the oldest logs "
                 "(firewall logs, system logs, etc.)?")
        confirm = QMessageBox.warning(self, tr('Confirm'), msg,
                                      QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok != confirm:
            return
        try:
            if self.client.call("supervisor", "purge"):
                self.mainwindow.addToInfoArea(
                    tr("Purge started."))
            else:
                self.mainwindow.addToInfoArea(
                    tr("A check or a purge is already running. "
                       "Please try again later."),
                    category=COLOR_WARNING)
        except Exception:
            self.mainwindow.addToInfoArea(tr("Error: failed to purge logs."),
                                          category=COLOR_CRITICAL)

    def restart_ufwi_rpcd(self):
        """
        ask confirmation before sending call
        """
        confirm = QMessageBox.warning(self, tr('Confirm'), tr("Do you want to restart the configuration service?"), QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok == confirm:
            self.mainwindow.addToInfoArea(tr('Restarting the configuration service'), category=COLOR_CRITICAL)
            try:
                self.client.call('tools', 'restartNucentral')
            except Exception:
                pass

    def restart_service(self, service):
        try:
            self.client.call('tools', 'restartService', service)
        except Exception:
            self.mainwindow.addToInfoArea(
                tr('Could not restart the %s service.') % service,
                category=COLOR_ERROR)

    def restart_winbind(self):
        self.restart_service('winbind')

    def restart(self):
        """
        ask confirmation before sending restart call
        """
        confirm = QMessageBox.warning(self, tr('Confirm'), tr('Do you want to restart the system?'), QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok == confirm:
            info = tr('Restarting the system')
            success_msg = tr('Restart in progress')
            error_msg = tr('Error while restarting the system')
            self.halt_restart(info, 'rebootSystem', success_msg, error_msg)

    def halt(self):
        """
        ask double confirmation before sending halt call
        """
        confirm = QMessageBox.warning(self, tr('Confirm'), tr('Do you want to halt the system?'), QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok != confirm:
            return

        confirm = QMessageBox.warning(self, tr('Confirm'), tr('Please note that you will have to be physically present in order to start the system. Halt anyway ?'), QMessageBox.Cancel, QMessageBox.Ok)
        if QMessageBox.Ok == confirm:
            info = tr('Halting the system')
            success_msg = tr('System halted')
            error_msg = tr('Error while halting the system')
            self.halt_restart(info, 'haltSystem', success_msg, error_msg)

    def halt_restart(self, msg, service, success_msg, error_msg):
            self.mainwindow.addToInfoArea(msg, category=COLOR_CRITICAL)
            # not any call must be done anymore, stop all qtimer
            self.mainwindow.disableAllApps()
            async = self.client.async()
            async.call('tools', service,
                callback = self.halt_ok, errback = self.halt_err,
                callbackArgs=(success_msg,), errbackArgs=(error_msg,)
            )

    def halt_ok(self, unused, msg):
        self.client.logout()   # destroy cookie
        self.mainwindow.addToInfoArea(msg)

    def halt_err(self, unused, msg):
        # should not happen (haltSystem doesn't return a deferred)
        self.mainwindow.addToInfoArea(msg)

    def diagnostic(self):
        hostname = QHostnameObject.getInstance().cfg.hostname
        now = time.strftime('%Y-%m-%d-%H-%M', time.localtime())
        default_filename = 'diagnostic_%s_%s.tar.gz' % (hostname, now)
        filename = QFileDialog.getSaveFileName(self, tr('Select a destination'),
                                               QString(default_filename))

        if filename.isEmpty():
            return

        filename = unicode(filename)

        self.mainwindow.addToInfoArea(tr('Fetching the diagnostic file'))

        async = self.client.async()
        async.call('tools', 'getDiagnosticFile',
            callback = self.successDiag,
            errback = self.errorDiag,
            callbackArgs=(filename,),
            )

    def successDiag(self, diagnostic, filename):
        with open(filename, 'wb') as fd:
            fd.write(decodeFileContent(diagnostic))
        self.mainwindow.addToInfoArea(tr("Diagnostic file saved in '%s'") % filename, COLOR_SUCCESS)

    def errorDiag(self, error):
        self.mainwindow.addToInfoArea(tr("Fetching diagnostic failed"), COLOR_ERROR)
        warning = QMessageBox(self)
        warning.setWindowTitle(tr('Fetching diagnostic failed'))
        warning.setText(tr('An error has occurred while fetching the diagnostic file'))
        warning.setDetailedText(exceptionAsUnicode(error))
        warning.setIcon(QMessageBox.Warning)
        warning.exec_()

    def mkTimer(self):
        if self.timer is not None and self.timer.isActive():
            self.timer.stop()
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        QObject.connect(self.timer, SIGNAL('timeout()'),
                        self.refreshVpnSupport)
        self.timer.start(REFRESH_INTERVAL_MILLISECONDS)

    def lastConnections(self):
        lines = self.client.call('tools', 'getVpnSupportLastConnections')
        title = tr('Last connections from support')
        dialog = QDialog(self)
        dialog.setModal(False)
        dialog.setWindowTitle(title)
        layout = QVBoxLayout(dialog)
        dialog.setLayout(layout)
        button = NuConfPageKit.createButton(tr('Close'), dialog, dialog,
                                            dialog.close)
        text = QTextEdit()
        text.setReadOnly(True)
        for line in lines:
            m = LAST_CONNECTIONS_RE.search(line)
            if m:
                if m.group(2) == 'opened':
                    text.append(m.group(1) + u' ' + tr('Connection opened'))
                elif m.group(2) == 'closed':
                    text.append(m.group(1) + u' ' + tr('Connection closed'))
        for widget in (text, button):
            layout.addWidget(widget)
            widget.show()
        dialog.resize(800, 560)
        dialog.show()

    def refreshVpnSupport(self):
        def successCB(statusAndIP):
            if not statusAndIP:
                return
            self.vpnSupportStatusLabel.setText(', '.join(
                    _tr_first_element(statusAndIP)))
            if statusAndIP[0] == 'disabled':
                show = 0
            else:
                show = 1
                if statusAndIP[0] == 'pending':
                    self.mkTimer()
            for widget in (
                self.lastConnectionsButton, self.lastConnectionsLabel,
                self.refreshVpnSupportButton, self.startVpnSupportButton,
                self.stopVpnSupportButton, self.vpnSupportLabel,
                self.vpnSupportStatusLabel, self.vpnSupportStatusTextLabel):
                if show:
                    widget.show()
                else:
                    widget.hide()
        def errorCB(error):
            self.mainwindow.addToInfoArea(
                tr('Could not fetch VPN support status and IP'))
        async = self.client.async()
        async.call('tools', 'getVpnSupportStatusAndIP',
                   callback=successCB, errback=errorCB)
    def startVpnSupport(self):
        self.client.call('tools', 'vpnSupport', 'start')
        self.refreshVpnSupport()
    def stopVpnSupport(self):
        self.client.call('tools', 'vpnSupport', 'stop')
        self.refreshVpnSupport()

