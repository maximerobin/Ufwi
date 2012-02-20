
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
from PyQt4.QtGui import (QAbstractItemView, QButtonGroup, QCheckBox,
    QFormLayout, QFrame, QGroupBox, QLabel, QLineEdit, QRadioButton,
    QSizePolicy, QTableWidget, QTableWidgetItem, QTextEdit, QVBoxLayout)
from PyQt4.QtCore import Qt, QString, SIGNAL
import locale

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_rpcc_qt.tools import unsetFlag

from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.input_widgets import TextWithDefault
from ufwi_conf.client.qt.iplist_editor import IpListEdit
from ufwi_conf.client.qt.full_featured_scrollarea import FullFeaturedScrollArea
from ufwi_conf.client.qt.widgets import CenteredCheckBox
from ufwi_conf.client.services.proxy import QSquidObject
from ufwi_conf.client.system.network import QNetObject
from ufwi_conf.common.net_exceptions import NoMatch

_LANGUAGE = "EN"
try:
    locale.resetlocale()
    if locale.getlocale()[0].startswith("fr"):
        _LANGUAGE = "FR"
except Exception:
    pass

def makeItem(label):
    item = QTableWidgetItem(label)
    unsetFlag(item, Qt.ItemIsEditable)
    return item

def add_category(table, row, category_name, category):
    centeredcheckbox = CenteredCheckBox(table)
    checkbox = centeredcheckbox.checkbox
    table.setCellWidget(row, 0, centeredcheckbox)
    table.setItem(row, 1, makeItem(category_name))
    table.setItem(row, 2, makeItem(category["NAME %s" % _LANGUAGE]))
    table.setItem(row, 3, makeItem(category["DESC %s" % _LANGUAGE]))
    return checkbox

