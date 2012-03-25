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
from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QCheckBox, QFormLayout, QFrame, QLabel, QMessageBox

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common import tr
from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcc_qt.colors import COLOR_CRITICAL
from ufwi_rpcc_qt.html import htmlList
from ufwi_rpcc_qt.input_widgets import AddButton

from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.system.network import QNetObject

if EDENWALL:
    from ufwi_conf.common.dhcpcfg import ENABLED, DISABLED, deserialize, DHCPRange, UNSET

from .adjust import adjust_ip
from .dhcprange import RangeFrontend as NewRangeFrontend

def _valuefromrouter(router):
    value = DHCPRange.ip_or_unset(router)
    if isinstance(value, (unicode, str)) and router == UNSET:
        return tr("No gateway set.")
    return value

class DhcpFrontend(ScrollArea):
    COMPONENT = 'dhcp'
    LABEL = tr('DHCP service')
    REQUIREMENTS = ('dhcp',)
    ICON = ':/icons/computeur.png'

    def __init__(self, client, parent=None):
        ScrollArea.__init__(self)

        if not EDENWALL:
            raise NuConfModuleDisabled("DHCP")

        self.error_message = tr("Incorrect DHCP specification")
        self.client =  client
        self.main_window = parent
        self.q_netobject = QNetObject.getInstance()

        # detect when DHCP backend is unavailable : raise NuConfModuleDisabled
        try:
            self.main_window.init_call("dhcp", "getDhcpConfig")
        except RpcdError:
            #dhcp module was not available, server side
            self.main_window.addToInfoArea(tr("DHCP interface disabled: DHCP backend not loaded"),
                category=COLOR_CRITICAL)
            raise NuConfModuleDisabled("DHCP")
        else:
            self.main_window.addToInfoArea(tr("DHCP interface enabled"))

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        # getDhcpConfig called in constructor of DhcpFrontend and DHCPWidget
        return ( ("dhcp", 'getDhcpConfig', 2), )

    def isModified(self):
        return self.dhcp_widget.isModified()

    def isValid(self):
        return self.dhcp_widget.isValid()

    def resetConf(self):
        self.loaded()

    def saveConf(self, message):
        self.dhcp_widget.saveConf(message)

    def loaded(self):
        if not EDENWALL:
            return
        self.dhcp_widget = DHCPWidget(self.client, self.main_window, self)
        self.setWidget(self.dhcp_widget)
        self.setWidgetResizable(True)

        self.connect(self.q_netobject, SIGNAL('reset'), self.dhcp_widget.fillView)

class DHCPWidget(QFrame):
    def __init__(self, client, main_window, parent):
        QFrame.__init__(self, parent)
        self._parent = parent
        self._loading = True
        self._modified = False
        self.client = client
        self.main_window = main_window
        self.addToInfoArea = self.main_window.addToInfoArea
        self.q_netobject = QNetObject.getInstance()
