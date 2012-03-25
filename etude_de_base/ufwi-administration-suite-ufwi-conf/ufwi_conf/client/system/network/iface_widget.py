# -*- coding: utf-8 -*-
"""
$Id$


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
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QAction
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QIcon
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMenu
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QWidget

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import getFirst
from ufwi_conf.common.net_interfaces import Ethernet
from ufwi_conf.common.net_interfaces import Vlanable
from ufwi_conf.client.system.network.wizards.network import NetworkWizard
from ufwi_conf.client.system.network.net_editor import NetEditor
from ufwi_conf.client.qt.foldable_widget import FoldableData
from ufwi_conf.client.qt.foldable_widget import FoldableWidget

class NetsAbstract(QLabel):
    def __init__(self, nets, parent=None):
        QLabel.__init__(self, parent)
        self.nets = nets
        self.update()

    def update(self):
        nets = list(self.nets)
        nets.sort()
        #self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        tooltip = u',\n'.join([net.label for net in nets])
        self.setToolTip(tooltip)
        if len(nets) == 0:
            self.setText(u"Not used")
            return
        if len(nets) == 1:
            self.setText(netAbstract(nets[0]))
            return
        for net in nets:
            text = u"%s, %s" % tuple((netAbstract(nets[i]) for i in xrange(2)))
        if len(nets) > 2:
            text += u"…"
        self.setText(text)

class NetDetails(QWidget):
    def __init__(self, net, parent=None):
        QWidget.__init__(self, parent)

        self.net = net
        form = QFormLayout(self)
        net_ips = NetIps(net)
        form.addRow(tr("IP addresses:"), net_ips)
        self.connect(net_ips, SIGNAL('double click'), self.edit)

    def edit(self):
        self.emit(SIGNAL('edit'))


def netAbstract(net):
    if net.ip_addrs:
        ip = getFirst(net.ip_addrs)
        return "%s/%s" % (unicode(ip), net.net.prefixlen())
    return "<i>%s</i>" % net.label

class NetIps(QFrame):
    def __init__(self, net, parent=None):
        QFrame.__init__(self, parent)
        self.net = net
        form = QFormLayout(self)

        if self.net.primary_ip_addrs or self.net.secondary_ip_addrs:
            service_name = tr("Service")
        else:
            service_name = u""

        form.addRow(service_name, self.mkIpList(self.net.service_ip_addrs))
        if self.net.primary_ip_addrs or self.net.secondary_ip_addrs:
            form.addRow(tr("Primary"), self.mkIpList(self.net.primary_ip_addrs))
            form.addRow(tr("Secondary"), self.mkIpList(self.net.secondary_ip_addrs))

    def mkIpList(self, ip_addrs):
        ip_addrs = list(ip_addrs)
        ip_addrs.sort()
        text = "<br/>".join(unicode(ip) for ip in ip_addrs)
        label = QLabel(text)
        label.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        label.setTextFormat(Qt.RichText)
        return label

class NetAbstract(QLabel):
    def __init__(self, net, parent=None):
        QLabel.__init__(self, parent)
        self.net = net
        self.update()

    def update(self):
        self.setText(netAbstract(self.net))

class FoldableNet(FoldableData):
    def __init__(self, net):
        self.net = net
        content = NetDetails(net)

        FoldableData.__init__(
            self,
            content=content,
            name=net.label,
            abstract=NetAbstract(net)
            )

class NetMenu(QMenu):
    def __init__(self, net, parent):
        QMenu.__init__(self, parent)
        def editIntermediate(value):
            self.emit(SIGNAL('edit'), net)

        def deleteIntermediate(value):
            self.emit(SIGNAL('delete'), net)

        edit_net = QAction(QIcon(":icons/edit"), self.tr("Edit network parameters"), parent)
        self.connect(edit_net, SIGNAL('triggered(bool)'), editIntermediate )

        del_net = QAction(QIcon(":icons/delete"), self.tr("Delete this network"), parent)
        self.connect(del_net, SIGNAL('triggered(bool)'), deleteIntermediate)

        self.setObjectName("menu_%s" % net.label)
        actions = edit_net, del_net
        for action in actions:
            self.addAction(action)

class InterfaceDetails(QWidget):
    def __init__(self, interface, parent=None):
        QWidget.__init__(self, parent)

        self.interface = interface
        self.net2widget = dict()

        self.form = QFormLayout(self)
        for label, data in interface.details():
            self.form.addRow(label, QLabel("<i>%s</i>" % data))

        nets = list(interface.nets)
        nets.sort()
        for net in nets:
            self.addNet(net)

    def addNet(self, net, part_of_larger_process=True):
        """
        part_of_larger_process=False means the intent of the user was to add net, and we are not called
        as part of a larger action.
        Therefore, the larger action should notify of modification if warn=False.
        """
        net_data = FoldableNet(net)
        net_widget = FoldableWidget(net_data, start_folded=True, parent=self)
        menu = NetMenu(net, self)
        net_data.setMenu(menu)
        self.form.addRow(net_widget)
        self.net2widget[net] = net_widget
        self.interface.nets.add(net)

        self.connect(net_widget, SIGNAL('net_changed'), self.drawNet)
        self.connect(net_widget, SIGNAL('edit'), self.editNet)
        self.connect(menu, SIGNAL('edit'), self.editNet)
        self.connect(menu, SIGNAL('delete'), self.deleteNet)
        if not part_of_larger_process:
            self.setModified()

    def deleteNetWithoutWarn(self, net):
        self.deleteNet(net, warn=False)

    def deleteNet(self, net, warn=True):
        """
        warn=True means the intent of the user was to delete the net, and we are not called
        as part of a larger action.
        Therefore, the larger action should notify of modification if warn=False.
        """
        if warn:
            if QMessageBox.warning(
                self, self.tr("About to delete a network"),
                self.tr("About to delete network %1").arg(unicode(net.label)),
                QMessageBox.Cancel, QMessageBox.Ok
                ) != QMessageBox.Ok:
                return

        self.net2widget[net].deleteLater()
        del self.net2widget[net]
        self.interface.delNet(net)
        if warn:
            self.setModified(part_of_larger_process=False)

    def drawNet(self, net):
        """
        Called when a net was just changed
        """
        self.deleteNet(net, warn=False)
        self.addNet(net)

    def editNet(self, net):
        edit_dialog = NetEditor(self.interface, net=net)
        def drawNetIntermediate():
            self.deleteNet(net, warn=False)
            self.addNet(edit_dialog.getNet())
            self.setModified(part_of_larger_process=False)
        self.connect(edit_dialog, SIGNAL('accepted()'), drawNetIntermediate)
        edit_dialog.exec_()

    def netWizard(self):
        net_wizard = NetworkWizard(self.interface, self)
        #FIXME: temp
        net_wizard.show()
        self.connect(net_wizard, SIGNAL('done'), self.netwizardDone)

    def netwizardDone(self, wizard):
        net = wizard.getNet()

        do_insert = True
        to_delete = set()
        for older_net in self.interface.nets:
            if older_net.net.overlaps(net.net):
                if QMessageBox.warning(
                self, self.tr('Warning'),
                    self.tr(
                        u'Another network is defined on the same interface. It overlaps '
                        u'the network you have just created.\n'
                        u'Drop existing network %1?'
                    ).arg(older_net.label),
                QMessageBox.Yes,
                QMessageBox.No
                ) == QMessageBox.Yes:
                    to_delete.add(older_net)
                else:
                    do_insert = False

        for older_net in to_delete:
            self.deleteNetWithoutWarn(older_net)

        if do_insert:
            self.interface.nets.add(net)
            self.addNet(net)
            self.setModified(part_of_larger_process=False)

    def setModified(self, part_of_larger_process=True):
        if not part_of_larger_process:
            self.emit(SIGNAL('modified'), self.interface)

class FoldableInterface(FoldableData):
    def __init__(self, interface, parent=None):
        #super.__init__ at bottom: we only prepare, here.
        self.interface = interface

        if interface.freeForIp():
            content = InterfaceDetails(interface)
            abstract = NetsAbstract(interface.nets)
            supplementary_info = u''
        else:
            content = QWidget()
            abstract = QLabel()
            if isinstance(interface, Ethernet):
                mac = getattr(interface, 'mac', u'')
                supplementary_info = u' - MAC: %s' % mac if mac else u''
            else:
                supplementary_info = u''

        #...Finally, the parent constructor...
        FoldableData.__init__(
            self,
            content=content,
            name=interface.fullName(),
            abstract=abstract
            )

        if self.closing:
            return

        if isinstance(interface, Vlanable):
            if interface.vlans:
                    vlans = list(vlan for vlan in interface.vlans)
                    vlans.sort()
                    try:
                        message = tr("Configured VLANs: ")
                        abstract.setText(
                            unicode("%s %s" % (message,
                                unicode('<i>%s</i>' % ', '.join(vlan for vlan in vlans))
                                + supplementary_info
                            )
                        ))
                    except RuntimeError, err:
                        print err
                        print dir(abstract)
        elif isinstance(interface, Ethernet):
            if interface.aggregated:
                abstract.setText(self.tr('Aggregated in a bonding') + supplementary_info)
        elif interface.reserved_for_ha:
            abstract.setText(self.tr('Used for the failover setup') + supplementary_info)