class ProxyFrontend(FullFeaturedScrollArea):
    COMPONENT = 'squid'
    LABEL = tr('Proxy service')
    REQUIREMENTS = ('squid', )
    ICON = ':/icons/worldmap.png'

    def __init__(self, client, parent):
        if not EDENWALL:
            raise NuConfModuleDisabled("proxy")
        self.blacklist_support = False
        self.qsquidobject = QSquidObject.getInstance()
        self.main_window = parent
        FullFeaturedScrollArea.__init__(self, client, parent)

        self.client = client
        self._modified = False
        self._not_modifying = False

    def fetchConfig(self):
        if not EDENWALL or self._module_disabled:
            return
        serialized = self.client.call(
            'squid', u'getSquidConfig')

        self.qsquidobject.squid = serialized
        message = tr("Proxy frontend disabled. An EdenWall Administration Suite upgrade is advised.")
        if self.qsquidobject.squid is None:
            self._disable(
                tr("Proxy configuration"),
                message,
                message
                )
            return
        else:
            object_version = self.qsquidobject.squid.getReceivedSerialVersion()
        self.whitelist_mode_support = object_version >= 3
        if object_version >= 2:
            self.blacklist_support = True
            self.custom_blacklist = self.client.call(
                'squid', 'getCustomBlacklist')
            self.custom_whitelist = self.client.call(
                'squid', 'getCustomWhitelist')
        else:
            self.blacklist_support = False

    def saveConf(self, message):
        if not EDENWALL:
            return
        FullFeaturedScrollArea.saveConf(self, message)

    def sendConfig(self, message):
        if not EDENWALL:
            return
        # Blacklist categories:
        if self.blacklist_support:
            categories_blacklist = []
            for (category_name, checkbox) in self.widget.categories.items():
                if checkbox.isChecked():
                    categories_blacklist.append(category_name)
            self.qsquidobject.squid.categories_blacklist = categories_blacklist

        serialized = self.qsquidobject.squid.serialize(downgrade=True)
        self.client.call('squid', 'setSquidConfig', serialized, message)

        # Custom blacklist:
        if self.blacklist_support:
            try:
                self.client.call(
                    'squid', 'setCustomBlacklist',
                    unicode(self.widget.custom_blacklist_edit.toPlainText()))
                self.client.call(
                    'squid', 'setCustomWhitelist',
                    unicode(self.widget.custom_whitelist_edit.toPlainText()))
            except Exception, err:
                self.main_window.addToInfoArea(
                    tr('Error while saving custom blacklist/whitelist: this appliance does not support custom blacklists (%s).') % err,
                    category=COLOR_ERROR)

    def isValid(self):
        try:
            self.qsquidobject.squid.setAuthorizedIPs(self.widget.ip_list)
        except ValueError, err:
            self.main_window.addToInfoArea(
                tr("Error in authorized IP addresses: ") +
                exceptionAsUnicode(err), category=COLOR_ERROR)
            return False
        self.qsquidobject.squid.parent_host = \
            unicode(self.widget.parent_host.text())
        self.qsquidobject.squid.parent_password = \
            unicode(self.widget.parent_password.text())
        self.qsquidobject.squid.parent_port = \
            unicode(self.widget.parent_port.text())
        self.qsquidobject.squid.parent_user = \
            unicode(self.widget.parent_user_name.text())
        check, message = self.qsquidobject.squid.isValidWithMsg()
        if not check:
            self.main_window.addToInfoArea(message, category=COLOR_ERROR)
            return False
        return True

    def buildInterface(self):
        if not EDENWALL or self._module_disabled:
            return
        self.default_gw = self.getDefaultGW()
        self.fetchConfig()
        self.widget = ProxyWidget(self)
        self.setWidget(self.widget)

        self.setWidgetResizable(True)
        self.error_message = self.tr("Incorrect proxy specification")

    def getDefaultGW(self):
        qnetobject = QNetObject.getInitializedInstance(self.client)
        if qnetobject.netcfg is None:
            self.setEnabled(False)
            self.main_window.addToInfoArea(
                tr("Proxy configuration: could not load network data, aborting"),
                COLOR_ERROR
                )
            return
        try:
            default_gw = QNetObject.getInstance().netcfg.getDefaultGateway(4)[0]
        except NoMatch:
            try:
                default_gw = QNetObject.getInstance().netcfg.getDefaultGateway(6)[0]
            except NoMatch:
                default_gw = ""

        if isinstance(default_gw, IP):
            return unicode(default_gw)
        else:
            return default_gw

    def setModified(self, modified=True):
        if self._modified == modified or self._not_modifying:
            return
        self._modified = modified
        if modified:
            self.main_window.setModified(self, True)

    def setViewData(self):
        if not EDENWALL or self._module_disabled:
            return
        self._not_modifying = True
        self.widget.enable_server.setChecked(self.qsquidobject.squid.enabled)
        self.widget.transparent.setChecked(self.qsquidobject.squid.transparent)
        self.widget.enable_antivirus.setChecked(
            self.qsquidobject.squid.antivirus_enabled)
        self.widget.ip_list.setIpAddrs(self.qsquidobject.squid.authorized_ips)

        # Parent proxy:
        self.widget.enable_parent_proxy.setChecked(
            self.qsquidobject.squid.parent_enabled)
        self.widget.parent_host.setText(
            QString(self.qsquidobject.squid.parent_host))
        self.widget.parent_password.setText(
            QString(self.qsquidobject.squid.parent_password))
        self.widget.parent_port.setText(
            QString(unicode(self.qsquidobject.squid.parent_port)))
        self.widget.parent_user_name.setText(
            QString(self.qsquidobject.squid.parent_user))

        # Blacklist:
        if self.blacklist_support:
            if self.qsquidobject.squid.blacklist_enabled or \
                    self.qsquidobject.squid.whitelist_mode:
                self.widget.no_filtering.setChecked(False)
                if self.qsquidobject.squid.whitelist_mode:
                    self.widget.whitelist_mode.setChecked(True)
                else:
                    self.widget.enable_blacklist.setChecked(True)
            else:
                self.widget.no_filtering.setChecked(True)
            for (category_name, checkbox) in self.widget.categories.items():
                checkbox.setChecked(category_name in
                                    self.qsquidobject.squid.categories_blacklist)
            self.widget.custom_blacklist_edit.setText(
                QString(self.custom_blacklist))
            self.widget.custom_whitelist_edit.setText(
                QString(self.custom_whitelist))

        self._not_modifying = False


    def setAntivirusEnabled(self, value):
        if value != self.qsquidobject.squid.antivirus_enabled:
            self.qsquidobject.squid.setAntivirusEnabled(value)
            self.setModified()

    def setBlacklistEnabled(self, value):
        if value != self.qsquidobject.squid.blacklist_enabled:
            self.qsquidobject.squid.setBlacklistEnabled(value)
            self.setModified()
        if value and self.qsquidobject.squid.whitelist_mode:
            self.qsquidobject.squid.setWhitelistMode(False)
            self.setModified()

    def setNoFiltering(self, value):
        self.setBlacklistEnabled(False)
        self.setWhitelistMode(False)

    def setEnabled(self, value):
        if value != self.qsquidobject.squid.enabled:
            self.qsquidobject.squid.setEnabled(value)
            self.setModified()

    def setParentEnabled(self, value):
        if value != self.qsquidobject.squid.parent_enabled:
            self.qsquidobject.squid.setParentEnabled(value)
            self.setModified()

    def setTransparent(self, value):
        if value != self.qsquidobject.squid.transparent:
            self.qsquidobject.squid.setTransparent(value)
            self.setModified()

    def setWhitelistMode(self, value):
        if value != self.qsquidobject.squid.whitelist_mode:
            self.qsquidobject.squid.setWhitelistMode(value)
            if value:
                self.qsquidobject.squid.setBlacklistEnabled(value)
            self.setModified()

