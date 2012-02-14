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

from itertools import chain
from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.tools import getFirst

from ufwi_ruleset.common.network import IPV4_ADDRESS
from ufwi_ruleset.common.rule import NAT_TYPES, NAT_TRANSLATE, NAT_PREROUTING_ACCEPT
from ufwi_ruleset.forward.attribute import Enum
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.flatten import flattenObjectList
from ufwi_ruleset.forward.platform import Platform
from ufwi_ruleset.forward.resource import (
    HostResource, HostnameResource, FirewallResource, InterfaceResource,
    NetworkResource, IPsecNetworkResource)
from ufwi_ruleset.forward.rule.rule import Rule
from ufwi_ruleset.forward.rule.attribute import ObjectSet, Comment

class NatRule(Rule):
    """
    NAT rule. Attributes:

     - type: NAT_TRANSLATE, NAT_PREROUTING_ACCEPT or NAT_POSTROUTING_ACCEPT
     - sources: list of networks
     - destinations: list of networks
     - filters: list of protocols
     - nated_sources: a network or None
     - nated_destinations: a network or None
     - nated_filters: a protocol or None
     - chain: 'PREROUTING' (Destination NAT) or 'POSTROUTING' (Source NAT)
    """
    XML_TAG = u'nat'
    UPDATE_DOMAIN = "nats"

    type = Enum(NAT_TYPES, default=NAT_TRANSLATE)
    sources = ObjectSet("resources", "source")
    destinations = ObjectSet("resources", "destination")
    filters = ObjectSet("protocols", "filter", optional=True)
    # FIXME: Replace by one resource
    nated_sources = ObjectSet("resources", "nated_source", optional=True)
    nated_destinations = ObjectSet("resources", "nated_destination", optional=True)
    nated_filters = ObjectSet("protocols", "nated_filter", optional=True)
    comment = Comment(optional=True)

    def setAttributes(self, attr, is_modify):
        Rule.setAttributes(self, attr, is_modify)
        if self.type != NAT_TRANSLATE:
            self.nated_sources.clear()
            self.nated_destinations.clear()
            self.nated_filters.clear()
            if self.type == NAT_PREROUTING_ACCEPT:
                self.chain = u'PREROUTING'
            else: # type == NAT_POSTROUTING_ACCEPT
                self.chain = u'POSTROUTING'
        else:
            if len(self.nated_sources) != 0:
                self.chain = u'POSTROUTING'
            else:
                self.chain = u'PREROUTING'

    def checkConsistency(self, loader_context=None):
        if len(self.destinations) == 0 and len(self.sources) == 0:
            raise RulesetError(tr("A NAT rule requires at least one source or one destination."))

        for source in flattenObjectList(self.sources):
            if isinstance(source, Platform):
                raise RulesetError(tr('Platforms can not be used'
                    ' in NAT rules'))

        for source in flattenObjectList(self.sources):
            if isinstance(source, Platform):
                raise RulesetError(tr('Platforms can not be used'
                    ' in NAT rules'))

        if self.type == NAT_TRANSLATE:
            if len(self.nated_destinations) == 0 and len(self.nated_sources) == 0:
                raise RulesetError(tr("A NAT rule requires at least one translated source or destination."))

        if len(self.nated_sources) != 0 and len(self.sources) == 0:
            raise RulesetError(tr("You need to specify a source to be able to translate it."))

        if len(self.nated_destinations) != 0 and len(self.destinations) == 0:
            raise RulesetError(tr("You need to specify a destination to be able to translate it."))

        if len(self.nated_filters) != 0 and len(self.nated_destinations) == 0:
            raise RulesetError(tr("You need to translate the destination address to be able to translate the protocol."))

        if len(self.nated_sources) > 1 or len(self.nated_destinations) > 1 or len(self.nated_filters) > 1 :
            raise RulesetError(tr("You can not create a NAT rule comprising more than one translated source, destination or protocol."))

        if len(self.nated_sources) != 0 and (len(self.nated_destinations) != 0 or len(self.nated_filters) != 0):
            raise RulesetError(tr("You can not set a translated source at the same time as a translated destination or protocol."))

        if len(self.nated_sources):
            nated_src = getFirst(self.nated_sources)
            if not isinstance(nated_src, (HostResource, HostnameResource,
            NetworkResource, IPsecNetworkResource, FirewallResource)):
                raise RulesetError(tr("The translated source must be a host, a network or the firewall interface."))

        if self.chain == 'POSTROUTING':
            for src in self.sources:
                if not isinstance(src, InterfaceResource):
                    continue
                raise RulesetError(tr("A source NAT rule can not use an interface in sources."))

        if len(self.nated_destinations):
            nated_dst = getFirst(self.nated_destinations)
            if not isinstance(nated_dst, (HostResource, HostnameResource,
            NetworkResource, IPsecNetworkResource)):
                raise RulesetError(tr("The translated destination must be a host or a network."))

        if self.chain == 'PREROUTING':
            for dst in self.destinations:
                if not isinstance(dst, InterfaceResource):
                    continue
                raise RulesetError(tr("A destination NAT rule can not use an interface in destinations."))

        if len(self.nated_filters) and not len(self.filters):
            raise RulesetError(tr("You have to specify at least one protocol to filter to translate it to another protocol."))

        if len(self.nated_filters):
            proto = getFirst(self.nated_filters)
            if proto.layer4 != u'tcp' and proto.layer4 != u'udp':
                raise RulesetError(tr("Translated port can only be TCP or UDP."))
            for obj in flattenObjectList(self.filters):
                if obj.layer4 != proto.layer4:
                    raise RulesetError(
                        tr("The translated port needs to use the same transport protocol (TCP/UDP) as the filtered port. "
                           "The %s protocol does not use the same transport protocol as the translated port.")
                        % proto.formatID())
            if (not proto.dport) or (proto.dport.first != proto.dport.last):
                raise RulesetError(tr("The translated port must be an unique port number."))

        for protocol in chain(self.filters, self.nated_filters):
            if IPV4_ADDRESS not in protocol.getAddressTypes():
                raise RulesetError(
                    tr("The %s protocol can not be used in IPv4!"),
                    protocol.formatID())

    def getReferents(self):
        return set(chain(
            self.sources, self.destinations, self.filters,
            self.nated_sources,
            self.nated_destinations,
            self.nated_filters))

    def createChainKey(self):
        return self.chain

    def exportXMLRPC(self, fusion):
        data = Rule.exportXMLRPC(self, fusion)
        data['chain'] = self.chain
        return data

    def __unicode__(self):
        return u'NAT rule #%s' % self.id

    def getAddressTypes(self):
        return set((IPV4_ADDRESS,))

