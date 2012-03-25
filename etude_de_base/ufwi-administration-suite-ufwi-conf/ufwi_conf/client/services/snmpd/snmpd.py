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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import (QCheckBox, QFormLayout, QFrame, QGroupBox, QLabel,
    QLineEdit, QVBoxLayout, QWidget)

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_rpcc_qt.genericdelegates import (ComboBoxColumnDelegate,
    EditColumnDelegate, PasswordColumnDelegate)
from ufwi_rpcc_qt.list_edit import ListEdit

from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.ip_inputs import NetworkEdit
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
from ufwi_conf.client.services.snmpd import QSnmpdObject

if EDENWALL:
    from ufwi_conf.common.snmpd_cfg import (INDEX_V2C_SOURCE,
        INDEX_V3_AUTHENTICATION_PASS, INDEX_V3_AUTHENTICATION_PROTO,
        INDEX_V3_ENCRYPTION_ALGO, INDEX_V3_ENCRYPTION_PASS,
        INDEX_V3_USERNAME)

class TextEdit(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)

    def getFieldInfo(self):
        return tr("Text field")

    def isValid(self):
        if not self.text():
            return False
        return True

class CommunityEdit(TextEdit):
    def __init__(self, parent=None):
        TextEdit.__init__(self, parent)

    def getFieldInfo(self):
        return tr("Community")

    def isValid(self):
        if not self.text():
            return False
        return True

class PassEdit(TextEdit):
    def __init__(self, parent=None):
        TextEdit.__init__(self, parent)
        self.setEchoMode(QLineEdit.Password)

    def getFieldInfo(self):
        return tr("Password")

    def isValid(self):
        if not self.text():
            return False
        return True

class UsernameEdit(TextEdit):
    def __init__(self, parent=None):
        TextEdit.__init__(self, parent)

    def getFieldInfo(self):
        return tr("Username")

    def isValid(self):
        if not self.text():
            return False
        return True


class SnmpdFrontend(FullFeaturedScrollArea):
    COMPONENT = 'snmpd'
    LABEL = tr('SNMP service')
    REQUIREMENTS = ('snmpd',)
    ICON = ':/icons/treeview.png'

    def __init__(self, client, parent):
        if not EDENWALL:
            raise NuConfModuleDisabled("snmpd")
        self._module_disabled = False
        self.qsnmpdobject = QSnmpdObject.getInstance()
        self.main_window = parent
        FullFeaturedScrollArea.__init__(self, client, parent)

        self.client = client
        self._modified = False
        self._not_modifying = False

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (('snmpd', 'getSnmpdConfig'), )

    def fetchConfig(self):
        serialized = self.main_window.init_call(
            'snmpd', u'getSnmpdConfig'
            )
        if serialized is None:
            self._no_backend()
            return
        self.qsnmpdobject.snmpd = serialized

    def sendConfig(self, message):
        serialized = self.qsnmpdobject.snmpd.serialize()
        self.client.call('snmpd', 'setSnmpdConfig', serialized, message)

    def isValid(self):
        self.qsnmpdobject.snmpd.setV2cList(self.serialize_list(
                self.widget.v2c_list_edit.rawData()))
        self.qsnmpdobject.snmpd.setV3List(self.serialize_list(
                self.widget.v3_list_edit.rawData()))
        check, self.error_message = self.qsnmpdobject.snmpd.isValidWithMsg()
        if not check:
            self.main_window.addToInfoArea(self.error_message, category=COLOR_ERROR)
            return False
        return True

    def buildInterface(self):
#        self.fetchConfig()
        if self._module_disabled:
            return
        self.widget = SnmpdWidget(self)
        self.setWidget(self.widget)

        self.setWidgetResizable(True)
        self.error_message = self.tr("Incorrect snmpd specification")

    def setModified(self, modified=True):
        if self._modified == modified or self._not_modifying:
            return
        self._modified = modified
        if modified:
            self.main_window.setModified(self, True)

    def setViewData(self):
        if self._module_disabled:
            return
        self._not_modifying = True

        # Enabled:
        self.widget.enable_server.setChecked(self.qsnmpdobject.snmpd.enabled)

        # V2c list:
        self.widget.v2c_list_edit.reset(
            self.qsnmpdobject.snmpd.v2c_list)

        # V3 list:
        self.widget.v3_list_edit.reset(
            self.qsnmpdobject.snmpd.v3_list)

        self._not_modifying = False

    def serialize_list(self, rawData):
        result = []
        for el in rawData:
            result.append(map(unicode, el))
        return result

    def setEnabled(self, value):
        if value != self.qsnmpdobject.snmpd.enabled:
            self.qsnmpdobject.snmpd.setEnabled(value)
            self.setModified()

    def _no_backend(self):
        self._disable(
            tr("Could not fetch SNMP component parameters"),
            tr(
                "Problem while fetching the server configuration "
                "for SNMP"
            ),
            tr(
                "The SNMP configuration interface is disabled because the configuration "
                "could not be fetched properly."
            )
        )


