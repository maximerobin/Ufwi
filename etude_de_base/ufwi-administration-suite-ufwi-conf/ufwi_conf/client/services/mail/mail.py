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
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import  QCheckBox
from PyQt4.QtGui import  QDoubleSpinBox
from PyQt4.QtGui import  QFormLayout
from PyQt4.QtGui import  QFrame
from PyQt4.QtGui import QGridLayout
from PyQt4.QtGui import  QGroupBox
from PyQt4.QtGui import  QLabel
from PyQt4.QtGui import  QMessageBox
from PyQt4.QtGui import  QSizePolicy
from PyQt4.QtGui import  QSpacerItem

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.genericdelegates import EditColumnDelegate
from ufwi_rpcc_qt.input_widgets import Button
from ufwi_rpcc_qt.list_edit import ListEdit

from ufwi_conf.client.multicall import Multicall
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.ip_inputs import FqdnEdit as DomainEdit, IpEdit
from ufwi_conf.client.qt.iplist_editor import NetworkListEdit
from ufwi_conf.client.qt.widgets import ScrollArea

if EDENWALL:
    from ufwi_conf.common.antispam_cfg import AntispamConf
    from ufwi_conf.client.services.mail.q_mail_object import QMailObject

class MailServicesFrontend(ScrollArea):
    """
    Services and system Frontend share same MailConfig instance.

    In order to get config, services frontend must be loaded after system frontend.
    """
    COMPONENT = 'exim'
    LABEL = tr('Mail service')
    REQUIREMENTS = ('exim',)
    ICON = ':/icons/edit.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        if not EDENWALL:
            raise NuConfModuleDisabled("mail")
        self.mainwindow = parent
        self._modified = False
        self.mail_modified = False
        self.spam_modified = False
        self._init_done = False
        self.spam_config = None
        self.client = client

        frame = QFrame(self)
        layout = QGridLayout(frame)

        title = QLabel('<H1>%s</H1>' % self.tr('Email Configuration'))
        layout.addWidget(title, 0, 0)

        self.antivirus_enable = self.buildAntivirus(layout, 1, 0)
        self.antispam_enable, self.mark_spam_level, self.deny_spam_level = self.buildAntispam(layout, 2, 0)

        self.relayed_domains = self.buildIncoming(layout, 3, 0)
        self.relayed_net = self.buildOutgoing(layout, 4, 0)
        self.test_mail = self.buildTestMail(layout, 5, 0)

        self.mainwindow.writeAccessNeeded(
            self.antivirus_enable,
            self.relayed_domains,
            self.relayed_net,
            self.test_mail
            )

        self.setWidget(frame)
        self.setWidgetResizable(True)

        self.resetConf()

        if self.spam_config is not None:
            self.mainwindow.writeAccessNeeded(self.antispam_enable)

        self._init_done = True
        self.mainwindow.addToInfoArea(tr('Email services interface enabled'))

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (("exim", 'getMailConfig'), ('antispam', 'getAntispamConfig'))

    def mailServicesIsValid(self):
        if not self.relayed_net.isValid(accept_empty=True):
            return False, tr('Networks for outgoing emails are invalid')

        return True, ''

    def resetConf(self):
        try:
            serialized = self.mainwindow.init_call('antispam', 'getAntispamConfig')
            self.spam_config = AntispamConf.deserialize(serialized)
        except:
            self.spam_config = None

        mail_inst = QMailObject.getInitializedInstance(self.client)
        self.antivirus_enable.setChecked(mail_inst.mailcfg.use_antivirus)

        if self.spam_config is not None:
            self.antispam_enable.setChecked(self.spam_config.use_antispam)
            self.mark_spam_level.setValue(self.spam_config.mark_spam_level)
            self.mark_spam_level.setMaximumWidth(self.mark_spam_level.fontMetrics().averageCharWidth() * 10)
            self.deny_spam_level.setValue(self.spam_config.deny_spam_level)
            self.deny_spam_level.setMaximumWidth(self.deny_spam_level.fontMetrics().averageCharWidth() * 10)
            if not self.spam_config.use_antispam:
                self.mark_spam_level.setEnabled(False)
                self.deny_spam_level.setEnabled(False)

        relayed_domains_data = []
        for domain, ip in mail_inst.mailcfg.relay_domain_in.iteritems():
            relayed_domains_data.append([domain, ip])
        self.relayed_domains.reset(relayed_domains_data)

        self.relayed_net.setIpAddrs(mail_inst.mailcfg.relay_net_out)

    def saveConf(self, message):
        assert self.spam_modified or self.mail_modified

        self.updateOutgoingNetworks()

        saveCalls = Multicall(self.client)

        # if needed: save antispam config, next mail config
        if self.spam_config is not None and self.spam_modified:
            saveCalls.addCall('antispam', "setAntispamConfig", self.spam_config.serialize(downgrade=True), message)

        if self.mail_modified:
            saveCalls.addCall('exim', "setMailConfig", QMailObject.getInstance().mailcfg.serialize(downgrade=True), message)

        saveCalls()

        self.mainwindow.addToInfoArea(tr("email configuration saved"))
        self.mail_modified = False
        self.spam_modified = False

    def isModified(self):
        return self.mail_modified or self.spam_modified

    def isValid(self):
        is_valid, self.error_message = QMailObject.getInstance().mailcfg.isValid()
        if is_valid:
            is_valid, self.error_message = self.spam_config.isValid()
        return is_valid

    def setMailModified(self, modified=True, message=''):
        if self._init_done:
            self.mail_modified = modified
            self.setModified(modified, message)

    def setSpamModified(self, modified, message=''):
        if self._init_done:
            self.spam_modified = modified
            self.setModified(modified, message)

    def setModified(self, modified, message=""):
        if modified:
            self.mainwindow.setModified(self, True)
            if message:
                self.mainwindow.addToInfoArea(message)

    def buildAntivirus(self, layout, row, col):
        antivirus = QGroupBox(self)
        antivirus.setTitle(tr('Antivirus'))
        antivirus_layout = QFormLayout(antivirus)
        antivirus_enable = QCheckBox()
        antivirus_layout.addRow(tr('Enable antivirus'), antivirus_enable)
        self.connect(antivirus_enable, SIGNAL('clicked(bool)'), self.setAntivirusEnabled)
        layout.addWidget(antivirus, row, col)
        return antivirus_enable

    def buildAntispam(self, layout, row, col):
        antispam = QGroupBox(self)
        antispam.setTitle(tr('Antispam'))
        antispam_layout = QFormLayout(antispam)
        antispam_enable = QCheckBox()
        info = QLabel(tr("This will add an <code>X-Spam-Score:</code> header "
            "field to all the messages and add a <code>Subject:</code> line "
            "beginning with *<i>SPAM</i>* and containing the original subject "
            "to the messages detected as spam."))
        info.setWordWrap(True)
        antispam_layout.addRow(info)
        antispam_layout.addRow(tr('Activate the antispam'), antispam_enable)
        mark_spam_level = QDoubleSpinBox(self)
        mark_spam_level.setDecimals(1)
        antispam_layout.addRow(tr('Mark the message as spam if its score is greater than'), mark_spam_level)
        deny_spam_level = QDoubleSpinBox(self)
        deny_spam_level.setDecimals(1)
        antispam_layout.addRow(tr('Refuse the message if its score is greater than'), deny_spam_level)

        # enable/disable spam levels
        self.connect(antispam_enable, SIGNAL('toggled(bool)'), mark_spam_level.setEnabled)
        self.connect(antispam_enable, SIGNAL('toggled(bool)'), deny_spam_level.setEnabled)

        # update config
        self.connect(mark_spam_level, SIGNAL('valueChanged(double)'), self.setMarkSpamLevel)
        self.connect(deny_spam_level, SIGNAL('valueChanged(double)'), self.setDenySpamLevel)
        self.connect(antispam_enable, SIGNAL('clicked(bool)'), self.setAntispamEnabled)

        layout.addWidget(antispam, row, col)

        self.mainwindow.writeAccessNeeded(mark_spam_level, deny_spam_level)

        return antispam_enable, mark_spam_level, deny_spam_level

    def buildIncoming(self, layout, row, col):
        incoming = QGroupBox(self)
        incoming.setTitle(tr('Incoming emails'))
        incoming_layout = QGridLayout(incoming)

        incoming_info = QLabel(tr('Domains for which EdenWall relays emails'))
        relayed_domains = ListEdit()
        relayed_domains.headers = self.getColumnLabels()
        relayed_domains.readOnly = self.mainwindow.readonly
        relayed_domains.setColDelegate(self.createDelegateForColumn)
        relayed_domains.setEditInPopup(True)
        relayed_domains.displayUpDown = False
        self.connect(relayed_domains, SIGNAL('itemDeleted'), self.incomingDeleted)
        self.connect(relayed_domains, SIGNAL('itemAdded'), self.incomingAdded)
        self.connect(relayed_domains, SIGNAL('itemModified'), self.incomingModified)
        self.connect(relayed_domains, SIGNAL('itemDeleted'), self.updateConfig)
        self.connect(relayed_domains, SIGNAL('itemAdded'), self.updateConfig)
        self.connect(relayed_domains, SIGNAL('itemModified'), self.updateConfig)

        incoming_layout.addWidget(incoming_info, 0, 0)
        incoming_layout.addWidget(relayed_domains, 1, 0)

        layout.addWidget(incoming, row, col)
        return relayed_domains

    def buildOutgoing(self, layout, row, col):
        outgoing = QGroupBox(self)
        outgoing.setTitle(tr('Outgoing emails'))
        outgoing_layout = QGridLayout(outgoing)

        relayed_net = NetworkListEdit(self)
        relayed_net.setMaximumHeight(relayed_net.fontMetrics().height() * 5)
        self.connect(relayed_net, SIGNAL("textChanged()"), self.setMailModified)
        outgoing_layout.addWidget(QLabel(tr('Networks for which EdenWall relays emails')), 0, 0)
        outgoing_layout.addWidget(relayed_net, 1, 0, 1, 2)

        outgoing_layout.addWidget(QLabel(tr(
            """If outgoing mail should be relayed through a 'smarthost', configure this host in the "Contact" page of the "Services" tab."""
        )))

        layout.addWidget(outgoing, row, col)
        return relayed_net

    def buildTestMail(self, layout, row, col):
        test = QGroupBox(self)
        test.setTitle(tr('Test for emails'))
        test_layout = QGridLayout(test)
        test_info = QLabel(tr('To check the configuration, you can send a test '
'email to the email address of your contact. Be sure to configure the '
'smarthost in the Email page if you need one.'))
        test_info.setWordWrap(True)
        test_button = Button(text=tr('Send test email'), flat=False)
        test_layout.addWidget(test_info, 0, 0, 1, 2)
        test_layout.addWidget(test_button, 1, 0)
        test_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Preferred), 1, 1)

        self.connect(test_button, SIGNAL('clicked()'), self.sendTestMail)

        layout.addWidget(test, row, col)

        return test_button

    # for ListEdit
    def getColumnLabels(self):
        return [tr('Domain'), tr('Mail relay host IP')]

    def createDelegateForColumn(self, column):
        if 0 == column:
            return EditColumnDelegate(DomainEdit)
        else:
            return EditColumnDelegate(IpEdit)
    # ... for ListEdit

    def setAntivirusEnabled(self, value):
        self.setMailModified()
        mail_inst = QMailObject.getInstance()
        mail_inst.pre_modify()
        mail_inst.mailcfg.use_antivirus = bool(value)
        mail_inst.post_modify()

    def setAntispamEnabled(self, value):
        self.setSpamModified(modified=True)
        self.spam_config.use_antispam = bool(value)

    def setMarkSpamLevel(self, level):
        self.setSpamModified(modified=True)
        self.spam_config.mark_spam_level = level

    def setDenySpamLevel(self, level):
        self.setSpamModified(modified=True)
        self.spam_config.deny_spam_level = level

    def incomingAdded(self):
        self.setMailModified(message=tr("'Incoming email': entry added"))

    def incomingDeleted(self):
        self.setMailModified(message=tr("'Incoming email': entry deleted"))

    def incomingModified(self):
        self.setMailModified(message=tr("'Incoming email': entry edited"))

    def updateConfig(self):
        entries = {}
        for domain, ip in self.relayed_domains.rawData():
            domain = unicode(domain)
            ip = unicode(ip)
            if entries.has_key(domain):
                QMessageBox.warning(self, tr('incoming emails: invalid entries'),
                    tr('Each domain must be unique (%s)') % unicode(domain))
            else:
                entries[domain] = ip

        mail_inst = QMailObject.getInstance()
        mail_inst.pre_modify()
        mail_inst.mailcfg.relay_domain_in = entries
        mail_inst.post_modify()

    def updateOutgoingNetworks(self):
        nets = []
        for net in self.relayed_net.value():
            net = unicode(net)
            nets.append(IP(net))

        mail_inst = QMailObject.getInstance()
        mail_inst.pre_modify()
        mail_inst.mailcfg.relay_net_out = nets
        mail_inst.post_modify()

    def sendTestMail(self):
        self.client.call('contact', 'sendTestMail')
        self.mainwindow.addToInfoArea(tr("test email was sent"))

