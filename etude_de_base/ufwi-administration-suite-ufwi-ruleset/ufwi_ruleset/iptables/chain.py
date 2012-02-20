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

from ufwi_ruleset.iptables.arguments import Arguments
from ufwi_ruleset.forward.resource import NetworkGroup

class IptablesChain:
    """
    Chain for rules from input interface to output interface

    >>> from ufwi_ruleset.forward.mockup import Interface
    >>> input = Interface(None, {'id': 'eth0', 'name': 'eth0'})
    >>> output = Interface(None, {'id': 'eth2', 'name': 'eth2'})
    >>> bichain = IptablesChain(input, output)
    >>> unicode(bichain)
    u'ETH0-ETH2'
    >>> unicode(bichain.create)
    u':ETH0-ETH2 - [0:0]'
    """
    def __init__(self, input, output):
        # Input and output interfaces: InterfaceResource objects
        self.input = input
        self.output = output

        # chain name (eg. "ETH0-ETH0")
        chain = "%s-%s" % (input.name, output.name)
        self.chain = chain.upper()

        # iptables-save line to create the chain (eg. ':ETH0-ETH0 - [0:0]')
        self.create = Counters(self, decision="-")

    def isGeneric(self):
        """
        True if input or output interface name ends with "+",
        False otherwise.
        """
        return self.input.name.endswith(u"+") or self.output.name.endswith(u"+")

    def __str__(self):
        return self.chain

    def __repr__(self):
        return "<IptablesChain %r>" % self.chain

class Counters:
    """
    Counters used in iptables-save header to create a chain.

    >>> counters = Counters("FORWARD")
    >>> unicode(counters)
    u':FORWARD ACCEPT [0:0]'
    >>> counters.chain
    'FORWARD'

    >>> print Counters("ETH0-ETH0", decision="-")
    :ETH0-ETH0 - [0:0]
    """
    def __init__(self, chain, decision="ACCEPT", bytes=0, packets=0):
        self.chain = chain
        self.decision = decision
        self.bytes = bytes
        self.packets = packets

    def __str__(self):
        return ":%s %s [%s:%s]" % (self.chain, self.decision, self.bytes, self.packets)

def getNetworks(interface):
    networks = []
    for resource in interface.getChildren():
        if isinstance(resource, NetworkGroup):
            continue
        networks.append(resource.address)
    return networks

def compareNetworks(interfaceA, interfaceB):
    networksA = getNetworks(interfaceA)
    networksB = getNetworks(interfaceB)
    for netA in networksA:
        for netB in networksB:
            ipA = netA.int()
            ipB = netB.int()
            if ipA != ipB:
                continue
            # Similar network, but different prefix.
            # Eg. 192.168.0.0/30 vs 192.168.0.0/24.
            return cmp(netA.prefixlen(), netB.prefixlen())
    return 0

def compareChains(chainA, chainB):
    genericA = chainA.isGeneric()
    genericB = chainB.isGeneric()
    if genericA and (not genericB):
        # generic chain are always before a non-generic chain
        return -1
    if genericB and (not genericA):
        # generic chain are always before a non-generic chain
        return 1
    if compareNetworks(chainA.input, chainB.input) > 0:
        # A and B input interfaces contain a similar network (same address),
        # but A network has a bigger prefix. Eg. 192.168.0.0/30 is before
        # 192.168.0.0/24.
        return -1
    if compareNetworks(chainA.output, chainB.output) > 0:
        # A and B output interfaces contain a similar network (same address),
        # but A network has a bigger prefix. Eg. 192.168.0.0/30 is before
        # 192.168.0.0/24.
        return 1
    # A and B don't share "similar" networks, all networks are different. Sort
    # by chain name, for better readability (eg. ETH0-ETH3 before ETH2-ETH3).
    return cmp(chainA.chain, chainB.chain)

def aclChain(acl):
    chain = u"%s-%s" % (acl.input.name, acl.output.name)
    return chain.upper()

def dispatchRules(chains):
    for chain in chains:
        yield Arguments(
            "-A", "FORWARD",
            "-i", chain.input.name,
            "-o", chain.output.name,
            "-j", chain.chain)

def aclForwardChains(acls):
    chain_set = set()
    chains = []
    for acl in acls:
        if not acl.isForward():
            continue
        chain = IptablesChain(acl.input, acl.output)
        if chain.chain in chain_set:
            continue
        chain_set.add(chain.chain)
        chains.append(chain)
    chains.sort(cmp=compareChains)
    return chains

