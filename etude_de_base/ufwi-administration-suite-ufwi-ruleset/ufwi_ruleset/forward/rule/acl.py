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

import itertools
from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS

from ufwi_ruleset.forward.action import Update
from ufwi_ruleset.forward.address_type import (INTERFACE_ADDRESS,
    checkAddressTypes, formatAddressTypes)
from ufwi_ruleset.forward.attribute import Boolean, Unicode, Enum, Integer
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.flatten import (flattenNetwork, flattenObjectList,
    flattenProtocolList, getFirstNetwork, getFirstObject)
from ufwi_ruleset.forward.resource import FirewallResource, InterfaceResource
from ufwi_ruleset.forward.resource.tools import checkNetworkInclusion
from ufwi_ruleset.forward.rule.rule import Rule
from ufwi_ruleset.forward.rule.attribute import ObjectSet, Comment
from ufwi_ruleset.common.rule import DECISIONS

def addressTypes(resources):
    addr_types = set()
    for resource in resources:
        addr_types |= resource.getAddressTypes()
    return addr_types

def createAddressTypes(sources, destinations, protocols):

    src_types = addressTypes(sources)
    dst_types = addressTypes(destinations)

    if not checkAddressTypes(src_types, dst_types):
        raise RulesetError(
            tr("Invalid address types combination! Source: %s; destination: %s."),
            formatAddressTypes(src_types),
            formatAddressTypes(dst_types))

    address_types = (src_types & dst_types) - set((INTERFACE_ADDRESS,))
    for protocol in protocols:
        new_types = address_types & protocol.getAddressTypes()
        if not len(new_types):
            raise RulesetError(
                tr("The %s protocol can not be used with the address types: %s"),
                protocol.formatID(), ', '.join(address_types))
        address_types = new_types
    return address_types

def getIface(resources, platforms):
    if resources:
        return getFirstObject(resources).interface
    else:
        return getFirstNetwork(platforms).interface

MAX_LOG_PREFIX_LENGTH = 63   # Max NFLOG comment length

class LogPrefix(Unicode):
    def getter(self, rule, name, prefix):
        prefix = Unicode.getter(self, rule, name, prefix)
        if prefix is None:
            return None
        if MAX_LOG_PREFIX_LENGTH < len(prefix):
            raise RulesetError(
                tr("The log prefix is too long (%s characters), the maximum is %s characters!"),
                len(prefix), MAX_LOG_PREFIX_LENGTH)
        for character in prefix:
            code = ord(character)
            if 32 <= code <= 126:
                continue
            raise RulesetError(
                tr("Invalid character in the log prefix: %s (code %s)"),
                repr(character), ord(character))
        return prefix

