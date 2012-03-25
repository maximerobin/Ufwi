#coding: utf-8
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

from IPy import IP

from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialogButtonBox
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.central_dialog import CentralDialog
from ufwi_conf.common.net_objects_rw import NetRW as Net
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.client.qt.exceptions import InputException
from ufwi_conf.client.qt.input_widgets import OptionnalLine
from ufwi_conf.client.qt.iplist_editor import NetIpListEdit
from ufwi_conf.client.qt.ip_inputs import NetworkEdit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.system.network.qnet_object import QNetObject

def validator(fn):
    """
    Decorator to use when you can tell that another validator will give a useful message
    """
    def wrapper(*args, **kwargs):
        try:
            result = fn(*args, **kwargs)
        except Exception, err:
            if err.args:
                msg = unicode(err.args[0])
            else:
                msg = None
            result = False, msg
        return result
    wrapper.__name__ = "Wrapper/%s" % fn.__name__
    return wrapper


class NetFrame(QFrame):
    def __init__(self, interface, net=None, parent=None):
        QFrame.__init__(self, parent)

        self.interface = None
        self.interface_label = QLabel()
        self.interface_label.setTextFormat(Qt.RichText)
        self.setInterface(interface)

        #synonym for "inside a wizard"
        self.new = net is None
        if self.new:
            net = Net("", IP("0.0.0.0"))

        self.net = net
        self.setWindowTitle(tr("Editing network %s") % self.net.label)

        self.net_ip = NetworkEdit(self, accept_empty=False)

        net_ip_text = "" if self.new else unicode(self.net.net)
        self.net_ip.setText(net_ip_text)

        self.ip_addrs = NetIpListEdit(self.net)

        self.inputs = (self.net_ip, self.ip_addrs)

        self.net_label = OptionnalLine(value=self.net.label, hint=tr('network label'))
        self.net_label.setWhatsThis("<h3>%s</h3>" % tr('Enter a label for this network'))

        self.message_area = MessageArea()
        self.message_area.setWordWrap()

        form = QFormLayout(self)
        form.addRow(tr("Supporting interface"), self.interface_label)
        form.addRow(tr("Network address"), self.net_ip)
        form.addRow(tr("IP addresses on this network"), self.ip_addrs)
        form.addRow(tr("Network label"), self.net_label)
        form.addRow(self.message_area)

        for item in self.inputs + (self.net_label,):
            self.connect(item, SIGNAL('editing done'), self.isValid)

        self.connect(self.net_label, SIGNAL("textChanged(QString)"), self.changeTitle)

    def setInterface(self, interface):
        self.interface = interface
        if interface is None:
            name = tr("unset")
        else:
            name = interface.fullName()
        self.interface_label.setText("<i>%s</i>" % name)

    def changeTitle(self, *args):
        """
        just discarding args after 'self'
        """
        self.emit(SIGNAL('change title'), unicode(self.net_label.value()).strip())

    @validator
    def _validNetIp(self):
        ok, msg = self.net_ip.isValidWithMsg()
        if not ok:
            err = "Network address field is incorrectly specified:<br/>%s"
            return False, tr(err) % msg
        return True, None

    @validator
    def _validIpAddrs(self):
        ok, msg = self.ip_addrs.isValidWithMsg(accept_empty=True)
        if not ok:
            #investigate
            try:
                self.ip_addrs.values()
            except InputException, err:
                return False, err.args[0]

            error_message = tr("IP addresses are incorrectly specified:")
            error_message += "<br/>%s" % msg
            return False, error_message
        return True, None

    @validator
    def _validCoherence(self):
        ip_supplied = False
        net_def = self.net_ip.value()
        all_ips = self.ip_addrs.values()
        for ip in all_ips['service'] | all_ips['primary'] | all_ips['secondary']:
            ip_supplied = True
            if not net_def.overlaps(ip):
                return False, tr("Not all IP addresses belong to the specified network (for instance %s)") % unicode(ip)
        if ip_supplied:
            return True, None

        return False, tr("Please specify at least one IP address")

    @validator
    def _validNet(self):
        net = Net("", IP("0.0.0.0")) #a default net
        self._setValues(net)
        ok, msg = net.isValidWithMsg()
        return ok, msg

    def getNet(self):

        if not self.isValid():
            raise NetCfgError("Invalid values")

