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

from __future__ import with_statement

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import (QButtonGroup, QDialog, QFrame, QGroupBox, QHBoxLayout,
    QInputDialog, QLabel, QLineEdit, QMessageBox, QRadioButton, QPushButton,
    QVBoxLayout, QWidget)

from .directory_widget import DirectoryWidget
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcc_qt.input_widgets import AddButton, RemButton

from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.upload_dialog import UploadDialog
from ufwi_conf.common.user_dir.base import CUSTOM, NUPKI, SSL_DISABLED
from ufwi_conf.common.user_dir.tests import ip_in_ldapuri

#Help text, split into several variables for easier translation
help_uri_title = tr("Field usage")
help_uri_general = tr(" Please enter one or several (space separated) ldap uris.")
help_uri_pre = tr("An LDAP uri comprises:")
help_uri_0 = tr('An optional protocol prefix: "ldap://" or "ldaps://" (default if not specified)')
help_uri_1 = tr('A server fully qualified name or hostname')
help_uri_2 = tr('An optional port number specification: ":636" (default for ldaps)')
help_uri = """\
<i>%s</i>
<hr/>
<h3>%s</h3>
<ul>
<li>%s</li>
<li>%s</li>
<li>%s</li>
</ul>
""" % (help_uri_general, help_uri_pre, help_uri_0, help_uri_1, help_uri_2)

help_uri_tooltip = """\
<span>
<h2>%s</h2>
%s
</span>
""" % (help_uri_title, help_uri)
help_uri_message_area = """\
<span>
%s
</span>
""" % (help_uri,)

numeric_warning_title = tr("Warning on LDAPS with IP address in URI")
numeric_warning=tr(
    "Although LDAPS way work well with an URI containing an IP address, "
    "such as 'ldaps://192.168.1.145:636', "
    "be warned that it will only be the case if this IP address is included in the "
    "certificate, either in CN or in subjectAltName.")

def separator():
    separator = QFrame()
    separator.setFrameStyle(QFrame.HLine)
    return separator