class Acl(Rule):
    """
    Filtering rule.

    Description attributes:

     - id: unique identifier (int)
     - address_type: IPV4_ADDRESS or IPV6_ADDRESS
     - comment: Comment (unicode)
     - chain: Network (iptables) chain, 'INPUT', 'OUTPUT' or 'FORWARD'

    State attributes:

     - enabled: If False, the rule is ignored in iptabes and LDAP generation
     - editable: If False, any modification is blocked

    Filtering attributes:

     - decision: 'ACCEPT', 'DROP' or 'REJECT'
     - input: Input interface (InterfaceResource)
     - output: Output interface (InterfaceResource)
     - sources, destinations: Resource objects of any type
       (interface, network, host, hostname)
     - source_platforms, destination_platforms: Platforms objects (list of
       pairs of resource and protocol)
     - protocols: Protocol object (IPv4, IPv6, Icmp, ICMPv6, Tcp,
       Udp, ...)
     - user_groups: User group  objects (UserGroup)
     - applications: Application objects (Application)
     - periodicities: Periodicitiy objects (Periodicity)
     - durations: Duration objects (Duration)
     - operating_systems: Operating system objets (OperatingSystem)

    Logging attributes:

     - log: Log connections? (bool)
     - log_prefix: Logging prefix (unicode)

    Other attributes:

     - update_domain: Ruleset update domain (u"acls")
    """
    XML_TAG = u'acl'

    decision = Enum(DECISIONS.keys())
    sources = ObjectSet('resources', 'source', optional=True)
    source_platforms = ObjectSet('platforms', 'source_platform', optional=True)
    protocols = ObjectSet('protocols', optional=True)
    destinations = ObjectSet('resources', 'destination', optional=True)
    destination_platforms = ObjectSet('platforms', 'destination_platform', optional=True)
    log = Boolean()
    log_prefix = LogPrefix(optional=True)
    user_groups = ObjectSet('user_groups', optional=True)
    applications = ObjectSet('applications', optional=True)
    operating_systems = ObjectSet('operating_systems', optional=True)
    periodicities = ObjectSet('periodicities', optional=True)
    durations = ObjectSet('durations', optional=True)
    auth_quality = Integer(min=0, max=5, default=3)
    comment = Comment(optional=True)

    MATCH_ATTRIBUTES = set(('sources', 'destinations', 'protocols', 'user_groups', 'source_platforms', 'destination_platforms'))

    # abstract attributes
    ADDRESS_TYPE = None
    ADDRESS_TYPE_ERROR = ""
    FORMAT = None   # format % (chain, acl_id)

    def __init__(self, acls, attr, loader_context=None):
        self.config = acls.ruleset.config
        Rule.__init__(self, acls, attr, loader_context)

    def onLoading(self, context):
        if context.version in ("3.0m3", "3.0dev4", "3.0dev5", "3.0dev6") \
        and self.user_groups:
            for protocol in set(self.protocols):
                # platform feature was not available in theses version but use
                # self.listAllProtocols() instead of self.protocols for consistency
                if all((object.layer4 in (u'tcp', u'udp'))
                for object in self.listAllProtocols()):
                    continue
                context.warning('Remove protocol %s from %s: it cannot be identified'
                    % (protocol.formatID(), self))
                self.protocols.remove(protocol)

    def setAttributes(self, attr, is_modify):
        Rule.setAttributes(self, attr, is_modify)

        if not self.user_groups:
            self.applications.clear()
            self.periodicities.clear()
            self.durations.clear()
            self.operating_systems.clear()

        self.input = getIface(self.sources, self.source_platforms)
        self.output = getIface(self.destinations, self.destination_platforms)

        if isinstance(self.input, FirewallResource):
            self.chain = u'OUTPUT'
        elif isinstance(self.output, FirewallResource):
            self.chain = u'INPUT'
        else:
            self.chain = u'FORWARD'
        self.address_type = self.ADDRESS_TYPE
        if not self.log:
            self.log_prefix = None

    def checkConsistency(self, loader_context=None):
        if not (self.sources | self.source_platforms):
            raise RulesetError(
                tr("%s has no source."),
                unicode(self))

        if not (self.destinations | self.destination_platforms):
            raise RulesetError(
                tr("%s has no destination."),
                unicode(self))

        if not((self.source_platforms | self.destination_platforms) or self.protocols):
            raise RulesetError(
                tr("%s has no protocol."),
                unicode(self))

        if self.sources and self.source_platforms:
            raise RulesetError(
                tr("%s source can not associate a platform with another type of object."),
                unicode(self))

        if self.destinations and self.destination_platforms:
            raise RulesetError(
                tr("%s destination can not associate a platform with another type of object."),
                unicode(self))

        if self.source_platforms and self.destination_platforms:
            raise RulesetError(tr('Platforms can not be used '
                'concurrently in source and destination'))

        if ((self.source_platforms or self.destination_platforms)
        and self.protocols):
             raise RulesetError(
                tr('Protocols can not be used together with platforms.'))

        checkNetworkInclusion(self, self.sources)
        checkNetworkInclusion(self, self.destinations)
        checkNetworkInclusion(self, flattenNetwork(self.source_platforms))
        checkNetworkInclusion(self, flattenNetwork(self.destination_platforms))

        if isinstance(self.input, FirewallResource) \
        and isinstance(self.output, FirewallResource):
            raise RulesetError(tr("The firewall can not be the source and the destination of a rule!"))

        if self.user_groups:
            if not self.isForward():
                raise RulesetError(
                    tr("INPUT/OUTPUT rules (%s) can not use identity!"),
                    unicode(self))
            for protocol in self.listAllProtocols():
                if protocol.layer4 in (u'tcp', u'udp'):
                    continue
                raise RulesetError(tr("The protocol %s of the %s cannot be identified."),
                    protocol.formatID(), unicode(self))

        if 1 < len(self.periodicities):
            raise RulesetError(
                tr("%s can not use more than one time criterion!"),
                unicode(self))
        if 1 < len(self.durations):
            raise RulesetError(
                tr("%s can not use more than one duration!"),
                unicode(self))
        if 1 < len(self.periodicities) + len(self.durations):
            raise RulesetError(
                tr("%s can not use one period and one duration!"),
                unicode(self))

        address_types = createAddressTypes(
            self.getSources(),
            self.getDestinations(),
            self.listAllProtocols())
        if self.address_type not in address_types:
            raise RulesetError(self.ADDRESS_TYPE_ERROR)

    def getReferents(self):
        return set(itertools.chain(
            (self.input, self.output),
            self.sources, self.destinations, self.protocols,
            self.source_platforms, self.destination_platforms,
            self.user_groups, self.applications, self.operating_systems,
            self.periodicities, self.durations))

    def exportXMLRPC(self, fusion):
        data = Rule.exportXMLRPC(self, fusion)
        data['address_type'] = self.address_type
        data['chain'] = self.chain
        data['input'] = self.input.getID(fusion)
        data['output'] = self.output.getID(fusion)
        return data

    def createChainKey(self):
        if self.chain == u'FORWARD':
            return (self.input.id, self.output.id)
        else:
            return self.chain

    def isInput(self):
        return (self.chain == u'INPUT')

    def isOutput(self):
        return (self.chain == u'OUTPUT')

    def isForward(self):
        return (self.chain == u'FORWARD')

    def __unicode__(self):
        return self.FORMAT % self.id

    def getAddressTypes(self):
        return set((self.address_type,))

    def checkRule(self, apply_rules, recursive=False):
        if not Rule.checkRule(self, apply_rules, recursive=recursive):
            return False
        if self.isForward() and (not self.config.isGateway()):
            apply_rules.error(
                tr("The firewall is configured as a local firewall: "
                   "%s can not be generated."),
                unicode(self))
            return False
        if self.user_groups and (not self.ruleset.useNuFW()):
            apply_rules.warning(
                tr("Identity-based Firewall is disabled: %s will not use identity."),
                unicode(self))
        return True

    def logPrefix(self, nufw=True, ldap=False):
        """
        Create the log prefix.

        Examples: "F12d:comment", "O12A:ACL #10 (ACCEPT)"
        """
        chain_letter = self.chain[0]
        if not ldap:
            decision_letter = self.decision[0]
            if (not nufw) or (not self.user_groups):
                # iptables decision: 'a', 'd' or 'r'
                decision_letter = decision_letter.lower()
            # else: NuFW decision: 'A', 'D', or 'R'
        else:
            decision_letter = '?'
        text = "%s%s%s:" % (chain_letter, self.id, decision_letter)
        if self.log_prefix:
            text += self.log_prefix
        elif not ldap:
            text += "ACL #%s (%s)" % (self.id, self.decision)
        return text

    def referentActionUpdates(self, action, referent, old_attr):
        old_id = old_attr['id']

        # Check that the ACL is a FORWARD rule, referent is an interface and
        # referent identifier changed
        if (self.chain != 'FORWARD') \
        or not isinstance(referent, InterfaceResource) \
        or (referent.id == old_id):
            return Rule.referentActionUpdates(self, action, referent, old_attr)

        # the chain is a forward chain, because referent cannot be the firewall
        # object (read only object)
        if referent is self.input:
            input_id = old_id
        else:
            input_id = self.input.id
        if referent is self.output:
            output_id = old_id
        else:
            output_id = self.output.id
        old_chain_key = (input_id, output_id)
        new_chain_key = (self.input.id, self.output.id)

        # add the required updates
        domain = self.rules.UPDATE_CHAIN_DOMAIN
        action.addApplyUpdate(Update(domain, "delete", (old_chain_key, -1)))
        action.addApplyUpdate(Update(domain, "create", (new_chain_key, -1)))
        action.addUnapplyUpdate(Update(domain, "delete", (new_chain_key, -1)))
        action.addUnapplyUpdate(Update(domain, "create", (old_chain_key, -1)))

    def getSources(self):
        if self.sources:
            return self.sources
        else:
            return self.source_platforms

    def getDestinations(self):
        if self.destinations:
            return self.destinations
        else:
            return self.destination_platforms

    def listAllProtocols(self):
        """return a list containing all protocols used by the rule
        return (None,) if no protocol are used"""
        if self.protocols:
            protocols = list(flattenObjectList(self.protocols))
            protocols.sort(key=lambda protocol: protocol.sortKey())
        else:
            if self.source_platforms:
                protocols = list(flattenProtocolList(self.source_platforms))
            elif self.destination_platforms:
                protocols = list(flattenProtocolList(self.destination_platforms))
            else:
                protocols = (None,)
        return protocols