class ProxyWidget(QFrame):
    def __init__(self, parent):
        QFrame.__init__(self, parent)
        self.parent = parent

        form = QFormLayout(self)
        title = QLabel("<H1>%s</H1>" % self.tr('HTTP Proxy Configuration'))
        form.addRow(title)

        self.enable_server = QCheckBox()
        self.connect(self.enable_server, SIGNAL('stateChanged(int)'),
                     parent.setEnabled)
        form.addRow(self.tr("Enable proxy server"), self.enable_server)

        self.transparent = QCheckBox()
        self.connect(self.transparent, SIGNAL('stateChanged(int)'),
                     parent.setTransparent)
        self.transparent_label = QLabel(self.tr("Enable transparent mode for the authorized IPs listed below"))
        self.transparent_label.setToolTip(self.tr("If your firewall rules do "
            "not block access to the web from other networks than listed "
            "below, the machines on those networks will be able to access "
            "the web directly."))
        form.addRow(self.transparent_label, self.transparent)

        self.enable_antivirus = QCheckBox()
        self.connect(self.enable_antivirus, SIGNAL('stateChanged(int)'),
                     parent.setAntivirusEnabled)
        form.addRow(self.tr("Enable antivirus"), self.enable_antivirus)

        #parent proxy

        group = QGroupBox()
        form.addRow(group)
        group.setTitle(self.tr("Parent Proxy"))

        parent_proxy_form = QFormLayout(group)
        self.enable_parent_proxy = QCheckBox()
        parent_proxy_form.addRow(self.tr("Enable parent proxy"), self.enable_parent_proxy)
        self.connect(self.enable_parent_proxy, SIGNAL('stateChanged(int)'),
                     parent.setParentEnabled)

        self.parent_host = TextWithDefault(parent.default_gw)
        parent_proxy_form.addRow(self.tr("Proxy host"), self.parent_host)

        self.parent_port = TextWithDefault("3128")
        parent_proxy_form.addRow(self.tr("Proxy port"), self.parent_port)

        self.parent_user_name = QLineEdit()
        self.parent_user_name_label = QLabel(self.tr("Username"))
        parent_proxy_form.addRow(self.parent_user_name_label, self.parent_user_name)

        self.parent_password = QLineEdit()
        self.parent_password.setEchoMode(QLineEdit.Password)
        self.parent_password_label = QLabel(self.tr("Password"))
        parent_proxy_form.addRow(self.parent_password_label, self.parent_password)
        parent.main_window.writeAccessNeeded(self.enable_parent_proxy,
            self.parent_host, self.parent_port, self.parent_user_name,
            self.parent_password)

        for w in (self.parent_host, self.parent_password, self.parent_port,
                  self.parent_user_name):
            self.connect(w, SIGNAL('textEdited(const QString&)'),
                         self.setModified)

        self.connect(
            self.enable_parent_proxy,
            SIGNAL('stateChanged(int)'),
            self.toggleParentProxy
            )
        self.connect(
            self.enable_antivirus,
            SIGNAL('stateChanged(int)'),
            self.toggleAntivirus
            )

        #Transparency

        transparent_group = QGroupBox()
        transparent_group.setTitle(self.tr("Transparent proxy"))
        # form.addRow(transparent_group)
        #transparent_form = QFormLayout(transparent_group)
        self.enable_transparent = QCheckBox()
        notice = QLabel()
        notice.setWordWrap(True)
        notice.setText(self.tr("<i><b>Notice:</b> Check this box to configure "
            "the proxy as an authenticating transparent proxy.<br/> Caution: "
            "the transparent proxy only works with the HTTP protocol and not "
            "with the HTTPS protocol.<br/> The transparent mode requires an "
            "authenticating \"transparent proxy\"-enabled rule in the firewall.</i>"))
        # transparent_form.addRow(notice)
        # transparent_form.addRow("Set transparent mode", self.enable_transparent)

        #Access control method

        auth_group = QGroupBox()
        form.addRow(auth_group)
        # auth_group.setTitle("Access control method to the proxy service")
        auth_group.setTitle(
            tr("List of authorized IP addresses (hosts and/or networks)"))
        auth_form = QFormLayout(auth_group)
        # sso_or_ip = QButtonGroup()
        # buttons_layout = QHBoxLayout()
        # auth_form.addRow(buttons_layout)
        # self.sso = QRadioButton("Authentication (SSO)")
        # self.ip_network = QRadioButton("IP/networks")
        # buttons_layout.addWidget(self.sso)
        # buttons_layout.addWidget(self.ip_network)
        # sso_or_ip.addButton(self.sso)
        # sso_or_ip.addButton(self.sso)
        # self.ip_network.setChecked(Qt.Checked)

        self.ip_list = IpListEdit(accept_empty=True)
        self.connect(self.ip_list, SIGNAL('textChanged()'),
                     parent.setModified)
        auth_form.addRow(self.ip_list)

        # parent.main_window.writeAccessNeeded(self.enable_transparent, self.sso, self.ip_network, self.ip_list)
        parent.main_window.writeAccessNeeded(self.ip_list)
