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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QTreeWidgetItem, QIcon

from ufwi_rpcd.common.human import humanYesNo
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.tools import unsetFlag

from ufwi_ruleset.common.network import INTERNET_IPV4, INTERNET_IPV6
from ufwi_rulesetqt.create_resource import CreateResourceDialog, NETWORK_TYPE_LABELS
from ufwi_ruleset.common.network import (FIREWALL_RESTYPE,
    INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE,
    NETWORK_RESTYPE, HOST_RESTYPE, HOSTNAME_RESTYPE,
    GENERIC_NETWORK_RESTYPE, GENERIC_HOST_RESTYPE,
    IPSEC_NETWORK_RESTYPE)
from ufwi_rulesetqt.library import Library, LibraryMenu, LibraryActions
from ufwi_rulesetqt.objects import Object, Group
from ufwi_rulesetqt.tools import getIdentifier
from ufwi_rulesetqt.filter import AddressTypeFilter
from ufwi_rulesetqt.library_model import NetworksModel

GENERIC_TYPES = set((GENERIC_INTERFACE_RESTYPE, GENERIC_NETWORK_RESTYPE, GENERIC_HOST_RESTYPE))

# Resource type only used for the icon
INTERNET_RESTYPE = u'INTERNET'

# Interface address type
INTERFACE_ADDRESS = u"interface"

class NetworkFilter(AddressTypeFilter):
    def __init__(self):
        AddressTypeFilter.__init__(self)
        self.show_firewall = True

    def matchAddress(self, address):
        address = unicode(address)
        return (self.pattern in address)

    def setFirewallVisibility(self, show):
        if self.show_firewall != show:
            self.show_firewall = show
            return True
        else:
            return False

    def match(self, object):
        if (not self.show_firewall) and (object['id'] == u'Firewall'):
            return False
        if not self.matchAddressType(object):
            return False
        if AddressTypeFilter.match(self, object):
            return True
        if ('address' in object) and self.matchAddress(object['address']):
            return True
        if ('addresses' in object) \
        and any(self.matchAddress(address) for address in object['addresses']):
            return True
        return False

class NetworkActions(LibraryActions):
    def __init__(self, library, network):
        LibraryActions.__init__(self, library, network)
        ruleset = library.ruleset
        self.template = ruleset.is_template \
            and bool(network) \
            and network.isEditable() \
            and (not isinstance(network, Group)) \
            and (not network.isGeneric())

class NetworkMenu(LibraryMenu):
    def __init__(self, library, config, create_text, modify_text, delete_text):
        LibraryMenu.__init__(self, library, create_text, modify_text, delete_text)
        self.config = config
        self.templatize_action = self.add(None,
            tr("Convert to generic network"),
            library.templatizeEvent)

    def display(self, event, actions):
        self.templatize_action.setEnabled(actions.template)
        LibraryMenu.display(self, event, actions)

