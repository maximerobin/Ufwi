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

from IPy import IP
from socket import getaddrinfo, AF_INET6, AF_INET, gaierror

from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.getter import getOptionalDict, getInteger, getUnicode, getList, getBoolean
from ufwi_rpcd.backend import Component, tr

from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS
from ufwi_ruleset.localfw import VERSION
from ufwi_ruleset.localfw.error import LocalFWError
from ufwi_ruleset.localfw.rule import FilterRule, IptableRule, RulesFile
from ufwi_ruleset.localfw.apply_rules import applyRules

def getIP(addr, address_type):
    try:
        addr = IP(addr)
    except ValueError:
        pass
    else:
        return set((addr,))

    if address_type == IPV6_ADDRESS:
        family = AF_INET6
    else:
        family = AF_INET

    addresses = set()
    try:
        for family2, socktype, proto, canonname, sockaddr \
        in getaddrinfo(addr, None, family):
            address = IP(unicode(sockaddr[0]))
            addresses.add(address)
    except gaierror, gai_err:
        raise LocalFWError(
            tr('Unable to get the "%s" host address: %s'),
            unicode(addr), toUnicode(gai_err.args[1]))
    if not addresses:
        raise LocalFWError(
            tr('Unable to resolve "%s" the host address'),
            unicode(addr))
    return addresses

def getAddressList(attr, key, address_type):
    default = (None,)
    if key not in attr:
        return default

    addresses = []
    for value in getList(getUnicode, attr.pop(key)):
        ips = getIP(value, address_type)
        addresses.extend(ips)
    if not addresses:
        return default
    return addresses

