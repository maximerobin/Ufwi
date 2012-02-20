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


from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QButtonGroup
from PyQt4.QtGui import QRadioButton
from PyQt4.QtGui import QGroupBox
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.input_widgets import OptionnalLine
from ufwi_conf.common.net_interfaces import Ethernet

class EthernetEditor(QFrame):
    def __init__(self, ethernet, parent=None):
        QFrame.__init__(self, parent)

        self.ethernet = ethernet

        self.buildGUI()
        self.fillValues()

    def buildGUI(self):
        #general setup
        form = QFormLayout(self)

        self.label = OptionnalLine(hint="Optional interface name")
        form.addRow(self.tr("Interface name"), self.label)

        self.speed_group = QButtonGroup()
        self.speed_box = QGroupBox(tr("Force an ethernet speed"))
        speed_layout = QVBoxLayout(self.speed_box)

        self.speed_GFull = QRadioButton(tr("Gigabit full duplex"))
        self.speed_GHalf = QRadioButton(tr("Gigabit half duplex"))
        self.speed_100Full = QRadioButton(tr("100 Mb Full duplex"))
        self.speed_100Half = QRadioButton(tr("100 Mb Half duplex"))
        self.speed_10Full = QRadioButton(tr("10 Mb Full duplex"))
        self.speed_10Half = QRadioButton(tr("10 Mb Half duplex"))

        def toggle(value):
            if value:
                self.speed_GFull.click()

        self.speed_box.setCheckable(True)
        self.speed_box.setChecked(Qt.Unchecked)
        self.connect(self.speed_box, SIGNAL('toggled(bool)'), toggle)

        for item in (
            self.speed_GFull,
            self.speed_GHalf,
            self.speed_100Full,
            self.speed_100Half,
            self.speed_10Full,
            self.speed_10Half,
            ):
            self.speed_group.addButton(item)
            speed_layout.addWidget(item)

        form.addRow(self.speed_box)

    def fillValues(self):
        name = self.ethernet.user_label
        if name != "":
            self.label.setText(name)
            self.label.checkEmpty()
            self.label.setStyleSheet('')

        if self.ethernet.eth_auto:
            self.speed_box.setChecked(Qt.Unchecked)
            return

        self.speed_box.setChecked(Qt.Checked)
        if self.ethernet.eth_duplex == Ethernet.FULL:
            if self.ethernet.eth_speed == 10:
                button = self.speed_10Full
            elif self.ethernet.eth_speed == 100:
                button = self.speed_100Full
            else:
                button = self.speed_GFull
        else:
            if self.ethernet.eth_speed == 10:
                button = self.speed_10Half
            elif self.ethernet.eth_speed == 100:
                button = self.speed_100Half
            else:
                button = self.speed_GHalf


        button.setChecked(Qt.Checked)

    def getConfig(self):
        auto = not self.speed_box.isChecked()
        if auto:
            return True, None, None
        selection = self.speed_group.checkedButton()
        if selection is self.speed_GFull:
            return False, 1000, Ethernet.FULL
        elif self.speed_GHalf:
            return False, 1000, Ethernet.HALF
        elif self.speed_100Full:
            return False, 100, Ethernet.FULL
        elif self.speed_100Half:
            return False, 100, Ethernet.HALF
        elif self.speed_10Full:
            return False, 10, Ethernet.FULL
        elif self.speed_10Half:
            return False, 10, Ethernet.HALF

        assert False, "this selection is unknown"

    def setName(self):
        new_name = self.label.value()
        if new_name != self.ethernet.user_label:
            self.ethernet.user_label = new_name
            #message = tr("renamed ethernet interface to: %s'") % new_name
        return True

    def accept(self, *args, **kwargs):
        ok = True
        ok &= self.setName()
        self.ethernet.setEthernetMode(*self.getConfig())
        if ok:
            self.emit(SIGNAL('edited'), "edited ethernet interface '%s'" \
            % self.ethernet.fullName())
        return ok

