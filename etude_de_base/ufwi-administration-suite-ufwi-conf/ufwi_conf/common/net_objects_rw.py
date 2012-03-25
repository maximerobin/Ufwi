
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

from ufwi_rpcd.common.config import serializeElement

from .id_store import PersistentID
from .net_exceptions import NetCfgError
from .net_objects import Net, Route, deserializeNet, deserializeRoute

class NetRW(Net):

    def addIP(self, ip):
        if not self.net.overlaps(ip):
            raise NetCfgError('%s should overlap %s' %( self.net, ip))
        self.service_ip_addrs.add(ip)

    def serialize(self):
        serialized = PersistentID.serialize(self)
        serialized['label'] = self.label
        serialized['string_desc'] = unicode(self.net)
        serialized['service_ip_addrs'] = serializeElement(self.service_ip_addrs)
        serialized['primary_ip_addrs'] = serializeElement(self.primary_ip_addrs)
        serialized['secondary_ip_addrs'] = serializeElement(self.secondary_ip_addrs)

        return serialized

    @staticmethod
    def deserialize(serialized):
        return deserializeNet(serialized, NetRW)

class RouteRW(Route):

    def serialize(self):
        serialized = PersistentID.serialize(self)
        serialized['dst'] = unicode(self.dst)
        serialized['router'] = unicode(self.router)
        return serialized

    @staticmethod
    def deserialize(serialized):
        return deserializeRoute(serialized, RouteRW)
