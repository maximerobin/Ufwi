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

from itertools import chain
from PyQt4.QtCore import Qt, SIGNAL, QRegExp

from ufwi_rpcc_qt.central_dialog import CentralDialog, IP_OR_HOSTNAME_OR_FQDN_REGEXP
from ufwi_rpcc_qt.tools import QComboBox_setCurrentText
from ufwi_rpcd.common.logger import Logger
from ufwi_rpcd.common.tools import inverseDict
from ufwi_rpcd.common import tr

from ufwi_ruleset.common.parameters import (
    LOCAL_FIREWALL, NUFW_GATEWAY,
    LOG_LIMIT_REGEX_STR)
from ufwi_rulesetqt.parameters_dialog_ui import Ui_Dialog

FIREWALL_TYPE_INDEXES = {
    LOCAL_FIREWALL: 0,
    u'gateway': 1,
    NUFW_GATEWAY: 2,
}
NUFW_TAB = 2
LDAP_TAB = 3
NUFW_TABS = (NUFW_TAB, LDAP_TAB)
FIREWALL_TYPES = inverseDict(FIREWALL_TYPE_INDEXES)
NUFW_GATEWAY_INDEX = FIREWALL_TYPE_INDEXES[NUFW_GATEWAY]

LOG_LIMIT_REGEXP = QRegExp(LOG_LIMIT_REGEX_STR)

class RulesetConfig(dict, Logger):
    def __init__(self, gui, client):
        dict.__init__(self)
        Logger.__init__(self)
        self.client = client
        self.gui = gui
        self.getConfig()
        self.update_callbacks = []   # def callback(config): ...

    def getConfig(self):
        conf = self.client.call('ufwi_ruleset', 'getConfig')
        self.update(conf)

    def save(self, changes):
        config = dict(self)
        config.update(changes)

        try:
            config = self.client.call('ufwi_ruleset', 'setConfig', config)
        except Exception, err:
            self.gui.exception(err)
            return False
        self.update(config)
        for callback in self.update_callbacks:
            callback(self)
        self.gui.setStatus(tr("Configuration saved."))
        return True

    def useNuFW(self):
        return (self['global']['firewall_type'] == NUFW_GATEWAY)

    def isGateway(self):
        return (self['global']['firewall_type'] != LOCAL_FIREWALL)

