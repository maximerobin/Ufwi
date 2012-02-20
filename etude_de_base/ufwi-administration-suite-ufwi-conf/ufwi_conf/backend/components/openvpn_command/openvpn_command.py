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


from ufwi_rpcd.backend import Component
from openvpn_command_client import startOpenVPNClient

class OpenVPNCommand(Component):

    NAME = "openvpn_command"
    VERSION = "1.0"
    API_VERSION = 2

    ROLES = {
        'conf_read' : set(('getUsersCount','getAllUsersCount', 'listVPN', 'getUserList')),
        'conf_write' : set(('@conf_read', 'addVPN', 'delVPN')),
        'multisite_read' : set(('getAllUsersCount',)),
        'multisite_write' : set(('@multisite_read',)),
        }

    def init(self, core):
        self.core = core
        self.client_list = {}
        return

    def service_addVPN(self, ctx, address, port):
        id = address + ':' + str(port)
        client = startOpenVPNClient(address, port)
        self.client_list[id] = client

    def service_delVPN(self, ctx, address, port):
        id = address + ':' + str(port)
        self.client_list[id].disconnect()
        del self.client_list[id]

    def service_listVPN(self, ctx):
        return self.client_list.keys()

    def service_getUsersCount(self, ctx, address, port):
        id = address + ':' + str(port)
        return self.client_list[id].getUserCount()

    def service_getAllUsersCount(self, ctx):
        count = 0
        for client in self.client_list.itervalues():
            count += client.getUserCount()
        return count

    def service_getUserList(self, ctx, address, port):
        id = address + ':' + str(port)
        ret = {}
        for entry in self.client_list[id].getClientList().iteritems():
            ret[entry[0]] = {}
            ret[entry[0]]['cert_cn'] = entry[1].cert_cn
            ret[entry[0]]['vpn_ip'] = entry[1].vpn_ip
            ret[entry[0]]['connected_since'] = entry[1].connected_since
        return ret

