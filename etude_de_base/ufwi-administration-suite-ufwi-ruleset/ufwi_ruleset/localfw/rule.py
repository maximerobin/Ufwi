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

from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.network import (INTERFACE_NAME_REGEX_STR,
    IPV4_ADDRESS, IPV6_ADDRESS)
from ufwi_ruleset.localfw.error import LocalFWError
from ufwi_ruleset.iptables.arguments import Arguments
import re

RULES_NAME_REGEX = re.compile("^[a-zA-Z0-9_-]{1,40}$")
IFACE_REGEX = re.compile(INTERFACE_NAME_REGEX_STR)

def checkAddressType(address, address_type):
    version = address.version()
    if address_type == IPV6_ADDRESS:
        return version == 6
    else:
        return version == 4

class BaseRule:
    def __init__(self, address_type):
        if address_type not in (IPV4_ADDRESS, IPV6_ADDRESS):
            raise LocalFWError(
                tr("Invalid address type: %s"),
                repr(address_type))
        self.address_type = address_type

    @abstractmethod
    def getIptable(self):
        pass

class IptableRule(BaseRule):
    def __init__(self, address_type, iptable):
        BaseRule.__init__(self, address_type)
        self.iptable = iptable

    def getIptable(self):
        return self.iptable

class FilterRule(BaseRule):
    def __init__(self, address_type, chain, proto, port, src_addr, dst_addr,
    in_iface, out_iface, decision, icmp_type=None, icmpv6_type=None):
        BaseRule.__init__(self, address_type)

        # Check values
        if chain not in ('INPUT', 'FORWARD', 'OUTPUT'):
            raise LocalFWError(tr("Invalid chain: %s"), chain)
        if proto is not None and proto not in ('ip', 'ah', 'esp', 'tcp', 'udp', 'icmp', 'icmpv6'):
            raise LocalFWError(tr("Unknown protocol: %s"), proto)

        # port (TCP/UDP)
        if port is not None \
        and not(0 <= port <= 65535):
            raise LocalFWError(tr("Invalid port number: %s"), repr(port))
        if (port is not None) and (proto not in ('tcp', 'udp')):
            raise LocalFWError(tr("Can not specify a port (%s) for the %s protocol"), port, proto)

        # ICMP, ICMPv6
        if icmp_type is not None \
        and not(0 <= icmp_type <= 255):
            raise LocalFWError(tr("Invalid ICMP type: %s"), repr(icmp_type))
        if (icmp_type is not None) and (proto != 'icmp'):
            raise LocalFWError(tr("Can not specify an icmp_type (%s) for the %s protocol"), icmp_type, proto)
        if icmpv6_type is not None \
        and not(0 <= icmpv6_type <= 255):
            raise LocalFWError(tr("Invalid ICMP type: %s"), repr(icmpv6_type))
        if (icmpv6_type is not None) and (proto != 'icmpv6'):
            raise LocalFWError(tr("Can not specify an icmpv6_type (%s) for the %s protocol"), icmpv6_type, proto)

        # input/output interface
        if in_iface is not None\
        and not IFACE_REGEX.match(in_iface):
            raise LocalFWError(tr("Invalid input interface name: %s"), repr(in_iface))
        if out_iface is not None\
        and not IFACE_REGEX.match(out_iface):
            raise LocalFWError(tr("Invalid output interface name: %s"), repr(out_iface))

        # Decision, source/destination addresses
        if decision not in ('ACCEPT', 'DROP', 'REJECT'):
            raise LocalFWError(tr("Invalid decision: %s"), decision)
        if src_addr and not checkAddressType(src_addr, address_type):
            raise LocalFWError(tr("Source address is not an %s address: %s"), address_type, unicode(src_addr))
        if dst_addr and not checkAddressType(dst_addr, address_type):
            raise LocalFWError(tr("Destination address is not an %s address: %s"), address_type, unicode(dst_addr))

        self.chain       = chain
        self.proto       = proto
        self.port        = port
        self.icmp_type   = icmp_type
        self.icmpv6_type = icmpv6_type
        self.src_addr    = src_addr
        self.dst_addr    = dst_addr
        self.in_iface    = in_iface
        self.out_iface   = out_iface
        self.decision    = decision

    def getIptable(self):
        line = Arguments('-A', self.chain)
        if self.proto:
            line += Arguments('-p', self.proto)
        if self.port:
            line += Arguments('--dport', self.port)
        if self.icmp_type:
            line += Arguments('--icmp-type', self.icmp_type)
        if self.icmpv6_type:
            line += Arguments('--icmpv6-type', self.icmpv6_type)
        if self.src_addr:
            line += Arguments('--src', self.src_addr)
        if self.dst_addr:
            line += Arguments('--dst', self.dst_addr)
        if self.in_iface:
            line += Arguments('-i', self.in_iface)
        if self.out_iface:
            line += Arguments('-o', self.out_iface)

        if self.proto in ('tcp', 'udp'):
            if (self.proto == 'tcp') and (self.chain != "INPUT"):
                line += Arguments('--syn')
            line += Arguments('-m', 'state', '--state', 'NEW')

        line += Arguments('-j', self.decision)
        return unicode(line)

class RulesFile:
    def __init__(self, name):
        if not RULES_NAME_REGEX.match(name):
            raise LocalFWError(tr("Invalid rule set name: %s"), repr(name))
        self.name = name
        self.clear()

    def clear(self):
        self.ipv4_filter_rules = []
        self.ipv4_mangle_rules = []
        self.ipv4_nat_rules = []
        self.ipv6_filter_rules = []
        self.ipv6_mangle_rules = []
        self.ipv6_nat_rules = []

    def addFilterRule(self, rule):
        if rule.address_type == IPV6_ADDRESS:
            rules = self.ipv6_filter_rules
        else:
            rules = self.ipv4_filter_rules
        rules.append(rule)

    def addMangleRule(self, rule):
        if rule.address_type == IPV6_ADDRESS:
            rules = self.ipv6_mangle_rules
        else:
            rules = self.ipv4_mangle_rules
        rules.append(rule)

    def addNatRule(self, rule):
        if rule.address_type == IPV6_ADDRESS:
            rules = self.ipv6_nat_rules
        else:
            rules = self.ipv4_nat_rules
        rules.append(rule)

