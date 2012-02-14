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

from IPy import IP
from PyQt4.QtCore import QVariant
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QValidator
from PyQt4.QtGui import QComboBox

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_conf.client.NuConfValidators import (hostnameValidator, hostIPValidator,
    hostOrIpValidator, hostOrFqdnOrIpValidator, netNameValidator, netValidator,
    portValidator, mailValidator)
from ufwi_conf.client.system.network.qnet_object import QNetObject
from ufwi_conf.client.system.network.network_models_names import MODEL_NETWORKS_EXCL_HA

from .exceptions import InputException
from .validable import Validable

class LineEdit(QLineEdit, Validable):
    def __init__(self, validator_cls, accept_empty, parent=None):
        QLineEdit.__init__(self, parent)
        Validable.__init__(self, accept_empty)
        self.validator = validator_cls(self)

    @abstractmethod
    def getFieldInfo(self):
        pass

    def focusInEvent(self, event):
        Validable.focusInEvent(self, event)
        QLineEdit.focusInEvent(self, event)

    def focusOutEvent(self, event):
        Validable.focusOutEvent(self, event)
        QLineEdit.focusOutEvent(self, event)

    def isValid(self):
        state, pos = self.validator.validate(self.text(), 0)
        return QValidator.Acceptable == state

    def isEmpty(self):
        return self.text().isEmpty()

class IpEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=True):
        LineEdit.__init__(self, hostIPValidator, accept_empty, parent)
        self.setWhatsThis(tr('<h3><font color="blue">%s</font></h3>%s') %
            (tr('IP address'), tr('Enter an IP address.')))

    def isValid(self, accept_empty=True):
        if self.text().isEmpty():
            return accept_empty
        try:
            IP(unicode(self.text()))
        except Exception:
            return False
        return True

    def getFieldInfo(self):
        return tr("IP address")

    def getValidator(self):
        return self.validator

    def value(self, text=None):
        return IP(unicode(self.text()))

    def isEmpty(self):
        return self.text().isEmpty()

class NetworkEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=True):
        LineEdit.__init__(self, netValidator, accept_empty, parent)

        help0 = tr('Enter a network address')
        help1 = "<ul><li>" + tr('either in the form IP/mask 192.168.1.0/255.255.255.0') + "</li>"
        help2 = "<li>" + tr("or in the form IP/prefix 192.168.1.0/24") + "</li></ul>"
        self.setWhatsThis(help0 + help1 + help2)

    def value(self, text=None):
        if text is None:
            text = unicode(self.text())
        try:
            return IP(text, make_net=True)
        except Exception:
            if not text:
                msg = tr("Network address unset!")
            else:
                msg = tr("Invalid network address: ") +  unicode(text)
            raise InputException(msg)

    def isValid(self, accept_empty=True):
        ok, msg = self.isValidWithMsg(accept_empty=accept_empty)
        return ok

    def isValidWithMsg(self, accept_empty=True):
        if self.text().isEmpty():
            if accept_empty:
                return True, ""
            else:
                return False, tr("Empty field.")
        try:
            IP(unicode(self.text()), make_net=True)
        except Exception:
            return False, tr("Unable to interpret value")
        return True, ""

    def getFieldInfo(self):
        return tr("Network address")

class IpOrFqdnEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, hostOrIpValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("fully qualified domain name or IP address")

class IpOrHostnameOrFqdnEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, hostOrFqdnOrIpValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("hostname or fully qualified domain name or IP address")

class HostnameEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, hostnameValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("a short host name (not a fully qualified host name)")

class FqdnEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, netNameValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("fully qualified domain name")

class PortEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, portValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("port number")

class MailEdit(LineEdit):
    def __init__(self, parent=None, accept_empty=False):
        LineEdit.__init__(self, mailValidator, accept_empty, parent)

    def getFieldInfo(self):
        return tr("email address")

class NetworkCombo(QComboBox):
    def __init__(self, modelname=MODEL_NETWORKS_EXCL_HA, parent=None):
        QComboBox.__init__(self, parent)
        self.qnetobject = QNetObject.getInstance()
        self.__modelname = modelname

        self.setModel(
            self.qnetobject.models[self.__modelname]
        )

    def getNet(self):
        index = self.currentIndex()
        data = self.qnetobject.item(self.__modelname, index)
        return data

    def getInterface(self):
        net = self.getNet()
        return self.qnetobject.netcfg.getInterfaceForNet(net)

    def selectNet(self, net):
        index = self.qnetobject.index(self.__modelname, net)
        self.setCurrentIndex(index)

class InterfaceChoice(QComboBox):
    """
    ComboBox which allow to choose interface

    Interfaces displayed can be filtered with chooseInterface:
    bool chooseInterace(interface)
        return True if interface must be added to the combobox
    """
    def __init__(self, chooseInterface, parent):
        QComboBox.__init__(self, parent)
        selectable = list()
        for interface in QNetObject.getInstance().netcfg.iterInterfaces():
            if not callable(chooseInterface) or chooseInterface(interface):
                selectable.append(("%s" % interface.fullName(), QVariant(interface.unique_id)))

        selectable.sort()
        for item in selectable:
            self.addItem(*item)

    def getInterface(self):
        """
        return current selected interface
        """
        index = self.currentIndex()
        items = self.itemData(index).toInt() # net_id, ok
        return QNetObject.getInstance().netcfg.getInterfaceByUniqueID(items[0])

    def selectInterface(self, interface):
        """
        select interface in the combobox
        """
        index = self.findData(QVariant(interface.unique_id))
        self.setCurrentIndex(index)

