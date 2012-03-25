"""
Copyright (C) 2009-2011 EdenWall Technologies

Written by Victor Stinner <vstinner AT edenwall.com>
Modified by Pierre-Louis Bonicoli <bonicoli@edenwall.com>

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

from ufwi_ruleset.forward.flatten import flattenNetworkList

from ufwi_ruleset.iptables.arguments import Arguments
from ufwi_ruleset.iptables.comment import comment
from ufwi_ruleset.iptables.chain import aclChain
from ufwi_ruleset.iptables.protocol import formatProtocol
from ufwi_ruleset.iptables.tools import formatIPsec

from ufwi_ruleset.forward.flatten import flattenObject, flattenObjectList
from ufwi_ruleset.forward.resource import InterfaceResource

def formatNetworks(networks, prefix):
    items = []
    for network in flattenNetworkList(networks):
        if isinstance(network, InterfaceResource):
            items.append((None, None))
            continue
        addresses = list(network.getAddresses())
        addresses.sort()
        for address in addresses:
            arguments = Arguments(prefix, address)
            items.append((network, arguments))
    return items

class AclGenerator:
    def __init__(self, iptables):
        self.iptables = iptables
        self.options = iptables.options
        if self.options.format == "iptables-restore":
            self.empty_line = "before"
        else:
            self.empty_line = None

    def aclRules(self, acl, chain):
        title = unicode(acl)
        if not acl.enabled:
            title += ' (disabled)'
        for line in comment(title, extra=acl.comment, empty_line=self.empty_line):
            yield line

        rules = AclRule(acl, chain, self.iptables)
        rule_number = 1
        for rule in rules.generateRules(rule_number):
            yield rule
            rule_number += 1

    def createRules(self, acls):
        # Create ACLs chains
        acl_chains = {
            u'INPUT': [],
            u'OUTPUT': [],
            u'FORWARD': [],
        }
        for acl in acls:
            if acl.isInput():
                key = u'INPUT'
            elif acl.isOutput():
                key = u'OUTPUT'
            else:
                key = u'FORWARD'
            acl_chains[key].append(acl)

        # Generate each chain
        for chain in (u'FORWARD', u'INPUT', u'OUTPUT'):
            acls = acl_chains[chain]
            for acl in acls:
                # Generate the rules of one ACL
                for line in self.aclRules(acl, chain):
                    yield line
                self.empty_line = "before"

def aclsRules(iptables, acls):
    return AclGenerator(iptables).createRules(acls)

class AclRule(object):
    def __init__(self, acl, chain, iptables):
        self.acl = acl
        self.chain = chain
        self.iptables = iptables
        self.rule_number = 1

        self.use_auth = (iptables.options.nufw and len(acl.user_groups))

        self.program = self.iptables.options.getProgram()

        if self.use_auth :
            self.decision = 'NFQUEUE'
        else:
            self.decision = acl.decision

        if chain == u"FORWARD":
            if iptables.options.dispatch:
                self.dispatch = Arguments("-A", aclChain(acl))
            else:
                self.dispatch = Arguments(
                   "-A", chain,
                   "-i", acl.input.name,
                   "-o", acl.output.name)
        elif chain == u"INPUT":
            self.dispatch = Arguments(
               "-A", chain,
               "-i", acl.input.name)
        else:
            self.dispatch = Arguments(
               "-A", chain,
               "-o", acl.output.name)

    def generateRules(self, rule_number):
        if self.acl.source_platforms or self.acl.destination_platforms:
            if self.acl.source_platforms:
                platforms = self.acl.source_platforms
            else:
                platforms = self.acl.destination_platforms

            for platform in platforms:
                for item in platform.items:
                    protocols = list(flattenObject(item.protocol))
                    protocols.sort(key=lambda protocol: protocol.sortKey())
                    networks = self.formatPlatformSrcDst(flattenObject(item.network))
                    for rule in self.aclRule(networks, protocols, rule_number):
                        yield rule
                        rule_number += 1
        else:
            protocols = list(flattenObjectList(self.acl.protocols))
            protocols.sort(key=lambda protocol: protocol.sortKey())
            networks = self.formatSrcDst()
            for rule in self.aclRule(networks, protocols, rule_number):
                yield rule
                rule_number += 1

    def aclRule(self, networks, protocols, rule_number):
        for network_args in networks:
            for protocol in protocols:
                params = Arguments()
                if not self.acl.enabled:
                    params += Arguments("#")
                if self.program:
                    params += Arguments(self.program)
                params += self.dispatch
                params += network_args
                if protocol:
                    params += formatProtocol(protocol, self.chain)
                if self.acl.log and (not self.use_auth):
                    yield self.logRule(params, rule_number)
                    rule_number += 1
                params += Arguments("-j", self.decision)
                params += self.iptables.ruleComment(self.acl, rule_number)
                yield params
                rule_number += 1

    def logRule(self, params, rule_number):
        text = self.acl.logPrefix(nufw=self.iptables.options.nufw)
        log = params
        log += self.iptables.logRule(self.decision, text, limit=None)
        log += self.iptables.ruleComment(self.acl, rule_number)
        return log

    def formatSrcDst(self):
        if self.chain != u"OUTPUT":
            sources = formatNetworks(self.acl.sources, "-s")
        else:
            sources = ((None, None),)

        if self.chain != u"INPUT":
            destinations = formatNetworks(self.acl.destinations, "-d")
        else:
            destinations = ((None, None),)

        for source, src_args in sources:
            for destination, dst_args in destinations:
                arguments = Arguments()
                if src_args:
                    arguments += src_args
                if dst_args:
                    arguments += dst_args
                arguments += formatIPsec(source, destination)
                yield arguments

    def formatPlatformSrcDst(self, platform_networks):
        if self.chain != u"OUTPUT":
            if self.acl.source_platforms:
                sources = formatNetworks(platform_networks, "-s")
            else:
                sources = formatNetworks(self.acl.sources, "-s")
        else:
            sources = ((None, None),)

        if self.chain != u"INPUT":
            if self.acl.destination_platforms:
                destinations = formatNetworks(platform_networks, "-d")
            else:
                destinations = formatNetworks(self.acl.destinations, "-d")
        else:
            destinations = ((None, None),)

        for source, src_args in sources:
            for destination, dst_args in destinations:
                arguments = Arguments()
                if src_args:
                    arguments += src_args
                if dst_args:
                    arguments += dst_args
                arguments += formatIPsec(source, destination)
                yield arguments