#Authorize authenticated users
#


        self.blacklist_label = QLabel('<h2>%s</h2>' % tr(
                'Domain and address filtering (blacklists and whitelists)'))

        self._build_filtering_mode(parent)

        # Blacklist categories
        if self.parent.blacklist_support:
            try:
                available_categories = self.parent.client.call(
                    'squid', "getAvailableCategories")
                self.categories_group = QGroupBox()
                self.categories_group.setTitle(
                    tr("Blacklist categories"))
                self.categories_group_layout = QVBoxLayout(self.categories_group)
                self.categories = {}
                self.categories_table = QTableWidget(0, 4)
                self.categories_table.setMinimumHeight(300)
                self.categories_table.setSizePolicy(QSizePolicy.Minimum,
                                                    QSizePolicy.Minimum)
                self.categories_table.setSelectionMode(QAbstractItemView.NoSelection)
                self.categories_table.horizontalHeader().setStretchLastSection(True)
                self.categories_table.verticalHeader().setHidden(True)
                self.categories_table.setHorizontalHeaderLabels(
                    [tr('Block'), tr('Code'), tr('Name'), tr('Description')])
                blacklist_categories = filter(
                    lambda cat: cat[1]['DEFAULT_TYPE'] == 'black',
                    available_categories.items())
                blacklist_categories.sort()
                self.categories_table.setRowCount(len(blacklist_categories))
                row = 0
                for (category_name, category) in blacklist_categories:
                    checkbox = add_category(
                        self.categories_table, row, category_name, category)
                    self.connect(checkbox, SIGNAL("clicked()"), self.setModified)
                    self.categories[category_name] = checkbox
                    row += 1
                parent.mainwindow.writeAccessNeeded(self.categories_table)
                self.categories_group_layout.addWidget(self.categories_table)
            except Exception, err:
                if self.parent.blacklist_support:
                    self.parent.main_window.addToInfoArea(
                        tr("Could not fetch available blacklist categories (%s).")
                        % err, category = COLOR_ERROR)

            # Custom blacklist group
            self.custom_blacklist_group = QGroupBox()
            form.addRow(self.custom_blacklist_group)
            self.custom_blacklist_group.setTitle(
                tr("Custom blacklist (domains or full URLs)"))
            self.custom_blacklist_form = QFormLayout(self.custom_blacklist_group)
            self.custom_blacklist_edit = QTextEdit()
            self.custom_blacklist_form.addRow(self.custom_blacklist_edit)

            # Custom whitelist group
            self.custom_whitelist_group = QGroupBox()
            form.addRow(self.custom_whitelist_group)
            self.custom_whitelist_group.setTitle(
                tr("Custom whitelist (domains or full URLs)"))
            self.custom_whitelist_form = QFormLayout(self.custom_whitelist_group)
            self.custom_whitelist_edit = QTextEdit()
            self.custom_whitelist_form.addRow(self.custom_whitelist_edit)

            parent.mainwindow.writeAccessNeeded(self.custom_blacklist_edit,
                self.custom_whitelist_edit)

            # Add the filtering options to the page:
            for group in (self.filtering_group,
                          self.categories_group,
                          self.custom_blacklist_group,
                          self.custom_whitelist_group):
                form.addRow(group)
            for custom_list_edit in (self.custom_blacklist_edit,
                                     self.custom_whitelist_edit):
                self.connect(custom_list_edit, SIGNAL('textChanged()'),
                             parent.setModified)

        parent.main_window.writeAccessNeeded(
            self.enable_server, self.enable_antivirus, self.enable_blacklist)

    def _build_filtering_mode(self, parent):
        self.filtering_group = QGroupBox()
        self.filtering_group.setTitle(tr("Filtering mode"))
        self.filtering_group.setLayout(QVBoxLayout())

        # Two or three radio buttons:
        self.no_filtering = QRadioButton(tr("No filtering"))
        self.connect(self.no_filtering, SIGNAL('clicked(bool)'),
                     parent.setNoFiltering)
        self.enable_blacklist = QRadioButton(
            tr("Blacklist/Whitelist-based filtering"))
        self.connect(self.enable_blacklist, SIGNAL('clicked(bool)'),
                     parent.setBlacklistEnabled)
        if parent.whitelist_mode_support:
            self.whitelist_mode = QRadioButton(tr(
                "Whitelist-only filtering (block everything except the whitelist)"))
            self.connect(self.whitelist_mode, SIGNAL('clicked(bool)'),
                         parent.setWhitelistMode)

        # Organize the 3 radio buttons:
        self.filtering_buttons = QButtonGroup()
        buttons = [self.no_filtering, self.enable_blacklist]
        if parent.whitelist_mode_support:
            buttons.append(self.whitelist_mode)
        for button in buttons:
            self.filtering_buttons.addButton(button)
            self.filtering_group.layout().addWidget(button)
        self.parent.mainwindow.writeAccessNeeded(*tuple(buttons))

    def setModified(self, *unused):
        self.parent.setModified()

    def toggleParentProxy(self, state):
        enable = (state == Qt.Checked)

        self.parent_host.setEnabled(enable)
        self.parent_port.setEnabled(enable)
        self.parent_user_name.setEnabled(enable)
        self.parent_password.setEnabled(enable)

    def toggleAntivirus(self, state):
        if state == Qt.Checked:
            self.parent_user_name.hide()
            self.parent_user_name_label.hide()
            self.parent_password.hide()
            self.parent_password_label.hide()
            return
        self.parent_user_name.show()
        self.parent_user_name_label.show()
        self.parent_password.show()
        self.parent_password_label.show()

