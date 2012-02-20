# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

from PyQt4.QtCore import QVariant, SIGNAL, QRegExp
from PyQt4.QtGui import QMessageBox, QLineEdit, QComboBox, QSpinBox, QCheckBox

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.central_dialog import CentralDialog, IP_OR_HOSTNAME_OR_FQDN_REGEXP

from ufwi_log.client.qt.ui.config_ui import Ui_ConfigDialog

ASCII7_REGEXP = QRegExp(ur"^[\x00-\x7f]*$")

class ConfigDialog(CentralDialog):
    def __init__(self, client, parent):

        CentralDialog.__init__(self, parent)
        self.main_window = parent
        self.ui = Ui_ConfigDialog()
        self.ui.setupUi(self)

        self.client = client
        self.firewall = ''

        if self.client.call('CORE', 'hasComponent', 'multisite_master'):
            firewalls = self.client.call('multisite_master', 'listFirewalls')
            self.ui.firewall.addItem(self.tr('EMF appliance'), QVariant(''))
            firewalls.sort()
            for fw, state, error, lastseen, ip in firewalls:
                self.ui.firewall.addItem(unicode(self.tr('Remote: %s')) % fw, QVariant(fw))
            self.connect(self.ui.firewall, SIGNAL('currentIndexChanged(int)'), self.firewallChanged)
        else:
            self.ui.firewall.hide()
            self.ui.firewall_label.hide()

        self.connectButtons(self.ui.buttonBox)
        self.setRegExpValidator(self.ui.hostnameEdit, IP_OR_HOSTNAME_OR_FQDN_REGEXP)
        self.setRegExpValidator(self.ui.databaseEdit, ASCII7_REGEXP)
        self.setRegExpValidator(self.ui.usernameEdit, ASCII7_REGEXP)
        self.setRegExpValidator(self.ui.passwordEdit, ASCII7_REGEXP)
        self.setRegExpValidator(self.ui.tableEdit, ASCII7_REGEXP)

        # To determine if there are changes, change the variable state when any
        # field is changed.
        self.changed = False
        for name in dir(self.ui):
            if name == 'firewall':
                continue
            widget = getattr(self.ui, name)
            if isinstance(widget, QLineEdit):
                self.connect(widget, SIGNAL('textChanged(const QString&)'), self.settingsChanged)
            elif isinstance(widget, QComboBox):
                self.connect(widget, SIGNAL('currentIndexChanged(int)'), self.settingsChanged)
            elif isinstance(widget, QSpinBox):
                self.connect(widget, SIGNAL('valueChanged(int)'), self.settingsChanged)
            elif isinstance(widget, QCheckBox):
                self.connect(widget, SIGNAL('toggled(bool)'), self.settingsChanged)

        # Prevent the user from changing database settings on an Edenwall
        if self.main_window.use_edenwall:
            self.ui.databaseGroupBox.hide()


    def settingsChanged(self, *args, **kwargs):
        self.changed = True

    def firewallChanged(self, i):
        firewall = unicode(self.ui.firewall.itemData(i).toString())

        if firewall == self.firewall:
            return

        if self.changed:
            reply = QMessageBox.question(self, self.tr("Save?"),
                                         self.tr("Do you want to save the changes to this firewall settings?"),
                                         QMessageBox.Save|QMessageBox.Cancel|QMessageBox.Discard);
            if reply == QMessageBox.Cancel:
                index = self.ui.firewall.findData(QVariant(self.firewall))
                self.ui.firewall.setCurrentIndex(index)
                return
            if reply == QMessageBox.Save:
                self.save()

        self.firewall = firewall
        self.load()

    def call(self, *args):
        if self.firewall:
            return self.client.call('multisite_master', 'callRemote', self.firewall, *args)
        else:
            return self.client.call(*args)

    def __load_ufwi_log(self):

        config_data = self.call('ufwi_log', 'getConfig')

        self.ui.hostnameEdit.setText(config_data['hostname'])
        self.ui.databaseEdit.setText(config_data['database'])
        self.ui.usernameEdit.setText(config_data['username'])
        self.ui.passwordEdit.setText(config_data['password'])
        index = self.ui.dbtypeEdit.findText(config_data['dbtype'])
        if index >= 0:
            self.ui.dbtypeEdit.setCurrentIndex(index)
        index = self.ui.typeEdit.findText(config_data['type'])
        if index >= 0:
            self.ui.typeEdit.setCurrentIndex(index)
        index = self.ui.ipEdit.findText(config_data['ip'])
        if index >= 0:
            self.ui.ipEdit.setCurrentIndex(index)

        self.ui.tableEdit.setText(config_data['table'])
        self.ui.maxrotateEdit.setValue(int(config_data['maxrotate']))

        if self.call('CORE', 'hasComponent', 'multisite_slave'):
            self.ui.importCheckbox.setEnabled(False)
            self.ui.importRotationLabel.setEnabled(False)
            self.ui.importRotation.setEnabled(False)
            self.ui.importCheckbox.setChecked(False)
            self.ui.exportCheckbox.setEnabled(True)
            self.ui.exportPeriodLabel.setEnabled(True)
            self.ui.exportPeriod.setEnabled(True)
            self.ui.exportCheckbox.setChecked(int(config_data['export_period']) > 0)
            self.ui.exportPeriod.setValue(int(config_data['export_period']))
        elif self.call('CORE', 'hasComponent', 'multisite_master'):
            self.ui.exportCheckbox.setEnabled(False)
            self.ui.exportPeriodLabel.setEnabled(False)
            self.ui.exportPeriod.setEnabled(False)
            self.ui.exportCheckbox.setChecked(False)
            self.ui.importCheckbox.setEnabled(True)
            self.ui.importRotationLabel.setEnabled(True)
            self.ui.importRotation.setEnabled(True)
            self.ui.importCheckbox.setChecked(int(config_data['import_rotation']) > 0)
            self.ui.importRotation.setValue(int(config_data['import_rotation']))
        else:
            #self.ui.exportCheckbox.setEnabled(False)
            #self.ui.exportPeriodLabel.setEnabled(False)
            #self.ui.exportPeriod.setEnabled(False)
            self.ui.exportCheckbox.setChecked(False)
            #self.ui.importCheckbox.setEnabled(False)
            #self.ui.importRotationLabel.setEnabled(False)
            #self.ui.importRotation.setEnabled(False)
            self.ui.importCheckbox.setChecked(False)
            self.ui.multisiteGroupBox.setEnabled(False)

        entities = config_data['anonymization'].split()
        self.ui.anonUser.setChecked('user' in entities)
        self.ui.anonIP.setChecked('ipaddr' in entities)
        self.ui.anonApp.setChecked('app' in entities)

    def __save_ufwi_log(self):

        config_data = {}

        config_data['hostname'] = unicode(self.ui.hostnameEdit.text())
        config_data['database'] = unicode(self.ui.databaseEdit.text())
        config_data['username'] = unicode(self.ui.usernameEdit.text())
        config_data['password'] = unicode(self.ui.passwordEdit.text())
        config_data['dbtype'] = unicode(self.ui.dbtypeEdit.currentText())
        config_data['type'] = unicode(self.ui.typeEdit.currentText())
        config_data['ip'] = unicode(self.ui.ipEdit.currentText())
        config_data['table'] = unicode(self.ui.tableEdit.text())
        config_data['maxrotate'] = unicode(self.ui.maxrotateEdit.value())
        if self.ui.exportCheckbox.isChecked():
            config_data['export_period'] = self.ui.exportPeriod.value()
        else:
            config_data['export_period'] = 0
        if self.ui.importCheckbox.isChecked():
            config_data['import_rotation'] = self.ui.importRotation.value()
        else:
            config_data['import_rotation'] = 0

        entities = []
        if self.ui.anonUser.isChecked(): entities.append('user')
        if self.ui.anonIP.isChecked():   entities.append('ipaddr')
        if self.ui.anonApp.isChecked():  entities.append('app')
        config_data['anonymization'] = ' '.join(entities)

        try:
            self.call('ufwi_log', 'setConfig', config_data)
        except Exception, err:
            self.main_window.exception(err)
            return False
        return True

    def __load_ocs(self):

        config_data = self.call('ocs', 'getConfig')

        self.ui.OCS_Hostname.setText(config_data['hostname'])
        self.ui.OCS_Database.setText(config_data['database'])
        self.ui.OCS_Username.setText(config_data['username'])
        self.ui.OCS_Password.setText(config_data['password'])

    def __save_ocs(self):
        config_data = {}

        config_data['hostname'] = unicode(self.ui.OCS_Hostname.text())
        config_data['database'] = unicode(self.ui.OCS_Database.text())
        config_data['username'] = unicode(self.ui.OCS_Username.text())
        config_data['password'] = unicode(self.ui.OCS_Password.text())

        try:
            self.call('ocs', 'setConfig', config_data)
        except Exception, err:
            self.main_window.exception(err)
            return False
        return True

    def load(self):
        try:
            enabled_modules = self.call('CORE', 'getComponentList')
        except Exception, err:
            self.main_window.exception(err, dialog=True)
            return False

        if not 'ufwi_log' in enabled_modules:
            self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.indexOf(self.ui.tabNulog), False)
            self.ui.tabNulog.setEnabled(False)
        else:
            self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.indexOf(self.ui.tabNulog), True)
            self.ui.tabNulog.setEnabled(True)
            self.__load_ufwi_log()

        if not 'ocs' in enabled_modules:
            self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.indexOf(self.ui.tabOCS), False)
            self.ui.tabOCS.setEnabled(False)
        else:
            self.ui.tabWidget.setTabEnabled(self.ui.tabWidget.indexOf(self.ui.tabOCS), True)
            self.ui.tabOCS.setEnabled(True)
            self.__load_ocs()

        self.changed = False

    def run(self):

        self.load()
        return self.execLoop()

    def save(self):
        if self.ui.tabNulog.isEnabled() and not self.__save_ufwi_log():
            return False
        if self.ui.tabOCS.isEnabled() and not self.__save_ocs():
            return False

        return True
