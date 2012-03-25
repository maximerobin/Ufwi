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
from PyQt4.QtGui import (QCheckBox, QComboBox, QFormLayout, QFrame,
    QHBoxLayout, QLabel, QLineEdit)

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.input_widgets import RemButton

from ufwi_conf.client.qt.ip_inputs import NetworkCombo
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.system.network import QNetObject
from ufwi_conf.client.system.network.network_models_names import \
    MODEL_NETWORKS_IPV4_EXCL_HA_SER_PRI_SEC, MODEL_NETWORKS_IPV4_EXCL_HA

if EDENWALL:
    from ufwi_conf.common.dhcpcfg import DHCPRange
    from ufwi_conf.common.dhcpcfg import UNSET
    from ufwi_conf.common.dhcp_exceptions import DHCPError
    from ufwi_conf.common.dhcp_exceptions import MissingData
    from ufwi_conf.client.system.ha import QHAObject

from .changes_handling import accept_translation
from .changes_handling import accept_suppression
from .changes_handling import _IGNORE
from .changes_handling import _DELETE_RANGE

_DEFAULT_TEXT = tr(
"Default value if unset : an IP address of the appliance."
)

def _get_optionnal_field(checkbox, field):
    """
    Checkbox: commanding the field
    Field: QLineEdit
    """
    if checkbox.isChecked():
        return unicode(field.text())
    return UNSET

def _fill_optional_field(checkbox, field, value):
    """
    returns
    Checkbox: commanding the field
    Field: QLineEdit
    """
    if value:
        field.setText(value)
        checkbox.setChecked(Qt.Checked)
        field.setEnabled(True)
        return
    field.setText(_DEFAULT_TEXT)
    checkbox.setChecked(Qt.Unchecked)
    field.setEnabled(False)

def _has_not_changed(dhcprange):
    """
    the range still matches its net
    """
    try:
        # In case start and end ip aren't valid, no need
        # to check if they match the network
        IP(dhcprange.start)
        IP(dhcprange.end)
    except ValueError:
        return True

    return all(
        dhcprange.net.net.overlaps(ip)
        for ip in (dhcprange.start, dhcprange.end)
        )

def _make_optional_ip(text):
    custom_ip = QCheckBox(text)
    custom_ip.setLayoutDirection(Qt.RightToLeft)
    address = QLineEdit()
    custom_ip.connect(custom_ip, SIGNAL("toggled(bool)"), address.setEnabled)

    def toggle_field(enabled):
        if enabled:
            if unicode(address.text()) == _DEFAULT_TEXT:
                if address.last_known is None:
                    address.clear()
                else:
                    address.setText(address.last_known)
            return
        address.last_known = address.text()
        address.setText(_DEFAULT_TEXT)

    address.toggle_field = toggle_field
    address.last_known = None

    custom_ip.connect(custom_ip, SIGNAL("toggled(bool)"), address.toggle_field)
    style =  u'QLineEdit::disabled {background: #ccc; font: italic;}'
    address.setStyleSheet(style)
    return custom_ip, address

