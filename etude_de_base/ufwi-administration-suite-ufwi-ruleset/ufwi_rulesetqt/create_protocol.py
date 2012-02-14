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

from PyQt4.QtCore import SIGNAL
from ufwi_rulesetqt.create_protocol_ui import Ui_Dialog as CreateProtocolForm
from ufwi_rpcc_qt.tools import QComboBox_setCurrentText
from ufwi_rpcd.common import tr
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX

class PortSelection:
    def __init__(self, parent, prefix):
        for name in ("label",
        "single_radio", "range_radio", "any_radio",
        "port_spin", "first_spin", "last_spin"):
            attr = getattr(parent, prefix + name)
            setattr(self, name, attr)
        parent.connect(self.single_radio,
            SIGNAL("toggled(bool)"),
            self.singlePort)
        parent.connect(self.range_radio,
            SIGNAL("toggled(bool)"),
            self.portRange)
        parent.connect(self.any_radio,
            SIGNAL("toggled(bool)"),
            self.anyPort)

    def setMode(self, mode, force=False):
        single = (mode == 'single')
        port_range = (mode == 'range')
        any_port = (mode == 'any')

        if not single:
            self.single_radio.setChecked(False)
        if not port_range:
            self.range_radio.setChecked(False)
        if not any_port:
            self.any_radio.setChecked(False)

        self.port_spin.setEnabled(single)
        self.first_spin.setEnabled(port_range)
        self.last_spin.setEnabled(port_range)

    def singlePort(self, checked):
        if checked:
            self.setMode('single')

    def portRange(self, checked):
        if checked:
            self.setMode('range')

    def anyPort(self, checked):
        if checked:
            self.setMode('any')

    def setEnabled(self, enabled):
        self.label.setEnabled(enabled)
        self.port_spin.setEnabled(enabled)
        self.first_spin.setEnabled(enabled)
        self.last_spin.setEnabled(enabled)
        self.single_radio.setEnabled(enabled)
        self.range_radio.setEnabled(enabled)
        self.any_radio.setEnabled(enabled)

    def setValue(self, text):
        if not text:
            self.setMode('any')
            self.any_radio.setChecked(True)
        elif ':' in text:
            first, last = text.split(':', 1)
            first = int(first)
            last = int(last)
            self.setMode('range')
            self.range_radio.setChecked(True)
            self.first_spin.setValue(first)
            self.last_spin.setValue(last)
            self.port_spin.setValue(first)
        else:
            self.setMode('single')
            port = int(text)
            self.single_radio.setChecked(True)
            self.port_spin.setValue(port)
            self.first_spin.setValue(port)
            self.last_spin.setValue(port)

    def value(self):
        if self.any_radio.isChecked():
            return u''
        elif self.range_radio.isChecked():
            return u'%s:%s' % (
                self.first_spin.value(),
                self.last_spin.value())
        else:
            return unicode(self.port_spin.value())

class CreateProtocolDialog(RulesetDialog, CreateProtocolForm):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.object_id = None
        self.setupWindow()
        self.sport_selection = PortSelection(self, "sport_")
        self.dport_selection = PortSelection(self, "dport_")

    def setupWindow(self):
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.setRegExpValidator(self.identifier_edit, IDENTIFIER_REGEX)
        self.setIntValidator(self.icmp_type_edit, 0, 255)

        self.connect(
            self.layer4_combo,
            SIGNAL("currentIndexChanged(const QString&)"),
            self.changeLayer4)

    def fillLayer4(self):
        self.layer4_combo.clear()
        protocols = ['tcp', 'udp']
        if self.window.currentTabIsIPv6():
            protocols.append('icmpv6')
        else:
            protocols.append('icmp')
        self.layer4_combo.addItems(protocols)

    def create(self):
        self.fillLayer4()
        self.object_id = None
        self.setWindowTitle(tr("Create a new protocol"))
        self.changeLayer4(u'tcp')
        self.identifier_edit.setText(u'')
        self.sport_selection.setValue(u'1024:65535')
        self.dport_selection.setValue(u'80')
        QComboBox_setCurrentText(self.layer4_combo, u'tcp')
        self.layer4_label.setEnabled(True)
        self.layer4_combo.setEnabled(True)
        self.identifier_edit.setFocus()
        self.execLoop()

    def modify(self, protocol):
        self.fillLayer4()
        self.object_id = protocol['id']
        self.setWindowTitle(tr('Edit the "%s" protocol') % self.object_id)
        # Fill the widgets of the window
        layer4 = protocol['layer4']
        self.identifier_edit.setText(protocol['id'])
        QComboBox_setCurrentText(self.layer4_combo, layer4)
        self.changeLayer4(layer4)
        if layer4 in (u"tcp", u"udp"):
            sport = protocol.get('sport', u'')
            dport = protocol.get('dport', u'')
            self.sport_selection.setValue(sport)
            self.dport_selection.setValue(dport)
        else:
            icmp_type = protocol.get('type', u'')
            self.icmp_type_edit.setText(unicode(icmp_type))
            icmp_code = protocol.get('code', u'')
            self.icmp_code_edit.setText(unicode(icmp_code))
        self.layer4_label.setEnabled(False)
        self.layer4_combo.setEnabled(False)
        self.identifier_edit.setFocus()
        self.execLoop()

    def changeLayer4(self, layer4):
        layer4 = unicode(layer4)
        port = False
        icmp = False
        if layer4 in (u'udp', u'tcp'):
            port = True
        else:
            icmp = True

        self.sport_selection.setEnabled(port)
        self.dport_selection.setEnabled(port)

        self.icmp_type_label.setEnabled(icmp)
        self.icmp_type_edit.setEnabled(icmp)
        self.icmp_code_label.setEnabled(icmp)
        self.icmp_code_edit.setEnabled(icmp)
        if port:
            self.layer4_stack.setCurrentIndex(0)
        else:
            self.layer4_stack.setCurrentIndex(1)

    def save(self):
        identifier = unicode(self.identifier_edit.text())
        layer4 = unicode(self.layer4_combo.currentText())
        sport = self.sport_selection.value()
        dport = self.dport_selection.value()
        icmp_type = unicode(self.icmp_type_edit.text())
        icmp_code = unicode(self.icmp_code_edit.text())

        if layer4 == u"tcp" or layer4 == u"udp":
            attr = {'layer4':layer4, 'sport':sport, 'dport':dport}
        else:
            attr = {'layer4':layer4, 'type':icmp_type, 'code':icmp_code}

        return self.saveObject(identifier, 'protocols', attr)