class LocalFWComponent(Component):
    """
    Local firewall component: manage the INPUT and OUTPUT rules
    of the filter, mangle and nat tables for Netfilter.
    """
    NAME = "localfw"
    VERSION = VERSION
    API_VERSION = 2
    REQUIRES = ('ufwi_ruleset',)
    ROLES = {
        'multisite_write' : set((
            'open', 'clear',
            'addFilterRule', 'addFilterIptable', 'addMangleIptable', 'addNatIptable',
            'apply', 'close'))
    }
    ACLS =  {
        'ufwi_ruleset' : set(('reapplyLastRuleset',))
    }

    def init(self, core):
        self.core = core

    def hasRules(self, context):
        return (self.NAME in context.getSession())

    def getRulesFile(self, context):
        return context.getSession()[self.NAME]

    def saveSession(self, context):
        context.getSession().save()

    def service_open(self, context, name):
        rules_file = RulesFile(name)
        context.getSession()[self.NAME] = rules_file
        self.saveSession(context)
        return rules_file.name

    def service_clear(self, context):
        rules = self.getRulesFile(context)
        rules.clear()
        self.saveSession(context)

    def service_addFilterRule(self, context, attr):
        """
        Create a filter rule. attr is a dictionary.

        Mandatory attr keys:
         - chain: 'INPUT', 'OUTPUT' or 'FORWARD'
         - decision: 'ACCEPT', 'REJECT' or 'DROP'

        Optional attr keys:
         - ipv6: False (IPv4) or True (IPv6), default: False (IPv4)
         - protocol: layer3 protocol ('ip', 'esp', 'ah') or layer4 protocol
           ('tcp', 'udp', 'icmp')
         - dport: tcp/udp destination port number in [0; 65535], eg. 80
         - sources: list of source addresses/hostnames,
           eg. ['0.0.0.0/0', '2000::/3', 'example.com']
         - destinations: list of destination addresses/hostnames,
           eg. ['0.0.0.0/0', '2000::/3', 'example.com']
         - input: input interface name, eg. 'eth0'
         - output: output interface name, eg. 'eth2'

        Return the number of created rules.

        The rule will be added before the ruleset rules.
        """

        # Mandatory attributes
        for key in ('decision', 'chain'):
            if key not in attr:
                raise LocalFWError(tr("Missing attribute: %s"), key)
        chain = getUnicode(attr.pop('chain'))
        decision = getUnicode(attr.pop('decision'))

        # Optional attributes
        if getOptionalDict(getBoolean, attr, 'ipv6', False):
            address_type = IPV6_ADDRESS
        else:
            address_type = IPV4_ADDRESS
        protocol = getOptionalDict(getUnicode, attr, 'protocol')
        dport = getOptionalDict(getInteger, attr, 'dport')
        sources = getAddressList(attr, 'sources', address_type)
        destinations = getAddressList(attr, 'destinations', address_type)
        input = getOptionalDict(getUnicode, attr, 'input')
        output = getOptionalDict(getUnicode, attr, 'output')
        kw = {
            'icmp_type': getOptionalDict(getInteger, attr, 'icmp_type'),
            'icmpv6_type': getOptionalDict(getInteger, attr, 'icmpv6_type'),
        }

        keys = attr.keys()
        if keys:
            raise LocalFWError(tr("Unknown attributes: %s"), ', '.join(keys))

        rules = self.getRulesFile(context)
        for source in sources:
            for destination in destinations:
                rule = FilterRule(address_type, chain, protocol,
                    dport, source, destination, input, output, decision, **kw)
                rules.addFilterRule(rule)

        self.saveSession(context)
        return len(sources) * len(destinations)

    def service_addFilterIptable(self, context, ipv6, iptable):
        """
        Add a filter rule. Arguments:

          - ipv6: boolean
          - iptable: unicode string

        Example: (False, '-A FORWARD -m mark ! --mark 0x20000/0x20000 -j IPS_NETS')
        is similar to 'iptables -t filter -A FORWARD -m mark ! --mark 0x20000/0x20000 -j IPS_NETS'

        The rule will be added before the ruleset rules.
        """
        if getBoolean(ipv6):
            address_type = IPV6_ADDRESS
        else:
            address_type = IPV4_ADDRESS
        rules = self.getRulesFile(context)
        rule = IptableRule(address_type, iptable)
        rules.addFilterRule(rule)

    def service_addMangleIptable(self, context, ipv6, iptable):
        """
        Add a mangle rule. Arguments:

          - ipv6: boolean
          - iptable: unicode string

        Example: (False, '-A POSTROUTING -m mark --mark 0x20000/0x20000 -j MARK --and-mark 0xfffdffff')
        is similar to 'iptables -t mangle -A POSTROUTING -m mark --mark 0x20000/0x20000 -j MARK --and-mark 0xfffdffff'

        The rule will be added before the ruleset rules.
        """
        if getBoolean(ipv6):
            address_type = IPV6_ADDRESS
        else:
            address_type = IPV4_ADDRESS
        rules = self.getRulesFile(context)
        rule = IptableRule(address_type, iptable)
        rules.addMangleRule(rule)

    def service_addNatIptable(self, context, ipv6, iptable):
        """
        Add a NAT rule. Arguments:

          - ipv6: boolean
          - iptable: unicode string

        Example: (False, '-A PREROUTING -p tcp --dport 80 -s $NET -j SOME_CHAIN')
        is similar to 'iptables -t nat -A PREROUTING -p tcp --dport 80 -s $NET -j SOME_CHAIN'

        The rule will be added before the ruleset rules.
        """
        if getBoolean(ipv6):
            address_type = IPV6_ADDRESS
        else:
            address_type = IPV4_ADDRESS
        rules = self.getRulesFile(context)
        rule = IptableRule(address_type, iptable)
        rules.addNatRule(rule)

    def service_apply(self, context):
        rules_file = self.getRulesFile(context)
        return applyRules(context, self, rules_file)

    def service_close(self, context):
        del context.getSession()[self.NAME]

    def checkServiceCall(self, context, service_name):
        ruleset_open = self.hasRules(context)
        if service_name == "open":
            if ruleset_open:
                rules = self.getRulesFile(context)
                raise LocalFWError(
                    tr("There is already an active rule set (%s)."),
                    rules.name)
        else:
            if not ruleset_open:
                raise LocalFWError(
                    tr("You have to open a rule set to use the %s() service."),
                    service_name)