class RangeFrontend(QFrame):
    def __init__(self, dhcprange=None, parent=None):
        QFrame.__init__(self, parent)
        if not EDENWALL:
            return

        #widgets
        self.__net_choice = None
        self.__start = None
        self.__end = None
        self.__custom_dns = None
        self.__dns_address = None
        self.__custom_router = None
        self.__router_address = None
        self.__message = None
        self.__rembutton = None

        self.q_netobject = QNetObject.getInstance()
        ha_object = QHAObject.getInstance()

        self._nets_source_model = \
            MODEL_NETWORKS_IPV4_EXCL_HA_SER_PRI_SEC if ha_object.has_ha() \
            else MODEL_NETWORKS_IPV4_EXCL_HA

        #__setup_gui will create self.__net_choice, automatically filled with nets
        #and we need a net to build a blank range
        self.__setup_gui()

        if dhcprange is None:
            net = self.__net_choice.getNet()
            dhcprange = DHCPRange(UNSET, UNSET, UNSET, UNSET, net)
        self.dhcprange = dhcprange
        self.__fill()
        self.__validate()
        self.__connect_signals()

    def __setup_gui(self):
        self.setFrameStyle(QFrame.StyledPanel)
        base_hbox = QHBoxLayout(self)

        form = self.__make_form()
        base_hbox.addLayout(form)

        self.__rembutton = RemButton()
        base_hbox.addWidget(self.__rembutton)

    def __connect_signals(self):
        self.q_netobject.registerCallbacks(
            self.__acceptNetworkChange,
            self.__handleNetworkChange,
            attach=self
            )
        for widget in (
            self.__start,
            self.__end,
            self.__custom_dns,
            self.__custom_router,
            self.__dns_address,
            self.__router_address,
            self.__net_choice
            ):
            self.__watch_modification(widget)

        self.connect(self.__rembutton, SIGNAL('clicked()'), self.__delete)
        self.connect(
            self.q_netobject.models[self._nets_source_model],
            SIGNAL('reset()'),
            self.__select_net
            )

    def __acceptNetworkChange(self):

        #The combobox is likely to have been reset
        self.__select_net()

        if not self.dhcprange.net in self.q_netobject.cfg.iterNetworks(
            include_ha=False,
            version=4
            ):
            return accept_suppression(self.dhcprange, self)
        elif _has_not_changed(self.dhcprange):
            return True, _IGNORE
        else:
            return accept_translation(
                self.dhcprange,
                self,
                self.__custom_dns.isChecked()
                )

    def __handleNetworkChange(self, *directive_and_data):
        """
        react to changes by q_netobject
        """

        directive = directive_and_data[0]

        if directive == _IGNORE:
            self.__modified()
            return
        elif directive == _DELETE_RANGE:
            self.__delete()
            return
        #directive == _TRANSLATE
        translation = directive_and_data[1]
        self.dhcprange.start = translation['start']
        self.dhcprange.end = translation['end']
        self.dhcprange.router = translation['router']
        self.__fill()
        self.__modified()


    def __watch_modification(self, widget):
        if isinstance(widget, QCheckBox):
            signal = SIGNAL('toggled(bool)')
        elif isinstance(widget, QLineEdit):
            signal = SIGNAL('textEdited(QString)')
            self.connect(widget, SIGNAL('editingFinished()'), self.__fill)
        elif isinstance(widget, QComboBox):
            signal = SIGNAL('activated(int)')
        self.connect(widget, signal, self.__modified)

    def __modified(self):
        """
        triggered when the range is modified
        """
        self.__report_data()
        self.__validate()
        self.emit(SIGNAL("modified"))

    def __delete(self):
        """
        triggered when the range is deleted
        """
        self.emit(SIGNAL("deleted"), self)
        self.close()

    def close(self):
        self.q_netobject.forget(self)
        QFrame.close(self)

    def __fill(self):
        self.__start.setText(self.dhcprange.getStartText())
        self.__end.setText(self.dhcprange.getEndText())
        _fill_optional_field(
            self.__custom_dns,
            self.__dns_address,
            self.dhcprange.getDnsText()
            )
        _fill_optional_field(
            self.__custom_router,
            self.__router_address,
            self.dhcprange.getRouterText()
            )
        self.__select_net()

    def __select_net(self):
        self.__net_choice.selectNet(self.dhcprange.net)
        self.dhcprange.net = self.__net_choice.getNet()

    def __report_data(self):
        """
        put the data from the frontend into the object
        """
        self.dhcprange.net = self.__net_choice.getNet()
        self.dhcprange.setStart(
            unicode(self.__start.text())
            )
        self.dhcprange.setEnd(
            unicode(self.__end.text())
            )

        self.dhcprange.setDns(
            _get_optionnal_field(self.__custom_dns, self.__dns_address)
            )

        self.dhcprange.setRouter(
            _get_optionnal_field(self.__custom_router, self.__router_address)
            )

    def __validate(self):
        try:
            self.dhcprange.isValid()
        except MissingData, err:
            self.__message.warning(
                tr("Incomplete data"),
                err.args[0]
                )
            self.__message.show()
        except DHCPError, err:
            self.__message.warning(
                tr("Erroneous data"),
                err.args[0]
                )
            self.__message.show()
        else:
            self.__message.hide()

    def __make_form(self):
        form = QFormLayout()

        range_title = QLabel(
            "<span><h3><i>%s</i></h3></span>" % tr("DHCP range")
            )
        form.addRow(range_title)

        self.__net_choice = NetworkCombo(modelname=self._nets_source_model)
        form.addRow(
            tr("Network"),
            self.__net_choice
            )

        self.__start = QLineEdit()
        form.addRow(tr("Start"), self.__start)

        self.__end = QLineEdit()
        form.addRow(tr("End"), self.__end)


        self.__custom_dns, self.__dns_address = _make_optional_ip(
            tr("Specify a DNS server")
            )
        form.addRow(self.__custom_dns, self.__dns_address)

        self.__custom_router, self.__router_address = _make_optional_ip(
            tr("Specify a router")
            )
        form.addRow(self.__custom_router, self.__router_address)

        self.__message = MessageArea()
        form.addRow(self.__message)

        return form


