"""
$Id$
"""
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


from functools import partial

from PyQt4.QtCore import SIGNAL
from PyQt4.QtCore import Qt
from PyQt4.QtGui import QAbstractItemView, QWidget
from PyQt4.QtGui import QHeaderView

from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcc_qt.colors import COLOR_FANCY, COLOR_WARNING
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.toolbar import ToolBar
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
if EDENWALL:
    from ufwi_conf.common.site2site_cfg import Site2SiteCfg

from .models import RSA_FINGERPRINT
from .models import RSAModel
from .models import RSA_NAME
from .models import RSA_PEER
from .models import VPN_EDIT
from .models import VPNEditDelegate
from .models import VPN_ENABLE
from .models import VPNEnableDelegate
from .models import VPN_GATEWAY
from .models import VPN_IDENTIFIER
from .models import VPN_NET_LOCAL
from .models import VPN_NET_REMOTE
from .models import VPNsModel
from .models import VPN_STATUS
from .site2site_ui import Ui_site2site

class Site2SiteFrontend(FullFeaturedScrollArea):
    COMPONENT = 'site2site'
    LABEL = tr('Site to site VPN')
    REQUIREMENTS = ('site2site',)
    ICON = ':/icons/vpn.png'

    def __init__(self, client, parent=None):
        self.__disabled = False
        self.cached_states = None
        if not EDENWALL:
            raise NuConfModuleDisabled("Site2site")
        FullFeaturedScrollArea.__init__(self, client, parent)

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (('site2site', 'getConfig'), ('site2site', 'vpnstates'))

    def __stretch_id_cols(self):
        vpn_hh = self.ui.VPNtable.horizontalHeader()
        for column in (
            VPN_STATUS,
            VPN_ENABLE,
            VPN_GATEWAY,
            VPN_NET_LOCAL,
            VPN_NET_REMOTE,
            VPN_EDIT):
            vpn_hh.setResizeMode(column, QHeaderView.ResizeToContents)

        vpn_hh.setResizeMode(VPN_IDENTIFIER, QHeaderView.Stretch)

        rsa_hh = self.ui.RSAtable.horizontalHeader()
        rsa_hh.setResizeMode(RSA_NAME, QHeaderView.Stretch)
        for column in (
            RSA_FINGERPRINT,
            RSA_PEER):
            rsa_hh.setResizeMode(column, QHeaderView.ResizeToContents)

    def __disable(self, title, message):
        if self.__disabled:
            return
        message_area = MessageArea()
        message_area.setMessage(
            title,
            message,
            "critical"
        )
        self.setWidget(message_area)
        self.__disabled = True

    def buildInterface(self):
        if self.__disabled:
            return

        self.ui = Ui_site2site()
        self.widget = QWidget(self)
        self.ui.setupUi(self.widget)
        self.setWidget(self.widget)
        self.setWidgetResizable(True)

        self.contextual_toolbar = ToolBar(
            (
                self.ui.actionRefresh_VPN_states,
            ),
            name=tr("Site2site")
            )
        self.mainwindow.writeAccessNeeded(self.ui.enableVPN, self.ui.addVPN,
            self.ui.delVPN, self.ui.VPNtable, self.ui.RSAtable, self.ui.addRSA,
            self.ui.delRSA)


        self.__rsamodel = RSAModel(self)
        self.ui.RSAtable.setModel(self.__rsamodel)

        self.__vpnmodel = VPNsModel(self.__rsamodel, self)
        self.ui.VPNtable.setModel(self.__vpnmodel)

        for table in (self.ui.VPNtable, self.ui.RSAtable):
            table.setEditTriggers(QAbstractItemView.AllEditTriggers)
            table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)
            #XXX doesn't work? for ui.VPNtable while alternate:
            table.verticalHeader().setHighlightSections(False)
            table.setSelectionBehavior(QAbstractItemView.SelectRows)
            table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.__stretch_id_cols()

        self.__connect()

    def setViewData(self):
        if self.__disabled:
            return

        self.ui.myfingerprint.setPlainText(self.config.myfingerprint)

        for model in self.__rsamodel, self.__vpnmodel:
            model.reset()
            #model.emit(SIGNAL("modelReset()"))

        self.ui.enableVPN.setChecked(self.config.enabled)
        enable_delegate = VPNEnableDelegate(self.ui.VPNtable)
        self.ui.VPNtable.setItemDelegateForColumn(VPN_ENABLE, enable_delegate)
        for index in self.__vpnmodel.iterIndexes(restrictcolumn=VPN_ENABLE):
            self.ui.VPNtable.openPersistentEditor(index)

        edit_delegate = VPNEditDelegate(self.__rsamodel, self.ui.VPNtable)
        self.ui.VPNtable.setItemDelegateForColumn(VPN_EDIT, edit_delegate)

        #The button that allows for edition is an active element
        for index in self.__vpnmodel.iterIndexes(restrictcolumn=VPN_EDIT):
            self.ui.VPNtable.openPersistentEditor(index)

        self.ui.delVPN.setEnabled(self.__vpnmodel.rowCount(self.ui.VPNtable.rootIndex()) > 0)
        self.ui.delRSA.setEnabled(self.__rsamodel.rowCount(self.ui.RSAtable.rootIndex()) > 0)
        if self.cached_states is not None:
            self.__vpnmodel.update_states(self.cached_states)

    def __connect(self):
        self.connect(self.ui.enableVPN, SIGNAL('clicked()'), self.setEnable)
        for model in (self.__rsamodel, self.__vpnmodel):
            self.connect(model, SIGNAL('dataChanged(QModelIndex,QModelIndex)'), partial(self.setModified, True))
        self.connect(self.ui.addVPN, SIGNAL('clicked()'), self.append_vpn)
        self.connect(self.ui.addRSA, SIGNAL('clicked()'), self.append_rsa)
        self.connect(self.ui.delRSA, SIGNAL('clicked()'), self.delete_rsa)
        self.connect(self.ui.delVPN, SIGNAL('clicked()'), self.delete_vpn)
        self.connect(self.__rsamodel, SIGNAL('candelete'), self.ui.delRSA.setEnabled)
        self.connect(self.__vpnmodel, SIGNAL('candelete'), self.ui.delVPN.setEnabled)
        for model in (self.__rsamodel, self.__vpnmodel):
            self.connect(model, SIGNAL("modified"), self.setModified)

        self.connect(self.ui.actionRefresh_VPN_states, SIGNAL('triggered(bool)'), self.refresh_vpn_states)

    def refresh_vpn_states(self, bool):
        async = self.client.async()
        async.call('site2site', 'vpnstates',
            callback=self._vpnstates_ok,
            errback=self._vpnstates_err
            )

    def _vpnstates_ok(self, value):
        self.mainwindow.addToInfoArea(
            tr(
                "Successfully updated the VPNs states.",
                "displayed in ufwi_conf info area"
              ),
            category=COLOR_FANCY
            )
        self.__vpnmodel.update_states(value)

    def _vpnstates_err(self, err):
        self.mainwindow.addToInfoArea(
            tr("Could not fetch the VPNs states. Error is:") + unicode(err),
            category=COLOR_WARNING
            )

    def setEnable(self):
        self.setModified()
        self.config.enabled = self.ui.enableVPN.isChecked()

    def append_rsa(self):
        self.__appenditem(self.ui.RSAtable, self.__rsamodel)

    def delete_rsa(self):
        self.__deleteitem(self.ui.RSAtable, self.__rsamodel)

    def delete_vpn(self):
        self.__deleteitem(self.ui.VPNtable, self.__vpnmodel)

    def append_vpn(self):
        row = self.__appenditem(self.ui.VPNtable, self.__vpnmodel)
        if row < 0:
            return
        for column in (VPN_EDIT, VPN_ENABLE):
            editor_index = self.__vpnmodel.createIndex(row, column)
            self.ui.VPNtable.openPersistentEditor(editor_index)
        #FIXME: dirty workaround, do something nicer if possible.
        #The problem is that either:
        # * we do nothing and columns are not properly resized
        # * we resize columns and some widgets are not repainted until
        #   the user changes the focus to another page/window and comes back
        #and no, repaint() is not working as expected.
        self.ui.VPNtable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOn)
        self.ui.VPNtable.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.ui.VPNtable.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)

    def __deleteitem(self, table, model):
        indexes = table.selectedIndexes()
        if len(indexes) == 0:
            return

        #only one column selected, see selection mode
        row = indexes[0].row()
        model.removeRow(row)

    def __appenditem(self, table, model):
        index = table.rootIndex()
        row = model.rowCount(index)
        if model.insertRow(row, index):
            table.selectRow(row)
            return row
        return -1

    def fetchConfig(self):
        deserialized = self.mainwindow.init_call('site2site', 'getConfig')
        if deserialized is None:
            self.mainwindow.addToInfoArea(tr("Could not fetch a configuration for site to site VPN (IPsec)"), category=COLOR_WARNING)
            self.__disable(
                tr("Page disabled"),
                tr("Error while loading site to site VPN (IPsec) configuration.")
                )
            return

        try:
            self.config = Site2SiteCfg.deserialize(deserialized)
        except DatastructureIncompatible, error:
            if error.server_more_recent:
                message = tr("Client-server version mismatch, the appliance version is more recent than the client version.")
            else:
                message = tr("Client-server version mismatch, the client version is more recent than the appliance version.")
            self.__disable(
                tr("Page disabled"),
                message
                )
            raise

        self.cached_states = self.mainwindow.init_call('site2site', 'vpnstates')

    def sendConfig(self, message):
        if self.__disabled:
            return
        serialized = self.config.serialize()
        self.client.call('site2site', 'setConfig', serialized, message)

    def isValid(self):
        ok, msg = self.config.isValidWithMsg()
        if not ok:
            self.mainwindow.addToInfoArea("%s %s" % ("[Site to site VPN]", msg), category=COLOR_WARNING)
        return ok