#        net_ip = self.net_ip.value()
#        label = self.net_label.value()
#        if label == '':
#            label = unicode(net_ip)
#        self.net.label = label
#        self.net.net = net_ip
#
#        ip_addrs = self.ip_addrs.values()
#        self.net.primary_ip_addrs = ip_addrs['primary']
#        self.net.secondary_ip_addrs = ip_addrs['secondary']
#        self.net.service_ip_addrs = ip_addrs['service']
        self._setValues(self.net)
        return self.net

    def _setValues(self, net):
        net_ip = self.net_ip.value()
        label = self.net_label.value()
        if label == '':
            label = unicode(net_ip)
        net.label = label
        net.net = net_ip
        ip_addrs = self.ip_addrs.values()
        net.primary_ip_addrs = ip_addrs['primary']
        net.secondary_ip_addrs = ip_addrs['secondary']
        net.service_ip_addrs = ip_addrs['service']

    def isValid(self):
        global_ok = True
        messages = []
        validators = (
            self._validNet,
            self._validNetIp,
            self._validIpAddrs,
            self._validCoherence
            )
        for validate in validators:
            ok, message = validate()
            global_ok &= ok
            if message is not None:
                messages.append(unicode(message))

            if not global_ok:
                break

        if global_ok:
            title = self.tr("Information")
            message = tr("Valid settings")
            status = MessageArea.INFO
        else:
            title = self.tr("Input error")
            message = '<ul>%s</ul>' % "".join('<li>%s</li>' % message for message in messages)
            status = MessageArea.WARNING

        if global_ok:
            # search if another interface have a net which overlaps
            netcfg = QNetObject.getInstance().netcfg
            current_net = self.net_ip.value()
            for iface in netcfg.iterInterfaces():
                if iface.unique_id != self.interface.unique_id:
                    ret, net = self.isNetInInterface(iface, current_net)
                    if ret:
                        global_ok = False
                        message = tr("Interface '%s' has a '%s' network which overlaps '%s'") % (iface.fullName(), net.strNormal(), current_net.strNormal())
                        status = MessageArea.WARNING
                        self.message_area.message.setWordWrap(True)
                        break

        self.message_area.setMessage(
            title,
            message,
            status=status
            )

        return global_ok

    def isNetInInterface(self, iface, net):
        """
        search if net overlap a network defined on interface iface
        return True, net or False, None
        """
        for net_iface in iface.nets:
            if net.overlaps(net_iface.net):
                return True, net_iface.net
        return False, None

class NetEditorHelp(QMessageBox):
    def __init__(self, parent=None):
        QMessageBox.__init__(self, parent)
        info_text = self._info_text()
        self.setInformativeText(info_text)
        self.setIcon(QMessageBox.Information)

    def _info_text(self):
        text0 = tr("In this dialog, you can define the configuration of a network for your EdenWall appliance or your EdenWall cluster.")

#        text1 = """
#        A network configuration consists of a network address.
#        Equivalent examples: 192.168.0.0/24 or 192.168.0/255.255.255.
#        """

        return text0

class NetEditor(CentralDialog):
    def __init__(self, interface, net=None, parent=None):
        CentralDialog.__init__(self, parent)

        self.net=net
        self.interface = interface

        self.editor = NetFrame(interface, net=net)
        #easy accessors
        self.net_label = self.editor.net_label
        self.ip_addrs = self.editor.ip_addrs
        self.net_ip = self.editor.net_ip

        button_box = QDialogButtonBox()
        button_box.setStandardButtons(QDialogButtonBox.Cancel|QDialogButtonBox.Ok |QDialogButtonBox.Help)
        self.ok_button = button_box.Ok
        self.connectButtons(button_box)

        #layout
        box = QVBoxLayout(self)
        box.addWidget(self.editor)
        box.addWidget(button_box)

        self.connect(self.editor, SIGNAL("change title"), self.changeTitle)
        self.editor.changeTitle()

        self.acceptableInput()

    def help_action(self):
        help_dialog = NetEditorHelp(self)
        help_dialog.show()

    def getNet(self):
        return self.editor.getNet()

    def changeTitle(self, value):
        self.setWindowTitle(tr("Editing network %s on %s") % (value, self.interface.fullName()))

    def acceptableInput(self):
        return self.editor.isValid()

