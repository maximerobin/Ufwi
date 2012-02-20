
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
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QLineEdit

from ufwi_rpcd.common import tr

from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Vlanable
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.input_widgets import VlanIdInput
from ufwi_conf.client.qt.input_widgets import RawDeviceChoice

from .qnet_object import QNetObject

class VlanEditor(QFrame):
    def __init__(self, vlan=None, raw_device=None, parent=None):
        QFrame.__init__(self, parent)
        self.q_netobject = QNetObject.getInstance()
        self.vlan = vlan

        layout = QFormLayout(self)

        self.raw_device = RawDeviceChoice(self.q_netobject.netcfg, vlan=vlan)
        layout.addRow(
            self.tr("Physical interface"),
            self.raw_device
        )

        self.vlan_id = VlanIdInput()
        layout.addRow(
            self.tr("ID:"),
            self.vlan_id
            )

        self.name = QLineEdit()
        layout.addRow(
            self.tr("Name:"),
            self.name
            )

        if vlan is not None:
            self.original_interface = vlan.raw_device
            self._name_edited = vlan.user_label != vlan.system_name
            self.name.setText(vlan.user_label)
            raw_device = vlan.raw_device
            self.vlan_id.setText(unicode(vlan.id))
        else:
            self.original_interface = None
            #will be set at true when we don't need to calculate self.name anymore
            self._name_edited = False
            self.computeName()

        self.connect(self.vlan_id, SIGNAL('textEdited(QString)'), self.computeName)
        self.connect(self.name, SIGNAL('textEdited(QString)'), self.nameCustomized)
        self.connect(self.raw_device, SIGNAL('currentIndexChanged(int)'), self.computeName)

        self.message = MessageArea()
        layout.addRow(self.message)

     #   for input in (self.name, self.vlan_id):
     #       self.connect(input, SIGNAL('editingFinished()'), self.isValid)

        self.isValid()

    #configure
        if raw_device is not None:
            self.raw_device.setSelection(raw_device)

    def nameCustomized(self, *args):
        self._name_edited = True

    def computeName(self, *args):
        if self._name_edited:
            return
        try:
            name = "%s.%s" % (self.raw_device.getSelection(), self.vlan_id.value())
        except:
            return
        self.name.setText(name)

    def  setErrorMessage(self, message):
        self._message = message
        self.message.setMessage(
            self.tr("Input error"),
            message,
            status=MessageArea.WARNING
            )

    def setOkMessage(self):
        self.message.setMessage(
            self.tr("Information"),
            self.tr("Valid configuration")
            )

    def getMessage(self):
        return self._message()

    def getName(self):
        return unicode(self.name.text()).strip()

    def getRawDevice(self):
        return self.raw_device.getSelection()

    def getID(self):
        return self.vlan_id.value()

    def isValid(self):
        try:
            vlan_id = self.getID()
        except:
            self.setErrorMessage(
                self.tr("Vlan ID should be an integer value")
                )
            return False

        if 0 > vlan_id or vlan_id > 4095:
            self.setErrorMessage(
                self.tr("Vlan ID must be an integer value in [1..4095]")
            )
            return False


        if self.getName() == "":
            self.computeName()

        self.setOkMessage()

        raw_device = self.getRawDevice()
        if not isinstance(raw_device, Vlanable):
            raw_device = \
            self.q_netobject.netcfg.getInterfaceBySystemName(raw_device)

        if self.original_interface == raw_device.system_name:
            #NOT checking against ID
            if not raw_device.isValid():
                self.setErrorMessage(
                    self.tr("This would make an invalid configuration for the physical interface.")
                    )
                return False
        else:
            if not raw_device.isValid(new_vlan_id=self.getID()):
                self.setErrorMessage(
                    self.tr("This would make an invalid configuration for "
                    "the physical interface (duplicate vlan ID...).")
                    )
                return False

        return True

    def accept(self, *args):
        if not self.isValid():
            return False
        try:
            return self.setValues()
        except NetCfgError:
            self.setErrorMessage(
                self.tr("Impossible configuration")
                )
            return False

    def setValues(self):
        self.emit(SIGNAL('modified'), tr("Vlan edited"))
        user_label = self.getName()
        raw_device = self.getRawDevice()
        vlan_id = self.getID()

        if self.vlan is None:
            self.q_netobject.netcfg.createVlan(
                raw_device,
                user_label,vlan_id
            )
            self.emit(SIGNAL('modified'), tr("New vlan interface created: '%s'") % user_label)
            return True

        self.vlan.user_label = user_label
        self.vlan.id = vlan_id

        self.q_netobject.netcfg.moveVlan(
            self.vlan,
            raw_device
        )
        self.emit(SIGNAL('modified'), tr("vlan interface edited: '%s'") % user_label)
        return True