class ParametersDialog(CentralDialog):
    def __init__(self, window, config):
        CentralDialog.__init__(self, window)
        self.window = window
        self.compatibility = window.compatibility
        self.setupDialog()
        self.config = config
        self.getCurrentConfig()

        self.execLoop()

    def setupDialog(self):
        self.ui = Ui_Dialog()

        # Create widgets
        self.ui.setupUi(self)
        self.nufw_widgets = (
            self.ui.periods_filename,
            self.ui.ldap_host,
            self.ui.ldap_port,
            self.ui.ldap_username,
            self.ui.ldap_basedn,
        )
        self.nflog_widgets = (
            self.ui.nflog_group_accept,
            self.ui.nflog_group_drop,
            self.ui.nflog_group_reject,
            self.ui.nflog_label,
            self.ui.accept_label,
            self.ui.drop_label,
            self.ui.reject_label,
        )

        # Signals
        self.connectButtons(self.ui.buttonBox)
        self.connect(self.ui.firewall_type,
            SIGNAL("currentIndexChanged(int)"),
            self.changeFirewallType)
        self.connect(self.ui.log_type,
            SIGNAL("currentIndexChanged(int)"),
            self.changeLogType)
        self.connect(self.ui.limited_radio,
            SIGNAL("toggled(bool)"),
            self.toggleLogLimit)

        # Validators
        self.setRegExpValidator(self.ui.log_limit, LOG_LIMIT_REGEXP)
        self.setNonEmptyValidator(self.ui.periods_filename)
        self.setRegExpValidator(self.ui.ldap_host, IP_OR_HOSTNAME_OR_FQDN_REGEXP)
        self.setIntValidator(self.ui.ldap_port, 1, 65535)
        self.setNonEmptyValidator(self.ui.ldap_username)
        self.setNonEmptyValidator(self.ui.ldap_basedn)

        # Hide some options on EdenWall
        if self.window.use_edenwall:
            widgets = (
               self.ui.firewall_type_label,
               self.ui.firewall_type,
               self.ui.log_type,
               self.ui.log_type_label,
            )
            for widget in chain(self.nflog_widgets, widgets):
                widget.hide()
            tabs = (NUFW_TAB, LDAP_TAB)
            for tab in sorted(tabs, reverse=True):
                self.ui.tab_widget.removeTab(tab)

        # Set initial state
        self.changeLogType(self.ui.log_type.currentIndex())
        self.changeFirewallType(self.ui.firewall_type.currentIndex())

    def toggleLogLimit(self, enabled):
        self.ui.log_limit.setEnabled(enabled)

    def changeFirewallType(self, index):
        use_nufw = (index == NUFW_GATEWAY_INDEX)
        self.ui.nufw.setEnabled(use_nufw)
        self.ui.ldap.setEnabled(use_nufw)
        for widget in self.nufw_widgets:
            widget.setEnabled(use_nufw)
        if not self.window.use_edenwall:
            for tab in NUFW_TABS:
                self.ui.tab_widget.setTabEnabled(tab, use_nufw)

    def changeLogType(self, index):
        enabled = (index == 2)
        for widget in self.nflog_widgets:
            widget.setEnabled(enabled)

    def getCurrentConfig(self):
        self.config.getConfig()
        use_nufw = (self.config['global']['firewall_type'] == NUFW_GATEWAY)
        self.ui.use_ipv6.setChecked(self.config['global']['use_ipv6'])
        index = FIREWALL_TYPE_INDEXES[self.config['global']['firewall_type']]
        self.ui.firewall_type.setCurrentIndex(index)

        QComboBox_setCurrentText(self.ui.log_type, self.config['iptables']['log_type'])
        QComboBox_setCurrentText(self.ui.default_drop, self.config['iptables']['default_drop'])

        log_limit = self.config['iptables']['log_limit']
        if log_limit:
            self.ui.limited_radio.setChecked(True)
            self.ui.log_limit.setText(log_limit)
        else:
            self.ui.unlimited_radio.setChecked(True)
            self.ui.log_limit.setText(u'')
            self.toggleLogLimit(False)

        self.ui.nflog_group_accept.setValue(self.config['iptables']['nflog_group_accept'])
        self.ui.nflog_group_drop.setValue(self.config['iptables']['nflog_group_drop'])
        self.ui.nflog_group_reject.setValue(self.config['iptables']['nflog_group_reject'])
        invalid = 0
        if self.config['iptables']['drop_invalid']:
            invalid = 1
            if self.config['iptables']['log_invalid']:
                invalid = 2
        self.ui.invalid_combo.setCurrentIndex(invalid)

        self.ui.nufw.setEnabled(use_nufw)
        self.ui.periods_filename.setText(self.config['nufw']['periods_filename'])
        if self.compatibility.user_group_name:
            if self.config['nufw']['require_group_name']:
                self.ui.group_name_radio.setChecked(True)
            else:
                self.ui.group_number_radio.setChecked(True)

        self.ui.ldap.setEnabled(use_nufw)
        self.ui.ldap_host.setText(self.config['ldap']['host'])
        self.ui.ldap_port.setText(unicode(self.config['ldap']['port']))
        self.ui.ldap_username.setText(self.config['ldap']['username'])
        self.ui.ldap_password.setText(self.config['ldap']['password'])
        self.ui.ldap_basedn.setText(self.config['ldap']['basedn'])

    def setLdapState(self, state):
        self.ui.ldap.setEnabled(state == Qt.Checked)

    def save(self):
        firewall_type = self.ui.firewall_type.currentIndex()
        firewall_type = FIREWALL_TYPES[firewall_type]
        invalid = self.ui.invalid_combo.currentIndex()
        drop_invalid = (1 <= invalid)
        log_invalid = (invalid == 2)
        if self.ui.limited_radio.isChecked():
            log_limit = unicode(self.ui.log_limit.text())
        else:
            log_limit = u''
        new_config = {
            'global': {
               'use_ipv6': self.ui.use_ipv6.isChecked(),
               'firewall_type': firewall_type,
            }, 'iptables': {
                'log_type': unicode(self.ui.log_type.currentText()),
                'default_drop': unicode(self.ui.default_drop.currentText()),
                'log_limit': log_limit,
                'nflog_group_accept': self.ui.nflog_group_accept.value(),
                'nflog_group_drop': self.ui.nflog_group_drop.value(),
                'nflog_group_reject': self.ui.nflog_group_reject.value(),
                'drop_invalid': drop_invalid,
                'log_invalid': log_invalid,
            }, 'nufw': {
                'periods_filename': unicode(self.ui.periods_filename.text()),
            }, 'ldap': {
                'host': unicode(self.ui.ldap_host.text()),
                'port': int(self.ui.ldap_port.text()),
                'username': unicode(self.ui.ldap_username.text()),
                'password': unicode(self.ui.ldap_password.text()),
                'basedn': unicode(self.ui.ldap_basedn.text()),
            },
        }
        if self.compatibility.user_group_name:
            group_name = self.ui.group_name_radio.isChecked()
            new_config['nufw']['require_group_name'] = group_name
        return self.config.save(new_config)

