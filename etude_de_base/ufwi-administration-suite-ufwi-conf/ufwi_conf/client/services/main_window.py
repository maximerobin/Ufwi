# -*- coding: utf-8 -*-

# $Id$

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


from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.client import RpcdError
from ufwi_conf.client.main_window import NuConfMainWindow
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible

# NuConf front-end modules:
from ufwi_conf.client.services.status_page import StatusPage
from ufwi_conf.client.services.access import AccessFrontend
from ufwi_conf.client.services.authentication import AuthenticationFrontend
if EDENWALL:
    from ufwi_conf.client.services.dhcp import DhcpFrontend
    from ufwi_conf.client.services.ids_ips import IdsIpsFrontend
    from ufwi_conf.client.services.mail import MailServicesFrontend
    from ufwi_conf.client.services.proxy import ProxyFrontend
    from ufwi_conf.client.services.roadwarrior import RoadWarriorFrontend, QOpenVpnObject
    from ufwi_conf.client.services.site2site import Site2SiteFrontend
    from ufwi_conf.client.services.snmpd import SnmpdFrontend

SERVICES = (
    StatusPage,
    AccessFrontend,
    AuthenticationFrontend,
)
if EDENWALL:
    SERVICES += (
        DhcpFrontend,
        IdsIpsFrontend,
        ProxyFrontend,
        MailServicesFrontend,
        Site2SiteFrontend,
        RoadWarriorFrontend,
        SnmpdFrontend,
        )

class MainWindow(NuConfMainWindow):
    ROLES = set(('conf_read', 'conf_write'))
    ICON = ':/icons/application.png'

    def __init__(self, application, client, **kw):
        NuConfMainWindow.__init__(self, application, client, tr("Services"), **kw)

    def _load(self):
        if EDENWALL and (not NuConfMainWindow.minimalMode):
            # before creation of frontends, initialize Q

            try:
                serialized_openvpn_conf = self.init_call('openvpn', 'getOpenVpnConfig')
                QOpenVpnObject.getInstance().openvpn = serialized_openvpn_conf
            except (RpcdError, DatastructureIncompatible):
                # openvpn backend is not available
                pass

    def getTree(self, minimal_mode, model):
        if minimal_mode:
            return [ ]
        else:
            if model == 'EMF':
                for page in (
                    "Authentication server",
                    "DHCP service",
                    "IDS/IPS",
                    "Proxy service"):
                    try:
                        self.remove_page_from_tree(SERVICES, page)
                    except ValueError:
                        pass
            return SERVICES

