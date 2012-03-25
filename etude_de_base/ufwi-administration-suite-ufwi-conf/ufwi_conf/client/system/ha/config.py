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

import time

from PyQt4.QtCore import QVariant, SIGNAL
from PyQt4.QtGui import (QAction, QComboBox, QDialog, QFormLayout, QFrame,
    QGridLayout, QIcon, QLabel, QMessageBox, QPushButton, QTextEdit ,QWizard,
    QWizardPage)

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.splash import SplashScreen
from ufwi_rpcc_qt.colors import COLOR_ERROR, COLOR_SUCCESS

from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.ip_inputs import InterfaceChoice
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.timer import Timer
from ufwi_conf.client.qt.toolbar import ToolBar
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
from ufwi_conf.client.system.network.qnet_object import QNetObject
from ufwi_conf.client.system.resolv.qhostname_object import QHostnameObject

if EDENWALL:
    from ufwi_conf.common.ha_statuses import (ENOHA,
        PENDING_PRIMARY, PENDING_SECONDARY, PRIMARY, SECONDARY)
    from ufwi_conf.common.ha_cfg import (ACTIVE, CONNECTED, HAConf, INACTIVE,
        NOT_CONNECTED, NOT_REGISTERED, configureHA, deconfigureHA)

from ufwi_conf.client.system.ha.qha_object import QHAObject

REFRESH_INTERVAL_MILLISECONDS = 15000
MAX_MISSING_UPGRADE_NUMS = 3

def span(text):
    return '<span>%s</span>' % text

