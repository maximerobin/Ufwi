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

from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS
from ufwi_rpcd.common.tools import abstractmethod

from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.port_interval import PortInterval, PORT_MIN, PORT_MAX
from ufwi_ruleset.forward.attribute import Integer, Unicode

# Layer 4 protocol name => protocol number
IP_PROTOCOL = {
    u'icmp': 1,
    u'tcp': 6,
    u'udp': 17,
    u'icmpv6': 58,    # IPv6 Next Header value
}

class Protocol(Object):
    UPDATE_DOMAIN = u'protocols'
    layer3 = Unicode(optional=True)
    layer4 = Unicode(optional=True)

    def __init__(self, library, values, loader_context=None):
        Object.__init__(self, values, loader_context)

    def __unicode__(self):
        return tr('The protocol %s') % self.formatID()

    def match(self, other):
        if not isinstance(other, Protocol):
            return False
        types_a = self.getAddressTypes()
        types_b = other.getAddressTypes()
        if not (types_a & types_b):
            return False
        return self._matchProtocol(other)

    @abstractmethod
    def _matchProtocol(self, other):
        pass

    def sortKey(self):
        return (self.layer3, self.layer4)

class ProtocolLayer3(Protocol):
    def _matchProtocol(self, other):
        if isinstance(other, BaseProtocolLayer4):
            # layer3 matchs any layer4 protocol
            return True
        if isinstance(other, ProtocolLayer3):
            return self.layer3 == other.layer3
        return False

class ProtocolAnyIPv4(ProtocolLayer3):
    # Any IPv4 packet
    XML_TAG = u"ipv4"
    layer3 = Unicode(u"ipv4", const=True)

    def getAddressTypes(self):
        return set((IPV4_ADDRESS,))

class ProtocolAnyIPv6(ProtocolLayer3):
    # Any IPv6 packet
    layer3 = Unicode(u"ipv6", const=True)
    XML_TAG = u"ipv6"

    def getAddressTypes(self):
        return set((IPV6_ADDRESS,))

class BaseProtocolLayer4(Protocol):
    layer4 = Unicode()

    def _matchProtocol(self, other):
        if not isinstance(other, BaseProtocolLayer4):
            return False
        if self.layer4 != other.layer4:
            return False
        return self._matchLayer4(other)

    @abstractmethod
    def _matchLayer4(self, other):
        pass

class ProtocolLayer4(BaseProtocolLayer4):
    # IPv4 and IPv6 layer4 protocol
    XML_TAG = u"layer4"
    layer4 = Integer(0, 255)

    def getAddressTypes(self):
        return set((IPV4_ADDRESS, IPV6_ADDRESS))

    def _matchLayer4(self, other):
        return True

class ProtocolIGMP(BaseProtocolLayer4):
    # IPv4 only
    XML_TAG = u"igmp"
    layer4 = Unicode(u"igmp", const=True)

    def getAddressTypes(self):
        return set((IPV4_ADDRESS,))

    def _matchLayer4(self, other):
        return True

class ProtocolIcmpBase(BaseProtocolLayer4):
    type = Integer(0, 255, optional=True)
    code = Integer(0, 255, optional=True)

    def _matchValue(self, value_a, value_b):
        if value_a is None:
            return True
        if value_b is None:
            return False
        return value_a == value_b

    def _matchLayer4(self, other):
        return self._matchValue(self.type, other.type) and self._matchValue(self.code, other.code)

    def sortKey(self):
        return BaseProtocolLayer4.sortKey(self) + (self.type, self.code)

class ProtocolIcmp(ProtocolIcmpBase):
    # IPv4 only
    XML_TAG = u"icmp"
    layer4 = Unicode(u"icmp", const=True)

    def getAddressTypes(self):
        return set((IPV4_ADDRESS,))

class ProtocolICMPv6(ProtocolIcmpBase):
    # IPv6 only
    XML_TAG = u"icmpv6"
    layer4 = Unicode(u"icmpv6", const=True)

    def getAddressTypes(self):
        return set((IPV6_ADDRESS,))

class ProtocolTcpUdp(BaseProtocolLayer4):
    # IPv4 and IPv6
    sport = PortInterval(optional=True)
    dport = PortInterval(optional=True)

    def _matchPort(self, port_a, port_b):
        if not port_a:
            return True
        if not port_b:
            return False
        return port_a.match(port_b)

    def _matchLayer4(self, other):
        return self._matchPort(self.sport, other.sport) and self._matchPort(self.dport, other.dport)

    def getAddressTypes(self):
        return set((IPV4_ADDRESS, IPV6_ADDRESS))

    def sortKey(self):
        def portKey(port):
            if port:
                return (port.first, port.last)
            else:
                return (PORT_MIN, PORT_MAX)
        return (BaseProtocolLayer4.sortKey(self)
            + portKey(self.sport)
            + portKey(self.dport))

class ProtocolTcp(ProtocolTcpUdp):
    XML_TAG = u'tcp'
    layer4 = Unicode(u"tcp", const=True)

class ProtocolUdp(ProtocolTcpUdp):
    XML_TAG = u'udp'
    layer4 = Unicode(u"udp", const=True)

class Protocols(Library):
    NAME = 'protocols'
    ACL_ATTRIBUTE = 'protocols'
    XML_TAG = u"protocols"
    CHILD_CLASSES = (
        ProtocolAnyIPv4, ProtocolAnyIPv6,
        ProtocolTcp, ProtocolUdp,
        ProtocolIcmp, ProtocolICMPv6,
        ProtocolIGMP,
        ProtocolLayer4,
    )
    LAYER3_TO_CLASS = dict((cls.layer3.default, cls)
        for cls in CHILD_CLASSES if cls.layer3.default)
    LAYER4_TO_CLASS = dict((cls.layer4.default, cls)
        for cls in CHILD_CLASSES if cls.layer4.default)

    def _createObject(self, attr):
        layer3 = attr.pop('layer3', None)
        layer4 = attr.pop('layer4', None)
        if layer3:
            cls = self.LAYER3_TO_CLASS[layer3]
        else:
            cls = self.LAYER4_TO_CLASS[layer4]
        return cls(self, attr)

