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

from PyQt4.QtCore import QSize

from ufwi_rpcd.common import tr

from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS

from ufwi_rulesetqt.create_protocol import CreateProtocolDialog
from ufwi_rulesetqt.library import Library, LibraryMenu
from ufwi_rulesetqt.objects import Object
from ufwi_rulesetqt.filter import AddressTypeFilter

LAYER_NAMES = {
    u'tcp': u'TCP',
    u'udp': u'UDP',
    u'icmp': u'ICMP',
    u'icmpv6': u'ICMPv6',
}

class Protocol(Object):
    ICONS = {
        "tcp": ":/icons-32/tcp.png",
        "udp": ":/icons-32/udp.png",
    }

    def getLayer(self):
        """
        Layer4 or Layer3 value
        """
        if 'layer4' in self:
            return self['layer4']
        else:
            return self['layer3']

    def getLayerLabel(self):
        if ('layer4' in self) \
        and self['layer4'] not in ('tcp', 'udp', 'icmp', 'icmpv6'):
            return tr('Layer 4')
        elif 'layer3' in self:
            return tr('Layer 3')
        else:
            layer = self['layer4']
            return LAYER_NAMES.get(layer, unicode(layer))

    def getToolTip(self):
        if 'layer4' in self:
            layer4 = self['layer4']
            if layer4 in ('tcp', 'udp', 'icmp', 'icmpv6'):
                text = LAYER_NAMES.get(layer4, unicode(layer4))
                for key in ("dport", "sport", "type", "code"):
                    if key not in self:
                        continue
                    text += u" %s=%s" % (key, self[key])
                return text
            else:
                return tr("Layer4: protocol=%s") % layer4
        else:
            return None

    def destinationRange(self):
        if 'dport' in dict(self):
            return self['dport'].split(':', 1), self['dport'].rsplit(':', 1)
        return 1, 65535

    def getIcon(self):
        layer = self.getLayer()
        return self.ICONS.get(layer)

    def getParents(self):
        parents = set()
        if 'layer4' in self:
            parents.add(u'Any IPv4')
            parents.add(u'Any IPv6')
            layer4 = self['layer4']
            if layer4 == 'tcp':
                parents.add(u'Any TCP')
            elif layer4 == 'udp':
                parents.add(u'Any UDP')
            elif layer4 == 'icmp':
                parents.add(u'Any ICMP')
            elif layer4 == 'icmpv6':
                parents.add(u'Any ICMPv6')
        return parents

    def getChildren(self):
        protocols = self.library
        identifier = self['id']
        if identifier == u'Any IPv4':
            return set(protocol['id'] for protocol in protocols
                if IPV4_ADDRESS in protocol['address_types'])
        if identifier == u'Any IPv6':
            return set(protocol['id'] for protocol in protocols
                if IPV6_ADDRESS in protocol['address_types'])

        layer3 = None
        layer4 = None
        if identifier == u'Any TCP':
            layer4 = 'tcp'
        elif identifier == u'Any UDP':
            layer4 = 'udp'
        elif identifier == u'Any ICMP':
            layer4 = 'icmp'
        elif identifier == u'Any ICMPv6':
            layer4 = 'icmpv6'
        else:
            return set()
        children = set()
        for protocol in protocols:
            if layer3 and protocol.get('layer3') != layer3:
                continue
            if layer4 and protocol.get('layer4') != layer4:
                continue
            children.add(protocol['id'])
        return children

    def createInformation(self):
        def formatValue(value):
            if value is not None:
                return value
            else:
                return tr("(any)")
        options = [
            (tr('Identifier'), self['id']),
        ]
        layer3 = self.get('layer3')
        layer4 = self.get('layer4')
        options.append((tr('Layer 3'), formatValue(layer3)))
        options.append((tr('Layer 4'), formatValue(layer4)))
        if layer4 in (u"tcp", u"udp"):
            options.append((tr("Destination port"), formatValue(self.get("dport"))))
            options.append((tr("Source port"), formatValue(self.get("sport"))))
        elif layer4 in (u"icmp", u"icmpv6"):
            options.append((tr("ICMP type"), formatValue(self.get("type"))))
            options.append((tr("ICMP code"), formatValue(self.get("code"))))
        options.append((tr('References'), self.createReferencesHTML()))

        return (tr('Protocol'), options)

class ProtocolFilter(AddressTypeFilter):
    def matchPort(self, text):
        text = unicode(text)
        if text == '1024:65535':
            return False
        return text.startswith(self.pattern)

    def match(self, object):
        if not self.matchAddressType(object):
            return False
        if AddressTypeFilter.match(self, object):
            return True
        for attr in ('sport', 'dport', 'type', 'code'):
            if (attr in object) \
            and self.matchPort(object[attr]):
                return True
        return False

class Protocols(Library):
    REFRESH_DOMAIN = u"protocols"
    URL_FORMAT = u"protocol:%s"
    RULESET_ATTRIBUTE = "protocols"
    CHILD_CLASS = Protocol

    def __init__(self, window):
        Library.__init__(self, window, "protocol")
        self.dialog = CreateProtocolDialog(window)
        self.setupWindow()
        self.filter = ProtocolFilter()

    def setupWindow(self):
        window = self.window
        self.setButtons()
        self.setContainer(window.protocol_list)
        self.container.setIconSize(QSize(24, 24))
        self.setMenu(LibraryMenu(self,
            tr("New protocol"),
            tr("Edit this protocol"),
            tr("Delete this protocol")))

    def getTreeKey(self, protocol):
        return protocol.getLayerLabel()

    def createTreeKeyLabel(self, label):
        return label

