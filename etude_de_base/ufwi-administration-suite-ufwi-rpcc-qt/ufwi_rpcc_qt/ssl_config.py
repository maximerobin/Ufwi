
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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QMessageBox, QDialog
from os.path import exists
from collections import defaultdict

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.logger import Logger
from ufwi_rpcd.client.ssl_config import ClientSSLConfig
from ufwi_rpcc_qt.ssl_passwd_ui import Ui_SSLDialog
from .user_settings import UserSettings

SETTINGS_APP_NAME = "edenwall-authentication"

class SSLPasswordDialog(QDialog, Ui_SSLDialog):
    def __init__(self, parent = None):
        QDialog.__init__(self)
        Ui_SSLDialog.__init__(self)
        self.setupUi(self)

class QtSSLConfig(ClientSSLConfig):
    def __init__(self):
        ClientSSLConfig.__init__(self)
        self.logger = Logger("ssl")
        self.temp_ignored_errors = defaultdict(set)
        self.loadOptions()
        # FIXME: call self.check()

    def _setUnicode(self, settings, key, value):
        if value is None:
            value = u''
        settings.setUnicode(key, value)

    def saveOptions(self):
        settings = UserSettings(SETTINGS_APP_NAME)
        settings.setInt('fqdn_check', self.fqdn_check)
        settings.setInt('check_peer', self.check)
        settings.setInt('send_cert', self.send_cert)

        ## option 'check' removed in 4.1.0 : disable ssl authentication and ssl checks
        # when it's disabled for backward compatibily
        # settings.setInt('check', self.enable_ssl_checks)
        settings.setInt('check', True)

        self._setUnicode(settings, 'cert', self.cert)
        self._setUnicode(settings, 'key', self.key)
        self._setUnicode(settings, 'ca', self.ca)
        self._setUnicode(settings, 'crl', self.crl)
        errors = self.generateIgnoredErrors(self.ignored_errors)
        if errors:
            settings.setStringList('ignored_errors', errors)

    def loadOptions(self):
        settings = UserSettings(SETTINGS_APP_NAME)
        self.check = settings.getInt('check_peer', self.check)
        self.fqdn_check = settings.getInt('fqdn_check', self.fqdn_check)
        self.send_cert = settings.getInt('send_cert', self.send_cert)

        ## option 'check' removed in 4.1.0 : disable ssl authentication and ssl checks
        # when it's disabled for backward compatibily
        # self.enable_ssl_checks = settings.getInt('check', self.enable_ssl_checks)
        if settings.getInt('check', True) == False:
            self.send_cert = False
            self.check = False

        for name in ('cert', 'key', 'ca', 'crl'):
            value = getattr(self, name)
            new_value = settings.getUnicode(name, value)
            if new_value:
                if exists(new_value):
                    setattr(self, name, new_value)
                else:
                    self.logger.info("Ignore %s=%s (missing file)"  % (name, new_value))
            else:
                setattr(self, name, u'')
        self.ignored_errors = self.parseIgnoredErrors(settings.getStringList('ignored_errors'))

    def parseIgnoredErrors(self, lst):
        # Parse a list of errors to ignore during verification
        # The list is alist of fingerprint followed by the error to ignore:
        # lst = [ fingerprint 1, error ignored for fingerprint 1, fingerprint 1, other error ... ]
        ignored_errors = defaultdict(set)

        if lst is None:
            return ignored_errors

        while len(lst) > 1:
            fingerprint = lst[0]
            err_no = int(lst[1])
            ignored_errors[fingerprint].add(err_no)
            del lst[0:2]

        return ignored_errors

    def generateIgnoredErrors(self, ignored_errors):
        lst = []
        for fingerprint in ignored_errors:
            for err_no in ignored_errors[fingerprint]:
                lst.append(fingerprint)
                lst.append(str(err_no))
        return lst

    def _user_verify(self, error):
        # temporary implementation using a QMessageBox
        # XXX in the future, we should create a dedicated UI

        # Check wether we should ignore this error
        err_no = error.number
        fingerprint = error.getFingerprint()
        if (fingerprint in self.ignored_errors) \
        and (err_no in self.ignored_errors[fingerprint]):
            return 1
        if (fingerprint in self.temp_ignored_errors) \
        and (err_no in self.temp_ignored_errors[fingerprint]):
            return 1

        msgBox = QMessageBox()
        msgBox.setIcon(QMessageBox.Critical)
        msgBox.setTextFormat(Qt.RichText)
        message = u"<b>%s!</b>" %  error.getMessage()
        msgBox.setText( tr('The "%s" certificate is invalid: %s') % (error.getSubject(), message))
        msgBox.setInformativeText( tr("Do you want to accept the following certificate?") )
        msgBox.setDetailedText(error.getCertText())
        msgBox.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        msgBox.addButton( tr("For this session only"), QMessageBox.AcceptRole )
        msgBox.setDefaultButton(QMessageBox.Cancel)

        ret = msgBox.exec_()
        if ret == QMessageBox.Ok:
            self.ignored_errors[fingerprint].add(err_no)
            self.saveOptions()
        elif ret == QMessageBox.AcceptRole:
            self.temp_ignored_errors[fingerprint].add(err_no)
        if ret in (QMessageBox.Ok, QMessageBox.AcceptRole):
            return 1
        else:
            return 0

    def user_verify(self, error):
        try:
            return self._user_verify(error)
        except Exception, err:
            self.logger.writeError(err, tr("Certificate validation error"))
            return 0

    def get_key_password(self, v):
        try:
            dlg = SSLPasswordDialog()
            if dlg.exec_():
                # Not supported by m2crypto:
                #return unicode(dlg.password.text())
                return str(dlg.password.text())
            return ''
        except Exception, err:
            self.logger.writeError(err, tr("Unable to get the certificate password"))

    def sslInfo(self, info):
        info.logInto(self.logger)

