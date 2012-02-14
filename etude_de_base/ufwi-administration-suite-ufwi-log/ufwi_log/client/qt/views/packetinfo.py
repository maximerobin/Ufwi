# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

from PyQt4.QtGui import QWidget, QTreeWidgetItem
from PyQt4.QtCore import SIGNAL
from base import BaseFragmentView
import re

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.ui.packetinfo_ui import Ui_PacketInfoFragment
from ufwi_log.client.qt.args import arg_types
from ufwi_log.client.qt.args.argdata import ArgDataAcl
from ufwi_log.client.qt.tools import createLink

class PacketInfoFragmentView(BaseFragmentView, QWidget):

    @staticmethod
    def name(): return tr('the packet info view')

    def __init__(self, fetcher, parent):

        QWidget.__init__(self, parent)
        self.pwdidget = parent
        self.ui = Ui_PacketInfoFragment()
        self.ui.setupUi(self)
        self.ui.userGroup.setVisible(False)
        BaseFragmentView.__init__(self, fetcher)

    def getTitle(self):
        if self.fetcher.args.has_key('packet_id'):
            return unicode(self.tr('Information for packet #%s')) % self.fetcher.args['packet_id']
        else:
            return unicode('')

    def setACL(self, acl):
        self.acl_label = ArgDataAcl(None, acl['value'], self.fetcher)
        self.ui.permission_layout.addWidget(self.acl_label.label)
        self.connect(self.acl_label, SIGNAL('EAS_Message'), self.pwdidget.EAS_SendMessage)

    def closeEvent(self, event):
        self.connect(self.acl_label, SIGNAL('EAS_Message'), self.pwdidget.EAS_SendMessage)

    def updateData(self, result):
        if self.is_closed:
            return

        self.result = result
        self.ui.flagstree.clear()

        if ":" in self.result['oob_prefix']:
            self.result['oob_prefix'] = self.result['oob_prefix'].split(':')[1]

        arg_data = arg_types['oob_time_sec'].data('oob_time_sec', self.result['oob_time_sec'])
        self.ui.timestamp.setText(arg_data.label)

        self.ui.state.setStyleSheet('background-color: %s;' % self.state_colours[int(self.result['raw_label'])])
        arg_data = arg_types['raw_label'].data('raw_label', self.result['raw_label'])
        self.ui.state.setText(arg_data.label.upper())


        if self.result['username']:
            self.ui.userGroup.setVisible(True)
            self.ui.username.setText(self.result['username'])
            self.ui.client_app.setText(self.result['client_app'])
            self.ui.client_os.setText(self.result['client_os'])
        else:
            self.ui.userGroup.setVisible(False)

        self.ui.ifin.setText(self.result['oob_in'])
        self.ui.ifout.setText(self.result['oob_out'])
        self.ui.logprefix.setText(self.result['oob_prefix'])
        self.ui.mark.setText(self.result['oob_mark'])
        self.ui.IPsrc.setText(self.result['ip_saddr_str'])
        self.ui.IPdst.setText(self.result['ip_daddr_str'])

        if self.result['proto'] == 'icmp' and self.result['icmp_type']:
            self.ui.icmpGroup.setVisible(True)
            self.ui.protoGroup.setVisible(False)
            self.ui.icmpType.setText(self.result['icmp_type'])
            self.ui.icmpCode.setText(self.result['icmp_code'])
        else:
            self.ui.icmpGroup.setVisible(False)
            self.ui.protoGroup.setVisible(True)
            self.ui.portsrc.setText(self.result['sport'])
            self.ui.portdst.setText(self.result['dport'])
            self.ui.protoGroup.setTitle(unicode(self.tr('%s protocol')) % self.result['proto'].upper())

        if (('mac_saddr_str' in self.result) and ('mac_daddr_str' in self.result)) \
        and (self.result['mac_saddr_str'] != '' or self.result['mac_daddr_str'] != ''):
            item = QTreeWidgetItem(self.ui.flagstree, [self.tr('Ethernet'), ''])
            self.ui.flagstree.addTopLevelItem(item)
            if self.result['mac_saddr_str'] != '':
                item.addChild(QTreeWidgetItem(item, [self.tr('Mac src'), self.result['mac_saddr_str']]))
            if self.result['mac_daddr_str'] != '':
                item.addChild(QTreeWidgetItem(item, [self.tr('Mac dest'), self.result['mac_daddr_str']]))

        if self.result['packets_in'] != '0' and self.result['bytes_in'] != '0':
            item = QTreeWidgetItem(self.ui.flagstree, [self.tr('Accounting'), ''])
            self.ui.flagstree.addTopLevelItem(item)
            item.addChild(QTreeWidgetItem(item, [self.tr('Connections In'), self.result['packets_in']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Connections Out'), self.result['packets_out']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Bytes In'), self.result['bytes_in']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Bytes Out'), self.result['bytes_out']]))

        if self.result['ip_id']:

            item = QTreeWidgetItem(self.ui.flagstree, [self.tr('IP headers'), ''])
            self.ui.flagstree.addTopLevelItem(item)
            item.addChild(QTreeWidgetItem(item, [self.tr('TOS'),          self.result['ip_tos']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('TTL'),          self.result['ip_ttl']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Total length'), self.result['ip_totlen']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Header length'),self.result['ip_ihl']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Checksum'),     self.result['ip_csum']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('Packet Id'),    self.result['ip_id']]))

        if self.result['proto'] == 'tcp' and self.result['tcp_seq']:

            item = QTreeWidgetItem(self.ui.flagstree, [self.tr('TCP headers'), ''])
            self.ui.flagstree.addTopLevelItem(item)
            item.addChild(QTreeWidgetItem(item, [self.tr('Seq Number'),        self.result['tcp_seq']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('ACK Number'),        self.result['tcp_ackseq']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('TCP Window'),        self.result['tcp_window']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('URG'),               self.result['tcp_urg']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('URGP'),              self.result['tcp_urgp']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('ACK'),               self.result['tcp_ack']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('PSH'),               self.result['tcp_psh']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('RST'),               self.result['tcp_rst']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('SYN'),               self.result['tcp_syn']]))
            item.addChild(QTreeWidgetItem(item, [self.tr('FIN'),               self.result['tcp_fin']]))

