"""
Copyright (C) 2010-2011 EdenWall Technologies

Written by Pierre-Louis Bonicoli <bonicoli@edenwall.com>

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

from ufwi_rpcd.common.getter import getUnicode
from ufwi_rpcd.common.xml_etree import etree

from ufwi_rpcd.backend import tr

from ufwi_ruleset.forward.attribute import Attribute
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.object import Object


class PlatformItem(object):
    def __init__(self, network, protocol):
        self.network = network
        self.protocol = protocol

class PlatformItems(Attribute):
    def _get(self, object, name, items):
        """
            return a list of PlatformItem
            items: follows XML-RPC format
        """
        networks = object.ruleset.resources
        protocols = object.ruleset.protocols
        values = []
        for item in items:

            if 'network' in item:
                network = getUnicode(item['network'])
            else:
                raise ValueError("Platform object: missing node 'network' in node 'item'")

            if 'protocol' in item:
                protocol = getUnicode(item['protocol'])
            else:
                raise ValueError("Platform object: missing node 'protocol' in node 'item'")

            network = networks[network]
            protocol = protocols[protocol]

            values.append(PlatformItem(network, protocol))

        if not values:
            return None
        return values

    def _readXML(self, library, group_node, name, context):
        """ return list of dict (XML-RPC format) """
        items = []
        for node in group_node.findall("item"):
            item = {}

            network = node.find('network')
            if network is None:
                raise ValueError("Platform object: missing node 'network' in node 'item'")
            item['network'] = network.text

            protocol = node.find('protocol')
            if protocol is None:
                raise ValueError("Platform object: missing node 'protocol' in node 'item'")
            item['protocol'] = protocol.text

            items.append(item)
        return items

    def _exportXML(self, node, name, items):
        for item in items:
            item_node = etree.SubElement(node, 'item')

            network = etree.SubElement(item_node, 'network')
            network.text = item.network.getOriginalID()

            protocol = etree.SubElement(item_node, 'protocol')
            protocol.text = item.protocol.getOriginalID()

    def _exportXMLRPC(self, objects, fusion):
        items = []
        for item in objects:
            network = item.network.id
            protocol = item.protocol.id
            items.append({'network': network, 'protocol': protocol})
        return items

class Platform(Object):
    XML_TAG = u"platform"
    UPDATE_DOMAIN = u'platforms'
    items = PlatformItems()

    def __init__(self, platforms, values, loader_context=None):
        self.ruleset = platforms.ruleset
        Object.__init__(self, values, loader_context)

    def setAttributes(self, attr, is_modify):
        Object.setAttributes(self, attr, is_modify)
        interface = self.items[0].network.interface
        if is_modify:
            if self.interface != interface:
                raise RulesetError(
                    tr("You can not change the interface (%s => %s) "
                       "of the %s platform."),
                    self.interface.formatID(), interface.formatID(),
                    self.formatID())
        else:
            self.interface = interface

    def checkConsistency(self, loader_context=None):
        # Import InterfaceResource and FirewallResource here instead of the top
        # of the file to avoid an import loop
        from ufwi_ruleset.forward.resource.interface import InterfaceResource
        from ufwi_ruleset.forward.resource.firewall import FirewallResource

        duplicates = set()
        for item in self.items:
            if isinstance(item.network, InterfaceResource):
                raise RulesetError(
                    tr("You can not use an interface (%s) in a platform (%s)."),
                    item.network.formatID(), self.formatID())
            if isinstance(item.network, FirewallResource):
                raise RulesetError(
                    tr("You can not use the firewall object in a platform (%s)."),
                    self.formatID())

            if item.network.interface != self.interface:
                raise RulesetError(
                    tr('A platform (%s) can not contain network objects '
                       'from different interfaces (%s and %s).'),
                    self.formatID(),
                    self.interface.formatID(),
                    item.network.interface.formatID())

            key = (item.network.id, item.protocol.id)
            if key in duplicates:
                raise RulesetError(
                    tr("Duplicate item in the platform %s: (%s, %s)."),
                    self.formatID(),
                    item.network.formatID(), item.protocol.formatID())
            duplicates.add(key)

    def __unicode__(self):
        return tr('The platform %s') % self.formatID()

    def getAddressTypes(self):
        """implementation of abstract method"""
        address_types = None
        for item in self.items:
            if address_types is not None:
                address_types &= item.network.getAddressTypes()
                address_types &= item.protocol.getAddressTypes()
            else:
                address_types = item.network.getAddressTypes()
                address_types &= item.protocol.getAddressTypes()
        return address_types

    def getReferents(self):
        referents = set()
        for item in self.items:
            referents.add(item.network)
            referents.add(item.protocol)
        return referents

    def exportXMLRPC(self, fusion):
        attr = Object.exportXMLRPC(self, fusion)
        attr['interface'] = self.interface.id
        return attr

class Platforms(Library):
    NAME = 'platforms'
    ACL_ATTRIBUTE = 'platforms'
    XML_TAG = u"platforms"
    CHILD_CLASSES = (Platform,)

    def createGroup(self, attr):
        raise RulesetError(
            tr("You can not create a group of platforms"))

