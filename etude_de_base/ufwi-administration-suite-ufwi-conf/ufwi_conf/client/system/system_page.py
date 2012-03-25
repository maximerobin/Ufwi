
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

from PyQt4.QtGui import QFormLayout, QLabel, QGroupBox, QHBoxLayout, QPixmap, QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.widgets import ScrollArea

#
# page not displayed by EAS
#
class SystemPage(ScrollArea):
    def __init__(self, client, parent=None):
        ScrollArea.__init__(self)
        box = QVBoxLayout(self)

        title = QLabel("<H1>System</H1>")
        box.addWidget(title)

        try:
            values = client.call('system_info', 'systemInfo')
        except Exception:
            parent.addToInfoArea(tr("Unmanaged error, warn developpers."))

        else:

            info_box = Device(values)
            box.addWidget(info_box)
        box.addStretch()

def strong(string):
    return "<b>%s</b>" % string

class Device(QGroupBox):
    def __init__(self, values, parent=None):
        QGroupBox.__init__(self, parent)

        self.setTitle(tr("Device information"))

        hbox = QHBoxLayout(self)

        edenwall_image = QPixmap(':/images/edenwall_small')
        label = QLabel()
        label.setPixmap(edenwall_image)
        hbox.addWidget(label)

        self.form = QFormLayout()
        hbox.addLayout(self.form)
        self.form.addRow(tr("Device type:"), QLabel(strong(values['type'])))
        self.form.addRow(tr("Property of:"), QLabel(strong(values['client'])))
        self.form.addRow(tr("Hardware version:"), QLabel(strong(values['hw_version'])))
        self.form.addRow(tr("Serial number:"), QLabel(strong(values['serial'])))
