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


from __future__ import with_statement

from os.path import expanduser

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QFileDialog

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.common.config import deserializeElement
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.client.qt.input_widgets import IpOrFqdnInput

from .directory_widget import DirectoryWidget

class KerberosWidget(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        DirectoryWidget.__init__(self, config, specific_config, mainwindow, parent=None)
        self.buildInterface(config)
        self.updateView()

    def updateView(self, config=None):
        if config is None:
            config = self.specific_config

        self.setText(self.kdc, config.kdc)
        self.setText(self.kerberos_domain, config.kerberos_domain)

    def buildInterface(self, config):
        self.kerberos_domain = QLineEdit()
        self.texts.add(self.kerberos_domain)
        self.kdc = IpOrFqdnInput()
        self.texts.add(self.kdc)
        upload_icon = QIcon(':/icons/up')
        upload_button = QPushButton(upload_icon, tr('Upload a Keytab'))

        self.form.addRow(tr('Kerberos domain'), self.kerberos_domain)
        self.form.addRow(tr('KDC'), self.kdc)
        self.form.addRow(tr('Upload a keytab'), upload_button)

        for widget, method in {
            self.kerberos_domain: self.setKerberos_domain,
            self.kdc: self.setKdc,
        }.iteritems():
            self.connect(widget, SIGNAL('textChanged(QString)'), self.signalModified)
            self.connect(widget, SIGNAL('textChanged(QString)'), method)

        self.connect(upload_button, SIGNAL('clicked()'), self.chooseKeytab)

    def setKerberos_domain(self, text):
        self.specific_config.kerberos_domain = self.readString(text)

    def setKdc(self, text):
        self.specific_config.kdc = self.readString(text)

    def chooseKeytab(self):
        homedir= expanduser("~")
        filename = unicode(
        QFileDialog.getOpenFileName(
            self.mainwindow,
            tr('Select a Kerberos Keytab file to upload'),
            homedir,
            tr('Kerberos keytab (*.keytab);; Any file (*)'),
            )
          )
        if not filename:
            return

        self.sendKeytab(filename)

    def sendKeytab(self, filename):
        with open(filename, 'rb') as fd:
            content = fd.read()

        content = encodeFileContent(content)

        self.mainwindow.addToInfoArea(tr('Upload a keytab file'))
        async = self.mainwindow.client.async()
        async.call('nuauth', "upload_krb_keytab", content,
            callback = self.success_upload,
            errback = self.error_upload
            )

    def success_upload(self, value):
        self.mainwindow.addToInfoArea(tr('[Keytab upload] Success!'))
        for item in deserializeElement(value):
            self.mainwindow.addToInfoArea(tr('[Keytab upload] %s') % item)

        self.signalModified()

    def error_upload(self, value):
        self.mainwindow.addToInfoArea(tr('[Keytab upload] Error!'), COLOR_ERROR)
        self.mainwindow.addToInfoArea(tr('[Keytab upload] %s') % value, COLOR_ERROR)

