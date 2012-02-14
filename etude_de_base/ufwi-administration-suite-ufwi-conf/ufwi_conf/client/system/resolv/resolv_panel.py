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

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import (QDialog, QInputDialog, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QWidget, QTextCursor, QFrame, QSpacerItem,
    QSizePolicy, QGridLayout, QMessageBox)

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.colors import COLOR_VERBOSE
from ufwi_conf.client.qt.input_widgets import EditButton, TestButton
from ufwi_conf.client.qt.ip_inputs import IpEdit, IpOrFqdnEdit, IpOrHostnameOrFqdnEdit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.common.resolvcfg import deserialize
from ufwi_conf.common.user_dir.protocols import getNetBiosName
from ufwi_conf.common.hostnamecfg import NOT_CHANGEABLE, CHANGE_DISCOURAGED

from .qhostname_object import QHostnameObject
from .qresolv_object import QResolvObject
from .result_ui import Ui_dns_result

_FULL_TEST_TEXT = tr(
"By default, the server will send an empty request to the default servers. "
"The configured name servers in the running configuration are %(DNS_SERVERS)s."
)
_FULL_TEST_TEXT_NOINFO = tr(
"By default, the server will send an empty request to the default servers."
)

_INFO_IMG = '<img src=":/icons-20/info.png"/>'

_HOSTNAME_CHANGE_DISCLAIMER = tr(
    "This server belongs to an AD domain. Are you sure you want to change its hostname?"
    )

_DOMAIN_CHANGE_DISCLAIMER = tr(
    "This server belongs to an AD domain. Are you sure you want to change its domain?"
    )

_HOSTNAME_NOT_CHANGEABLE = tr(
    "The hostname can not be changed because the server belongs to a "
    "high availability cluster", "message displayed in info area"
    )

_HOSTNAME = tr("Hostname")

_CANNOT_CHANGE_HOSTNAME = tr(
        "The name of a high availability cluster cannot be changed.",
        "this message triggered when user attempts to change the "
        "hostname if the edenwall is the primary of an HA cluster"
        )

_CANNOT_CHANGE_HOSTNAME_TITLE = tr(
        "Hostname change is disabled",
        "title of a message box"
        )

#unused, marks strings as translatable.
_DNS_ERRORS = (
    tr('Unreachable server')
)

class DnsResult(QDialog, Ui_dns_result):
    def __init__(self, result, parent=None):
        QDialog.__init__(self, parent)
        Ui_dns_result.setupUi(self, self)

        for line in result:
            self.plainTextEdit.appendPlainText(line)
        self.plainTextEdit.setReadOnly(True)
        self.plainTextEdit.moveCursor(QTextCursor.Start)
        self.connect(self.copy_button, SIGNAL("clicked()"), self.copyall)

    def copyall(self):
        self.plainTextEdit.selectAll()
        self.plainTextEdit.copy()

