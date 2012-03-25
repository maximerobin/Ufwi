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

from PyQt4.QtCore import SIGNAL, QRegExp
from IPy import IP

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.central_dialog import HOSTNAME_OR_FQDN_REGEXP, IPV4_REGEXP, IPV6_REGEXP

from ufwi_ruleset.common.network import (isNetwork,
    FIREWALL_RESTYPE, INTERFACE_RESTYPE, GENERIC_INTERFACE_RESTYPE,
    NETWORK_RESTYPE, GENERIC_NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE,
    HOST_RESTYPE, GENERIC_HOST_RESTYPE,
    HOSTNAME_RESTYPE,
    IPV4_ADDRESS, IPV6_ADDRESS,
    INTERFACE_NAME_REGEX_STR)
from ufwi_rulesetqt.create_resource_ui import Ui_CreateResource as CreateResourceForm
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX

INTERFACE_NAME_REGEX = QRegExp(INTERFACE_NAME_REGEX_STR)

STACK_INDEXES = {
    INTERFACE_RESTYPE: 0,
    NETWORK_RESTYPE: 1,
    HOST_RESTYPE: 2,
    HOSTNAME_RESTYPE: 3,
    IPSEC_NETWORK_RESTYPE: 4,
}
TEMPLATE_STACK = 5

NETWORK_TYPE_LABELS = {
    FIREWALL_RESTYPE: tr('Firewall'),
    INTERFACE_RESTYPE: tr('Physical interface'),
    GENERIC_INTERFACE_RESTYPE: tr('Generic interface'),
    NETWORK_RESTYPE: tr('Network'),
    GENERIC_NETWORK_RESTYPE: tr('Generic network'),
    IPSEC_NETWORK_RESTYPE: tr('IPsec network'),
    HOST_RESTYPE: tr('Host'),
    GENERIC_HOST_RESTYPE: tr('Generic host'),
    HOSTNAME_RESTYPE: tr('Hostname'),
}

