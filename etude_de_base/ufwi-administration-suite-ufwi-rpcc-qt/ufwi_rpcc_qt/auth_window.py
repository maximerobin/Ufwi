
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

from PyQt4.QtCore import Qt, SIGNAL, QRegExp
from PyQt4.QtGui import QDesktopWidget
from ufwi_rpcc_qt.ufwi_rpcd_client import RpcdClient, DEFAULT_STREAMING_PORT
from ufwi_rpcd.client.base import (RpcdError,
    DEFAULT_HOST, DEFAULT_PROTOCOL, DEFAULT_HTTP_PORT, DEFAULT_HTTPS_PORT
    )
from auth_ui import Ui_AuthWindow
from PyQt4.QtGui import QMessageBox
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import writeError
from ufwi_rpcc_qt.central_dialog import CentralDialog
from ufwi_rpcc_qt.user_settings import UserSettings
from ufwi_rpcc_qt.cert_dialog import CertificateDialog
from .ssl_config import QtSSLConfig
from ufwi_rpcd.common import EDENWALL

DEFAULT_LOGIN = u'admin'

PROTOCOLS = ['https', 'http']

class AuthWindow(CentralDialog, Ui_AuthWindow):
    def __init__(self, parent=None, options=None):
        CentralDialog.__init__(self, parent)
        self.setupUi(self)
        self.options = options
        self.ssl_options = QtSSLConfig()
        self.load_settings()
        self.host_edit.lineEdit().setText(self.host)
        self.streaming_spinbox.setValue(self.streaming_port)
        self.login_edit.setText(self.login)
        self.setProtocol(self.protocol)
        if (self.protocol == u'http' and self.port == DEFAULT_HTTP_PORT) \
        or (self.protocol == u'https' and self.port == DEFAULT_HTTPS_PORT):
            self.defaultPort(True)
        else:
            self.customPort(True)
        self.port_spinbox.setValue(self.port)

        self.connect(self.custom_radio, SIGNAL("toggled(bool)"), self.customPort)
        self.connect(self.default_radio, SIGNAL("toggled(bool)"), self.defaultPort)
        self.connect(self.protocol_combo, SIGNAL("currentIndexChanged(int)"), self.protocolChanged)
        self.connect(self.configure_ssl, SIGNAL("clicked()"), self.configureSSL)
        self.connect(self.bt_advanced, SIGNAL("toggled(bool)"), self.toggle_advanced)

        if not EDENWALL:
            self.setWindowTitle( self.tr("NuFirewall Authentication"))

        if options:
            if options.host:
                self.host_edit.lineEdit().setText(options.host)
            if options.username:
                self.login_edit.setText(options.username)
            if options.password:
                self.password_edit.setText(options.password)
            if options.cleartext:
                self.setProtocol("http")
            if options.secure:
                self.setProtocol("https")
            if options.port:
                self.port_spinbox.setValue(options.port)
                self.custom_radio.setChecked(True)
            if options.streaming_port:
                self.streaming_spinbox.setValue(options.streaming_port)

        self.connectButtons(self.buttonBox)
        hostname_regex = QRegExp(
            ur"^[a-z0-9_-]+(\.[a-z0-9_-]*)*$",
            Qt.CaseInsensitive)
        self.setRegExpValidator(self.host_edit.lineEdit(), hostname_regex)
        notempty = QRegExp(ur"^.+$")
        self.setRegExpValidator(self.login_edit, notempty)

        self.toggle_advanced(False)

        self.center()

    def setProtocol(self, protocol):
        try:
            index = PROTOCOLS.index(protocol)
        except ValueError:
            # Use https by default
            index = 0
        self.protocol_combo.setCurrentIndex(index)

    def center(self):
        screen = QDesktopWidget().screenGeometry()
        size =  self.geometry()
        self.move((screen.width()-size.width())/2, (screen.height()-size.height())/2)

    def customPort(self, checked):
        if checked:
            self.port_spinbox.setEnabled(True)
            self.default_radio.setChecked(False)
            self.custom_radio.setChecked(True)

    def defaultPort(self, checked):
        if checked:
            self.port_spinbox.setEnabled(False)
            self.default_radio.setChecked(True)
            self.custom_radio.setChecked(False)

    def protocolChanged(self, index):
        self.protocol = PROTOCOLS[index]
        if self.protocol == u'https':
            self.port = DEFAULT_HTTPS_PORT
        else:
            self.port = DEFAULT_HTTP_PORT
        self.port_spinbox.setValue(self.port)

    def toggle_advanced(self, toggled):
        if toggled:
            self.frame.show()
            self.setMinimumSize( self.sizeHint() )
            self.resize( self.sizeHint() )
        else:
            self.frame.hide()
            self.setMinimumSize( self.sizeHint() )
            self.resize( self.sizeHint() )

    def get_client(self, client_name, client_release=None):
        tries = 0
        while True:
            tries += 1
            if (1 < tries) \
            or (self.options and not(self.options.username and self.options.password and self.options.host)):
                ret = self.exec_()
                if not ret:
                    return None
            try:
                self.host = unicode(self.host_edit.lineEdit().text())
                self.protocol = PROTOCOLS[self.protocol_combo.currentIndex()]
                if self.custom_radio.isChecked():
                    self.port = self.port_spinbox.value()
                elif self.protocol == 'https':
                    self.port = DEFAULT_HTTPS_PORT
                else: # self.protocol == 'http'
                    self.port = DEFAULT_HTTP_PORT
                self.streaming_port = self.streaming_spinbox.value()
                self.login = self.login_edit.text()
                protocol = unicode(self.protocol)
                options = {
                    'host': unicode(self.host),
                    'protocol': protocol,
                    'client_name': client_name,
                    'client_release': client_release,
                }
                options['port'] = self.port
                options['streaming_port'] = self.streaming_port
                options['ssl_config'] = self.ssl_options
                self.check_proto_not_cleartext(options)
                client = RpcdClient(**options)
                client.authenticate(
                    unicode(self.login),
                    unicode(self.password_edit.text()))
                self.save_settings()
                self.ssl_options.saveOptions()
                return client
            except RpcdError, err:
                writeError(err, unicode(self.tr("Connection error")))
                QMessageBox.critical(self, self.tr("Connection error"), unicode(err))

    def save_settings(self):
        settings = UserSettings("Rpcd")
        settings.beginGroup("Client")
        hosts_list = [self.host]
        for i in xrange(self.host_edit.count()):
            s = unicode(self.host_edit.itemText(i))
            if s != self.host:
                hosts_list.append(s)
        settings.setStringList("host", hosts_list)
        settings.setUnicode("login", self.login)
        settings.setInt("port", self.port)
        settings.setInt("streaming_port", self.streaming_port)
        settings.setUnicode("protocol", self.protocol)
        # no, we won't save the password (plain text)
        settings.endGroup()

    def load_settings(self):
        settings = UserSettings("Rpcd")
        settings.beginGroup("Client")
        self.login = settings.getUnicode("login", DEFAULT_LOGIN)

        host_list = settings.getStringList("host", None)
        if not host_list:
            host_list = [DEFAULT_HOST]
        self.host = unicode(host_list[0])
        for host in host_list:
            self.host_edit.addItem(host)

        self.protocol = settings.getUnicode("protocol", DEFAULT_PROTOCOL)
        self.port = settings.getInt("port", DEFAULT_HTTPS_PORT)
        self.streaming_port = settings.getInt("streaming_port", DEFAULT_STREAMING_PORT)
        settings.endGroup()

    def check_proto_not_cleartext(self, options):
        if options['protocol'] == 'http':
            ret = QMessageBox.warning( self, tr("Insecure protocol"),
                tr("You are connecting using an insecure protocol. Everything will be transmitted in clear, including your login and password.\nDo you really want to do that ?"),
                QMessageBox.Ok | QMessageBox.Cancel)
            if ret != QMessageBox.Ok:
                raise RpcdError("UserError", tr("Aborted by user"))

    def configureSSL(self):
        dlg = CertificateDialog()
        if dlg.start():
            self.ssl_options = dlg.ssl_options