class ResolvFrontend(ScrollArea):
    COMPONENT = 'resolv'
    IDENTIFIER = 'dns'
    LABEL = tr('Hostname and DNS')
    REQUIREMENTS = ('resolv', 'hostname')
    FIXED_WIDTH = 40
    ICON = ':/icons/computeur.png'

    def __init__(self, client, parent=None):
        ScrollArea.__init__(self)
        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.cfg = {}
        self.host_loaded = False
        self.resolv_loaded = False
        self._can_edit_hostname = True
        self.qhostnamecfg = QHostnameObject.getInstance()
        self.qresolvcfg = QResolvObject.getInstance()

        main_widget = QWidget()
        self.setWidget(main_widget)
        self.setWidgetResizable(True)

        self.form = QFormLayout(main_widget)

        self.form.addRow(QLabel("<h1>%s</h1>" % tr('Hostname')))

        host_box = self.mkHostBox()
        self.form.addRow(host_box)

        self.form.addItem(
            QSpacerItem(1, 1, QSizePolicy.Minimum, QSizePolicy.Expanding)
            )

        self.form.addRow(QLabel("<h1>%s</h1>" % tr('DNS')))
        self.dns1 = self.addField(tr("Server 1"), IpEdit)
        self.dns2_label = QLabel(tr("Server 2"))
        self.dns2 = self.addField(self.dns2_label, IpEdit)

        self.form.addRow(QLabel("<h1>%s</h1>" % tr('Active configuration test')))

        self.test_group = _mkTestGroup()
        self.form.addRow(self.test_group)
        self.connect(self.test_group.test_button, SIGNAL('clicked()'), self.full_test)

        self.mainwindow.writeAccessNeeded(
            self.dns1,
            self.dns2,
            self.edit_hostname,
            self.edit_domain
            )

        self.message = MessageArea()
        self.message.setWidth(80)
        self.error_message = ''

        self.form.addRow(self.message)

        self.resetConf()
        if not self.host_loaded and not self.resolv_loaded:
            raise NuConfModuleDisabled

        if self.resolv_loaded:
            self._connectsignals()

    def _connectsignals(self):
        self.connect(self.dns1, SIGNAL('editingFinished()'),
            partial(self.setDns, self.dns1, self.qresolvcfg.resolvcfg.setNameserver1))
        self.connect(self.dns2, SIGNAL('editingFinished()'),
            partial(self.setDns, self.dns2, self.qresolvcfg.resolvcfg.setNameserver2))
        self.connect(self.dns1, SIGNAL('textEdited(QString)'), lambda x: self.setModified(True))
        self.connect(self.dns2, SIGNAL('textEdited(QString)'), lambda x: self.setModified(True))

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (
            ('resolv', 'getResolvConfig'),
            ('resolv', 'getRunningConfig'),
            ('hostname', 'getHostnameConfig'),
        )

    def setDns(self, edit_dns, set_dns):
        set_dns(edit_dns.text())

    def mkHostBox(self):
        box = QGroupBox(tr("Hostname and domain configuration"))
        form = QFormLayout(box)
        form.setLabelAlignment(Qt.AlignLeft)

        self.hostname = QLabel()
        self.edit_hostname = EditButton(flat=False)
        self.connect(self.edit_hostname, SIGNAL('clicked()'), self._edit_hostname)
        form.addRow(self.hostname, self.edit_hostname)

        self.domain = QLabel()
        self.edit_domain = EditButton(flat=False)
        self.connect(self.edit_domain, SIGNAL('clicked()'), self._edit_domain)
        form.addRow(self.domain, self.edit_domain)

        self.qhostnamecfg.registerCallbacks(
            lambda: True,
            self.updateHostname)

        self.qresolvcfg.registerCallbacks(
            lambda: True,
            self.updateDomain)

        return box

    def updateHostname(self):
        if not self.host_loaded:
            hostname_text = "<i>%s</i>" % tr("not fetched",
                "The hostname is normally fetched from the server, and this "
                "text handles the case when it failed. "
                "The text 'not fetched' is written in italics."
                )
            self._can_edit_hostname = False
        else:
            changeable = self.qhostnamecfg.hostnamecfg.changeable
            self._can_edit_hostname = changeable != NOT_CHANGEABLE
            hostname_text = "%s %s" % (
                    tr("Hostname:", "Displaying the hostname"),
                    self.qhostnamecfg.hostnamecfg.hostname
                )
            if changeable == NOT_CHANGEABLE:
                self.mainwindow.addToInfoArea(_HOSTNAME_NOT_CHANGEABLE, COLOR_VERBOSE)

        self.hostname.setText(hostname_text)

    def updateDomain(self):
        self.domain.setText(tr("Domain: %s") % self.qresolvcfg.resolvcfg.domain)

    def __editFieldDialog(self, title, label, text):
        """
        return text, ok
        """
        #Signature: text, ok = QInputDialog.getText(
        #    QWidget parent,
        #    QString title,
        #    QString label,
        #    QLineEdit.EchoMode echo = QLineEdit.Normal,
        #    QString text = QString(),
        #    Qt.WindowFlags f = 0)
        return QInputDialog.getText(
            self,
            title,
            label,
            QLineEdit.Normal,
            text
            )

    def _continue_edit(self, title, message):
        continuing = QMessageBox.question(
            self,
            title,
            message,
            QMessageBox.Cancel|QMessageBox.Ok,
            QMessageBox.Cancel, #default button
            )
        return continuing == QMessageBox.Ok

    def _edit_hostname(self):
        changeable = self.qhostnamecfg.hostnamecfg.changeable

        if not self._can_edit_hostname:
            QMessageBox.critical(
                self,
                _CANNOT_CHANGE_HOSTNAME_TITLE,
                _CANNOT_CHANGE_HOSTNAME,
                )
            return

        if changeable == CHANGE_DISCOURAGED:
            if not self._continue_edit(
                tr("About hostname change", "popup title"),
                _HOSTNAME_CHANGE_DISCLAIMER
                ):
                    return

        hostname, ok = self.__editFieldDialog(
            tr("Edit hostname"),
            tr("Enter new hostname"),
            self.qhostnamecfg.hostnamecfg.hostname
            )

        if ok:
            hostname = unicode(hostname).strip()
            if hostname == self.qhostnamecfg.hostnamecfg.hostname:
                return
            self.qhostnamecfg.pre_modify()
            self.qhostnamecfg.hostnamecfg.hostname = hostname
            self.qhostnamecfg.post_modify()
            self.setModified()

    def _edit_domain(self):
        changeable = self.qhostnamecfg.hostnamecfg.changeable

        if changeable == CHANGE_DISCOURAGED:
            if not self._continue_edit(
                tr("About domain change", "popup title"),
                _DOMAIN_CHANGE_DISCLAIMER
                ):
                    return
        domain, ok = self.__editFieldDialog(
            tr("Edit domain"),
            tr("Enter new domain name"),
            self.qresolvcfg.resolvcfg.domain
            )

        if ok:
            domain = unicode(domain).strip()
            if domain == self.qresolvcfg.resolvcfg.domain:
                return
            self.qresolvcfg.pre_modify()
            self.qresolvcfg.resolvcfg.setDomain(domain)
            self.qresolvcfg.post_modify()
            self.setModified()

    def default_test(self):
        async = self.client.async()
        async.call('resolv', 'test',
            {},
            callback=self.defaultTest_success,
            errback=self.test_error
            )
        self.mainwindow.addToInfoArea(tr("Testing current DNS server..."))

    def full_test(self):
        fields = {
            self.test_group.server_input: tr("test server field"),
            self.test_group.query_input: tr("test query field"),
        }

        default_test = True

        for item in fields:
            if not item.isEmpty():

                default_test = False

                if not item.isValid():
                    self.mainwindow.addToInfoArea(
                        tr("Wrong value in %s, can not test.") % fields[item]
                    )
                    return

        if default_test:
            self.default_test()
            return

        self.deactivate_tests()

        async = self.client.async()
        async.call('resolv', 'test',
            {
                'server': unicode(self.test_group.server_input.text()).strip(),
                'query': unicode(self.test_group.query_input.text()).strip()
            },
            callback=self.test_success,
            errback=self.test_error
            )
        self.mainwindow.addToInfoArea(tr("Testing DNS server with custom parameters..."))

    def defaultTest_success(self, result):
        self.mainwindow.addToInfoArea(tr("[DNS Test] Success: The server is available (empty query)."))
        self.reactivate_tests()

    def test_success(self, result):
        self.mainwindow.addToInfoArea(tr("[DNS Test] Success!"))
        dialog = DnsResult(result, self)
        dialog.exec_()
        self.reactivate_tests()

    def test_error(self, err):
        err = exceptionAsUnicode(err)
        self.mainwindow.addWarningMessage(
            tr("[DNS Test] Error! %s") % err
            )
        self.reactivate_tests()

    def deactivate_tests(self):
        self.test_group.test_button.setEnabled(False)

    def reactivate_tests(self):
        self.test_group.test_button.setEnabled(True)

    def addField(self, field_name, inputcls):
        field = inputcls(self)
        field.setFixedWidth(field.fontMetrics().averageCharWidth() * self.FIXED_WIDTH)
        self.form.addRow(field_name, field)
        return field

    def isModified(self):
        return self._modified

    def setModified(self, modif=True):
        if modif:
            self.mainwindow.setModified(self, True)
        self._modified = modif

    def resetConf(self):
        self._reset_hostname()
        self._reset_resolv()

        self.updateHostname()
        self.updateDomain()
        self.dns1.setText(self.qresolvcfg.resolvcfg.nameserver1)
        self.dns1.validColor()
        self.dns2.setText(self.qresolvcfg.resolvcfg.nameserver2)
        self.dns2.validColor()

        self.message.setNoMessage()
        self.setModified(False)

        self._reset_tests_texts()

    def isValid(self):
        self.message.setNoMessage()
        self.error_message = ''
        hasInvalidData = False
        for widget in [self.dns1, self.dns2]:
            if not widget.isValid():
                hasInvalidData = True
                error = "'%s' : must be '%s'<br />" % (widget.text(), widget.getFieldInfo())
                self.error_message += error
                self.message.setMessage('', "<ul>%s" % error, status=MessageArea.WARNING)

        confs = {
                tr("hostname"): self.qhostnamecfg.cfg,
                tr("DNS"): self.qresolvcfg.cfg
                }

        for name, item in confs.iteritems():
            if not item.isValid():
                hasInvalidData = True
                error = tr("%s configuration is invalid<br />") % name
                self.message.setMessage('', error, status=MessageArea.WARNING)
                self.error_message += error

        if not hasInvalidData:
            error = self.qresolvcfg.resolvcfg.isInvalid()
            if error:
                hasInvalidData = True
                self.error_message = error
                self.message.setMessage('', error, status=MessageArea.WARNING)

        if hasInvalidData:
            self.mainwindow.addToInfoArea(tr("'Hostname and DNS : invalid configuration'"))
            return False
        else:
            return True

    def saveConf(self, message):
        if self.host_loaded:
            self.client.call('hostname', 'setShortHostname', self.qhostnamecfg.hostnamecfg.hostname, message)
        if self.resolv_loaded:
            self.client.call('resolv', 'setResolvConfig', self.qresolvcfg.resolvcfg.serialize(), message)

        self.setModified(False)
        self.mainwindow.addToInfoArea(tr("'Hostname and DNS : configuration saved'"))

    def _reset_hostname(self):
        """
        Specifically resets values for hostname config.
        sets self.host_loaded according to success in doing so.
        """
        self.host_loaded = self._reset_helper(
            'hostname',
            'getHostnameConfig',
            self.qhostnamecfg,
            tr("Hostname interface enabled"),
            tr("Hostname interface disabled: backend not loaded")
        )

    def _reset_resolv(self):
        """
        Specifically resets values for DNS resolution config.
        sets self.resolv_loaded according to success in doing so.
        """
        self.resolv_loaded = self._reset_helper(
            'resolv',
            'getResolvConfig',
            self.qresolvcfg,
            tr("DNS interface enabled"),
            tr("DNS interface disabled: backend not loaded")
        )

    def _reset_tests_texts(self):
        serialized = self._fetch_serialized('resolv', 'getRunningConfig')

        if serialized is not None:
            running_cfg = deserialize(serialized)
            servers = {'DNS_SERVERS': ' and '.join(
                tuple(running_cfg.iterNameServers())
                )}
            text = _FULL_TEST_TEXT % servers
        else:
            self.message.warning(
                tr("Warning on tests", "Testing DNS resolution from the server"),
                tr(
                    "Tests are run with the configuration that is applied on "
                    "the appliance. This configuration can not be displayed "
                    "(probably because the software version of the appliance does "
                    "not provide this functionality)."
                  )
                )
            text = _FULL_TEST_TEXT_NOINFO

        self.test_group.full_test_info.setText("%s %s" % (_INFO_IMG, text))

