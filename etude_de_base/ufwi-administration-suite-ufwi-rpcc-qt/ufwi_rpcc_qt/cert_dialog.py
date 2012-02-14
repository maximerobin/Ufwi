
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

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QFileDialog, QMessageBox
from functools import partial
from M2Crypto.X509 import load_cert, X509Error

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.central_dialog import CentralDialog

from .cert_dialog_ui import Ui_Dialog
from .ssl_config import QtSSLConfig

class CertificateDialog(CentralDialog, Ui_Dialog):
    def __init__(self, parent=None, options=None):
        CentralDialog.__init__(self, parent)
        self.setupUi(self)
        self.ssl_options = QtSSLConfig()
        self.fill()
        self.connect(self.use_ca_checkbox, SIGNAL("stateChanged(int)"), self.useCa)
        self.connect(self.use_cert_checkbox, SIGNAL("stateChanged(int)"), self.useCert)
        self.connect(self.use_crl_checkbox, SIGNAL("stateChanged(int)"), self.useCrl)
        self.connect(self.cert_button, SIGNAL("clicked()"), partial(self.selectFile, 'cert', tr('Select a certificate')))
        self.connect(self.key_button, SIGNAL("clicked()"), partial(self.selectFile, 'key', tr('Select a private key')))
        self.connect(self.ca_button, SIGNAL("clicked()"), partial(self.selectFile, 'ca', tr('Select a CA certificate')))
        self.connect(self.crl_button, SIGNAL("clicked()"), partial(self.selectFile, 'crl', tr('Select a CRL')))
        self.showCertificate('cert')
        self.showCertificate('ca')

        version_warning = QtSSLConfig.getM2CryptoVersionWarning()
        if version_warning:
            QMessageBox.warning(None, tr('SSL warning'), '\n'.join(version_warning))

        if QtSSLConfig.m2crypto_version < QtSSLConfig.M2CRYPTO_0_20_0_EW2:
            self.crl_groupbox.setEnabled(False)

    def _setFilename(self, widget, filename):
        if filename is None:
            filename = u''
        widget.setText(filename)

    def fill(self):
        self._setFilename(self.cert_path, self.ssl_options.cert)
        self._setFilename(self.key_path, self.ssl_options.key)
        self._setFilename(self.ca_path, self.ssl_options.ca)
        self._setFilename(self.crl_path, self.ssl_options.crl)

        use_ca = self.ssl_options.check
        self.use_ca_checkbox.setChecked(use_ca)
        if use_ca:
            self.useCa(Qt.Checked)
        else:
            self.useCa(Qt.Unchecked)

        use_cert = self.ssl_options.send_cert
        self.use_cert_checkbox.setChecked(use_cert)
        if use_cert:
            self.useCert(Qt.Checked)
        else:
            self.useCert(Qt.Unchecked)

        use_crl = bool(self.ssl_options.crl)
        self.use_crl_checkbox.setChecked(use_crl)
        self.useCrl(Qt.Checked)

        self.fqdn_checkbox.setChecked(self.ssl_options.fqdn_check)

    def saveOptions(self):
        self.ssl_options.check = self.use_ca_checkbox.isChecked()
        if not self.use_crl_checkbox.isChecked():
            self.ssl_options.crl = None
        self.ssl_options.fqdn_check = self.fqdn_checkbox.isChecked()
        self.ssl_options.send_cert = self.use_cert_checkbox.isChecked()

    def start(self):
        while True:
            ok = self.exec_()
            if not ok:
                return False
            self.saveOptions()
            err = self.ssl_options.validate()
            if err:
                QMessageBox.critical(self, tr("Edenwall authentication"), err)
                continue
            self.ssl_options.saveOptions()
            return True

    def useCa(self, state):
        use_ca = (state == Qt.Checked)
        self.ca_path.setEnabled(use_ca)
        self.ca_label.setEnabled(use_ca)
        self.ca_button.setEnabled(use_ca)
        self.fqdn_checkbox.setEnabled(use_ca)

    def useCert(self, state):
        use_cert = (state == Qt.Checked)
        self.label.setEnabled(use_cert)
        self.cert_path.setEnabled(use_cert)
        self.cert_button.setEnabled(use_cert)
        self.label_2.setEnabled(use_cert)
        self.key_path.setEnabled(use_cert)
        self.key_button.setEnabled(use_cert)
        self.cert_text.setEnabled(use_cert)

    def useCrl(self, state):
        use_crl = (state == Qt.Checked)
        self.crl_path.setEnabled(use_crl)
        self.crl_button.setEnabled(use_crl)

    def selectFile(self, attr, title, callback=None):
        dlg = QFileDialog(self, title)
        ok = dlg.exec_()
        if not ok:
            return
        filename = dlg.selectedFiles()[0]
        setattr(self.ssl_options, attr, unicode(filename))
        self.cert_path.setText(self.ssl_options.cert)
        self.key_path.setText(self.ssl_options.key)
        self.ca_path.setText(self.ssl_options.ca)
        self.crl_path.setText(self.ssl_options.crl)
        if attr == 'cert' or attr == 'ca':
            self.showCertificate(attr)

    def showCertificate(self, attr):
        filename = getattr(self.ssl_options, attr)
        if filename:
            try:
                cert = load_cert(filename)
                txt = cert.as_text()
            except X509Error:
                txt = tr('Selected file is not a PEM encoded certificate.')
            except IOError:
                txt = tr('Unable to read the certificate.')
        else:
            txt = tr('No certificate selected')
        widget = getattr(self, attr + '_text')
        widget.document().setPlainText(txt)
        scrollbar = widget.horizontalScrollBar()
        scrollbar.setValue(scrollbar.minimum())
        scrollbar = widget.verticalScrollBar()
        scrollbar.setValue(scrollbar.minimum())
