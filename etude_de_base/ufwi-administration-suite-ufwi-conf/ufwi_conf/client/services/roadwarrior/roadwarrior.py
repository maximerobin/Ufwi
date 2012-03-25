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
    QCheckBox, QComboBox, QFileDialog, QFormLayout, QFrame, QGridLayout,
    QGroupBox, QLabel, QMessageBox, QPushButton, QVBoxLayout)
from PyQt4.QtCore import QString, SIGNAL

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.colors import COLOR_ERROR

from ufwi_conf.client.qt.ip_inputs import IpOrHostnameOrFqdnEdit, NetworkEdit, PortEdit
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.services.roadwarrior import QOpenVpnObject
from ufwi_conf.client.qt.iplist_editor import NetworkListEdit
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled

from nupki.qt.nupki_embed import PkiEmbedWidget

class RoadWarriorFrontend(ScrollArea):
    COMPONENT = 'openvpn'
    LABEL = tr('Mobile VPN')
    REQUIREMENTS = ('openvpn',)
    ICON = ':/icons/vpn.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        if not EDENWALL:
            raise NuConfModuleDisabled("Roadwarrior")
        self.loaded_done = False
        self.mainwindow = parent
        self.client = client
        self.modified = False
        self.error_message = ''
        self._buildGui()

        self.qopenvpnobject = QOpenVpnObject.getInstance()
        self.qopenvpnobject.openvpn = self.client.call('openvpn',
                                                       'getOpenVpnConfig')

        # FIXME: Remove isValid() or call it more even?
        self.isValid()

        self.resetConf()

    def _buildGui(self):
        frame = QFrame()
        layout = QVBoxLayout(frame)
        layout.addWidget(QLabel(tr("<H1>Mobile VPN</H1>")))

        self.activation_box = QGroupBox(tr("Feature Activation"))
        self.activation = QGridLayout(self.activation_box)

        # enabled checkbox:
        self.enabledCheckBox = QCheckBox()
        self.mainwindow.writeAccessNeeded(self.enabledCheckBox)
        self.connect(self.enabledCheckBox, SIGNAL('toggled(bool)'),
                     self.setEnabled)
        self.enabledLabel = QLabel(tr('Enable Mobile VPN'))
        self.activation.addWidget(self.enabledLabel, 0, 0)
        self.activation.addWidget(self.enabledCheckBox, 0, 1)
        layout.addWidget(self.activation_box)

        options_box = QGroupBox(tr("Network Configuration"))
        options = QFormLayout(options_box)

        self.serverIpEdit = IpOrHostnameOrFqdnEdit()
        self.connect(self.serverIpEdit, SIGNAL('editingFinished()'),
                     self.setServer)

        self.protocolComboBox = QComboBox()
        self.protocolComboBox.addItem('tcp')
        self.protocolComboBox.addItem('udp')
        self.connect(self.protocolComboBox,
                     SIGNAL('currentIndexChanged(QString)'), self.setProtocol)

        self.portEdit = PortEdit()
        self.connect(self.portEdit, SIGNAL('editingFinished()'), self.setPort)

        self.clientNetNetworkEdit = NetworkEdit()
        self.connect(self.clientNetNetworkEdit, SIGNAL('editingFinished()'),
                     self.setClientNetwork)

        self.redirectCheckBox = QCheckBox()
        self.connect(self.redirectCheckBox, SIGNAL('toggled(bool)'),
                     self.setRedirect)

        options.addRow(tr("Server public address (for client configuration)"),
                       self.serverIpEdit)
        options.addRow(tr("Protocol"), self.protocolComboBox)
        options.addRow(tr("Port"), self.portEdit)
        options.addRow(tr("Virtual network address of VPN clients"), self.clientNetNetworkEdit)
        options.addRow(tr("Redirect default gateway through the VPN"),
                       self.redirectCheckBox)

        self.pushed_routes = self._mkPushedRoutes(5)
        options.addRow(QLabel(tr("This VPN's routed networks")))
        options.addRow(self.pushed_routes)
        self.connect(self.pushed_routes, SIGNAL('textChanged()'), self.setModified)
        self.connect(self.pushed_routes, SIGNAL('textChanged()'), self.setPushedRoutes)

        layout.addWidget(options_box)

        self.pki_embed = PkiEmbedWidget(self.client, self, "openvpn", PkiEmbedWidget.SHOW_ALL | PkiEmbedWidget.CRL_OPTIONAL, self.setModified)
        layout.addWidget(self.pki_embed)

        self.mainwindow.writeAccessNeeded(
            self.serverIpEdit, self.protocolComboBox, self.portEdit,
            self.clientNetNetworkEdit, self.redirectCheckBox,
            self.pushed_routes, self.pki_embed)

        getClientConfigButton = QPushButton(tr('Get client configuration'))
        self.connect(getClientConfigButton, SIGNAL('clicked()'),
                     self.getClientConfig)
        layout.addWidget(getClientConfigButton)


        layout.addStretch()

        self.setWidget(frame)
        self.setWidgetResizable(True)

    def _mkPushedRoutes(self, lines):
        pushed_routes = NetworkListEdit()
        pushed_routes.setMaximumHeight(
            pushed_routes.fontMetrics().height() * lines
            )
        return pushed_routes

    def loaded(self):
        self.loaded_done = True

    def isLoaded(self):
        return self.loaded_done

    def isModified(self):
        return self.modified

    def isValid(self):
        valid, msg = self.qopenvpnobject.openvpn.isValidWithMsg()
        if msg is not None:
            self.error_message = msg

        cert_validity = self.pki_embed.validate()
        if cert_validity is not None:
            if msg is None:
                self.error_message = ''
            self.error_message += '<br/>' + cert_validity + '<br/>'
            self.mainwindow.addToInfoArea(cert_validity, category=COLOR_ERROR)
            valid = False
        return valid

    def resetConf(self):
        self.qopenvpnobject.openvpn = self.client.call('openvpn',
                                                       'getOpenVpnConfig')
        self.serverIpEdit.setText(unicode(self.qopenvpnobject.openvpn.server))
        self.portEdit.setText(unicode(self.qopenvpnobject.openvpn.port))
        index = self.protocolComboBox.findText(
            unicode(self.qopenvpnobject.openvpn.protocol))
        if index != -1:
            self.protocolComboBox.setCurrentIndex(index)
        self.clientNetNetworkEdit.setText(
            self.qopenvpnobject.openvpn.client_network)
        for input_widget in (self.serverIpEdit, self.portEdit):
            input_widget.validColor()
        if self.qopenvpnobject.openvpn.enabled:
            self.enabledCheckBox.setChecked(self.qopenvpnobject.openvpn.enabled)
        self.redirectCheckBox.setChecked(self.qopenvpnobject.openvpn.redirect)

        # Certificates configuration
        ssl_conf = self.qopenvpnobject.openvpn.getSSLDict()
        self.pki_embed.setConfig(ssl_conf)

        pushed_routes = self.qopenvpnobject.openvpn.manual_pushed_routes
        self.pushed_routes.clear()
        for net in pushed_routes:
            self.pushed_routes.append("%s\n" % net)

        self.setModified(False)

    def saveConf(self, message):
        conf = self.pki_embed.getConfig()
        self.qopenvpnobject.openvpn.setSSLDict(conf)

        serialized = self.qopenvpnobject.openvpn.serialize(downgrade=True)
        self.client.call("openvpn", 'setOpenVpnConfig', serialized, message)

    def setModified(self, isModified=True, message=u""):
        if isModified:
            self.modified = True
            self.mainwindow.setModified(self, True)
            if message:
                self.mainwindow.addToInfoArea(unicode(message))
            if self.isLoaded():
                self.qopenvpnobject.post_modify()
        else:
            self.modified = False

    def error(self, message):
        self.mainwindow.addToInfoArea(message, category=COLOR_ERROR)

    def getClientConfig(self):
        filename = QFileDialog.getSaveFileName(self, tr('Select a destination'),
                                               QString(u'client.ovpn'))
        if not filename:
            return
        async = self.client.async()
        self.desc = tr('Client configuration')
        async.call(
            "openvpn", 'getClientConfig',
            callback = self.successDiag,
            errback = self.errorDiag,
            callbackArgs=(filename, self.desc)
        )
    def successDiag(self, file_, filename, desc):
        with open(filename, 'wb') as fd:
            fd.write(decodeFileContent(file_))
        self.mainwindow.addToInfoArea(tr("%s saved in '%s'.") % (desc,
                                                                 filename))
    def errorDiag(self, error):
        self.mainwindow.addToInfoArea(tr("Fetching %s failed.") % self.desc)
        warning = QMessageBox(self)
        warning.setWindowTitle(tr('Fetching diagnostic failed'))
        warning.setText(tr('An error has occurred while fetching %s.') %
                        self.desc)
        warning.setDetailedText(exceptionAsUnicode(error))
        warning.setIcon(QMessageBox.Warning)
        warning.exec_()

    def setEnabled(self, value):
        if value != self.qopenvpnobject.openvpn.enabled:
            self.qopenvpnobject.openvpn.setEnabled(value)
            self.setModified()
    def setServer(self):
        value = self.serverIpEdit.text()
        if value != self.qopenvpnobject.openvpn.server:
            self.qopenvpnobject.openvpn.setServer(value)
            self.setModified()
    def setPort(self):
        value = self.portEdit.text()
        if value != self.qopenvpnobject.openvpn.port:
            self.qopenvpnobject.openvpn.setPort(value)
            self.setModified()
    def setProtocol(self, value):
        if value != self.qopenvpnobject.openvpn.protocol:
            self.qopenvpnobject.openvpn.setProtocol(value)
            self.setModified()
    def setClientNetwork(self):
        value = self.clientNetNetworkEdit.text()
        if value != self.qopenvpnobject.openvpn.client_network:
            self.qopenvpnobject.openvpn.setClientNetwork(value)
            self.setModified()
    def setRedirect(self, value):
        if value != self.qopenvpnobject.openvpn.redirect:
            self.qopenvpnobject.openvpn.setRedirect(value)
            self.setModified()

        #disable pushed_routes when redirecting default gw
        enable = (not value) and (not self.mainwindow.isReadOnly())
        self.pushed_routes.setEnabled(enable)

    def setPushedRoutes(self):
        if self.pushed_routes.isValid():
            pushed_routes = tuple(self.pushed_routes.value())
            self.qopenvpnobject.openvpn.manual_pushed_routes = pushed_routes

    def onApplyFinished(self):
        self.pki_embed.feed()