def _mktestlabel():
    label = QLabel()
    label.setWordWrap(True)
    label.setFrameStyle(QFrame.Panel | QFrame.Sunken)
    label.setText('\n'*10)
    return label

def _mkTestGroup():
    groupbox = QGroupBox()
    form = QGridLayout(groupbox)
    groupbox.test_button = TestButton(text=tr("Make the appliance perform the DNS query"))
    groupbox.server_input = IpOrFqdnEdit(groupbox, accept_empty=True)
    groupbox.query_input = IpOrHostnameOrFqdnEdit(groupbox, accept_empty=True)
    groupbox.full_test_info = _mktestlabel()

    for widget in (groupbox.server_input, groupbox.query_input, groupbox.full_test_info):
        widget.setMinimumWidth(250)

    left_col_align = Qt.AlignLeft
    right_col_align = Qt.AlignRight

    row = 0 #== row
    form.addWidget(
        groupbox.test_button,
        row, 0, 1, 1, left_col_align
        )

    form.addWidget(
        groupbox.full_test_info,
        row, 1, 2, 1, right_col_align #2 rows
        )

    row += 2 #== row
    form.addWidget(
        QLabel(tr(
            "Name server to use (empty for the name "
            "server configured on the appliance)"
            )),
        row, 0, 1, 1, left_col_align
        )

    form.addWidget(
        groupbox.server_input,
        row, 1, 1, 1, right_col_align
        )

    row += 1 #== row
    form.addWidget(
        QLabel(tr("Host or IP address to resolve (optional)")),
        row, 0, 1, 1, left_col_align
        )
    form.addWidget(
        groupbox.query_input,
        row, 1, 1, 1, right_col_align
        )

    for inputfield in (groupbox.server_input, groupbox.query_input):
        groupbox.connect(inputfield, SIGNAL('returnPressed()'), groupbox.test_button.click)

    return groupbox