class SnmpdWidget(QFrame):
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.parent = parent

        form = QVBoxLayout(self)
        title = QLabel("<H1>%s</H1>" % self.tr('SNMP Server Configuration'))
        form.addWidget(title)

        # Enable:
        self.enable_line = QWidget()
        self.enable_line.setLayout(QFormLayout())
        self.enable_server = QCheckBox()
        self.connect(self.enable_server, SIGNAL('stateChanged(int)'),
                     parent.setEnabled)
        self.enable_line.layout().addRow(self.tr("Enable SNMP server"),
                                         self.enable_server)
        form.addWidget(self.enable_line)
        parent.main_window.writeAccessNeeded(self.enable_server)

        # V2c list (source network, community):
        self.v2c_list_groupbox = QGroupBox()
        self.v2c_list_groupbox.setTitle(self.tr("SNMPv2c access list"))
        self.v2c_list_groupbox.setLayout(QVBoxLayout())
        self.v2c_list_edit = ListEdit()
        self.v2c_list_edit.headers = self.getColumnLabelsV2c()
        self.v2c_list_edit.readOnly = self.parent.main_window.readonly
        self.v2c_list_edit.editInPopup = True
        self.v2c_list_edit.displayUpDown = False
        self.v2c_list_edit.setColDelegate(self.createDelegateForColumnV2c)
        self.connect(self.v2c_list_edit, SIGNAL('itemDeleted'),
                     self.setModified)
        self.connect(self.v2c_list_edit, SIGNAL('itemAdded'),
                     self.setModified)
        self.connect(self.v2c_list_edit, SIGNAL('itemModified'),
                     self.setModified)
        self.v2c_list_groupbox.layout().addWidget(self.v2c_list_edit)
        parent.main_window.writeAccessNeeded(self.v2c_list_edit)
        form.addWidget(self.v2c_list_groupbox)

        # V3 list (username, auth passphrase, auth proto, privacy key, algo):
        self.v3_list_groupbox = QGroupBox()
        self.v3_list_groupbox.setTitle(self.tr("SNMPv3 access list"))
        self.v3_list_groupbox.setLayout(QVBoxLayout())
        self.v3_list_edit = ListEdit()
        self.v3_list_edit.readOnly = self.parent.main_window.readonly
        self.v3_list_edit.headers = self.getColumnLabelsV3()
        self.v3_list_edit.displayUpDown = False
        self.v3_list_edit.editInPopup = True
        self.v3_list_edit.setColDelegate(self.createDelegateForColumnV3)
        self.connect(self.v3_list_edit, SIGNAL('itemDeleted'),
                     self.setModified)
        self.connect(self.v3_list_edit, SIGNAL('itemAdded'),
                     self.setModified)
        self.connect(self.v3_list_edit, SIGNAL('itemModified'),
                     self.setModified)
        self.v3_list_groupbox.layout().addWidget(self.v3_list_edit)
        parent.main_window.writeAccessNeeded(self.v3_list_edit)
        form.addWidget(self.v3_list_groupbox)

    def createDelegateForColumnV2c(self, column):
        if column == INDEX_V2C_SOURCE:
            return EditColumnDelegate(NetworkEdit)
        return EditColumnDelegate(CommunityEdit)

    def createDelegateForColumnV3(self, column):
        if column == INDEX_V3_USERNAME:
            return EditColumnDelegate(UsernameEdit)
        elif column == INDEX_V3_AUTHENTICATION_PASS:
            return PasswordColumnDelegate(PassEdit)
        elif column == INDEX_V3_AUTHENTICATION_PROTO:
            return ComboBoxColumnDelegate(("SHA", "MD5"))
        elif column == INDEX_V3_ENCRYPTION_PASS:
            return PasswordColumnDelegate(PassEdit)
        elif column == INDEX_V3_ENCRYPTION_ALGO:
            return ComboBoxColumnDelegate(("AES", "DES"))
        return EditColumnDelegate(PassEdit)

    def getColumnLabelsV2c(self):
        return [self.tr("Source host or network"), self.tr("Community")]

    def getColumnLabelsV3(self):
        return [self.tr("Username"), self.tr("Passphrase"),
                self.tr("Protocol"), self.tr("Privacy key"),
                self.tr("Encrypting algorithm")]

    def setModified(self, *unused):
        self.parent.setModified()

