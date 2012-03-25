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

from PyQt4.QtCore import Qt, QSize, SIGNAL
from PyQt4.QtGui import (QLineEdit, QPushButton, QIcon, QWidget, QHBoxLayout,
    QFileDialog, QComboBox)

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.input_widgets import AddButton, RemButton
from ufwi_conf.client.NuConfValidators import hostnameValidator, hostOrIpValidator, hostIPValidator, hostIP4Validator, hostIP6Validator

from ufwi_conf.common.net_interfaces import Vlanable

class AddressInput(QLineEdit):
    def __init__(self, version=4, parent=None):
        QLineEdit.__init__(self, parent)
        self.setIpVersion(version)

    def setIpVersion(self, version):
        self.ip_version = version
        if version == 4:
            validator = hostIP4Validator(self)
        elif version == 6:
            validator = hostIP6Validator(self)
        else:
            #4 AND 6
            validator = hostIPValidator(self)
        self.setValidator(validator)

    def getText(self):
        return unicode(self.text())

class HostnameInput(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)
        self.setValidator(hostnameValidator(self))

    def getText(self):
        return unicode(self.text())

class IpOrFqdnInput(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)
        self.setValidator(hostOrIpValidator(self))

    def getText(self):
        return unicode(self.text())

class PasswordInput(QLineEdit):
    def __init__(self, parent=None):
        QLineEdit.__init__(self, parent)
        self.setEchoMode(QLineEdit.Password)

    def getText(self):
        return unicode(self.text())

class NuconfButton(QPushButton):
    _ICON_SIZE = 16
    def __init__(self, text=None, flat=True, parent=None, enabled=True):
        QPushButton.__init__(self, parent)
        self.setEnabled(enabled)
        self.setFlat(flat)
        if text is not None:
            self.setText(text)
        self.setIconSize(QSize(NuconfButton._ICON_SIZE, NuconfButton._ICON_SIZE))

    def setText(self, text):
        QPushButton.setText(self, text)
        self.fixWidth(text)

    def fixWidth(self, text):
        chars = len(text) + 6 #safe margin
        textwidth = self.fontMetrics().averageCharWidth() * chars
        outermargin = 20
        wanted_with = NuconfButton._ICON_SIZE + outermargin + textwidth
        self.setFixedWidth(wanted_with)

class NoopButton(NuconfButton):
    def __init__(self, parent=None):
        NuconfButton.__init__(self, parent)
        self.setEnabled(False)
    def mouseDoubleClickEvent(self, event):
        pass
    mouseClickEvent = mouseDoubleClickEvent

class EditButton(NuconfButton):
    def __init__(self, menu=None, text=tr("Edit"), flat=True, parent=None):
        NuconfButton.__init__(self, text=text, flat=flat, parent=parent)
        self.setIcon(QIcon(":/icons/edit.png"))
        self.setToolTip(tr("Click to edit"))

        if menu is not None:
            ################
            #Required because in the case of the network widget (not interface)
            #The menu gets deleted if we don't keep a reference !
            #Likely a borderline case
            self.menu = menu
            ################
            self.setMenu(menu)

class TestButton(NuconfButton):
    def __init__(self, text=tr("Test")):
        NuconfButton.__init__(self, text=text, flat=False)
        self.setIcon(QIcon(":/icons/run.png"))

class AddRemoveWidget(QWidget):
    def __init__(self, parent = None):
        QWidget.__init__(self, parent)
        self.add = AddButton()
        self.rem = RemButton()

        layout = QHBoxLayout(self)
        layout.setAlignment(Qt.AlignRight)
        layout.addStretch()
        layout.addWidget(self.add)
        layout.addWidget(self.rem)

