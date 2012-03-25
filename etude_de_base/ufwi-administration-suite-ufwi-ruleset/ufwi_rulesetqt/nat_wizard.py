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

from PyQt4.QtGui import QDialog
from PyQt4.QtCore import SIGNAL, Qt

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.html import htmlImage, htmlTable

from ufwi_ruleset.common.network import (
    NETWORK_RESTYPE, GENERIC_NETWORK_RESTYPE,
    HOST_RESTYPE, GENERIC_HOST_RESTYPE,
    HOSTNAME_RESTYPE, INTERFACE_RESTYPE,
    IPV4_ADDRESS, IPV6_ADDRESS)

from ufwi_rulesetqt.resources import Resource
from ufwi_rulesetqt.protocols import Protocol, CreateProtocolDialog
from ufwi_rulesetqt.html import htmlTitle, htmlMultiColTable
from ufwi_rulesetqt.nat_wizard_ui import Ui_Dialog
from ufwi_rulesetqt.objects import Group
from ufwi_rulesetqt.tools import getIdentifier

class NatWizard(Ui_Dialog):
    def __init__(self, window):
        self.dialog = QDialog(window)
        self.setupUi(self.dialog)
        self.window = window
        self.rule_type = 0

        # Set defaults parameters
        window.connect(self.next_button, SIGNAL("clicked()"), self.nextFrame)
        window.connect(self.previous_button, SIGNAL("clicked()"), self.previousFrame)
        window.connect(self.dnat_port_nated_checkbox, SIGNAL("toggled(bool)"), self.dnat_port_nated_combo.setEnabled)
        window.connect(self.dnat_port_combo, SIGNAL("activated(int)"), self.DNATPortChanged)
        window.connect(self.dnat_port_combo, SIGNAL("activated(int)"), self.portChanged)
        window.connect(self.dnat_port_nated_combo, SIGNAL("activated(int)"), self.portChanged)

        # Refresh the DNAT description
        window.connect(self.dnat_source_combo, SIGNAL("activated(int)"),        self.setDNATDescription)
        window.connect(self.dnat_translate_combo, SIGNAL("activated(int)"),     self.setDNATDescription)
        window.connect(self.dnat_port_combo, SIGNAL("activated(int)"),          self.setDNATDescription)
        window.connect(self.dnat_port_nated_combo, SIGNAL("activated(int)"),    self.setDNATDescription)
        window.connect(self.dnat_port_nated_checkbox, SIGNAL("toggled(bool)"),  self.setDNATDescription)

        # Refresh the DNAT description
        window.connect(self.snat_source_combo, SIGNAL("activated(int)"),        self.setSNATDescription)
        window.connect(self.snat_translate_combo, SIGNAL("activated(int)"),     self.setSNATDescription)

        # Fill the various network combo box
        self.snat_source_combo.clear()
        self.snat_translate_combo.clear()
        self.dnat_source_combo.clear()
        self.dnat_translate_combo.clear()
        self.networks_model = self.window.getModel('resources')

        networks = list(self.networks_model.resourcesIterator())
        networks.sort(key=getIdentifier)
        for res in networks:
            if isinstance(res, Group):
                continue
            # Reject IPv6 objects
            if IPV6_ADDRESS in res['address_types'] and IPV4_ADDRESS not in res['address_types']:
                continue
            if res['type'] in (NETWORK_RESTYPE, GENERIC_NETWORK_RESTYPE):
                self.snat_source_combo.addItem(res['id'])
                self.snat_translate_combo.addItem(res['id'])
                self.dnat_source_combo.addItem(res['id'])
                # Select the Internet resource by default
                if res.isInternet():
                    self.snat_translate_combo.setCurrentIndex(self.snat_translate_combo.count() - 1)
                    self.dnat_source_combo.setCurrentIndex(self.dnat_source_combo.count() - 1)
            elif res['type'] in (HOST_RESTYPE, GENERIC_HOST_RESTYPE, HOSTNAME_RESTYPE):
                self.dnat_translate_combo.addItem(res['id'])

        self.fillPortCombo()
        self.setDNATDescription()
        self.setSNATDescription()
        self.dialog.exec_()

    def fillPortCombo(self):
        # Fill the various service boxes
        self.dnat_port_combo.clear()
        self.dnat_port_nated_combo.clear()
        port_list = []
        protocols = self.window.getLibrary('protocols')
        for port in protocols:
            if isinstance(port, Protocol) and port.getLayer() in (u'tcp', u'udp'):
                first, last = port.destinationRange()
                if first == last:
                    port_list.append(port['id'])
        port_list.sort()

        self.dnat_port_combo.addItem(tr("Any"))
        for port in port_list:
            self.dnat_port_combo.addItem(port)
            self.dnat_port_nated_combo.addItem(port)
        self.dnat_port_combo.addItem(tr("New service..."))
        self.dnat_port_nated_combo.addItem(tr("New service..."))

        self.DNATPortChanged(0)

    def DNATPortChanged(self, index):
        enable = bool(index)
        self.dnat_port_nated_checkbox.setEnabled(enable)
        self.dnat_port_nated_combo.setEnabled(enable and self.dnat_port_nated_checkbox.checkState() == Qt.Checked)

    def portChanged(self, index):
        # Check if the "New service" entry was selected
        if self.dnat_port_combo.currentIndex() == self.dnat_port_combo.count() - 1 or \
        self.dnat_port_nated_combo.currentIndex() == self.dnat_port_nated_combo.count() - 1:
            dialog = CreateProtocolDialog(self.window)
            dialog.create()
            self.fillPortCombo()

    def nextFrame(self):
        stack_index = self.stackedWidget.currentIndex()
        if stack_index == 0:
            if self.snat_radio.isChecked():
                if not self.snat_source_combo.count():
                    self.window.error(
                        tr("You need to create at least one network to use the NAT wizard"),
                        dialog=True)
                    return
                self.setFrame(1)
            else:
                if not self.dnat_translate_combo.count():
                    self.window.error(
                        tr("You need to create at least one host to use the NAT wizard"),
                        dialog=True)
                    return
                self.setFrame(2)
        elif stack_index != 3:
            self.setFrame(3)
            self.setDescription()
        else:
            if self.createRule():
                self.dialog.accept()

    def previousFrame(self):
        if self.stackedWidget.currentIndex() == 3:
            self.setFrame(self.previous_frame)
        else:
            self.setFrame(0)

    def setFrame(self, index):
        self.previous_frame = self.stackedWidget.currentIndex()
        self.stackedWidget.setCurrentIndex(index)
        if index == 3:
            self.next_button.setText(tr("Finish"))
        else:
            self.next_button.setText(tr("Next"))
        self.previous_button.setEnabled(index != 0)

    def getNetwork(self, identifier):
        return self.networks_model.getResource(identifier)

    def setDNATDescription(self):
        # Present a nice description of the rule:
        # DNAT
        network = unicode(self.dnat_source_combo.currentText())
        if not network:
            return
        dnat_source_icon = self.getNetwork(network).getIcon()
        network = unicode(self.dnat_translate_combo.currentText())
        if not network:
            return
        dnat_destination_icon = self.getNetwork(network).getIcon()

        table = [ [htmlImage(dnat_source_icon), htmlImage(":/icons/go-next.png"), htmlImage(Resource.ICONS[INTERFACE_RESTYPE]), htmlImage(":/icons/go-next.png"), htmlImage(dnat_destination_icon)] ]

        src = self.dnat_source_combo.currentText()
        if self.dnat_port_combo.currentIndex() != 0:
            src += ' : ' +  self.dnat_port_combo.currentText()

        dst = self.dnat_translate_combo.currentText()
        if self.dnat_port_combo.currentIndex() != 0 and self.dnat_port_nated_checkbox.checkState() == Qt.Checked:
            dst += ' : ' + self.dnat_port_nated_combo.currentText()

        table += [ [src, '', tr('Firewall'), '', dst] ]
        desc  = htmlMultiColTable(table)
        self.dnat_description.setText(unicode(desc))

    def setSNATDescription(self):
        # Present a nice description of the rule:
        # DNAT
        network = unicode(self.snat_source_combo.currentText())
        if not network:
            return
        dnat_source_icon = self.getNetwork(network).getIcon()
        network = unicode(self.snat_translate_combo.currentText())
        if not network:
            return
        dnat_destination_icon = self.getNetwork(network).getIcon()

        table = [ [htmlImage(dnat_source_icon), htmlImage(":/icons/go-next.png"), htmlImage(Resource.ICONS[INTERFACE_RESTYPE]), htmlImage(":/icons/go-next.png"), htmlImage(dnat_destination_icon)] ]

        src = self.snat_source_combo.currentText()
        dst = self.snat_translate_combo.currentText()

        table += [ [src, '', tr('Firewall'), '', dst] ]
        desc  = htmlMultiColTable(table)
        self.snat_description.setText(unicode(desc))

    def setDescription(self):
        # Present a nice description of the rule:
        if self.previous_frame == 1:
            # SNAT
            snat_source_icon = self.getNetwork(unicode(self.snat_source_combo.currentText())).getIcon()
            snat_destination_icon = self.getNetwork(unicode(self.snat_translate_combo.currentText())).getIcon()

            desc = htmlTitle(tr('Source address translation'))
            table = [ ('', htmlImage(snat_source_icon) + ' ' + self.snat_source_combo.currentText()),
                      (tr('when connecting to '), htmlImage(snat_destination_icon) + ' ' + self.snat_translate_combo.currentText()),
                      (tr('translates into '), htmlImage(Resource.ICONS[INTERFACE_RESTYPE]) + ' ' + 'Firewall.') ]
        else:
            # DNAT
            dnat_source_icon = self.getNetwork(unicode(self.dnat_source_combo.currentText())).getIcon()
            dnat_destination_icon = self.getNetwork(unicode(self.dnat_translate_combo.currentText())).getIcon()

            desc = htmlTitle(tr('Destination address translation'))
            table = [ ('', htmlImage(dnat_source_icon) + ' ' + self.dnat_source_combo.currentText()),
                      (tr('when connecting to '), htmlImage(Resource.ICONS[INTERFACE_RESTYPE]) + ' ' + 'Firewall.') ]

            protocols = self.window.getLibrary('protocols')
            if self.dnat_port_combo.currentIndex() != 0:
                identifier = unicode(self.dnat_port_combo.currentText())
                dnat_port_icon = protocols[identifier].getIcon()
                table += [ (tr('on port '), htmlImage(dnat_port_icon) + ' ' + self.dnat_port_combo.currentText()) ]

            table += [ (tr('connects to'), htmlImage(dnat_destination_icon) + ' ' + self.dnat_translate_combo.currentText()) ]

            if self.dnat_port_combo.currentIndex() != 0 and self.dnat_port_nated_checkbox.checkState() == Qt.Checked:
                identifier = unicode(self.dnat_port_nated_combo.currentText())
                dnat_port_icon = protocols[identifier].getIcon()
                table += [ (tr('on port '), htmlImage(dnat_port_icon) + ' ' + self.dnat_port_nated_combo.currentText()) ]

        desc += htmlTable(table)
        self.rule_description.setText(unicode(desc))

    def createRule(self):
        rule = {
            'enabled': True,
            'filters': [],
            'nated_filters': []}
        if self.previous_frame == 1:
            # SNAT rule
            rule['sources'] = [unicode(self.snat_source_combo.currentText())]
            rule['destinations'] = [unicode(self.snat_translate_combo.currentText())]
            rule['nated_sources'] = [u'Firewall']
            rule['nated_destinations'] = []
        else:
            # DNAT rule
            rule['sources'] = [unicode(self.dnat_source_combo.currentText())]
            rule['destinations'] = [u'Firewall']
            rule['nated_sources'] = []
            rule['nated_destinations'] = [unicode(self.dnat_translate_combo.currentText())]

            if self.dnat_port_combo.currentIndex() != 0:
                rule['filters'] = [ unicode(self.dnat_port_combo.currentText()) ]
                if self.dnat_port_nated_checkbox.checkState() == Qt.Checked:
                    rule['nated_filters'] = [ unicode(self.dnat_port_nated_combo.currentText()) ]
        try:
            updates = self.window.ruleset('ruleCreate', 'nats', rule)
            self.window.refresh(updates)
        except Exception, err:
            self.window.exception(err, dialog=True)
            return False
        return True
