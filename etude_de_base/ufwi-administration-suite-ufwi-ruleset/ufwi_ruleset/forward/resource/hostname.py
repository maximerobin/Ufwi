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

from socket import getaddrinfo, AF_INET6, AF_INET, gaierror
import re

from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.network import HOSTNAME_OR_FQDN_REGEX_PART
from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.xml_etree import etree

from ufwi_ruleset.common.network import HOSTNAME_RESTYPE, IPV4_ADDRESS, IPV6_ADDRESS
from ufwi_ruleset.forward.attribute import Unicode, Enum, Attribute, getUnicode
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.address_type import formatAddressTypes
from ufwi_ruleset.forward.resource import Resource
from ufwi_ruleset.forward.resource.tools import parseIPAddress
from ufwi_ruleset.forward.match import matchAddresses

HOSTNAME_REGEX = re.compile(ur"^%s$" % HOSTNAME_OR_FQDN_REGEX_PART, re.IGNORECASE)

class Hostname(Unicode):
    def getter(self, object, name, value):
        value = Unicode.getter(self, object, name, value)
        if value is None:
            return None
        value = value.lower()
        if not HOSTNAME_REGEX.match(value):
            raise RulesetError(tr("Invalid hostname: %s"), value)
        return value

class AddressSet(Attribute):
    type = set

    def getter(self, rule, name, items):
        values = set()
        for item in items:
            value = getUnicode(item)
            if value is not None:
                value = parseIPAddress(value)
            if value is None:
                raise TypeError(
                    "Attribute %s.%s list contains an invalid address: %s" % (
                    object.__class__.__name__, name,
                    repr(item)))
            values.add(value)
        if not values:
            return None
        return values

    def _readXML(self, library, parent_node, name, context):
        return [node.text for node in parent_node.findall(u"address")]

    def _exportXML(self, node, name, addresses):
        addresses = list(addresses)
        addresses.sort()
        for address in addresses:
            sub_node = etree.SubElement(node, u"address")
            sub_node.text = unicode(address)

    def _exportXMLRPC(self, addresses, fusion):
        addresses = list(addresses)
        addresses.sort()
        return map(unicode, addresses)

class HostnameResource(Resource):
    XML_TAG = 'hostname'
    TYPE = HOSTNAME_RESTYPE
    hostname = Hostname()
    address_type = Enum((IPV4_ADDRESS, IPV6_ADDRESS))
    addresses = AddressSet(optional=True)

    def __init__(self, parent, attr, loader_context=None):
        Resource.__init__(self, parent.resources, parent, parent.interface, attr, loader_context)
        self.allow_child = False

    def checkConsistency(self, loader_context=None):
        Resource.checkConsistency(self, loader_context)
        if not self.addresses:
            raise RulesetError(
                tr("The %s hostname have no address"), self.formatID())

    def setAttributes(self, attr, is_modify):
        if 'address_type' not in attr:
            families = self.parent.getAddressTypes()
            if len(families) != 1:
                raise RulesetError(
                    tr("The %s network has multiple address families: %s!"),
                    self.parent.formatID(), formatAddressTypes(families))
            attr['address_type'] = list(families)[0]
        Resource.setAttributes(self, attr, is_modify)
        if is_modify or (not self.addresses):
            self.addresses = set(self.resolveHostname())

    def __unicode__(self):
        return tr('The %s hostname (%s)') % (self.formatID(), self.hostname)

    def checkUnicity(self, new_resource, loader_context=None):
        if isinstance(new_resource, HostnameResource) \
        and new_resource.hostname == self.hostname:
            message = tr('The "%s" hostname (%s) already exists: hostname "%s"!')
            args = (new_resource.hostname, new_resource.formatID(),
                    self.formatID())
            if loader_context is not None:
                loader_context.warning(message, args)
            else:
                raise RulesetError(message, *args)
        Resource.checkUnicity(self, new_resource, loader_context)

    def getAddressTypes(self):
        return set((self.address_type,))

    def hasAddresses(self):
        return True

    def getAddresses(self):
        return tuple(self.addresses)

    def resolveHostname(self):
        if self.address_type == IPV6_ADDRESS:
            family = AF_INET6
        else:
            family = AF_INET
        addresses = set()
        try:
            for family, socktype, proto, canonname, sockaddr \
            in getaddrinfo(self.hostname, None, family):
                address = parseIPAddress(sockaddr[0])
                addresses.add(address)
        except gaierror, err:
            message = toUnicode(err.args[1])
            raise RulesetError(
                tr('Unable to get the address of the hostname "%s": %s!'),
                self.hostname, message)
        return addresses

    def exportXML(self, parent):
        if self.from_template:
            return None
        return Resource.exportXML(self, parent)

    def _matchResource(self, other):
        try:
            if other.isGeneric():
                return False
            other_addresses = other.getAddresses()
        except NotImplementedError:
            return False
        return matchAddresses(self.addresses, other_addresses)
Resource.registerSubclass(HostnameResource)

