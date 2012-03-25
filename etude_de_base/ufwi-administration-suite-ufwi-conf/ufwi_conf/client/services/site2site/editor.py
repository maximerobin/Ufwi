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


from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QDialog, QMessageBox

from ufwi_rpcd.common import tr
from ufwi_conf.common.site2site_cfg import VPN
from ufwi_conf.common.site2site_cfg import PSK
from ufwi_conf.common.site2site_cfg import Fingerprint
from ufwi_conf.client.qt.abstract_editor import AbstractEditor

from .vpn_editor_ui import Ui_Dialog
from .new_fingerprint_ui import Ui_FingerprintDialog

VPN_ROLE = Qt.UserRole + 20

def _hms(seconds):
    hours = seconds / 3600
    seconds -= 3600*hours
    minutes = seconds / 60
    seconds -= 60*minutes
    return hours, minutes, seconds


_WARNING_RSA_WITHOUT_KEY = tr(
    "The RSA key system is selected, but no RSA key is registered "
    "on this system",
    "Warning dialog that can be displayed when user attempts to validate "
    "an ipsec config dialog"
)
_WARNING_RSA_WITHOUT_KEY_TITLE = tr("Invalid configuration", "title of a popup")

class VPNEditor(AbstractEditor, Ui_Dialog):
    def __init__(self, vpn, rsamodel, parent=None):
        self.__rsamodel = rsamodel
        AbstractEditor.__init__(self, vpn, parent)

    def _setup_ui(self):
        self.setupUi(self)
        self.rsacombo.setModel(self.__rsamodel)
        self.__connect_signals()

    def _validate(self):
        if self.rsa_choice.isChecked() and self.rsacombo.currentIndex() < 0:
            QMessageBox.warning(self,
                _WARNING_RSA_WITHOUT_KEY_TITLE,
                _WARNING_RSA_WITHOUT_KEY
                )
            return False
        return True

    def fix_identifier(self, qstring):
        self.identifier.setText(
            ''.join(
                unicode(self.identifier.text()).split()
                )
            )

    def __connect_signals(self):
        self.connect(self.rsacombo, SIGNAL('currentIndexChanged(int)'), self.select_fingerprint)
        self.connect(self.importrsa, SIGNAL('clicked()'), self.import_rsa)
        self.connect(self.identifier, SIGNAL('textChanged(QString)'), self.fix_identifier)

        self.connect(self.key_lifetime_dial, SIGNAL("valueChanged(int)"), self.__key_life_ints)
        self.connect(self.ike_lifetime_dial, SIGNAL("valueChanged(int)"), self.__ike_life_ints)

        for field in (
            self.key_lifetime_hours,
            self.key_lifetime_minutes,
            self.key_lifetime_seconds):
            self.connect(
                field,
                SIGNAL("valueChanged(int)"),
                self.__key_life_texts_to_spin
                )

        for field in (
            self.ike_lifetime_hours,
            self.ike_lifetime_minutes,
            self.ike_lifetime_seconds):
            self.connect(
                field,
                SIGNAL("valueChanged(int)"),
                self.__ike_life_texts_to_spin
                )

    def select_fingerprint(self, fingerprint_row):
        print "select_fingerprint"

    def import_rsa(self):

        dialog = QDialog()
        ui = Ui_FingerprintDialog()
        ui.setupUi(dialog)
        result = dialog.exec_()
        if not result:
            return
        fingerprint = Fingerprint(
            identifier=unicode(ui.identifier.text()),
            fingerprint=unicode(ui.fingerprint.toPlainText())
            #set peer on successful exit only
            )
        index = self.rsacombo.rootModelIndex()
        self.__rsamodel.appendvalue(fingerprint, index)

    def _import_data(self):
        for attr in VPN.BOOL_ATTRS:
            self._import('bool', attr)
        for attr in VPN.STRING_ATTRS:
            self._import('string', attr)

        self.__import_key_lifetime()
        self.__import_ike_lifetime()
        self.__import_key()

    def __import_key_lifetime(self):
        self.key_lifetime_dial.setValue(self._cfg.ike_lifetime)
        self.__key_life_ints(self._cfg.key_life)

    def __import_ike_lifetime(self):
        self.ike_lifetime_dial.setValue(self._cfg.ike_lifetime)
        self.__ike_life_ints(self._cfg.ike_lifetime)

    def __ike_life_ints(self, seconds):
        hours, minutes, seconds = _hms(seconds)
        self.ike_lifetime_hours.setValue(hours)
        self.ike_lifetime_minutes.setValue(minutes)
        self.ike_lifetime_seconds.setValue(seconds)

    def __key_life_ints(self, seconds):
        hours, minutes, seconds = _hms(seconds)
        self.key_lifetime_hours.setValue(hours)
        self.key_lifetime_minutes.setValue(minutes)
        self.key_lifetime_seconds.setValue(seconds)

    def __key_life_texts_to_spin(self, value):
        seconds = \
            self.key_lifetime_hours.value() * 3600 \
            + self.key_lifetime_minutes.value() * 60 \
            + self.key_lifetime_seconds.value()
        self.key_lifetime_dial.setValue(seconds)
        if seconds > 86400:
            self.__key_life_ints(86400)

    def __ike_life_texts_to_spin(self, value):
        seconds = \
            self.ike_lifetime_hours.value() * 3600 \
            + self.ike_lifetime_minutes.value() * 60 \
            + self.ike_lifetime_seconds.value()
        self.ike_lifetime_dial.setValue(seconds)
        if seconds > 86400:
            self.__ike_life_ints(86400)

    def __import_key(self):
        if self._cfg.keytype() == PSK:
            self.psk_choice.setChecked(Qt.Checked)
            return
        #RSA
        self.rsa_choice.setChecked(Qt.Checked)
        row = self.__rsamodel.rowOf(self._cfg.fingerprint)
        if row != -1:
            self.rsacombo.setCurrentIndex(row)

    def _report_data(self):
        for attr in VPN.BOOL_ATTRS:
            self._export('bool', attr)
        for attr in VPN.STRING_ATTRS:
            self._export('string', attr)

        self.__report_key_lifetime()
        self.__report_ike_lifetime()
        self.__report_key()

    def __report_key_lifetime(self):
        self._cfg.key_life = self.key_lifetime_dial.value()

    def __report_ike_lifetime(self):
        self._cfg.ike_lifetime = self.ike_lifetime_dial.value()

    def __report_key(self):
        if not self.rsa_choice.isChecked():
            return
        row = self.rsacombo.currentIndex()
        fingerprint = self.__rsamodel.fingerprintAtRow(row)
        fingerprint.peer = self._cfg.gateway
        self._cfg.fingerprint = fingerprint