#        try:
#            self.q_netobject.registerCallbacks(self.acceptNetworkChange, self.handleNetworkChange)
#        except Exception, err:
#            raise

        self.dhcpcfg = None
        self.range_widgets = set()
        self.drawGUI()
        self.resetConf()
        self._loading = False

    def drawGUI(self):
        form_layout = QFormLayout(self)
        form_layout.setFormAlignment(Qt.AlignLeft)
        title = QLabel(tr("<H1>DHCP Configuration</H1>"))
        form_layout.addRow(title)

        self.enable = QCheckBox(tr("Enable DHCP Server on configured LANs"))
        form_layout.addRow(self.enable)
        self.main_window.writeAccessNeeded(self.enable)

        self.add_button = AddButton()
        self.add_button.setText(tr("Add a range"))
        self.main_window.writeAccessNeeded(self.add_button)
        form_layout.addRow(self.add_button, QLabel())
        if not self.main_window.readonly:
            self.connect(self.enable, SIGNAL('stateChanged(int)'), self.setDHCPEnabled)
            self.connect(self.add_button, SIGNAL('clicked()'), self.addRange)

        self.setLayout(form_layout)

    def addRange(self):
        self.setModified(True)
        self.addRangeFrontend()

    def fetchCfg(self):
        dhcpcfg_repr = self.main_window.init_call("dhcp", "getDhcpConfig")
        if dhcpcfg_repr is None:
            #Failing to fetch dhcp config
            return None
        netcfg = self.q_netobject.netcfg
        if netcfg is None:
            return None
        return deserialize(dhcpcfg_repr, netcfg)

    def setDHCPEnabled(self, state):
        self.setModified(True)
        if state == Qt.Unchecked:
            self.dhcpcfg.enabled = DISABLED
        else:
            self.dhcpcfg.enabled = ENABLED

    def isModified(self):
        return self._modified

    def setModified(self, bool=True):
        if self._loading:
            return
        if bool == True:
            self.main_window.setModified(self._parent, True)
        if self._modified is False and bool is True:
            self.addToInfoArea(tr("DHCP Server configuration edited."))
        self._modified = bool

    def resetConf(self):
        self.dhcpcfg = self.fetchCfg()
        if self.dhcpcfg is None:
            self._clearWidgets()
            msg_area = MessageArea()
            msg_area.setMessage(
                tr("Problem loading the network or dhcp configuration!"),
                tr("A problem occured while loading the network "
                "or dhcp config from the appliance!"),
                "critical"
                )
            self.layout().insertRow(2, msg_area)
            self.enable.setEnabled(False)
            self.add_button.setEnabled(False)
        else:
            self.fillView()
        self._modified = False

    def _clearWidgets(self):
        for widget in self.range_widgets:
            # sometimes the widget stay visible
            widget.close()

        self.range_widgets.clear()

    def fillView(self):
        self._clearWidgets()
        if self.dhcpcfg is None:
            return

        for range in self.dhcpcfg.ranges:
            self.addRangeFrontend(range=range)
        if  self.dhcpcfg.enabled == ENABLED:
            check_state = Qt.Checked
        else:
            check_state = Qt.Unchecked
        self.enable.setCheckState(check_state)

    def addRangeFrontend(self, range=None):
        # called by resetConf so we can access to QNetObject.getInstance().netcfg
        range_widget = NewRangeFrontend(dhcprange=range)

        self.main_window.writeAccessNeeded(range_widget)
        self.range_widgets.add(range_widget)
        self.connect(range_widget, SIGNAL('deleted'), self.delRangeFrontend)
        self.connect(range_widget, SIGNAL('modified'), self.setModified)
        if range is None:
            self.dhcpcfg.ranges.add(range_widget.dhcprange)
        layout = self.layout()
        layout.insertRow(2, range_widget)

        range_widget.setParent(self)

    def getWidgetFromRange(self, range):
        for widget in self.range_widgets:
            if widget.range is range:
                return widget

    def delRangeFrontend(self, range_widget):
        self.dhcpcfg.ranges.discard(range_widget.dhcprange)
        self.range_widgets.discard(range_widget)
        self.setModified(True)

    def isValid(self):
        to_remove = set()
        for range_widget in self.range_widgets:
            dhcprange = range_widget.dhcprange
            if dhcprange not in self.dhcpcfg.ranges or dhcprange.is_fully_unset():
                to_remove.add(range_widget)
                continue
        for range_widget in to_remove:
            self.delRangeFrontend(range_widget)
            range_widget.close()
        return self.dhcpcfg.isValid()

    def saveConf(self, message):
        dhcpcfg_repr = self.dhcpcfg.serialize()
        self.client.call("dhcp", 'setDhcpConfig', dhcpcfg_repr, message)
        self.setModified(False)
        self.addToInfoArea(tr("DHCP server configuration uploaded to server."))

    def acceptNetworkChange(self):
        deletable = set()
        translatable = set()

        translated_ranges = {}

        if self.dhcpcfg is None:
            return True, translated_ranges, deletable

        deletable, translatable = self.dhcpcfg.computeChanges(self.q_netobject.netcfg)

        if not (deletable | translatable):
            #Nothing to do (yay!) we agree with proposed changes
            return True

        #oh, questions arrive
        accept = True
        generic_text = "<h2>%s</h2>" % tr("This change affects the DHCP server configuration")

        #TODO: add questions and return


        for range in translatable:

            if not accept:
                break

            if not isinstance(range.router, IP):
                new_router_ip = UNSET
            else:
                new_router_ip = adjust_ip(range.net.net, range.router)

            widget_range = self.getWidgetFromRange(range)
            simulation = {
                'start': adjust_ip(range.net.net, range.start),
                'end': adjust_ip(range.net.net, range.end),
                'router': new_router_ip,
                'custom_dns': widget_range.custom_dns,
                }

            cur_router = _valuefromrouter(range.router)
            new_router = _valuefromrouter(simulation['router'])

            help_items = []
            help_items.append(tr("Clicking \"Yes\" will change the DHCP range."))
            help_items.append(tr("Clicking \"Ignore\" will not change the DHCP range. Double-check the DHCP server configuration before saving."))
            help_items.append(tr("Clicking \"Cancel\" will cancel your changes to the network configuration"))
            help_text = unicode(htmlList(help_items))

            title = tr("DHCP: Translate a range?")

            html = u"""<table>
                %(title)s<br />
                %(ask)s<br />
                <tr>
                    <td><h2>%(start)s</h2></td>
                    <td>%(cur_start)s</td>
                    <td><img src=":/icons-32/go-next"/></td>
                    <td>%(simu_start)s</td>
                </tr>
                <tr>
                    <td><h2>%(end)s</h2></td>
                    <td>%(cur_end)s</td>
                    <td><img src=":/icons-32/go-next"/></td>
                    <td>%(simu_end)s</td>
                </tr>
                <tr>
                    <td><h2>%(router)s</h2></td>
                    <td>%(cur_router)s</td>
                    <td><img src=":/icons-32/go-next"/></td>
                    <td>%(simu_router)s</td>
                </tr>
            </table>
            """ % {
                'title' : tr("You changed the network address for the '<i>%s</i>' network") % range.net.label,
                'ask' : tr("Do you want to adjust the range?"),
                'start' : tr("Start IP"),
                'cur_start' : range.start,
                'simu_start' : unicode(simulation['start']),
                'end' : tr("End IP"),
                'cur_end' : range.end,
                'simu_end' : unicode(simulation['end']),
                'router' : tr("Router IP"),
                'cur_router' : cur_router,
                'simu_router' : unicode(new_router),
            }

            html += help_text

            message_box = QMessageBox(self)
            message_box.setWindowTitle(title)
            message_box.setText(generic_text)
            message_box.setInformativeText(html)
            message_box.setStandardButtons(
                QMessageBox.Yes | QMessageBox.Ignore | QMessageBox.Cancel
            )

            clicked_button = message_box.exec_()
            accept = clicked_button in (QMessageBox.Yes, QMessageBox.Ignore)
            if clicked_button == QMessageBox.Yes:
                translated_ranges[range] = simulation

        deletable_ranges = frozenset()

        if accept and deletable:
            deletable_tr = tr("Consequence: the following DHCP range will be deleted:")
            deletable_html = u"<ul>"
            for range in deletable:
                deletable_html += "<li>%s %s: %s > %s</li>" % (
                    deletable_tr,
                    unicode(range.net),
                    unicode(range.start),
                    unicode(range.end)
                    )
            deletable_html += u"</ul>"
            title = tr("DHCP configuration")
            message_box = QMessageBox(self)
            message_box.setWindowTitle(title)
            message_box.setText(generic_text)
            message_box.setInformativeText(deletable_html)
            message_box.setStandardButtons(
                QMessageBox.Yes | QMessageBox.Cancel
            )

            clicked_button = message_box.exec_()
            accept = (clicked_button == QMessageBox.Yes)
            if accept:
                deletable_ranges = deletable

        if not accept:
            return False

        return True, translated_ranges, deletable_ranges

    def handleNetworkChange(self, *args):
        if args:
            translated_ranges, deleted_ranges = args

            changed = False
            for range in deleted_ranges:
                self.dhcpcfg.ranges.remove(range)
                changed = True

            for range, translation in translated_ranges.iteritems():
                range.start = translation['start']
                range.end = translation['end']
                range.router = translation['router']
                changed = True

            if changed:
                self.setModified(True)
        self.fillView()