class CreateResourceDialog(RulesetDialog, CreateResourceForm):
    def __init__(self, resources):
        RulesetDialog.__init__(self, resources.window)
        self.compatibility = self.window.compatibility
        self.resources = resources
        self.ruleset = resources.window.ruleset
        self.ipv6 = None
        self.setupWindow()

    def create(self, parent):
        self.setIPv6()
        self.auto_update_id = True
        self.resource_id = None
        self.resource_parent = parent
        self.name_text.setText(u'')
        self.identifier_text.setText(u'')

        if parent:
            parent_type = parent['type']
            if not self.ruleset.is_template:
                if parent_type == GENERIC_INTERFACE_RESTYPE:
                    parent_type = INTERFACE_RESTYPE
                elif parent_type == GENERIC_NETWORK_RESTYPE:
                    parent_type = NETWORK_RESTYPE
            if parent_type == GENERIC_INTERFACE_RESTYPE:
                types = (GENERIC_NETWORK_RESTYPE, NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE)
                child_type = GENERIC_NETWORK_RESTYPE
            elif parent_type == INTERFACE_RESTYPE:
                types = (NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE)
                child_type = NETWORK_RESTYPE
            elif parent_type == GENERIC_NETWORK_RESTYPE:
                types = (
                    GENERIC_NETWORK_RESTYPE, NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE,
                    GENERIC_HOST_RESTYPE, HOST_RESTYPE, HOSTNAME_RESTYPE)
                child_type = GENERIC_HOST_RESTYPE
            else: # parent_type == NETWORK_RESTYPE:
                types = (
                    NETWORK_RESTYPE, IPSEC_NETWORK_RESTYPE,
                    HOST_RESTYPE, HOSTNAME_RESTYPE)
                if parent.isInternet():
                    child_type = HOSTNAME_RESTYPE
                else:
                    child_type = HOST_RESTYPE
        else:
            if self.ruleset.is_template:
                child_type = GENERIC_INTERFACE_RESTYPE
            else:
                child_type = INTERFACE_RESTYPE
            types = (child_type,)
        if (IPSEC_NETWORK_RESTYPE in types) \
        and (not self.compatibility.ipsec_network):
            types = list(types)
            types.remove(IPSEC_NETWORK_RESTYPE)
        self.setType(types, (len(types) != 1), child_type)

        if self.ipv6:
            mask = 64
        else:
            mask = 24
        network_text = u''
        if parent and ("address" in parent) and (not parent.isInternet()):
            text = parent['address']
            ip = IP(text)
            network_text = unicode(ip.net())
            if isNetwork(ip):
                address = unicode(IP(ip.int() + 1))
                mask = ip.prefixlen() + 1
            else:
                address = text
            self.identifier_text.setText(address)
        else:
            address = u''
        self.network_text.setText(network_text)
        self.ipsec_network_text.setText(network_text)
        self.address_text.setText(address)
        self.ipsec_gateway_text.setText(address)
        if address:
            self.auto_update_id = False
        if mask is not None:
            self.network_spin.setValue(mask)
            self.ipsec_network_spin.setValue(mask)
        self.hostname_text.setText(u'')

        self.setWindowTitle(tr("Create a new network"))
        self.identifier_text.setFocus()
        return self.execLoop()

    def modify(self, resource):
        self.setIPv6()
        self.auto_update_id = False
        self.resource_id = resource['id']
        self.resource_parent = None

        # Set resource type
        restype = resource['type']
        types = (restype,)
        self.setType(types, False, restype)

        # Fill text widgets
        self.identifier_text.setText(resource['id'])
        if restype == INTERFACE_RESTYPE:
            self.name_text.setText(resource['name'])
        elif restype == NETWORK_RESTYPE:
            network = resource['address']
            address = unicode(network.net())
            self.network_text.setText(address)
            self.network_spin.setValue(network.prefixlen())
        elif restype == IPSEC_NETWORK_RESTYPE:
            network = resource['address']
            address = unicode(network.net())
            self.ipsec_network_text.setText(address)
            self.ipsec_network_spin.setValue(network.prefixlen())
            self.ipsec_gateway_text.setText(resource.get('gateway', u''))
        elif restype == HOST_RESTYPE:
            address = resource['address']
            self.address_text.setText(unicode(address))
        elif restype == HOSTNAME_RESTYPE:
            hostname = resource['hostname']
            self.hostname_text.setText(hostname)

        self.setWindowTitle(tr('Edit the "%s" network') % self.resource_id)
        self.identifier_text.setFocus()
        return self.execLoop()

    def setupWindow(self):
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.address_widgets = (
            self.name_text, self.hostname_text,
            self.address_text, self.ipsec_gateway_text,
        )
        self.network_widgets = (
            (self.network_text, self.network_spin),
            (self.ipsec_network_text, self.ipsec_network_spin),
        )
        self.connect(
            self.type_combo,
            SIGNAL("currentIndexChanged(int)"),
            self.changeTypeEvent)
        self.connect(
            self.identifier_text,
            SIGNAL("textEdited(const QString&)"),
            self.updateIdentifier)
        for widget in self.address_widgets:
            self.connect(widget,
                SIGNAL("textEdited(const QString&)"),
                self.disableAutoUpdate)
        for text_widget, spin_widget in self.network_widgets:
            self.connect(text_widget,
                SIGNAL("textEdited(const QString&)"),
                self.disableAutoUpdate)
        self.setRegExpValidator(self.identifier_text, IDENTIFIER_REGEX)
        self.setRegExpValidator(self.name_text, INTERFACE_NAME_REGEX)
        self.setRegExpValidator(self.hostname_text, HOSTNAME_OR_FQDN_REGEXP)
        #self.setIntValidator(self.icmp_code_edit, 0, 255)

    def updateIdentifier(self, text):
        if not self.auto_update_id:
            return
        text = unicode(text)
        for widget in self.address_widgets:
            widget.setText(text)
        try:
            ip = IP(text)
            network = unicode(ip.net())
            mask = ip.prefixlen()
        except ValueError:
            network = text
            mask = None
        for text_widget, spin_widget in self.network_widgets:
            self.network_text.setText(network)
            if mask is not None:
                spin_widget.setValue(mask)


    def disableAutoUpdate(self, text):
        self.auto_update_id = False

    def changeTypeEvent(self, index):
        if index < 0:
            return
        restype = self.restypes[index]
        self.setStack(restype)

    def setStack(self, restype):
        index = STACK_INDEXES.get(restype, TEMPLATE_STACK)
        self.stack.setCurrentIndex(index)
        self.name_text.setEnabled(index == 0)
        self.network_text.setEnabled(index == 1)
        self.address_text.setEnabled(index == 2)
        self.hostname_text.setEnabled(index == 3)
        self.ipsec_network_text.setEnabled(index == 4)
        self.ipsec_gateway_text.setEnabled(index == 4)

    def setType(self, types, editable_type, choice):
        self.restypes = {}
        self.restype_indexes = {}
        self.restype_names = []
        self.type_combo.clear()
        for index, type in enumerate(types):
            self.restypes[index] = type
            self.restype_indexes[type] = index
            self.type_combo.addItem(NETWORK_TYPE_LABELS[type])
            if type == choice:
                self.type_combo.setCurrentIndex(index)
        self.type_combo.setEnabled(editable_type)
        self.setStack(choice)

    def setIPv6(self):
        ipv6 = self.window.currentTabIsIPv6()
        self.ipv6 = ipv6
        if ipv6:
            mask = 128
            regex = IPV6_REGEXP
        else:
            mask = 32
            regex = IPV4_REGEXP
        self.network_spin.setMaximum(mask)
        self.ipsec_network_spin.setMaximum(mask)
        self.setRegExpValidator(self.network_text, regex)
        self.setRegExpValidator(self.ipsec_network_text, regex)
        self.setRegExpValidator(self.address_text, regex)