class AclIPv4(Acl):
    ADDRESS_TYPE = IPV4_ADDRESS
    UPDATE_DOMAIN = "acls-ipv4"
    FORMAT = u'IPv4 rule #%s'
    ADDRESS_TYPE_ERROR = tr("An IPv4 rule can not contain IPv6 objects.")

    @classmethod
    def fromXML(cls, rules, attr, context, action):
        ipv4 = True
        ipv6 = False
        if context.version in ("3.0m3", "3.0dev4", "3.0dev5"):
            # These versions doesn't support platform object
            ruleset = rules.ruleset
            sources = attr.get('sources', tuple())
            destinations = attr.get('destinations', tuple())
            protocols = attr.get('protocols', tuple())
            sources = [ruleset.resources[id] for id in sources]
            destinations = [ruleset.resources[id] for id in destinations]
            protocols = [ruleset.protocols[id] for id in protocols]
            address_types = createAddressTypes(sources, destinations, protocols)
            ipv4 = (IPV4_ADDRESS in address_types)
            ipv6 = (IPV6_ADDRESS in address_types)
        if ipv4:
            Acl.fromXML(rules, attr, context, action)
        if ipv6:
            AclIPv6.fromXML(rules.ruleset.acls_ipv6, attr, context, action)


class AclIPv6(Acl):
    ADDRESS_TYPE = IPV6_ADDRESS
    UPDATE_DOMAIN = "acls-ipv6"
    FORMAT = u'IPv6 rule #%s'
    ADDRESS_TYPE_ERROR = tr("An IPv6 rule can not contain IPv4 objects.")