class TextWithDefault(QLineEdit):
    DEFAULT = "background-color: #dddddd; color: #333333;"
    OTHER = ""
    def __init__(self, default, parent=None):
        QLineEdit.__init__(self, parent)
        self.default = unicode(default).strip()
        self.setText(self.default)
        self.colorValue()
        self.connect(self, SIGNAL("textChanged(QString)"), self.colorValue)

    def value(self):
        return unicode(self.text()).strip()

    def colorValue(self):
        if self.isChanged() or self.value() == '':
            self.setStyleSheet(TextWithDefault.OTHER)
        else:
            self.setStyleSheet(TextWithDefault.DEFAULT)

    def isChanged(self):
        return self.value() != self.default

    def focusInEvent(self, event):
        self.selectAll()

class VlanIdInput(QLineEdit):
    def __init__(self, vlan=None, parent=None):
        QLineEdit.__init__(self, parent)
        if vlan is None:
            suggested = 2
            self.setText(unicode(suggested))

    def value(self):
        return int(unicode(self.text()).strip())

class RawDeviceChoice(QComboBox):
    def __init__(self, netcfg, vlan=None, parent=None):
        QComboBox.__init__(self, parent)
        vlanables = list(netcfg.iterVlanables())
        vlanables.sort()
        self.index2raw_device = {}
        self.raw_device2index = {}
        for index, item in enumerate(vlanables):
            self.addItem(item.fullName())
            sys_name = item.system_name
            self.index2raw_device[index] = sys_name
            self.raw_device2index[sys_name] = index

        if vlan is not None:
                self.setSelection(vlan.raw_device)

    def getSelection(self):
        index = self.currentIndex()
        return self.index2raw_device[index]

    def setSelection(self, raw_device):
        if isinstance(raw_device, Vlanable):
            raw_device = raw_device.system_name
        index = self.raw_device2index[raw_device]
        self.setCurrentIndex(index)

class FileSelector(QWidget):
    def __init__(self, title="Select file", filter="All files (*.*)", parent=None):
        """If filter contains a pair of parentheses containing one or more of
        anything*something, separated by spaces, then only the text contained
        in the parentheses is used as the filter.

        Equivalent filters:
        "All C++ files (*.cpp *.cc *.C *.cxx *.c++)"
        "*.cpp *.cc *.C *.cxx *.c++"

        filter can also be a set, tuple or list
        """

        QWidget.__init__(self, parent)

        self.filter = filter
        self.title = title

        box = QHBoxLayout(self)

        self.edit = QLineEdit()
        self.edit.setMinimumWidth(self.edit.fontMetrics().averageCharWidth() * 15)
        box.addWidget(self.edit)

        button = QPushButton(tr("Browse"))
        self.connect(button, SIGNAL('clicked()'), self.openFileDialog)
        box.addWidget(button)

        box.addStretch()

    def openFileDialog(self):
        selected =  self.edit.text()
        filename = QFileDialog.getOpenFileName(self, self.title, selected, self.filter)

        if filename:
            self.edit.setText(filename)
            self.emit(SIGNAL('modified'), filename)

class OptionnalLine(QLineEdit):
    def __init__(self, value=None, hint=None, parent=None):
        QLineEdit.__init__(self, parent)

        self.hint_mode = False
        if hint is None:
            hint = tr("Optional field")
            self.hint_mode = True
        self.hint = hint


        self._cached_value = None

        if value is not None:
            self.setText(value)

        self.connect(self, SIGNAL('textChanged(QString)'), self.checkEmpty)

        self.checkEmpty()

    def checkEmpty(self, *args):
        value = self._value()
        changed = value != self._cached_value
        self._cached_value = value

        if value in ('', self.hint):
            self.hint_mode = True
            #self.setStyleSheet('font-style:italic;')
            self.setText(self.hint)
            self.selectAll()
        else:
            self.hint_mode = False
            self.setStyleSheet('')

        if changed:
            self.emit(SIGNAL('changed'), self.value())

    def focusInEvent(self, event):
        QLineEdit.focusInEvent(self, event)
        if self.hint_mode:
            self.selectAll()

    def _value(self):
        return unicode(self.text()).strip()

    def value(self):
        if self.hint_mode:
            result = ''
        else:
            result = self._value()
        return result