class HAConfigFrontend(FullFeaturedScrollArea):
    COMPONENT = 'ha'
    LABEL = tr('High Availability')
    REQUIREMENTS = ('ha',)
    ICON = ':/icons/picto_ha.png'

    if EDENWALL:
        LINK_STATE = {
            NOT_REGISTERED: tr('Not registered'),
            NOT_CONNECTED: tr('Not connected'),
            CONNECTED: tr('Connected'),
        }

        NODE_STATE = {
            NOT_REGISTERED: tr('Not registered'),
            ACTIVE: tr('Active'),
            INACTIVE: tr('Inactive'),
        }

        STATE_DESCRIPTIONS = {
            ENOHA: span(tr('High availability is not configured.')),
            PENDING_PRIMARY: span(tr('Primary; click "Join" to <br/>complete high availability configuration.')),
            PRIMARY: span(tr('Primary, in function.')),
            SECONDARY: span(tr('Secondary, in function.')),
            PENDING_SECONDARY: span(tr('Secondary; connect EAS to the primary server to <br/>complete high availability configuration.')),
        }

    def __init__(self, client, parent):
        self.auth_page = None
        self.group_page = None
        self.auth_configs = {}
        self.group_configs = {}
        self.mainwindow = parent

        self.node_status_label = QLabel()   # status of current node (active / inactive)
        self.link_status_label = QLabel() # status of dedicaced link
        self.interface_label = QLabel()
        self.activity_label = QLabel()
        self.last_error_text = QTextEdit()
        self.last_error_text.setReadOnly(True)
        self.last_error_text.setMaximumHeight(100)
        self.type_label = QLabel()
        self.join = None

        self.link_state = None
        self.ha_last_date = None

        self.version = self.mainwindow.init_call('ha', 'getComponentVersion')

        FullFeaturedScrollArea.__init__(self, client, parent)
        self.missing_upgrades = []

        # create timer only if HA activated
        if self.__ha_type() != ENOHA:
            self.timer = Timer(
                self.setViewData,
                REFRESH_INTERVAL_MILLISECONDS,
                self.mainwindow.keep_alive.thread,
                self
                )
        else:
            self.timer = None

        self.force_join = QAction(QIcon(":/icons/force_join"), tr("Force joining secondary"), self)
        self.connect(self.force_join, SIGNAL('triggered(bool)'), self.joinSecondary)
        self.force_takeover = QAction(QIcon(":/icons/ha_takeover"), tr("Force to become active"), self)
        self.connect(self.force_takeover, SIGNAL('triggered(bool)'), self.takeover)

        buttons = [self.force_join, self.force_takeover]
        self.contextual_toolbar = ToolBar(buttons, name=tr("High Availability"))

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (('ha', 'getState'), ('ha', 'getFullState'),
            ('ha', 'getComponentVersion'))

    def __ha_type(self):
        config = QHAObject.getInstance().cfg
        if config is None:
            return ENOHA
        return config.ha_type

    def buildInterface(self):
        frame = QFrame()
        self.setWidget(frame)
        self.setWidgetResizable(True)
        layout = QGridLayout(frame)

        title = u'<h1>%s</h1>' % self.tr('High Availability Configuration')
        layout.addWidget(QLabel(title), 0, 0, 1, -1)

        configure = QPushButton(QIcon(":/icons/configurationha.png"), tr('Configure'))
        self.mainwindow.writeAccessNeeded(configure)
        layout.addWidget(configure, 1, 3)

        self.join = QPushButton(QIcon(":/icons/joinha.png"), tr('Join Secondary'))
        layout.addWidget(self.join, 2, 3)

        if "1.1" == self.version:
            layout.addWidget(QLabel(tr('Appliance status')), 3, 0)
            layout.addWidget(self.node_status_label, 3, 1)
            row = 4
        else:
            row = 3

        self.last_error_title = QLabel(tr('Last error'))
        self.missing_upgrade_text_label = QLabel()
        self.missing_upgrade_nums_label = QLabel()
        widgets = [
            (QLabel(tr('Link status')), self.link_status_label),
            (QLabel(tr('Type')),self.type_label),
            (QLabel(tr('Interface')),self.interface_label),
            (QLabel(tr('Last activity')), self.activity_label),
            (self.last_error_title, self.last_error_text),
            (self.missing_upgrade_text_label, self.missing_upgrade_nums_label),
        ]

        for index, (label, widget) in enumerate(widgets):
            layout.addWidget(label, row+index, 0)
            layout.addWidget(widget, row+index, 1)

        # syncUpgrades_button = QPushButton(tr('Synchronize upgrades'))
        # layout.addWidget(syncUpgrades_button, 7, 2)
        # self.connect(syncUpgrades_button, SIGNAL('clicked()'), self.syncUpgrades)

        layout.setColumnStretch(0,  1)
        layout.setColumnStretch(1,  5)
        layout.setColumnStretch(2, 10)
        layout.setColumnStretch(3,  1)
        layout.setRowStretch(row+6, row+7)
        self.connect(configure, SIGNAL("clicked()"), self.displayConfig)
        self.connect(self.join, SIGNAL("clicked()"), self.joinSecondary)

    def displayConfig(self):
        config = QHAObject.getInstance().hacfg
        if config.ha_type == PRIMARY:
            QMessageBox.warning(
                self,
                tr('High availability already configured'),
                tr('High availability status disallows editing the configuration'))
            return

        ha_wizard = ConfigWizard(self)
        ret = ha_wizard.exec_()
        if ret != QDialog.Accepted:
            return False

        qhaobject = QHAObject.getInstance()
        qhaobject.pre_modify()

        config = qhaobject.hacfg

        qnetobject = QNetObject.getInstance()
        qnetobject.pre_modify()
        net_cfg = qnetobject.netcfg

        old_type = config.ha_type
        new_config = ha_wizard.getData()
        config.ha_type = new_config.ha_type
        config.interface_id = new_config.interface_id
        config.interface_name = new_config.interface_name
        if config.ha_type in (PENDING_PRIMARY, PENDING_SECONDARY):
            iface = net_cfg.getIfaceByHardLabel(config.interface_id)
            configureHA(net_cfg, iface)
            network_modified = True
        elif config.ha_type != old_type:
            deconfigureHA(net_cfg)
            network_modified = True
            # XXX should not reconfigure now ?
        else:
            network_modified = False

        valid = qnetobject.post_modify()
        if not valid:
            qhaobject.revert()
        else:
            # FIXME: use post_modify() result?
            qhaobject.post_modify()
            self.setModified(True)
            if network_modified:
                network = self.mainwindow.getPage('network')
                network.setModified(True)
                dhcp = self.mainwindow.getPage('dhcp')
                dhcp.dhcp_widget.setModified(True)
                dhcp.dhcp_widget.fillView()

        self.setViewData()
        return True

    def hide_last_error(self):
        self.last_error_text.clear()
        self.last_error_text.hide()
        self.last_error_title.hide()

    def show_last_error(self, last_error):
        if last_error:
            self.last_error_text.setText(last_error)
            self.last_error_title.show()
            self.last_error_text.show()
        else:
            self.hide_last_error()

    def syncUpgrades(self):
        # First, update the list of missing upgrades:
        defer = self.setViewData()
        if defer:
            defer.addCallback(self._syncUpgrades)

    def _syncUpgrades(self):
        pass

    def fetchConfig(self):
        # we use QHAObject
        pass

    def __disable(self):
        self.close()
        raise NuConfModuleDisabled("Disabling high availability interface")

    def setViewData(self):
        config = QHAObject.getInstance().hacfg

        if "1.0" == self.version:
            raw_state = self.mainwindow.init_call('ha', 'getState')
            if raw_state is None:
                self.__disable()
                return
            self.link_state, self.ha_last_date, last_error = raw_state
            self.link_status_label.setText(self.LINK_STATE.get(self.link_state,
                tr('(unknown)')))
        else:
            raw_state = self.mainwindow.init_call('ha', 'getFullState')
            if raw_state is None:
                self.__disable()
                return
            node_state = raw_state['node_state']
            self.link_state = raw_state['link_state']
            self.ha_last_date = raw_state['seen_other']
            last_error = raw_state['last_error']

            self.link_status_label.setText(self.LINK_STATE.get(self.link_state,
                tr('(unknown)')))
            self.node_status_label.setText(self.NODE_STATE.get(node_state,
                tr('(unknown)')))

        # TEMP : use compatibility instead
        try:
            try:
                if raw_state.get('link_state', None) == CONNECTED:
                    self.join.setEnabled(False)
            except Exception:
                if isinstance(raw_state, list) and len(raw_state) > 0:
                    if raw_state[0] == CONNECTED:
                        self.join.setEnabled(False)
        except TypeError:
            pass

        ha_type = self.__ha_type()

        self.type_label.setText(
            HAConfigFrontend.STATE_DESCRIPTIONS[ha_type]
            )

        if ha_type != ENOHA:
            if self.ha_last_date not in (0, None):
                fmt = '%Y-%m-%d %H:%M:%S'
                seen = time.strftime(fmt, time.localtime(self.ha_last_date))
                self.activity_label.setText(unicode(seen))
            if config.interface_id is not None:
                qnetobject = QNetObject.getInstance()
                iface = qnetobject.netcfg.getIfaceByHardLabel(config.interface_id)
                self.interface_label.setText(iface.fullName())
            try:
                last_error = self.client.call('ha', 'getLastError')
                self.show_last_error(last_error)
            except Exception:
                self.hide_last_error()
        else:
            self.interface_label.clear()
            self.activity_label.clear()
            self.hide_last_error()
        if ha_type == PRIMARY:
            async = self.client.async()
            async.call('ha', 'getMissingUpgradeNums',
                       callback=self._get_missing_upgrade_nums,
                       errback=self.writeError)
        self.mainwindow.writeAccessNeeded(self.join)
        if self.join.isEnabled():
            self.join.setEnabled(PENDING_PRIMARY == ha_type)

    def _get_missing_upgrade_nums(self, missing_upgrade_nums):
        try:
            self.missing_upgrade_nums = missing_upgrade_nums
            if type(missing_upgrade_nums) != type([]):
                self.missing_upgrade_nums_label.setText(tr('N/A'))
            elif not missing_upgrade_nums:
                self.missing_upgrade_nums_label.setText(tr('None '))
            else:
                sample = sorted(missing_upgrade_nums)
                if len(sample) > MAX_MISSING_UPGRADE_NUMS:
                    sample = sample[:MAX_MISSING_UPGRADE_NUMS] + ['...']
                self.missing_upgrade_nums_label.setText(
                    ', '.join([unicode(num) for num in sample]))
            self.missing_upgrade_text_label.setText(
                tr('Missing upgrades on the secondary'))
        except Exception:
            pass

    def sendConfig(self, message):
        """
        Save HA config
        """
        serialized =  QHAObject.getInstance().hacfg.serialize()
        self.client.call('ha', 'configureHA', serialized, message)

    def joinSecondary(self):
        self.mainwindow.addToInfoArea(
            tr("Attempting to enslave the secondary, please wait...")
            )
        self.splash = SplashScreen()
        self.splash.setText(tr("Attempting to enslave the secondary..."))
        self.splash.show()
        async = self.client.async()
        async.call('ha', 'startHA',
            callback = self.successJoin,
            errback = self.errorJoin
            )

    def successJoin(self, ok):
        self.splash.hide()
        self.timer = Timer(
            self.setViewData,
            REFRESH_INTERVAL_MILLISECONDS,
            self.mainwindow.keep_alive.thread,
            self
            )
        self.join.setEnabled(False)
        self.mainwindow.addToInfoArea(tr("Joining secondary: success"), category=COLOR_SUCCESS)

    def errorJoin(self, error):
        self.splash.hide()
        self.mainwindow.addToInfoArea(tr('Joining secondary: fail'), category=COLOR_ERROR)
        warning = QMessageBox(self)
        warning.setWindowTitle(tr('Joining secondary: fail'))
        warning.setText(tr('An error was encountered while joining secondary.'))
        errmsg = exceptionAsUnicode(error)
        if "current state=ENOHA" in errmsg:
            errmsg = tr(
                "Can not join yet: the appliance is still not configured for "
                "high availability. Did you save and apply your changes?"
                )
        warning.setDetailedText(errmsg)
        warning.setIcon(QMessageBox.Warning)
        warning.exec_()

    def takeover(self):
        try:
            self.client.call('ha', 'takeover')
        except Exception, err:
            self.mainwindow.exception(err)
            return
        self.mainwindow.addToInfoArea(tr('Take over request sent.'), category=COLOR_SUCCESS)

    def isValid(self):
        msg = QHAObject.getInstance().hacfg.isValidWithMsg()

        if msg is not None:
            self.error_message = msg[0] % msg[1:] # used by main_window
            return False
        else:
            return True

    def setModified(self, is_modified):
        FullFeaturedScrollArea.setModified(self, is_modified)
        if is_modified:
            QHAObject.getInstance().post_modify()

    def unload(self):
        if self.timer is not None and self.timer.isActive():
            self.timer.stop()

