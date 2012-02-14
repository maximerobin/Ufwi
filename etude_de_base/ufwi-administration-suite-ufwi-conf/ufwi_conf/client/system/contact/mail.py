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

from PyQt4.QtGui import (
    QCheckBox, QGridLayout, QGroupBox, QLabel, QSpacerItem, QSizePolicy,
    QFrame, QComboBox, QMessageBox, QLineEdit, QInputDialog
    )
from PyQt4.QtCore import SIGNAL

from functools import partial
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.validators import check_mail
from ufwi_rpcc_qt.input_widgets import Button
from ufwi_conf.client.qt.widgets import ScrollArea
from ufwi_conf.client.qt.ip_inputs import IpOrFqdnEdit, MailEdit
from ufwi_conf.client.services.mail.q_mail_object import QMailObject
from ufwi_conf.common.contact_cfg import ContactConf

class ContactFrontend(ScrollArea):
    COMPONENT = 'contact'
    LABEL = tr('Contact and mail')
    REQUIREMENTS = ('contact',)
    ICON = ':/icons/edit.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.error_message = ''
        self.config = None
        frame = QFrame(self)
        layout = QGridLayout(frame)

        title = QLabel(u'<H1>%s</H1>' % tr('Contact Configuration'))
        layout.addWidget(title, 0, 0)

        self.admin_mail = self.buildAdminMail(layout, 1, 0)
        self.sender_mail = self.buildSenderMail(layout, 2, 0)
        self.smarthost_group, self.use_smarthost, self.mail_relay = \
            self.buildOutgoing(layout, 3, 0)
        self.language = self.buildChooseLanguage(layout, 4, 0)
        self.buildTestMail(layout, 5, 0)
        layout.setRowStretch(6, 15)

        self.setWidget(frame)
        self.setWidgetResizable(True)

        self.resetConf()
        self.mainwindow.addToInfoArea(tr('Contact interface enabled'))

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return ( ("contact", 'getContactConfig'), )

    def resetConf(self):
        self._modified = False

        serialized = self.mainwindow.init_call("contact", u'getContactConfig')
        self.config = ContactConf.deserialize(serialized)

        self.admin_mail.setText(self.config.admin_mail)
        self.sender_mail.setText(self.config.sender_mail)

        if self.config.language in ContactConf.CODE_TO_NAME:
            lang_id = self.language.findText(ContactConf.CODE_TO_NAME[self.config.language])
            self.language.setCurrentIndex(lang_id)

        smarthost = QMailObject.getInitializedInstance(self.client).mailcfg.smarthost
        self.use_smarthost.setChecked(bool(smarthost))
        self.mail_relay.setEnabled(self.use_smarthost.isChecked())
        self.mail_relay.setText(smarthost)
        self.smarthost_group.setVisible(True)

    def saveConf(self, message):
        assert self._modified

        serialized = self.config.serialize(downgrade=True)
        self.client.call("contact", 'setContactConfig', serialized, message)

        self.setModified(False)

        self.mainwindow.addToInfoArea(tr('contact configuration saved'))

    def setModified(self, isModified=True, message=""):
        self._modified = isModified
        if self._modified:
            self.mainwindow.setModified(self, True)
            if message:
                self.mainwindow.addToInfoArea(message)

    def isModified(self):
        return self._modified

    def isValid(self):
        ok, self.error_message = self.config.isValidWithMsg()
        return ok

    def buildAdminMail(self, layout, row, col):
        admin_mail = QGroupBox(self)
        admin_mail.setTitle(tr("Administrator email address"))
        admin_mail_layout = QGridLayout(admin_mail)
        admin_mail_info = QLabel(tr("Administrator email address (EdenWall will send the system alerts to this address)"))
        admin_mail_info.setWordWrap(True)
        admin_mail_edit = MailEdit()
        admin_mail_edit.setMinimumWidth(admin_mail_edit.fontMetrics().averageCharWidth() * 15)
        admin_mail_edit.setMaximumWidth(admin_mail_edit.fontMetrics().averageCharWidth() * 45)
        admin_mail_layout.addWidget(admin_mail_info, 0, 0)
        admin_mail_layout.addWidget(admin_mail_edit, 1, 0)
        admin_mail_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum) , 2, 0)
        self.connect(admin_mail_edit, SIGNAL('textEdited(QString)'), self.setAdminMail)
        layout.addWidget(admin_mail, row, col)
        self.mainwindow.writeAccessNeeded(admin_mail_info, admin_mail_edit)
        return admin_mail_edit

    def buildSenderMail(self, layout, row, col):
        sender_mail = QGroupBox(self)
        sender_mail.setTitle(tr("Sender email address for system messages"))
        sender_mail_layout = QGridLayout(sender_mail)

        sender_mail_info = QLabel(
            tr("Email address that will be used as the sender address in the emails sent to the administrator by EdenWall.")
            )
        sender_mail_info.setWordWrap(True)
        sender_mail_edit = MailEdit()
        sender_mail_edit.setMinimumWidth(sender_mail_edit.fontMetrics().averageCharWidth() * 15)
        sender_mail_edit.setMaximumWidth(sender_mail_edit.fontMetrics().averageCharWidth() * 45)
        sender_mail_layout.addWidget(sender_mail_info, 0, 0)
        sender_mail_layout.addWidget(sender_mail_edit, 1, 0)
        sender_mail_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum) , 2, 0)
        self.connect(sender_mail_edit, SIGNAL('textEdited(QString)'), self.setSenderMail)
        layout.addWidget(sender_mail, row, col)
        self.mainwindow.writeAccessNeeded(sender_mail_info, sender_mail_edit)
        return sender_mail_edit

    def buildOutgoing(self, layout, row, col):
        outgoing = QGroupBox(self)
        outgoing.setTitle(tr('Outgoing emails'))
        outgoing_layout = QGridLayout(outgoing)

        use_smarthost = QCheckBox()
        outgoing_layout.addWidget(QLabel(tr('Use smarthost')), 1, 0)
        outgoing_layout.addWidget(use_smarthost, 1, 1)

        mail_relay = IpOrFqdnEdit()
        outgoing_layout.addWidget(QLabel(tr('Host which relays EdenWall emails')), 2, 0)
        outgoing_layout.addWidget(mail_relay, 2, 1)
        self.mainwindow.writeAccessNeeded(use_smarthost, mail_relay)

        self.connect(use_smarthost, SIGNAL('toggled(bool)'), mail_relay.setEnabled)
        self.connect(use_smarthost, SIGNAL('clicked()'),
                     partial(self.setModified, True))
        self.connect(mail_relay, SIGNAL('textEdited(QString)'), self.setSmarthost)

        layout.addWidget(outgoing, row, col)
        return outgoing, use_smarthost, mail_relay

    def buildChooseLanguage(self, layout, row, col):
        language = QGroupBox(self)
        language.setTitle(tr('Language for emails'))
        language_layout = QGridLayout(language)
        language_info = QLabel(tr('Language for emails sent by EdenWall to the Administrator'))
        language_info.setWordWrap(True)
        language_choose = QComboBox()
        for name in ContactConf.CODE_TO_NAME.itervalues():
            language_choose.addItem(name)
        language_layout.addWidget(language_info, 0, 0, 1, 0)
        language_layout.addWidget(language_choose, 1, 0)
        language_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum) , 1, 1)
        self.connect(language_choose, SIGNAL('activated(QString)'), self.setLanguage)
        layout.addWidget(language, row, col)
        self.mainwindow.writeAccessNeeded(language_info, language_choose)
        return language_choose

    def buildTestMail(self, layout, row, col):
        test = QGroupBox(self)
        test.setTitle(tr('Test for emails'))
        test_layout = QGridLayout(test)
        test_info = QLabel(tr(
            "To check the configuration, you can send a test "
            "email to your contact email address. Be sure to configure the "
            "smarthost in the Mail page if needed."
            ))
        test_info.setWordWrap(True)
        test_button = Button(text=tr('Send test email'), flat=False)
        test_layout.addWidget(test_info, 0, 0, 1, 0)
        test_layout.addWidget(test_button, 1, 0)
        test_layout.addItem(QSpacerItem(0, 0, QSizePolicy.Expanding, QSizePolicy.Minimum) , 1, 1)
        self.connect(test_button, SIGNAL('clicked()'), self.sendTestMail)
        layout.addWidget(test, row, col)
        self.mainwindow.writeAccessNeeded(test_info, test_button)
        return test_button

    def sendTestMail(self):
        title = None
        query = None
        default = ""
        dest = self.config.admin_mail
        if not dest:
            title = tr('No default recipient')
            query = tr('contact email address is empty, enter a recipient:')
        elif not check_mail(dest):
            title = tr('contact email address is invalid')
            query = tr('Fix contact email address:')
            default = dest

        if title is not None:
            dest, validated = QInputDialog.getText(self, title, query, QLineEdit.Normal, default)
            dest = unicode(dest)
            if not validated:
                self.mainwindow.addToInfoArea(tr('email sending was cancelled'))
                return
            elif not check_mail(dest):
                QMessageBox.warning(self, tr('Test cancelled'),
                    tr("Invalid contact email address '%s'") % dest)
                return
            else:
                self.setAdminMail(dest)
                self.admin_mail.setText(dest)

        # Used if user leave Sender mail empty
        if len(self.config.sender_mail) == 0:
            self.setSenderMail(self.config.admin_mail)
            self.sender_mail.setText(self.config.admin_mail)
            self.sender_mail.validColor()

        self.client.call("contact", 'sendTestMail', self.config.sender_mail, dest)
        self.mainwindow.addToInfoArea(tr("test email was sent to '%s'") % dest)

    def setAdminMail(self, value):
        self.setModified(isModified=True)
        self.config.admin_mail = unicode(value).strip()

    def setSenderMail(self, value):
        self.setModified(isModified=True)
        self.config.sender_mail = unicode(value).strip()


    def setSmarthost(self, value):
        self.setModified(isModified=True)
        mail_inst = QMailObject.getInstance()
        mail_inst.pre_modify()
        mail_inst.mailcfg.smarthost = unicode(value)
        mail_inst.post_modify()

        # Notify exim page of modification
        mail = self.mainwindow.getPage('exim')
        mail.setMailModified(True)

    def setLanguage(self, value):
        for code, name in ContactConf.CODE_TO_NAME.iteritems():
            if name == unicode(value):
                if self.config.language != code:
                    self.config.language = code
                    self.setModified(isModified=True)
                return
