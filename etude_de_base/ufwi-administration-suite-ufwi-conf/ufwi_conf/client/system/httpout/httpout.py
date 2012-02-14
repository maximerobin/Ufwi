# -*- coding: utf-8 -*-
"""
$Id$
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

from PyQt4.QtCore import QCoreApplication, Qt, SIGNAL
from PyQt4.QtGui import (
    QCheckBox,
    QFormLayout,
    QLabel,
    QLineEdit,
    QWidget,
)

from ufwi_rpcd.common import tr

from ufwi_conf.client.qt.ip_inputs import IpOrHostnameOrFqdnEdit, PortEdit
from ufwi_conf.client.qt.input_widgets import PasswordInput
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
from ufwi_conf.client.system.httpout import QHttpOutObject
translate = QCoreApplication.translate

class HttpOutFrontend(FullFeaturedScrollArea):
    COMPONENT = 'httpout'
    LABEL = tr('Outgoing HTTP proxy')
    REQUIREMENTS = ('httpout',)
    FIXED_WIDTH = 40
    ICON = ':/icons/worldmap.png'

    def __init__(self, client, parent):
        self.qhttpoutobject = QHttpOutObject.getInstance()
        FullFeaturedScrollArea.__init__(self, client, parent)
        self.client = client
        self.mainwindow = parent
        self.buildInterface()
        self.setViewData()

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (("httpout", 'getHttpOutConfig'),)

    def addField(self, field_name, input_):
        field = input_(self)
        field.setFixedWidth(field.fontMetrics().averageCharWidth() * self.FIXED_WIDTH)
        self.mainwindow.writeAccessNeeded(field)
        self.form.addRow(field_name, field)
        return field

    def buildInterface(self):
        main_widget = QWidget()
        self.setWidget(main_widget)
        self.setWidgetResizable(True)
        self.form = QFormLayout(main_widget)

        title = u'<h1>%s</h1>' % \
            self.tr('Outgoing HTTP and HTTPS proxy configuration')

        self.form.addRow(QLabel(title))
        self.use_proxy = self.addField(tr("Use proxy"), QCheckBox)
        self.host = self.addField(tr("Host"), IpOrHostnameOrFqdnEdit)
        self.port = self.addField(tr("Port"), PortEdit)
        self.user = self.addField(tr("User"), QLineEdit)
        self.password = self.addField(tr("Password"), PasswordInput)

        self.connect(self.use_proxy, SIGNAL('stateChanged(int)'),
                     self.setUseProxy)
        for pair in (
            (self.host, self.setHost),
            (self.port, self.setPort),
            (self.user, self.setUser),
            (self.password, self.setPassword),
        ):
            self.connect(pair[0], SIGNAL('textEdited(QString)'), pair[1])

    def fetchConfig(self):
        self.qhttpoutobject.httpout = self.client.call('httpout',
                                                       'getHttpOutConfig')

    def isValid(self):
        return True

    def sendConfig(self, message):
        serialized = self.qhttpoutobject.httpout.serialize()
        self.client.call("httpout", 'setHttpOutConfig', serialized, message)

    def setViewData(self):
        self.use_proxy.setChecked(self.qhttpoutobject.httpout.use_proxy)
        self.host.setText(unicode(self.qhttpoutobject.httpout.host))
        self.port.setText(unicode(self.qhttpoutobject.httpout.port))
        self.user.setText(unicode(self.qhttpoutobject.httpout.user))
        self.password.setText(self.qhttpoutobject.httpout.password)
        for input_widget in (self.host, self.port):
            input_widget.validColor()
        if self.qhttpoutobject.httpout.use_proxy:
            self.toggleFields(Qt.Checked)
        else:
            self.toggleFields(Qt.Unchecked)

    def setModified(self, modified=True):
        self._modified = modified
        if modified:
            self.mainwindow.setModified(self)

    def toggleFields(self, value):
        for w in (self.host, self.port, self.user, self.password):
            w.setDisabled(value != Qt.Checked)
            try:
                w.setValidatorEnabled(value == Qt.Checked)
            except AttributeError:
                pass  # No validator.

    # Slots:

    def setUseProxy(self, value):
        if value != self.qhttpoutobject.httpout.use_proxy:
            self.qhttpoutobject.httpout.setUseProxy(value)
            self.setModified()
        self.toggleFields(value)
    def setHost(self, value):
        if value != self.qhttpoutobject.httpout.host:
            self.qhttpoutobject.httpout.setHost(value)
            self.setModified()
    def setPort(self, value):
        if value != self.qhttpoutobject.httpout.port:
            self.qhttpoutobject.httpout.setPort(value)
            self.setModified()
    def setUser(self, value):
        if value != self.qhttpoutobject.httpout.user:
            self.qhttpoutobject.httpout.setUser(value)
            self.setModified()
    def setPassword(self, value):
        if value != self.qhttpoutobject.httpout.password:
            self.qhttpoutobject.httpout.setPassword(value)
            self.setModified()

