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

from logging import debug
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.genericdelegates import EditColumnDelegate
from ufwi_rpcc_qt.list_edit import ListEdit

from ufwi_conf.client.qt.ip_inputs import IpOrFqdnEdit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.network.wizards.routes import RouteWizard
from ufwi_conf.common.net_objects_rw import RouteRW

from .qnet_object import QNetObject

DESTINATION, GATEWAY, INTERFACE = range(3)

class RoutesFrontend(ScrollArea):
    COMPONENT = 'network'
    IDENTIFIER = 'routes'
    LABEL = tr('Routed networks')
    REQUIREMENTS = ('network',)
    ICON = ':/icons/network.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        self.mainwindow = parent
        self._modified = False
        self.q_netobject = QNetObject.getInstance()
        self.connect(self.q_netobject, SIGNAL('cancelled'), self.resetConf)
        box_layout = QVBoxLayout(self)

        title = QLabel("<H1>%s</H1>" % tr("Routed networks"))
        box_layout.addWidget(title)
        if self.q_netobject.netcfg is None:
            debug("Routes can not load: no netcfg loaded")
            msg_area = MessageArea()
            msg_area.setMessage(
                tr("Routes not loaded"),
                tr("Could not get networking information from the appliance"),
                "critical"
                )
            box_layout.addWidget(msg_area)
            box_layout.addStretch()
            return

        self.ifaces_frontend = parent.widgets['Network']
        self.connect(self.ifaces_frontend, SIGNAL('modified'), self.resetConf)

        # TODO write useful routesList.setEditBoxDescription('') (used when a route is modified)
        self.routesList = ListEdit()
        self.routesList.headers = [self.tr('Destination'), self.tr('Gateway'), 'Interfaces']
        # Interfaces column is hidden
        self.routesList.hideColumn(2)
        self.routesList.readOnly = self.mainwindow.readonly
        self.routesList.displayUpDown = False
        self.routesList.editInPopup = True
        self.routesList.setColDelegate(self.createDelegateForColumn)
        self.routesList.setEditBox(self.createWizard)
        self.mainwindow.writeAccessNeeded(self.routesList)

        self.connect(self.routesList, SIGNAL('itemDeleted'), self.routeDeleted)
        self.connect(self.routesList, SIGNAL('itemAdded'), self.routeAdded)
        self.connect(self.routesList, SIGNAL('itemModified'), self.routeModified)

        box_layout.addWidget(self.routesList)

        self.resetConf()

    # for ListEdit

    def createDelegateForColumn(self, column):
        return EditColumnDelegate(IpOrFqdnEdit)

    def createWizard(self, data, options, title, parent=None):
        return RouteWizard(data, title, parent)
    # ... for ListEdit

    def setModified(self, isModified=True):
        self._modified = True
        if self._modified:
            self.mainwindow.setModified(self, True)

    def isModified(self):
        return self._modified

    def resetConf(self):
        netcfg = self.q_netobject.netcfg
        routes = []
        for route in netcfg.iterRoutes():
            interface = netcfg.getRouteInterface(route)
            routes.append([unicode(route.dst), unicode(route.router), interface.system_name, route])
        self.routesList.reset(routes)

    def routeDeleted(self):
        self.setModified(True)
        self.updateRoutes()
        self.ifaces_frontend.setModified(tr("Route deleted", "This text appears in ufwi_conf log console"))

    def routeAdded(self):
        self.setModified(True)
        self.updateRoutes()
        self.ifaces_frontend.setModified(tr("New route", "This text appears in ufwi_conf log console"))

    def routeModified(self):
        self.setModified(True)
        self.updateRoutes()
        self.ifaces_frontend.setModified(tr("Route edited", "This text appears in ufwi_conf log console"))

    def updateRoutes(self):
        netcfg = self.q_netobject.netcfg

        for iface in self.q_netobject.netcfg.iterInterfaces():
            iface.routes.clear()

        routes = self.routesList.rawData()
        for route in routes:
            dest = unicode(route[DESTINATION])
            gateway = unicode(route[GATEWAY])
            iface = unicode(route[INTERFACE])
            interface = netcfg.getInterfaceBySystemName(iface)
            assert interface is not None
            interface.addRoute(RouteRW(dest, gateway))

