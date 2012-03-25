
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

from PyQt4.QtCore import Qt, QRegExp, SIGNAL
from PyQt4.QtGui import QDialog, QDialogButtonBox
from ufwi_rpcd.common.network import (IPV4_REGEX_STR, IPV6_REGEX_STR,
    HOSTNAME_REGEX_STR,
    FQDN_REGEX_STR_PART, FQDN_REGEX_STR,
    HOSTNAME_OR_FQDN_REGEX_PART, HOSTNAME_OR_FQDN_REGEX_STR,
    MAIL_REGEX_STR, NET_ALL_REGEX_STR)
from ufwi_rpcc_qt.validate_widgets import ValidateWidgets

IPV4_REGEXP = QRegExp(IPV4_REGEX_STR)
IPV6_REGEXP = QRegExp(IPV6_REGEX_STR)
IP_ALL_REGEXP = QRegExp(ur"%s|%s" % (IPV4_REGEX_STR, IPV6_REGEX_STR))

HOSTNAME_REGEXP = QRegExp(HOSTNAME_REGEX_STR, Qt.CaseInsensitive)
FQDN_REGEXP = QRegExp(FQDN_REGEX_STR, Qt.CaseInsensitive)
HOSTNAME_OR_FQDN_REGEXP = QRegExp(HOSTNAME_OR_FQDN_REGEX_STR, Qt.CaseInsensitive)

IP_OR_FQDN_REGEXP =  QRegExp(ur"^(?:%s|%s|%s)$" % (IPV4_REGEX_STR, IPV6_REGEX_STR, FQDN_REGEX_STR_PART), Qt.CaseInsensitive)
IP_OR_HOSTNAME_OR_FQDN_REGEXP = QRegExp(ur"^(?:%s|%s|%s)$" % (IPV4_REGEX_STR, IPV6_REGEX_STR, HOSTNAME_OR_FQDN_REGEX_PART), Qt.CaseInsensitive)

MAIL_REGEXP = QRegExp(MAIL_REGEX_STR, Qt.CaseInsensitive)

NET_ALL_REGEXP = QRegExp(NET_ALL_REGEX_STR)

class CentralDialog(QDialog, ValidateWidgets):
    def __init__(self, window, accept=None):
        QDialog.__init__(self, window)
        if accept is None:
            accept = self.accept
        ValidateWidgets.__init__(self, accept)

    def connectButtons(self, button_box):
        self.connect(button_box, SIGNAL("accepted()"), self.checkAccept)
        self.ok_button = button_box.button(QDialogButtonBox.Ok)
        if hasattr(button_box, 'Cancel'):
            self.connect(button_box, SIGNAL("rejected()"), self.close)
        if hasattr(button_box, 'Help'):
            self.connect(button_box, SIGNAL("helpRequested()"), self.help_action)

    def help_action(self):
        """
        Override this method if you provide a help button
        """

    def execLoop(self):
        while True:
            ret = self.exec_()
            if not ret:
                return False
            if self.save():
                return True

