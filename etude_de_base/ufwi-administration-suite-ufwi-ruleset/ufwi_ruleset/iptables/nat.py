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

from ufwi_rpcd.common.tools import getFirst
from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.rule import NAT_TRANSLATE
from ufwi_ruleset.forward.flatten import flattenNetworkList
from ufwi_ruleset.forward.resource import (FirewallResource,
    NetworkResource, IPsecNetworkResource)
from ufwi_ruleset.forward.flatten import flattenObjectList

from ufwi_ruleset.iptables.arguments import Arguments
from ufwi_ruleset.iptables.comment import comment
from ufwi_ruleset.iptables.protocol import formatProtocol
from ufwi_ruleset.iptables.tools import formatIPsec

def formatNetworks(resources, rule, chain, is_source):
    if is_source:
        networks = rule.sources
        filter_interface = (chain != u'POSTROUTING')
    else:
        networks = rule.destinations
        filter_interface = (chain != u'PREROUTING')

    items = []
    for network in flattenNetworkList(networks):
        args = Arguments()
        if filter_interface:
            if is_source:
                args += Arguments("-i", network.interface.name)
            else:
                args += Arguments("-o", network.interface.name)
        if network.hasAddresses():
            addresses = list(network.getAddresses())
            addresses.sort()
            for addr in addresses:
                if addr.version() != 4:
                    continue
                if is_source:
                    network_args = args + Arguments("-s", unicode(addr))
                else:
                    network_args = args + Arguments("-d", unicode(addr))
                items.append((network, network_args))
        else:
            items.append((network, args))
    return items

def formatSrcDst(resources, nat, chain):
    if chain == 'PREROUTING':
        ipsec_direction = 'in'
    else:
        ipsec_direction = 'out'
    sources = formatNetworks(resources, nat, chain, True)
    destinations = formatNetworks(resources, nat, chain, False)
    for source, src_args in sources:
        for destination, dst_args in destinations:
            args = Arguments()
            if src_args:
                args += src_args
            if dst_args:
                args += dst_args
            args += formatIPsec(source, destination, ipsec_direction)
            yield args

def getFirstAddress(rule, network, apply_rules):
    addresses = network.getAddresses()
    address = unicode(addresses[0])
    if 1 < len(addresses):
        apply_rules.warning(
            tr('The "%s" network has multiple addresses (%s), '
               'use only the first one (%s) for %s'),
            network.id, len(addresses), address, unicode(rule))
    return address

def iptableRules(iptables, nat, empty_line, apply_rules):
    ruleset = nat.ruleset

    if iptables.options.format == "iptables":
        prefix = Arguments("iptables", "-t", "nat")
    else:
        prefix = Arguments()

    # Create header (title and comment)
    title = unicode(nat)
    if not nat.enabled:
        title += u' (disabled)'
    for line in comment(title, extra=nat.comment, empty_line=empty_line):
        yield line

    # Create source and destination parameters
    chain = nat.createChainKey()

    # Create protocols
    protocols = list(flattenObjectList(nat.filters))
    if not protocols:
        protocols = (None,)

    # Get nated sources
    if len(nat.nated_sources):
        nated_src = getFirst(nat.nated_sources)
    else:
        nated_src = None

    # Get nated destinations
    if len(nat.nated_destinations):
        nated_dst = getFirst(nat.nated_destinations)
    else:
        nated_dst = None

    if nat.type != NAT_TRANSLATE:
        suffix = Arguments('-j', 'ACCEPT')
    elif chain == u'POSTROUTING' and isinstance(nated_src, FirewallResource):
        suffix = Arguments('-j', 'MASQUERADE')
    elif chain == u'POSTROUTING':
        source = getFirstAddress(nat, nated_src, apply_rules)
        if isinstance(nated_src, (NetworkResource, IPsecNetworkResource)):
            suffix = Arguments('-j', 'NETMAP', '--to', source)
        else:
            suffix = Arguments('-j', 'SNAT', '--to-source', source)
    elif chain == u'PREROUTING':
        dest = getFirstAddress(nat, nated_dst, apply_rules)
        if len(nat.nated_filters):
            newproto = getFirst(nat.nated_filters)
            dest += u':%s' % newproto.dport
        if isinstance(nated_dst, (NetworkResource, IPsecNetworkResource)):
            suffix = Arguments('-j', 'NETMAP', '--to', dest)
        else:
            suffix = Arguments('-j', 'DNAT', '--to-destination', dest)

    rule_number = 1
    for network_args in formatSrcDst(ruleset.resources, nat, chain):
        for proto in protocols:
            iptable_rule = prefix

            if not nat.enabled:
                iptable_rule += Arguments("#")
            iptable_rule += Arguments('-A', chain)
            iptable_rule += network_args
            if proto:
                iptable_rule += formatProtocol(proto, chain)

            iptable_rule += suffix
            if iptables.options.format != "iptables":
                iptable_rule += iptables.ruleComment(nat, rule_number)
            rule_number += 1

            yield iptable_rule

def natsRules(iptables, acls, apply_rules):
    empty_line = None
    for acl in acls:
        for line in iptableRules(iptables, acl, empty_line, apply_rules):
            yield line
        empty_line = "before"

