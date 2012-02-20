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


from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_conf.client.main_window import NuConfMainWindow
from ufwi_conf.client.system.network import QNetObject
from ufwi_rpcd.common import EDENWALL

if EDENWALL:
    from ufwi_conf.client.system.ha import QHAObject

# NuConf front-end modules:
#from ufwi_conf.client.system.admin_access import UsersFrontend, AclFrontend, SessionsFrontend, AdminFrontend
from ufwi_conf.client.system.contact import ContactFrontend
from ufwi_conf.client.system.ha import HAConfigFrontend
from ufwi_conf.client.system.httpout import HttpOutFrontend
if EDENWALL:
    from ufwi_conf.client.system.license import LicenseFrontend
from ufwi_conf.client.system.network.ifaces_panel import IfacesFrontend
from ufwi_conf.client.system.network.routes_panel import RoutesFrontend
from ufwi_conf.client.system.ntp import NtpFrontend
from ufwi_conf.client.system.nuauth.user_dir import NuauthFrontEnd
from ufwi_conf.client.system.resolv import ResolvFrontend
from ufwi_conf.client.system.syslog_export import SyslogExportFrontend
from ufwi_conf.client.system.tools import ToolsFrontend
from ufwi_conf.client.system.Update import Update

from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible

if EDENWALL:
    _LICENSE_FRONTEND_INFO = LicenseFrontend

SYSTEM = [
    IfacesFrontend,
    RoutesFrontend,
    ContactFrontend,
    HAConfigFrontend,
    ResolvFrontend,
    NtpFrontend,
    HttpOutFrontend,
    NuauthFrontEnd,
    SyslogExportFrontend,
    Update,
    ToolsFrontend,
]
if EDENWALL:
    SYSTEM.insert(-2, _LICENSE_FRONTEND_INFO)

class MainWindow(NuConfMainWindow):
    ROLES = set(('conf_read', 'conf_write'))
    ICON = ':/icons/settings.png'

    def __init__(self, application, client, **kw):
        self.__cached_has_ha = None

        NuConfMainWindow.__init__(self, application, client, tr("System"), **kw)

    @staticmethod
    def get_calls():
        return (
            ('network', 'getNetconfig'), ('ha', 'getConfig'),
        )

    def _load(self):
        if not NuConfMainWindow.minimalMode:
            # before creation of frontends, initialize QNetObject, QHAObject
            serialized_net_conf = self.init_call('network', 'getNetconfig')
            if serialized_net_conf is not None:
                QNetObject.getInstance().netcfg = serialized_net_conf


            if not self.__has_ha():
                return
            try:
                serialized_ha_conf = self.init_call('ha', 'getConfig')
                if serialized_ha_conf is None:
                    return
                QHAObject.getInstance().hacfg = serialized_ha_conf
            except (RpcdError, DatastructureIncompatible):
                # ha backend is not available
                pass

    def __has_ha(self):
        if not EDENWALL:
            return False
        if self.__cached_has_ha is not None:
            return self.__cached_has_ha
        value = 'ha' in self.available_backends
        self.__cached_has_ha = value
        return value

    def getTree(self, minimal_mode, model):
        if not EDENWALL:
            return SYSTEM
        if minimal_mode:
            return [ _LICENSE_FRONTEND_INFO, ]
        else:
            if not self.__has_ha():
                try:
                    self.remove_page_from_tree(SYSTEM, tr('High Availability'))
                except ValueError:
                    pass
            return SYSTEM

