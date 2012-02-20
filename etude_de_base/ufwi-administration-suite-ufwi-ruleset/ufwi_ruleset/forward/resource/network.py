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
from IPy import IP

from ufwi_ruleset.common.network import (isNetwork,
    NETWORK_RESTYPE, HOST_RESTYPE, IPSEC_NETWORK_RESTYPE,
    GENERIC_NETWORK_RESTYPE, GENERIC_HOST_RESTYPE,
    INTERNET_IPV4, INTERNET_IPV6,
    IPV4_ADDRESS, IPV6_ADDRESS)

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.attribute import Attribute, Enum, getUnicode
from ufwi_ruleset.forward.resource import Resource
from ufwi_ruleset.forward.resource.tools import parseIPAddress
from ufwi_ruleset.forward.match import matchAddresses

LOCAL_LINK_IPV6 = IP('fe80::/64')
LOCAL_MULTICAST_IPV6 = IP('ff02::/16')

def adresssType(address):
    if address.version() == 6:
        return IPV6_ADDRESS
    else:
        return IPV4_ADDRESS

def checkHost(address):
    if isNetwork(address):
        raise RulesetError(
            tr('"%s" is not an host address!'),
            unicode(address))

class Address(Attribute):
    type = IP
    xmlrpc = unicode

    def getter(self, object, name, text):
        text = getUnicode(text)
        if not text:
            return None
        return parseIPAddress(text)

class AddressType(Enum):
    def exportXML(self, object, name, node):
        if not object.isGeneric():
            return
        return Enum.exportXML(self, object, name, node)

class BaseNetworkResource(Resource):
    TEMPLATE_TYPE = None
    address = Address(optional=True)
    address_type = AddressType((IPV4_ADDRESS, IPV6_ADDRESS))

    def __init__(self, parent, attr, loader_context=None):
        Resource.__init__(self, parent.resources, parent, parent.interface,
            attr, loader_context)

    def setAttributes(self, attr, is_modify):
        if 'address_type' not in attr:
            address = parseIPAddress(attr['address'])
            attr['address_type'] = adresssType(address)
        Resource.setAttributes(self, attr, is_modify)
        if self.address is None:
            self.type = self.TEMPLATE_TYPE
        else:
            self.type = self.TYPE

    def templatize(self, attr):
        attr['address'] = None

    def getAddressTypes(self):
        return set((self.address_type,))

    def checkResource(self, new_resource, loader_context=None):
        Resource.checkResource(self, new_resource, loader_context)
        if self.isGeneric() or new_resource.hasAddresses():
            # Don't check template networks
            return

        for address in new_resource.getAddresses():
            if self.address in address:
                raise RulesetError(
                    tr('The %s network (%s) is larger than the network %s (%s)!'),
                    new_resource.formatID(), unicode(address),
                    self.formatID(), unicode(self.address))

            if address not in self.address:
                raise RulesetError(
                    tr('The %s address (%s) is not part of the %s network (%s)!'),
                    unicode(address), new_resource.formatID(),
                    self.formatID(), unicode(self.address))

    def checkUnicity(self, new_resource, loader_context=None):
        Resource.checkUnicity(self, new_resource, loader_context)
        if self.hasAddresses() \
        and new_resource.hasAddresses() \
        and self.address in new_resource.getAddresses():
            message = tr('The "%s" address (%s) already exists: network %s!')
            args = (unicode(new_resource.address), new_resource.formatID(),
                    self.formatID())
            if loader_context is not None:
                loader_context.warning(message, args)
            else:
                raise RulesetError(message, *args)

    def hasAddresses(self):
        return (self.type != self.TEMPLATE_TYPE)

    def getAddresses(self):
        return (self.address,)

    def __unicode__(self):
        if self.address:
            return tr('The %s network (%s)') % (self.formatID(), self.address)
        else:
            return tr('The %s generic network') % self.formatID()

    def _matchResource(self, other):
        if not self.hasAddresses():
            return False
        try:
            if not other.hasAddresses():
                return False
            other_addresses = other.getAddresses()
        except NotImplementedError:
            return False
        return matchAddresses((self.address,), other_addresses)

    def setPhysical(self, address):
        self.address = address
        self.type = self.TYPE

    def setGeneric(self):
        self.address = None
        self.type = self.TEMPLATE_TYPE

    def isGeneric(self, recursive=False):
        if self.type == self.TEMPLATE_TYPE:
            return True
        if recursive:
            return self.interface.isGeneric()
        else:
            return False