class LdapWidget(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        assert config is not None
        assert specific_config is not None
        DirectoryWidget.__init__(self, config, specific_config, mainwindow, parent)
        self.buildInterface(config)
        self.updateView(self.specific_config)

    def buildInterface(self, config):
        #<server uri>
        self.uri = QLineEdit()
        self.texts.add(self.uri)
        self.connect(self.uri, SIGNAL('textChanged(QString)'), self.setUri)
        self.connect(self.uri, SIGNAL('textChanged(QString)'), self.signalModified)
        self.connect(self.uri, SIGNAL('textEdited(QString)'), self.helpURI)
        self.connect(self.uri, SIGNAL('editingFinished()'), self.noHelpURI)
        self.connect(self.uri, SIGNAL('editingFinished()'), self.updateUri)
        self.form.addRow(tr('LDAP Server(s) uri'), self.uri)

        self.uri.setToolTip(help_uri_tooltip)
        self.connect(self.uri, SIGNAL('returnPressed()'), self.signalModified)

        self.uri_message_area = MessageArea()
        self.empty_uri_label = QLabel()
        self.form.addRow(self.empty_uri_label, self.uri_message_area)
        self.empty_uri_label.hide()
        self.uri_message_area.hide()
        self.uri_message_area.setMessage(help_uri_title, help_uri_message_area)

        self.numeric_uri_warning = MessageArea()
        empty  = QLabel()
        self.form.addRow(empty, self.numeric_uri_warning)
        empty.hide()
        self.numeric_uri_warning.hide()
        self.numeric_uri_warning.warning(numeric_warning_title, numeric_warning)
        self.numeric_uri_warning.setWidth(60)

        #</server uri>

        #<other fields>
        for args in self._genTextFieldsData():
            text_input = self.addTextInput(*args[1:])
            setattr(self, args[0], text_input)
            self.connect(text_input, SIGNAL('editingFinished(QString)'), self.valid)
        #</other fields>

        self.ssl_box = self.mkSslBox()
        self.connect(self.ssl_box, SIGNAL('toggled(bool)'), self.toggleSsl)
        self.form.addRow(self.ssl_box)

        self.form.addRow(separator())

        test_widget = QPushButton(tr("Test this configuration"))
        self.form.addRow("", test_widget)
        test_widget.connect(test_widget, SIGNAL('clicked()'), self.test_ldap)

    def _genTextFieldsData(self):
        return (
            ('dn_users', tr('LDAP DN for users'), self.setDnUsers),
            ('dn_groups', tr('LDAP DN for groups'), self.setDnGroups),
            ('user', tr('DN used to log in on the LDAP server'), self.setUser),
            ('password', tr('Password used to log in on the LDAP server'), self.setPassword, False)
        )

    def test_ldap(self):
        dc, base, uri, filter, password = self.specific_config.generateTest()
        if uri is None or uri == '':
            QMessageBox.critical(
                self,
                "Missing data",
                "Please fill URI field"
                )
            return
        if dc is None:
            dc == ''

        filter, ok = QInputDialog.getText(
            self,
            tr("LDAP Filter"),
            tr("Please enter a filter:"),
            QLineEdit.Normal,
            filter
            )

        if not ok:
            return

        async = self.mainwindow.client.async()
        async.call(
            'nuauth',
            'testLDAP',
            dc, base, uri, unicode(filter), password,
            callback = self.success_test,
            errback = self.error_test
            )

    def success_test(self, result):

        ans_no = tr("OK")
        ans_yes = tr("Show the server's answer")
        show_details = QMessageBox.question(
            self,
            tr('LDAP test results'),
            tr('LDAP test completed without error'),
            ans_no,
            ans_yes
            )

        if show_details == 0:
            return

        title = tr('LDAP test results')
        QMessageBox.information(
            self,
            title,
            '<span><h2>%s</h2><pre>%s</pre></span>' % (title, unicode(result))
            )

    def error_test(self, result):
        basic_text = tr('LDAP test completed with an error')
        formatted_text = u"""\
<span>
%s
<pre>
%s
</pre>
</span>
""" % (basic_text, unicode(result))
        QMessageBox.warning(
            self,
            tr('LDAP test results'),
            formatted_text
            )

    def helpURI(self, text):
        self.uri_message_area.show()

    def noHelpURI(self):
        self.uri_message_area.hide()

    def toggleSsl(self, value):
        if value:
            self.selectCustomOrNupki(NUPKI)
        else:
            self.specific_config.custom_or_nupki = SSL_DISABLED
        self.signalModified()

    def setUri(self, uris_text):
        self.specific_config.setUri(self.readString(uris_text))
        self.signalModified()

        self.numeric_uri_warning.setVisible(ip_in_ldapuri(self.specific_config.uri))

    def setUser(self, user):
        self.specific_config.user = self.readString(user)

    def setPassword(self, password):
        self.specific_config.password = self.readString(password)

    def setDnUsers(self, dn):
        self.specific_config.dn_users = self.readString(dn)

    def setDnGroups(self, dn):
        self.specific_config.dn_groups = self.readString(dn)

    def mkSslBox(self):
        group = QGroupBox(tr("Check server certificate"))
        group.setCheckable(True)
        box = QVBoxLayout(group)

        #id 0
        nupki = QRadioButton(tr("Upload certificate"))
        #id 1
        custom = QRadioButton(tr("Use an internal PKI"))

        hbox = QHBoxLayout()
        box.addLayout(hbox)
        self.nupki_or_custom = QButtonGroup()
        self.connect(self.nupki_or_custom, SIGNAL('buttonClicked(int)'), self.toggleCustomOrNupki)
        for index, radio in enumerate((custom, nupki)):
            hbox.addWidget(radio)
            self.nupki_or_custom.addButton(radio, index)

        self.file_selector_widget = QWidget()
        vbox = QVBoxLayout(self.file_selector_widget)
        selector_label = QLabel(tr("Manually uploaded LDAP certificate"))
        vbox.addWidget(selector_label)
        add_cert_trigger = AddButton(text=tr("Upload a certificate"))
        vbox.addWidget(add_cert_trigger)
        vbox.addWidget(separator())

        self.has_cert_message = QLabel(
            tr("There is no manually uploaded server certificate")
            )
        self.del_cert = RemButton(
            tr("Delete certificate file from server")
            )
        vbox.addWidget(self.has_cert_message)
        vbox.addWidget(self.del_cert)

        self.connect(add_cert_trigger, SIGNAL('clicked()'), self.upload_server_cert)

        self.connect(self.del_cert, SIGNAL('clicked()'), self.delete_server_cert)

        self.nupki_message = MessageArea()
        self.nupki_message.setMessage(tr("Warning"),
            tr(
                "There is no server certificate in the internal PKI.<br/>"
                "Please import or generate one using an internal PKI."
            )
            )

        for anti_button, widget in ((custom, self.nupki_message), (nupki, self.file_selector_widget)):
            box.addWidget(widget)
            self.connect(anti_button, SIGNAL('toggled(bool)'), widget.setVisible)

        self.selectCustomOrNupki(CUSTOM)

        return group

    def upload_server_cert(self):
        dialog = UploadDialog(
            selector_label=tr("LDAP certificate"),
            filter=tr("Certificate file (*.crt *.pem *)")
            )
        accepted = dialog.exec_()

        if accepted != QDialog.Accepted:
            return

        filename = dialog.filename

        if not filename:
            return
        with open(filename, 'rb') as fd:
            content = fd.read()

        content = encodeFileContent(content)

        self.mainwindow.addToInfoArea(tr('Uploading of a certificate file for the ldap server'))
        async = self.mainwindow.client.async()
        async.call("nuauth", "upload_ldap_server_cert", content,
            callback = self.success_upload,
            errback = self.error_upload
            )

    def success_upload(self, value):
        self.mainwindow.addToInfoArea(tr('[LDAP server cert upload] Success!'))
        self.specific_config.server_cert_set = True
        self.setServerCert()

        self.signalModified()

    def error_upload(self, value):
        self.mainwindow.addToInfoArea(tr('[LDAP server cert upload] Error!'), COLOR_ERROR)
        self.mainwindow.addToInfoArea(tr('[LDAP server cert upload] %s') % value, COLOR_ERROR)

    def setServerCert(self):
        if self.specific_config.server_cert_set:
            self.del_cert.show()
            self.has_cert_message.hide()
        else:
            self.del_cert.hide()
            self.has_cert_message.show()

    def delete_server_cert(self):
        confirm_box = QMessageBox(self)
        confirm_box.setText(
            tr(
                "Please confirm the deletion of the "
                "manually uploaded LDAP server certificate."
            )
            )
        confirm_box.setInformativeText(
            tr("Do you really want to delete the certificate file?")
            )
        confirm_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm_box.setDefaultButton(QMessageBox.Cancel)
        confirm = confirm_box.exec_()

        if confirm != QMessageBox.Ok:
            return

        async = self.mainwindow.client.async()
        async.call("nuauth", "delete_ldap_server_cert",
            callback = self.success_delete,
            errback = self.error_delete
            )

    def success_delete(self, value):
        self.mainwindow.addToInfoArea(tr('[LDAP server cert deletion] Success!'))
        self.specific_config.server_cert_set = False
        self.setServerCert()

        self.signalModified()

    def error_delete(self, value):
        self.mainwindow.addToInfoArea(tr('[LDAP server cert deletion] Error!'), COLOR_ERROR)
        self.mainwindow.addToInfoArea(tr('[LDAP server cert deletion] %s') % value, COLOR_ERROR)

    def toggleCustomOrNupki(self, id):
        if id == 0:
            self.specific_config.custom_or_nupki = NUPKI
        else:
            self.specific_config.custom_or_nupki = CUSTOM
        self.signalModified()

    def selectCustomOrNupki(self, custom_or_nupki):
        if custom_or_nupki == CUSTOM:
            self.file_selector_widget.setEnabled(True)
            self.nupki_message.hide()
            id = 1
        else:
            custom_or_nupki = NUPKI
            self.file_selector_widget.hide()
            id = 0
        self.nupki_or_custom.button(id).setChecked(True)

    def setSslData(self, config):
        ssl_enabled = (SSL_DISABLED != config.custom_or_nupki)
        self.ssl_box.setChecked(ssl_enabled)
        if ssl_enabled:
            self.selectCustomOrNupki(config.custom_or_nupki)

    def updateUri(self, config=None):
        if config is None:
            config = self.specific_config
        self.setText(self.uri, config.uri)

    def updateView(self, config=None):
        if config is None:
            config = self.specific_config
        self.updateUri(config=config)
        self.setSslData(config)
        #never copy this one:
        self.setDefaultText(self.dn_users, self.specific_config.dn_users)
        self.setDefaultText(self.dn_groups, self.specific_config.dn_groups)
        self.setDefaultText(self.user, config.user)
        self.setDefaultText(self.password, config.password)
        self.setServerCert()