#        self.setRegExpValidator(self.ipsec_gateway_text, regex)

    def testIPAddress(self, address, ip_version):
        try:
            test_address = IP(address)
            if test_address.version() != ip_version:
                raise ValueError()
        except ValueError:
            if ip_version == 6:
                text = tr('Invalid IPv6 address: "%s"!')
            else:
                text = tr('Invalid IPv4 address: "%s"!')
            self.window.error(text % address, dialog=True)
            return False
        return True

    def getType(self):
        type_index = self.type_combo.currentIndex()
        return self.restypes[type_index]

    def save(self):
        restype = self.getType()
        identifier = unicode(self.identifier_text.text())
        attr = {'id': identifier}
        if self.ipv6:
            ip_version = 6
        else:
            ip_version = 4

        if restype == NETWORK_RESTYPE:
            attr['address'] = "%s/%s" % (
                unicode(self.network_text.text()),
                self.network_spin.value())
        elif restype == IPSEC_NETWORK_RESTYPE:
            attr['address'] = "%s/%s" % (
                unicode(self.ipsec_network_text.text()),
                self.ipsec_network_spin.value())
            attr['gateway'] = unicode(self.ipsec_gateway_text.text())
            if attr['gateway'] \
            and (not self.testIPAddress(attr['gateway'], ip_version)):
                return False

        elif restype == HOST_RESTYPE:
            attr['address'] = unicode(self.address_text.text())
        elif restype == HOSTNAME_RESTYPE:
            attr['hostname'] = unicode(self.hostname_text.text())
        elif restype == INTERFACE_RESTYPE:
            attr['name'] = unicode(self.name_text.text())
        elif restype != GENERIC_INTERFACE_RESTYPE:
            # Template
            if ip_version == 6:
                attr['address_type'] = IPV6_ADDRESS
            else:
                attr['address_type'] = IPV4_ADDRESS
        if 'address' in attr:
            if not self.testIPAddress(attr['address'], ip_version):
                return False
        try:
            if self.resource_id:
                arguments = ('objectModify', 'resources', self.resource_id, attr)
            else:
                if self.resource_parent:
                    parent_id = self.resource_parent['id']
                else:
                    parent_id = u''
                arguments = ('resourceCreate', restype, parent_id, attr)
            updates = self.ruleset(*arguments, **{'append_fusion': True})
        except Exception, err:
            self.window.exception(err, dialog=True)
            return False
        self.window.refresh(updates)
        return True

