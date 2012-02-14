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
    QLabel, QGroupBox, QCheckBox, QFormLayout, QRadioButton, QButtonGroup,
    QVBoxLayout, QFrame)
from PyQt4.QtCore import SIGNAL, Qt

from ufwi_rpcd.common import EDENWALL, tr
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.client.qt.iplist_editor import NetworkListEdit
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.services.authentication import QAuthCertObject
from nupki.qt.nupki_embed import PkiEmbedWidget

class AuthenticationFrontend(ScrollArea):
    COMPONENT = 'auth_cert'
    LABEL = tr('Authentication server')
    REQUIREMENTS = ('auth_cert',)
    ICON = ':/icons/auth_protocol.png'

    def __init__(self, client, parent):
        self.__loading = True
        ScrollArea.__init__(self)
        self.mainwindow = parent
        self.client = client
        self.modified = False

        self.qauthcertobject = QAuthCertObject.getInstance()

        frame = QFrame(self)

        layout = QVBoxLayout(frame)

        layout.addWidget(QLabel('<H1>%s</H1>' % tr('Authentication server') ))

        head_box = QGroupBox(tr("How the authentication server handles certificates"))
        head = QFormLayout(head_box)
        self.strictCheckBox = QCheckBox()
        head.addRow(QLabel(tr("Strict mode (check the client's certificate against the installed CA)")), self.strictCheckBox)
        self.connect(self.strictCheckBox, SIGNAL('toggled(bool)'),
                     self.setStrict)

        self.cl_auth_box = QGroupBox(tr("Client authentication with a certificate is"))
        cl_auth = QVBoxLayout(self.cl_auth_box)
        self.auth_by_cert = QButtonGroup()
        self.auth_by_cert.setExclusive(True)

        self.mainwindow.writeAccessNeeded(self.strictCheckBox)

        labels = [tr('forbidden'), tr('allowed'), tr('mandatory')]
        for index, label_button in enumerate(labels):
            button = QRadioButton(label_button)
            self.auth_by_cert.addButton(button, index)
            cl_auth.addWidget(button)
            self.mainwindow.writeAccessNeeded(button)
        self.auth_by_cert.button(0).setChecked(Qt.Checked)
        self.connect(self.auth_by_cert, SIGNAL('buttonClicked(int)'),
                     self.auth_by_cert_modified)


        # Captive portal
        # --------------
        self.portal_groupbox = QGroupBox(tr("Captive portal"))
        self.portal_groupbox.setLayout(QVBoxLayout())

        # Enabled checkbox:
        self.portal_checkbox = QCheckBox(tr("Enable captive portal"))
        self.connect(self.portal_checkbox, SIGNAL('toggled(bool)'),
                     self.setPortalEnabled)

        # List of networks redirected to the captive portal:
        self.portal_nets_groupbox = QGroupBox(
            tr("Networks handled by the captive portal"))
        self.portal_nets_groupbox.setLayout(QVBoxLayout())
        self.portal_nets_edit = NetworkListEdit()
        self.connect(self.portal_nets_edit, SIGNAL('textChanged()'), self.setPortalNets)
        self.portal_nets_groupbox.layout().addWidget(self.portal_nets_edit)

        # Pack the widgets:
        for widget in (self.portal_checkbox, self.portal_nets_groupbox):
            self.portal_groupbox.layout().addWidget(widget)
        self.mainwindow.writeAccessNeeded(self.portal_checkbox)
        self.mainwindow.writeAccessNeeded(self.portal_nets_edit)

        if not EDENWALL:
            self.portal_groupbox.setVisible(False)


        # authentication server
        self.pki_widget = PkiEmbedWidget(self.client, self, 'auth_cert', PkiEmbedWidget.SHOW_ALL|PkiEmbedWidget.CRL_OPTIONAL, self.setModified)
        self.mainwindow.writeAccessNeeded(self.pki_widget)

        layout.addWidget(head_box)
        layout.addWidget(self.cl_auth_box)
        layout.addWidget(self.portal_groupbox)
        layout.addWidget(self.pki_widget)
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

    def saveConf(self, message):
        self.qauthcertobject.auth_cert.auth_by_cert = self.auth_by_cert.checkedId()

        conf = self.pki_widget.getConfig()
        self.qauthcertobject.auth_cert.setSSLDict(conf)

        serialized = self.qauthcertobject.auth_cert.serialize(downgrade=True)
        self.client.call('auth_cert', 'setAuthCertConfig', serialized, message)

    def resetConf(self):
        auth_cert_loaded = self._reset_helper(
            'auth_cert',
            'getAuthCertConfig',
            self.qauthcertobject,
            tr("Authentication interface enabled"),
            tr("Authentication disabled: backend not loaded")
        )
        self.setModified(False)

        remote = self.qauthcertobject.auth_cert.getReceivedSerialVersion()
        if remote < 3:
            self.mainwindow.addWarningMessage(tr('Captive portal configuration disabled: this frontend and your appliance software versions are not compatible.'))
        enable_portal = (
            auth_cert_loaded
            and EDENWALL
            and remote >= 3
            )
        self.portal_groupbox.setVisible(enable_portal)

        if not auth_cert_loaded:
            return


        self.strictCheckBox.setChecked(self.qauthcertobject.auth_cert.strict)
        if not self.qauthcertobject.auth_cert.auth_by_cert:
            self.qauthcertobject.auth_cert.auth_by_cert = 0
        self.auth_by_cert.button(
            self.qauthcertobject.auth_cert.auth_by_cert).setChecked(True)

        # Captive portal:
        self.portal_checkbox.setChecked(
            self.qauthcertobject.auth_cert.portal_enabled)
        self.portal_nets_edit.setIpAddrs(
            self.qauthcertobject.auth_cert.portal_nets)

        # Certificate (PKI):
        pki_conf = self.qauthcertobject.auth_cert.getSSLDict()
        self.pki_widget.setConfig(pki_conf)

    def error(self, message):
        self.mainwindow.addToInfoArea(message, category=COLOR_ERROR)

    def auth_by_cert_modified(self, idbox):
        button_name = self.auth_by_cert.button(idbox).text()
        info = tr("Certificates - Authentication with client certificate : '%s'") % button_name
        self.setModified(message=info)

    def setPortalEnabled(self, value):
        if value != self.qauthcertobject.auth_cert.portal_enabled:
            self.qauthcertobject.auth_cert.setPortalEnabled(value)
            self.setModified()

    def setPortalNets(self):
        if self.portal_nets_edit.isValid():
            self.qauthcertobject.auth_cert.setPortalNets(
                self.portal_nets_edit.value())
            self.setModified()

    def setStrict(self, value):
        if value != self.qauthcertobject.auth_cert.strict:
            self.qauthcertobject.auth_cert.setStrict(value)
            self.setModified()
        self.cl_auth_box.setEnabled(value)

    def isValid(self):
        cert_validity = self.pki_widget.validate()
        if cert_validity is not None:
            self.error_message = '<br/>' + cert_validity + '<br/>'
            self.mainwindow.addToInfoArea(cert_validity, category=COLOR_ERROR)
            return False
        return True

    def onApplyFinished(self):
        self.pki_widget.feed()

