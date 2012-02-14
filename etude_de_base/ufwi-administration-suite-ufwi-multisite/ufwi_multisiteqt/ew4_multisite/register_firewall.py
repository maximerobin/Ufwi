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

$Id$
"""

from IPy import IP
from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import SIGNAL

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.central_dialog import CentralDialog, IP_OR_FQDN_REGEXP, HOSTNAME_OR_FQDN_REGEXP
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from nuconf.common.netcfg import deserializeNetCfg

from .ui.register_firewall_ui import Ui_RegisterFirewall
from .strings import APP_TITLE

class InvalidHostname(Exception):
    pass

class RegisterFirewallWindow(CentralDialog):

    PORTS = {'HTTP':  8080,
             'HTTPS': 8443,
            }

    def __init__(self, client, edw_list, parent=None):
        CentralDialog.__init__(self, parent)

        self.ui = Ui_RegisterFirewall()
        self.ui.setupUi(self)
        self.connectButtons(self.ui.buttonBox)
        self.setRegExpValidator(self.ui.name, HOSTNAME_OR_FQDN_REGEXP)
        self.setRegExpValidator(self.ui.hostname, IP_OR_FQDN_REGEXP)
        self.setNonEmptyValidator(self.ui.password)
        self.setNonEmptyValidator(self.ui.login)
        self.connect(self.ui.protocol, SIGNAL('currentIndexChanged(int)'), self.protocolChanged)
        self.setWindowTitle(APP_TITLE)

        self.client = client
        self.edw_list = edw_list

    def isDefaultPort(self, port):
        for proto, dport in self.PORTS.iteritems():
            if dport == port:
                return True
        return False

    def protocolChanged(self, i):
        last_port = self.ui.port.value()
        if not self.isDefaultPort(last_port):
            # Change port to default protocol port only if user
            # hasn't changed it to a non-default port before.
            return

        protocol = unicode(self.ui.protocol.currentText())
        try:
            self.ui.port.setValue(self.PORTS[protocol])
        except KeyError:
            print "%s isn't a valid protocol?" % protocol

    def run(self):
        return self.execLoop()

    def save(self):
        try:
            hostname = unicode(self.ui.hostname.text())
            self.checkHostname(hostname)
            name = unicode(self.ui.name.text())
            for edw in self.edw_list:
                if edw.getID() == name:
                    if QMessageBox.warning(None, APP_TITLE, tr("A firewall with this name is already registered. Do you want to register it again?"), QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
                        return False
                    break
            port = self.ui.port.value()
            protocol = unicode(self.ui.protocol.currentText()).lower()
            login = unicode(self.ui.login.text())
            password = unicode(self.ui.password.text())

            self.client.call('multisite_master', 'register_firewall', name, hostname, port, protocol, login, password)
            return True
        except (RpcdError, InvalidHostname), e:
            QMessageBox.critical(self, self.tr('Rpcd error'), exceptionAsUnicode(e))
            return False

    def checkHostname(self, hostname):
        net = self.client.call('network', 'getNetconfig')
        net = deserializeNetCfg(net)

        if IP(hostname) in list(net.iterAddresses()) + [IP('127.0.0.1'), IP('::1')]:
            raise InvalidHostname(tr('You cannot register this EMF appliance on itself'))

        #raise Exception('blah')