class Resource(Object):
    SMALL_ICONS = {
        FIREWALL_RESTYPE: ":/icons-20/carte_reseau.png",
        INTERFACE_RESTYPE: ":/icons-20/carte_reseau.png",
        GENERIC_INTERFACE_RESTYPE: ":/icons-20/carte_reseau.png",
        NETWORK_RESTYPE: ":/icons-20/network.png",
        GENERIC_NETWORK_RESTYPE: ":/icons-20/network.png",
        IPSEC_NETWORK_RESTYPE: ":/icons-20/network.png",
        HOST_RESTYPE: ":/icons-20/computeur.png",
        GENERIC_HOST_RESTYPE: ":/icons-20/computeur.png",
        HOSTNAME_RESTYPE: ":/icons-20/computeur.png",
        INTERNET_RESTYPE: ":/icons-20/worldmap.png",
    }
    ICONS = {
        FIREWALL_RESTYPE: ":/icons-32/carte_reseau.png",
        INTERFACE_RESTYPE: ":/icons-32/carte_reseau.png",
        GENERIC_INTERFACE_RESTYPE: ":/icons-32/carte_reseau.png",
        NETWORK_RESTYPE: ":/icons-32/network.png",
        GENERIC_NETWORK_RESTYPE: ":/icons-32/network.png",
        IPSEC_NETWORK_RESTYPE: ":/icons-32/network.png",
        HOST_RESTYPE: ":/icons-32/computeur.png",
        GENERIC_HOST_RESTYPE: ":/icons-32/computeur.png",
        HOSTNAME_RESTYPE: ":/icons-32/computeur.png",
        INTERNET_RESTYPE: ":/icons-32/worldmap.png",
    }
    BACKGROUNDS = {
        FIREWALL_RESTYPE: ":/backgrounds/interface",
        INTERFACE_RESTYPE: ":/backgrounds/interface",
        GENERIC_INTERFACE_RESTYPE: ":/backgrounds/interface",
        INTERNET_RESTYPE: ":/backgrounds/internet",
        NETWORK_RESTYPE: ":/backgrounds/network",
        GENERIC_NETWORK_RESTYPE: ":/backgrounds/network",
        IPSEC_NETWORK_RESTYPE: ":/backgrounds/network",
        HOST_RESTYPE: ":/backgrounds/go-home.png",
        GENERIC_HOST_RESTYPE: ":/backgrounds/go-home.png",
        HOSTNAME_RESTYPE: ":/backgrounds/go-home.png",
    }

    def __init__(self, library, data):
        Object.__init__(self, library, data)
        if self['type'] in (NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE):
            self['address'].NoPrefixForSingleIp = False

    def isGeneric(self):
        return self['type'] in GENERIC_TYPES

    def getToolTip(self):
        if self['type'] == NETWORK_RESTYPE:
            return tr('Network %s') % self['address']
        elif self['type'] == IPSEC_NETWORK_RESTYPE:
            return tr('IPsec network %s') % self['address']
        elif self['type'] == HOST_RESTYPE:
            return tr('Host %s') % self['address']
        elif self['type'] == INTERFACE_RESTYPE:
            return tr('Interface %s') % self['name']
        elif self['type'] == HOSTNAME_RESTYPE:
            addresses = self['addresses']
            truncate = (3 < len(addresses))
            addresses = u', '.join(unicode(addr) for addr in addresses[:3])
            if truncate:
                addresses += ', ...'
            return tr('Hostname %s (%s)') % (self['hostname'], addresses)
        else:
            return None

    def allowCreate(self):
        return self['allow_child']

    def isInternet(self):
        if self['type'] != NETWORK_RESTYPE:
            return False
        return self['address'] in (INTERNET_IPV4, INTERNET_IPV6)

    def _getIcon(self, icons):
        if self.isInternet():
            network_type = INTERNET_RESTYPE
        else:
            network_type = self['type']
        return icons[network_type]

    def getSmallIcon(self):
        return self._getIcon(self.SMALL_ICONS)

    def getIcon(self):
        return self._getIcon(self.ICONS)

    def getBackground(self):
        if self.isInternet():
            return self.BACKGROUNDS[INTERNET_RESTYPE]
        else:
            return self.BACKGROUNDS.get(self['type'])

    def _getParent(self, parents):
        if 'parent' not in self:
            return
        parent = self['parent']()
        parents.add(parent['id'])
        parent._getParent(parents)

    def getParents(self):
        parents = set()
        self._getParent(parents)
        return parents

    def _getChildren(self, children):
        if 'children' not in self:
            return
        for child in self['children'].itervalues():
            children.add(child['id'])
            child._getChildren(children)

    def getChildren(self):
        children = set()
        self._getChildren(children)
        return children

    def createInformation(self):
        resource_type = self['type']
        options = [
            (tr('Identifier'), self['id']),
        ]
        if self.library.window.debug:
            options.extend((
                (u'allow_child', humanYesNo(self['allow_child'])),
                (u'is_generic', humanYesNo(self['is_generic'])),
            ))
            if 'parent' in self:
                parent = self['parent']()
                options.append((u'parent', parent['id']))
        if 'name' in self:
            options.append((tr('Name'), self['name']))
        if 'hostname' in self:
            options.append((tr('Hostname'), self['hostname']))
        if resource_type == IPSEC_NETWORK_RESTYPE:
            options.append((tr('Remote network'), unicode(self['address'])))
            options.append((tr('Remote gateway'), unicode(self['gateway'])))
        else:
            if 'address' in self:
                options.append((tr('Address'), unicode(self['address'])))
            if 'gateway' in self:
                options.append((tr('Gateway'), unicode(self['gateway'])))
        if 'addresses' in self:
            addresses = self['addresses']
            addresses = tuple(unicode(address) for address in addresses)
            options.append((tr('Addresses'), addresses))
        if resource_type not in (INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE) \
        and ('interface' in self):
            options.append((tr('Interface'), self['interface']))
        options.append((tr('References'), self.createReferencesHTML()))

        title = NETWORK_TYPE_LABELS[resource_type]
        address_types = self['address_types'] - set((INTERFACE_ADDRESS,))
        if address_types:
            title += ' (%s)' % u', '.join(address_types)
        return (title, options)

class NetworkGroup(Group):
    def _getChildren(self, children):
        # group has no child
        pass

class Resources(Library):
    REFRESH_DOMAIN = u"resources"
    URL_FORMAT = u"resource:%s"
    RULESET_ATTRIBUTE = "resources"
    CHILD_CLASS = Resource
    GROUP_CLASS = NetworkGroup
    ACTIONS = NetworkActions
    MODEL_CLASS = NetworksModel

    def __init__(self, window):
        Library.__init__(self, window, "resource")
        self.dialog = CreateResourceDialog(self)
        self.setupWindow(window)
        self.filter = NetworkFilter()

    def setupWindow(self, window):
        self.setButtons()
        self.setContainer(window.resource_tree)
        menu = NetworkMenu(self, window.config,
            tr("New"),
            tr("Edit"),
            tr("Delete"))
        self.setMenu(menu)

    def __iter__(self):
        return self.model.resourcesIterator()

    def create(self):
        parent = self.currentObject()
        self.dialog.create(parent)

    def modify(self, resource):
        self.dialog.modify(resource)

    def createInterfaceEvent(self):
        self.dialog.create(None)

    def _createTree(self, resources):
        resources.sort(key=getIdentifier)
        root = []
        for resource in resources:
            ignore = not self.filter.match(resource)
            tree = self.createTreeItem(resource)
            if 'children' in resource:
                children = resource['children'].values()
                nodes = self._createTree(children)
                for node in nodes:
                    tree.addChild(node)
                    ignore = False
            if resource['editable']:
                font = tree.font(0)
                font.setBold(True)
                tree.setFont(0, font)
            if ignore:
                continue
            root.append(tree)
        return root

    def createTree(self):
        nodes = self._createTree(list(self.model))
        root = QTreeWidgetItem([tr("Network interfaces")])
        root.setIcon(0, QIcon(":/icons-32/home.png"))
        unsetFlag(root, Qt.ItemIsSelectable)
        for node in nodes:
            root.addChild(node)
        return [root]

