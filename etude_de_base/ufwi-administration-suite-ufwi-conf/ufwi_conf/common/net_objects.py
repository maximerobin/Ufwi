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


import IPy

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.config import deserializeElement
from ufwi_rpcd.common.config import serializeElement
from ufwi_rpcd.common.config import dict2list

from .id_store import PersistentID

def getItemOrDefault(dictionnary, item_name, function):
    """
    default value is returned by callable
    """
    result = dictionnary.get(item_name)
    if result is None:
        result = function()
    return result

class Net(PersistentID):
    ID_OFFSET = 0x0fffffff

    def __init__(self, label, net, **kwargs):
        assert isinstance(net, IPy.IP)
        PersistentID.__init__(self, **kwargs)
        self.label = label
        self.net = net


        self.primary_ip_addrs = \
        self.secondary_ip_addrs = \
        self.service_ip_addrs = None

        for attr_name in (
            'primary_ip_addrs',
            'secondary_ip_addrs',
            'service_ip_addrs',
            ):
            value = getItemOrDefault(
                kwargs,
                attr_name,
                set
                )
            setattr(
                self,
                attr_name,
                value
                )

    def _ip_addrs(self):
        return self.primary_ip_addrs | self.secondary_ip_addrs | self.service_ip_addrs

    ip_addrs = property(fget=_ip_addrs)

    def equalsSystemWise(self, other):
        if self.net != other.net:
            return False
        if not all(
            my_set == other_set
            for my_set, other_set in (
                (self.primary_ip_addrs, other.primary_ip_addrs),
                (self.secondary_ip_addrs, other.secondary_ip_addrs),
                (self.service_ip_addrs, other.service_ip_addrs),
            )
            ):
            return False

        return True

    def isValid(self):
        return self.isValidWithMsg()[0]

    def isValidWithMsg(self):
        has_primary_IP = len(self.primary_ip_addrs) > 0
        has_secondary_IP = len(self.secondary_ip_addrs) > 0

        ok = has_primary_IP is has_secondary_IP
        if not ok:
            message = tr(
                "A network with primary IPs must have "
                "secondary IPs, and conversely."
                )
            if has_primary_IP:
                complement = tr(
                    "You specified at least one primary IP "
                    "address, but no secondary address."
                )
            else:
                complement = tr(
                    "You specified at least one secondary IP "
                    "address, but no primary address."
                )
            return False, "%s\n%s" % (message, complement)

        for ip in self.ip_addrs:
            if ip.len() != 1:
                message = tr("The IP address field can not contain a network definition. Invalid IP:")
                message = "%s %s" % (message, unicode(ip))
                return False, message

        for ip in self.ip_addrs:
            if not self.net.overlaps(ip):
                return False, tr("'%s' does not match all network IP addresses ('%s')") % (ip, self.net)

        return True, tr("Valid network")

    def printFull(self):
        print "Net: '%s' %s" % (self.label, self.net)
        for ip in self.ip_addrs:
            print "    %s" % ip

    def strVersion(self):
        version = self.net.version()
        if version == 4:
            return 'inet'
        elif version == 6:
            return 'inet6'
        else:
            raise NotImplementedError("unknown IP version: %s" % version)

    def __repr__(self):
        addresses = ', '.join(str(addr) for addr in self.ip_addrs)
        return '<Net unique_id=%s label=%r net=%s ip_addrs=(%s)>' % (
            self.unique_id, self.label, self.net, addresses)

    def displayName(self):
        ip = unicode(self.net)
        if self.label == ip:
            return self.label
        if self.label == '':
            return ip
        return "%s (%s)" % (self.label, ip)

    @staticmethod
    def deserialize(serialized):
        return deserializeNet(serialized, Net)

class Route(PersistentID):
    """
    Attributes:
    dst: IPy.IP
    router: IPy.IP

    Method:
    isDefault: True if this is a default route for ipv4 or ipv6
    """
    ID_OFFSET = 0x1fffffff
    IPV4_DEFAULT = '0.0.0.0/0'
    IPV6_DEFAULT = '::/0'
    DEFAULT_ROUTES = {
        4: IPy.IP(IPV4_DEFAULT, make_net = True),
        6: IPy.IP(IPV6_DEFAULT, make_net = True)
    }

    def __init__(self, dst, router, **kwargs):
        PersistentID.__init__(self, **kwargs)
        if not isinstance(router, IPy.IP):
            router = IPy.IP(router)
        if not isinstance(dst, IPy.IP):
            if dst == 'default':
                dst = Route.DEFAULT_ROUTES[router.version()]
            else:
                dst = IPy.IP(dst, make_net = True)
        self.dst = dst
        self.router = router

    def equalsSystemWise(self, other):
        if self.router != other.router:
            return False
        if self.dst != other.dst:
            return False
        return True

    @classmethod
    def isDefaultDestination(cls, destination):
        # self.dst.overlaps(...) returns -1 (is contained) or 0 (no overlap) to mean False
        return any([destination.overlaps(net) == 1 for net in Route.DEFAULT_ROUTES.values()])

    def isDefault(self):
        return self.isDefaultDestination(self.dst)

    @staticmethod
    def deserialize(serialized):
        return deserializeRoute(serialized, Route)

def deserializeNet(serialized, cls):
    #BEGIN backwards compatibility
    ip_addrs = serialized.get('ip_addrs')
    if ip_addrs is not None:
        #convert existing IPs in service IPs
        ip_addrs = set(dict2list(ip_addrs))
        serialized['service_ip_addrs'] = serializeElement(ip_addrs)
        del serialized['ip_addrs']
    #END backwards compatibility

    label = serialized.pop('label')
    net = IPy.IP(serialized.pop('string_desc'), make_net = True)
    for attr in ('primary_ip_addrs', 'secondary_ip_addrs', 'service_ip_addrs'):
        serialized[attr] = deserializeElement(serialized[attr])

    _keys2unicode(serialized)

    return cls(label, net, **serialized)

def _keys2unicode(dictionnary):
    for attr, value in dictionnary.iteritems():
        if not isinstance(attr, str):
            del dictionnary[attr]
            dictionnary[str(attr)] = value

def deserializeRoute(serialized, cls):
    dst = IPy.IP(serialized.pop('dst'), make_net = True)
    router = IPy.IP(serialized.pop('router'))
    _keys2unicode(serialized)
    route = cls(dst, router, **serialized)
    return route

