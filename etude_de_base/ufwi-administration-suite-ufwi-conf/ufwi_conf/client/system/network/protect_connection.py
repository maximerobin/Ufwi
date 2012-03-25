#coding: utf-8

"""
Tell the user when a network modification means no more network connection,
at least between EAS and EdenWall

$Id$


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
from PyQt4.QtCore import QObject
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox
from socket import gethostbyname

from ufwi_rpcd.common import tr
from ufwi_conf.client.system.network.qnet_object import QNetObject

class Protector(QObject):
    def __init__(self, edenwall_ip, parent_widget):
        QObject.__init__(self)

        if isinstance(edenwall_ip, (str, unicode, int)):
            try:
                edenwall_ip = IP(edenwall_ip)
            except ValueError:
                edenwall_ip = gethostbyname(edenwall_ip)
                #not checking for error because we have been to resolve the
                #hostname a minute ago when we started EAS
                edenwall_ip = IP(edenwall_ip)

        if not isinstance(edenwall_ip, IP):
            raise TypeError("Need an IP descriptor or an IPy.IP")

        self.__edenwall_ip = edenwall_ip
        self.__parent_widget = parent_widget
        self.__qnetobject = QNetObject.getInstance()
        self.__qnetobject.registerCallbacks(
            self.acceptNetworkChange,
            self.handleNetworkChange
            )

        self.connect(
            self.__qnetobject,
            SIGNAL('reset'),
            self.reset
            )
        self.__danger_state_known = False
        self.reset()

    def reset(self):
        self.__danger_state_known = self.__indanger()

    def __indanger(self):
        return not self.__qnetobject.netcfg.hasIP(self.__edenwall_ip)

    def acceptNetworkChange(self):
        indanger = self.__indanger()
        if indanger == self.__danger_state_known:
            #Situation not changed
            return True

        if not indanger:
            self.__danger_state_known = False
            return True

        #delete the IP I use ?!
        confirmed = self.__ask(
            tr(
                "Your Administration Console is connected to this IP address (%s). "
                "Changing this interface is likely to interrupt your session."
            ) % self.__edenwall_ip
            )
        if confirmed:
            self.__danger_state_known = True
        return confirmed

    def handleNetworkChange(self):
        self.__danger_state_known = self.__indanger()

    def __ask(self, message):
        result = QMessageBox.question(
            self.__parent_widget,
            tr("This configuration change may be harmful"),
            message,
            QMessageBox.Ok|QMessageBox.No
            )

        return result == QMessageBox.Ok


