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

from datetime import datetime

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QVBoxLayout
from PyQt4.QtGui import QWidget

from ufwi_rpcd.common import tr
from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.colors import COLOR_CRITICAL, COLOR_ERROR, COLOR_SUCCESS
from ufwi_rpcc_qt.genericdelegates import EditColumnDelegate
from ufwi_rpcc_qt.html import Html, htmlBold
from ufwi_rpcc_qt.list_edit import ListEdit

from ufwi_conf.client.qt.input_widgets import TestButton
from ufwi_conf.client.qt.ip_inputs import IpOrFqdnEdit
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled

class NtpFrontend(ScrollArea):
    COMPONENT = 'ntp'
    LABEL = tr('NTP service')
    REQUIREMENTS = ('ntp',)
    ICON = ':/icons/chrono.png'

    def __init__(self, client, parent=None):
        ScrollArea.__init__(self)
        self.ntp_widget = NTPWidget(client, parent, self)
        self.setWidget(self.ntp_widget)
        self.setWidgetResizable(True)

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return ( ("ntp", 'getNtpConfig'), )

    def isModified(self):
        return self.ntp_widget.isModified()

    def isValid(self):
        return self.ntp_widget.isValid()

    def resetConf(self):
        self.ntp_widget.resetConf()

    def saveConf(self, message):
        self.ntp_widget.saveConf(message)

class NTPWidget(QFrame):
    def __init__(self, client, mainwindow, parent=None):
        QFrame.__init__(self, parent)
        self.init_done = False
        self.modified = False
        self.client = client
        self.mainwindow = mainwindow
        self._parent = parent

        form_layout = QVBoxLayout(self)
        title = QLabel("<H1>%s</H1>" % tr('NTP Configuration'))
        form_layout.addWidget(title)

        self.ntpServers = ListEdit()
        self.ntpServers.headers = self.getColumnLabels()
        self.ntpServers.displayUpDown = True
        self.ntpServers.readOnly = mainwindow.readonly
        self.ntpServers.editInPopup = True
        self.ntpServers.setColDelegate(self.createDelegateForColumn)
        self.mainwindow.writeAccessNeeded(self.ntpServers)

        self.connect(self.ntpServers, SIGNAL('itemDeleted'), self.serverDeleted)
        self.connect(self.ntpServers, SIGNAL('itemAdded'), self.serverAdded)
        self.connect(self.ntpServers, SIGNAL('itemModified'), self.serverModified)
        self.connect(self.ntpServers, SIGNAL('itemSorted'), self.serverSorted)

        self.addToInfoArea = mainwindow.addToInfoArea

        if self.resetConf():
            self.addToInfoArea(tr("NTP interface enabled"))
        else:
            self.addToInfoArea(tr("NTP interface disabled: NTP backend not loaded"), category=COLOR_CRITICAL)
            raise NuConfModuleDisabled("NTP")

        self.build()
        self.init_done = True

    def createDeleg(self):
        return EditColumnDelegate(IpOrFqdnEdit)

    def build(self):

        #Texts for buttons
        sync_text = tr('Force synchronization')
        get_time_text = tr('Get the EdenWall appliance time')

        #we need to use the longest string to set correct and same
        #width of the buttons
        sync_len = len(sync_text)
        get_time_len = len(get_time_text)
        if sync_len > get_time_len:
            longest_text = sync_text
        else:
            longest_text = get_time_text

        #sync button
        synchronize = TestButton(text=sync_text)
        self.mainwindow.writeAccessNeeded(synchronize)
        self.connect(synchronize, SIGNAL('clicked()'), self.callSynchronize)

        #get time button
        server_time = TestButton(text=get_time_text)
        self.connect(server_time, SIGNAL('clicked()'), self.getServerTime)

        #add to layout and set the same width
        layout = self.layout()
        for button in (synchronize, server_time):
            layout.addWidget(button)
            button.fixWidth(longest_text)

        #the ntp servers tabular
        self.layout().addWidget(self.ntpServers)

    def callSynchronize(self):
        self.mainwindow.addToInfoArea(tr('Launch NTP synchronization'))
        async = self.client.async()
        async.call("ntp", "syncTime",
            callback = self.success_sync,
            errback = self.error_sync
            )
        #TODO: implement callback/errback
        #return self.client.call("ntp", "syncTime")

    def getServerTime(self):
        async = self.client.async()
        async.call("ntp", "getServerTime",
            callback = self.printServerTime,
            errback = self.error_time
            )

    def printServerTime(self, time):
        server_time = unicode(datetime.fromtimestamp(float(time)))
        server_time = unicode(htmlBold(server_time))
        html = tr("Server time: %s") % server_time
        html = Html(html, escape=False)
        self.addToInfoArea(html)
        QMessageBox.information(self, tr("Server time"), tr("Server time: %s") % server_time)

    def success_sync(self, time):
        self.addToInfoArea(tr("NTP synchronization succeeded"), category=COLOR_SUCCESS)
        self.printServerTime(time)

    def error_sync(self, error):
        self.addToInfoArea(tr("NTP synchronization failed"), category=COLOR_ERROR)
        warning = QMessageBox(self)
        warning.setWindowTitle(tr('NTP synchronization failed'))
        warning.setText(tr('An error occurred during NTP synchronization'))
        warning.setDetailedText(exceptionAsUnicode(error))
        warning.setIcon(QMessageBox.Warning)
        warning.exec_()

    def error_time(self, *args):
        self.addToInfoArea(tr("Problem getting server time: %s") % args)

    def resetConf(self):
        try:
            self.ntpcfg = self.mainwindow.init_call("ntp", "getNtpConfig")
        except RpcdError:
            QWidget.setEnabled(self, False)
            return False

        data = []
        for server in self.ntpcfg['ntpservers'].split(' '):
            data.append([server])

        self.ntpServers.reset(data)

        return True

    def saveConf(self, message):
        self.ntpcfg['ntpservers'] = ''
        servers = []
        for server in self.ntpServers.rawData():
            servers.append(unicode(server[0]).strip())
        self.ntpcfg['ntpservers'] = ' '.join(servers)

        self.client.call("ntp", 'setNtpConfig', self.ntpcfg, message)
        self.setModified(False)

    def setModified(self, isModified=True, message=""):
        if self.init_done:
            if isModified:
                self.modified = True
                self.mainwindow.setModified(self._parent, True)
                if message:
                    self.mainwindow.addToInfoArea(message)
            else:
                self.modified = False

    def isModified(self):
        return self.modified

    def isValid(self):
        return True

    # for ListEdit
    def getColumnLabels(self):
        return [tr('NTP servers')]

    def createDelegateForColumn(self, column):
        return EditColumnDelegate(IpOrFqdnEdit)
    # ... for ListEdit

    def serverAdded(self):
        self.setModified(True, tr("NTP: server added"))

    def serverDeleted(self):
        self.setModified(True, tr("NTP: server deleted"))

    def serverModified(self):
        self.setModified(True, tr("NTP: server edited"))

    def serverSorted(self):
        self.setModified(True, tr("NTP: order of servers changed"))