class ConfigWizard(QWizard):
    def __init__(self, parent):
        QWizard.__init__(self, parent)
        self.config_page = ConfigPage(self)
        self.addPage(self.config_page)

    def getData(self):
        return self.config_page.getData()

class ConfigPage(QWizardPage):
    def __init__(self, parent):
        QWizardPage.__init__(self, parent)
        layout = QFormLayout(self)

        config = QHAObject.getInstance().hacfg

        self.setTitle(tr("High Availability Configuration"))

        self.ha_type = QComboBox() # primary / secondary
        self.ha_type.addItem(tr('Disabled'), QVariant(ENOHA))
        self.ha_type.addItem(tr('Primary'), QVariant(PENDING_PRIMARY))
        self.ha_type.addItem(tr('Secondary'), QVariant(PENDING_SECONDARY))
        index = self.ha_type.findData(QVariant(config.ha_type))
        self.ha_type.setCurrentIndex(index)

        layout.addRow(tr('Status of this cluster member:'), self.ha_type)
        self.registerField('type', self.ha_type)

        self.interface = InterfaceChoice(self.selectInterface, self)
        self.label_interface = QLabel(tr('Interface'))
        layout.addRow(self.label_interface, self.interface)
        self.registerField('interface', self.interface)

        self.connect(self.ha_type, SIGNAL('currentIndexChanged(int)'), self.toggleType)
        self.toggleType(index)

        if config.ha_type != ENOHA:
            message = tr("'%s' already configured as '%s'.") % (config.interface_id,
                config.ha_type)
            message += '<br />'
            message += tr("The configuration for this interface will be cleared.")

            warning_message = MessageArea()
            warning_message.setMessage(tr("Warning"), message,
                status=MessageArea.WARNING)
            layout.addRow(warning_message)

    def selectInterface(self, interface):
        return interface.canReserve() or interface.hasHA()

    def toggleType(self, index):
        selected_type = self.ha_type.itemData(index)
        self.interface.setVisible(selected_type.toString() != ENOHA)
        self.label_interface.setVisible(selected_type.toString() != ENOHA)

    def validatePage(self):
        type_index, is_ok = self.field('type').toInt()
        ha_type = unicode(self.ha_type.itemData(type_index).toString())

        if QHAObject.getInstance().cfg.ha_type == SECONDARY and ha_type == ENOHA:
            #SECONDARY -> ENOHA is forbidden
            #when PRIMARY, this wizard is not even displayed
            QMessageBox.warning(self,
                tr('Invalid configuration'),
                tr(
                    "In order to fully deconfigure high availability, you "
                    "need to restore this appliance to factory defaults."
                )
                )
            return False

        if ha_type != ENOHA:
            net_cfg = QNetObject.getInstance().netcfg
            iface = self.interface.getInterface()
            iface_id = net_cfg.getHardLabel(iface)
            iface_name = iface.system_name
        else:
            iface_id = None
            iface_name = None
        config = HAConf(ha_type=ha_type, interface_id=iface_id, interface_name=iface_name)
        msg = config.isValidWithMsg()
        if msg is None:
            self.config = config
        else:
            QMessageBox.warning(self, tr('Invalid configuration'), msg[0] % msg[1:])
        if msg is not None:
            return False

        if ha_type != PENDING_PRIMARY:
            return True

        user_valid = QMessageBox.question(
                self,
                tr("Configuring primary appliance. Are you sure?"),
                "<div>%s<br/>%s<br/>%s<br/>%s</div>" % (
                    tr(
                        "After this configuration step, <b>you will not be able to "
                        "change the hostname anymore.</b>"
                      ),
                    tr(
                        "Abort now, or reject the saved configuration if you "
                        "need to change the hostname."
                      ),
                    tr("The hostname is currently <i><b>'%(HOSTNAME)s'</b></i>"
                      ) % {'HOSTNAME': QHostnameObject.getInstance().cfg.hostname},
                    tr("Do you want to continue?"),
                    ),
                QMessageBox.Yes | QMessageBox.Abort
                )

        return user_valid == QMessageBox.Yes

    def getData(self):
        return self.config

