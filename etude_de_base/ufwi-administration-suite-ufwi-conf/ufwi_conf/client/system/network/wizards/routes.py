# -*- coding: utf-8 -*-

"""
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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QGridLayout
from PyQt4.QtGui import QGroupBox
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QPushButton
from PyQt4.QtGui import QWizardPage

from ufwi_rpcd.common import tr

from ufwi_conf.common.net_exceptions import NoMatch
from ufwi_conf.common.net_objects_rw import RouteRW
from ufwi_conf.common.net_objects import Route
from ufwi_conf.client.qt.ip_inputs import IpEdit
from ufwi_conf.client.qt.ip_inputs import NetworkEdit
from ufwi_conf.client.qt.ip_inputs import NetworkCombo

from .common import NetworkCommonWizard
from ..qnet_object import QNetObject
from ..network_models_names import MODEL_NETWORKS_EXCL_HA

DESTINATION, GATEWAY = range(2)

class Help(QFrame):
    def __init__(self, parent=None):
        QFrame.__init__(self, parent)
        layout = QHBoxLayout(self)
        self.icon = QLabel()
        self.icon.setPixmap(QPixmap(":/icons-32/info"))
        layout.addWidget(self.icon)
        self.message = QLabel()
        self.message.setWordWrap(True)
        layout.addWidget(self.message)
        layout.addStretch()
        self.setNoMessage()

    def setMessage(self, text):
        self.message.setText(text)
        self.message.show()
        self.icon.show()
        self.setFrameStyle(QFrame.StyledPanel)

    def setNoMessage(self):
        self.message.hide()
        self.icon.hide()
        self.setFrameStyle(QFrame.NoFrame)

def _strdefault(string):
    """
    0 if not a default or not an IP
    4 if == 0.0.0.0
    6 if == 0::
    """
    try:
        ip = IP(string)
    except:
        return 0
    if ip == Route.DEFAULT_ROUTES[4]:
        return 4
    elif ip == Route.DEFAULT_ROUTES[6]:
        return 6
    return 0

def _valid_gateway_on_network(gateway_ip, str_gateway, selected_net):
    if \
    not(
        (gateway_ip.version() == 6) and (gateway_ip.iptype() == 'LINKLOCAL')
        ) \
    and (1 != selected_net.net.overlaps(str_gateway)):
        return False, tr('The gateway is not in the selected network')
    return True, ''

def _valid_not_too_much_default_gw(
    netcfg,
    dst_ip,
    dst_version,
    editing_default_v4,
    editing_default_v6
    ):
    if any([dst_ip.overlaps(net) == 1 for net in Route.DEFAULT_ROUTES.values()]):
        try:
            netcfg.getDefaultGateway(dst_version)
        except NoMatch:
            # no default route
            pass
        else:
            if dst_version == 4:
                if not editing_default_v4:
                    return False, tr('There is already a default IPv4 route.')
            else:
                if not editing_default_v6:
                    return False, tr('There is already a default IPv6 route.')

    return True, ''


class FormPage(QWizardPage):
    def __init__(self, data, ip_version=4, parent=None):
        QWizardPage.__init__(self, parent)

        self.__editing_default_state = _strdefault(unicode(data[DESTINATION]))

        self.qnetobject = QNetObject.getInstance()
        self.buildGui()
        self.fillView(data)

    def _isEditingDefaultV4Route(self):
        return self.__editing_default_state == 4

    def _isEditingDefaultV6Route(self):
        return self.__editing_default_state == 6

    def buildGui(self):
        layout = QFormLayout(self)
        self.is_default = False
        self.setTitle(tr("Route specification"))
        self.setSubTitle(tr("Specify a route"))

        self.network = NetworkCombo(parent=self, modelname=MODEL_NETWORKS_EXCL_HA)
        layout.addRow(tr("Network :"), self.network)

        dst_group = QGroupBox()
        layout.addRow(dst_group)
        dst_group.setTitle(tr("Route parameters"))
        form = QGridLayout(dst_group)

        self.destination = NetworkEdit()
        self.gateway = IpEdit()

        self.registerField("destination", self.destination)
        form.addWidget(QLabel(tr("Destination")), 0, 0)
        form.addWidget(self.destination, 0, 1)
        self.connect(self.gateway, SIGNAL('textChanged(QString)'), self.ifCompleteChanged)
        self.connect(self.destination, SIGNAL('textChanged(QString)'), self.ifCompleteChanged)

        build_default = QPushButton(tr("Build a default route"))
        form.addWidget(build_default, 0, 2)
        self.connect(build_default, SIGNAL('clicked()'), self.setDefaultRoute)

        self.registerField("gateway", self.gateway)
        form.addWidget(QLabel(tr("Gateway")), 2, 0)
        form.addWidget(self.gateway, 2, 1)

        self.message = Help()

        form.addWidget(self.message, 3, 0, 1, 3)

    def fillView(self, data):
        if data[DESTINATION]:
            self.destination.setText(data[DESTINATION])

        if data[GATEWAY]:
            self.gateway.setText(data[GATEWAY])
            gateway = IP(unicode(data[GATEWAY]))
            net = self.qnetobject.netcfg.getNetForIp(gateway)
            if net is not None:
                self.network.selectNet(net)

    def ifCompleteChanged(self, orig_value=False):
        new_value = self.isComplete()
        if new_value != orig_value:
            self.emit(SIGNAL('completeChanged()'))

    def setDefaultRoute(self):
        selected_net = self.network.getNet()
        if selected_net is None:
            self.message.setMessage("<i>%s</i>" % tr("There is no network configuration, you cannot configure routes"))
            version = 4
        else:
            version = selected_net.net.version()

        if 4 == version:
            default = Route.IPV4_DEFAULT
        else:
            default = Route.IPV6_DEFAULT
        self.destination.setText(default)

    def isComplete(self):
        gw_text = unicode(self.field('gateway').toString())
        dst_text = unicode(self.field('destination').toString())
        if not gw_text:
            self.message.setMessage("<i>%s</i>" % tr("Please fill the gateway field"))
            return False

        if (not self.gateway.isValid()):
            self.message.setMessage("<i>%s</i>" % tr("Invalid gateway"))
            return False

        if not dst_text:
            self.message.setMessage("<i>%s</i>" % tr("Please fill the destination field"))
            return False

        if not self.destination.isValid():
            self.message.setMessage("<i>%s</i>" % tr("Invalid destination"))
            return False

        destination_version, gateway_version = \
            (item.version() for item in (self.destination.value(), self.gateway.value()))

        if destination_version != gateway_version:
            error = "%s (%s) %s (%s)." % (
                tr("The gateway IP version"), gateway_version,
                tr("does not match the destination IP version"), destination_version
            )

            self.message.setMessage(error)
            return False

        str_gateway = unicode(self.field('gateway').toString())
        gateway_ip = IP(str_gateway)

        selected_net = self.network.getNet()
        if selected_net is None:
            self.message.setMessage("<i>%s</i>" % tr("There is no network configuration, you cannot configure routes"))
            return False

        ok, msg = _valid_gateway_on_network(gateway_ip, str_gateway, selected_net)
        if not ok:
            self.message.setMessage(msg)
            return False

        ok, msg = _valid_not_too_much_default_gw(
            self.qnetobject.netcfg,
            self.destination.value(),
            destination_version,
            self._isEditingDefaultV4Route(),
            self._isEditingDefaultV6Route()
            )
        if not ok:
            self.message.setMessage(msg)
            return False

        ok, msg = self.qnetobject.netcfg.isValidWithMsg()
        if not ok:
            self.message.setMessage(msg)
            return False

        self.message.setNoMessage()
        return True

    def validatePage(self):
        route = self.integrate_route()
        if not route.isDefault():
            return True
        try:
            default_router, interface = self.qnetobject.netcfg.getDefaultGateway(
                route.dst.version()
                )
        except NoMatch:
            return True

        default_route = None
        for other_route in interface.routes:
            if other_route.isDefault():
                default_route = other_route
        if default_route is not None:
            interface.routes.discard(default_route)

        ok, msg = self.qnetobject.netcfg.isValidWithMsg()
        if not ok:
            self.message.setMessage(msg)
            return False

        return True

    def integrate_route(self):
        route = RouteRW(
            self.destination.value(),
            self.gateway.value(),
            )
        return route

class RouteWizard(NetworkCommonWizard):
    def __init__(self, data, title, parent=None):
        NetworkCommonWizard.__init__(self, parent=parent)

        self.data_page = FormPage(data)
        self.addPage(self.data_page)

        self.network = self.data_page.network
        self.gateway_input = self.data_page.gateway
        self.destination_input = self.data_page.destination

    def interface(self):
        return self.network.getInterface()

    def integrate_route(self):
        return self.data_page.integrate_route()

    def getData(self):
        return [ unicode(i) for i in (unicode(self.destination_input.value()),
            unicode(self.gateway_input.value()),
            self.network.getInterface().system_name) ]
