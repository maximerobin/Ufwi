
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
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QWizard
from PyQt4.QtGui import QWizardPage

from netobjects_widgets import AddressAndMaskInput, IPVersionInput

class WizardNetIntroPage(QWizardPage):
    def __init__(self, iface, parent=None):
        QWizardPage.__init__(self, parent)
        self.setTitle("Introduction")
#        self.setPixmap(QWizard.WatermarkPixmap, QPixmap(":/images/watermark1.png"))

        label = QLabel(self.tr("This wizard will configure a network for your interface <b>%s</b>.",  iface.user_label))
        label.setWordWrap(True)

        layout = QVBoxLayout()
        layout.addWidget(label)
        self.setLayout(layout)

class WizardLabelIPVersionPage(QWizardPage):

    def __init__(self, parent=None):
        QWizardPage.__init__(self, parent)
        self.setTitle("Network name and IP Version")
#        self.setPixmap(QWizard.WatermarkPixmap, QPixmap(":/images/watermark1.png"))

        layout = QFormLayout()

        self.net_label = QLineEdit()
        layout.addRow("Network name", self.net_label)

        self.choice = IPVersionInput()
        layout.addRow("Protocol version", self.choice)

        self.setLayout(layout)

    def validatePage(self):
        text = unicode(self.net_label.text()).strip()
        if text:
            return True
        return False

class WizardNetAddrPage(QWizardPage):

    def __init__(self, ip_version_page, parent=None):
        QWizardPage.__init__(self, parent)
        self.setTitle("Network specification")
#        self.setPixmap(QWizard.WatermarkPixmap, QPixmap(":/images/watermark1.png"))

        label = QLabel("Please enter network definition below")
        self.ip_mask = AddressAndMaskInput(4)
        self.ip_mask.prefix.setValue(24)
        self.connect(ip_version_page.choice, SIGNAL('ip_version_changed'), self.ip_mask.setVersion)
        layout = QFormLayout()
        layout.addRow(label)
        layout.addRow("Base address / prefix", self.ip_mask)
        self.msg = QLabel("")
        layout.addRow(self.msg)
        self.setLayout(layout)

    def validatePage(self):
        try:
            IP("%s/%s" % (self.ip_mask.address.text(), self.ip_mask.prefix.value()), make_net=True)
        except Exception:
            return False
        return True

class NetWizard(QWizard):
    def __init__(self, iface, net=None, parent=None):
        QWizard.__init__(self, parent)
        raise Exception()
        self.addPage(WizardNetIntroPage(iface))
        self.label_ip_version_page = WizardLabelIPVersionPage()
        self.addPage(self.label_ip_version_page)
        self.net_add_page = WizardNetAddrPage(self.label_ip_version_page)
        self.addPage(self.net_add_page)
        self.setWindowTitle("Network Wizard")

        self.connect(self, SIGNAL('accepted()'), self._done)

    def _done(self, *args):
        self.emit(SIGNAL('done'), self)

    @property
    def label(self):
        return unicode(self.label_ip_version_page.net_label.text())

    @property
    def prefix(self):
        return int(self.net_add_page.ip_mask.prefix.value())

    @property
    def address(self):
        return unicode(self.net_add_page.ip_mask.address.text())