class NetworkResource(BaseNetworkResource):
    XML_TAG = 'network'
    TYPE = NETWORK_RESTYPE
    TEMPLATE_TYPE = GENERIC_NETWORK_RESTYPE

    def setAttributes(self, data, is_modify):
        BaseNetworkResource.setAttributes(self, data, is_modify)
        if self.type == NETWORK_RESTYPE:
            self.address.NoPrefixForSingleIp = False

    def isInternet(self):
        """
        Is an Internet resource? Eg. the network "0.0.0.0/0".
        """
        if self.type == NETWORK_RESTYPE:
            return self.address in (INTERNET_IPV4, INTERNET_IPV6)
        else:
            return False

    def getNetworkByAddress(self, address):
        if self.address \
        and address == self.address:
            return self
        return BaseNetworkResource.getNetworkByAddress(self, address)

    def _removeTemplate(self, action, template_name):
        Resource._removeTemplate(self, action, template_name)
        if self.isGeneric():
            self.ruleset.generic_links.removeTemplateAction(
                action, template_name, 'networks', self,
                tr('Unable to delete the template "%s": the generic network %s is not defined'))

    def _modifyChildren(self, old_attr):
        """
        Iterate on all network and host children if the network address
        changed, otherwise create an empty iterator.
        """
        if self.isGeneric() or ('address' not in old_attr):
            return
        if self.address == IP(old_attr['address']):
            return
        for child in self.iterChildren(recursive=True):
            if not isinstance(child, BaseNetworkResource):
                continue
            if child.isGeneric():
                continue
            yield child

    def onModify(self, old_attr):
        """
        If the network address changed, update all network and host children address.

        Example with the host 192.168.0.16 in the network 192.168.0.0/16: if
        the network address is changed to 10.8.0.0/24, the host address is
        updated to 10.8.0.16.
        """
        for child in self._modifyChildren(old_attr):
            if self.address.version() == 6:
                size = 128
            else:
                size = 32
            prefixlen = child.address.prefixlen()
            low_mask = 2 ** (size - self.address.prefixlen()) - 1
            high_mask = 2 ** size - 1
            high_mask &= ~low_mask
            address = self.address.int() & high_mask
            address |= child.address.int() & low_mask
            if prefixlen != size:
                child.address = IP("%s/%s" % (child.address, prefixlen))
            else:
                child.address = IP(address)

    def onModifyAction(self, action, old_attr):
        for child in self._modifyChildren(old_attr):
            action.addBothUpdate(child.createUpdate())

Resource.registerSubclass(NetworkResource)

class IPsecNetworkResource(NetworkResource):
    XML_TAG = 'ipsec_network'
    TYPE = IPSEC_NETWORK_RESTYPE
    TEMPLATE_TYPE = None   # there are no generic IPsec network

    gateway = Address(optional=True)

    def hasAddresses(self):
        return True

    def checkConsistency(self, loader_context=None):
        NetworkResource.checkConsistency(self, loader_context)
        if (self.gateway is not None) \
        and (self.address.version() != self.gateway.version()):
            raise RulesetError(
                tr('Gateway (%s) of the IPsec network %s must be an %s address!'),
                unicode(self.gateway), self.formatID(), self.address_type)

Resource.registerSubclass(IPsecNetworkResource)

class HostResource(BaseNetworkResource):
    XML_TAG = 'host'
    TYPE = HOST_RESTYPE
    TEMPLATE_TYPE = GENERIC_HOST_RESTYPE

    def __init__(self, parent, attr, loader_context=None):
        BaseNetworkResource.__init__(self, parent, attr, loader_context)
        self.allow_child = False

    def checkConsistency(self, loader_context=None):
        BaseNetworkResource.checkConsistency(self, loader_context)
        if self.address is not None:
            checkHost(self.address)

    def __unicode__(self):
        if self.address:
            return tr('The %s host (%s)') % (self.formatID(), self.address)
        else:
            return tr('The %s generic host') % self.formatID()

    def getHostByAddress(self, address):
        if self.address \
        and address == self.address:
            return self
        return BaseNetworkResource.getHostByAddress(self, address)

    def _removeTemplate(self, action, template_name):
        Resource._removeTemplate(self, action, template_name)
        if self.isGeneric():
            self.ruleset.generic_links.removeTemplateAction(
                action, template_name, 'hosts', self,
                tr('Unable to delete the template "%s": the generic host %s is not defined'))
Resource.registerSubclass(HostResource)

