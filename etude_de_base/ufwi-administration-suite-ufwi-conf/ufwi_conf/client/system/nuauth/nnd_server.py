from __future__ import with_statement

import os
from itertools import chain
from PyQt4.QtGui import QDialog, QFileDialog, QMessageBox

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcc_qt.colors import COLOR_ERROR
from ufwi_conf.common.user_dir.base import LDAP, EDIRECTORY
from .nnd_base import NndDialog, bindbutton, bindlineedit, infer_bind_dn, pretty_bind_dn
from .nnd_server_ui import Ui_NndServer

class ServerDialog(NndDialog, Ui_NndServer):
    def __init__(self, nnd_widget, conf, domain_conf, name=""):
        NndDialog.__init__(self, nnd_widget, conf, title=tr("server"), name=name)
        self.domain_conf = domain_conf
        self.setinitialvalues()
        self.server_expert_cb()

    def fail(self, message):
        QMessageBox.warning(self, tr("Incomplete or invalid input"), message)
        return False

    def accept(self):
        label = unicode(self.conf.label)
        if not label:
            return self.fail(tr("The server name must not be empty"))
        if self.name != label:
            for server in self.domain_conf.servers:
                if label == server.label:
                    return self.fail(tr("This server name already exists"))

        if not self.conf.ldapuri:
            return self.fail(tr("An LDAP uri is required."))

        if not self.anonymous_checkbox.isChecked() and not self.conf.has_bind_info():
            return self.fail(tr(
                "No user/password data is specified, "
                "do you want an anonymous LDAP bind?"
                ))


        self._save_conf()
        self.setResult(QDialog.Accepted)
        self.done(True)

    def _save_conf(self):
        """
        Raise ValueError
        """
        for name in self._iterFields():
            checkbox = self._checkbox_from_name(name)

            if checkbox.isChecked():
                lineedit = self._lineedit_from_name(name)
                u_text = unicode(lineedit.text())
                try:
                    setattr(self.conf, name, u_text)
                except ValueError, err:
                    message = tr("%s: %s") % (checkbox.text(), err.args[0])
                    self.fail(message)

            else:
                setattr(self.conf, name, "")

        if self.anonymous_checkbox.isChecked():
            self.conf.bind_dn = ""
            self.conf.bind_pw = ""

    def _buttons_and_callbacks(self, main_widget):
        yield self.expert_checkbox, self.server_expert_cb

        yield self.upload_ca_button, self.upload_ca_cb

        yield self.anonymous_checkbox, self.anonymous_cb

        for name in """
            tls
            check_cert
            """.split():
            callback = getattr(main_widget, "set_server_%s_cb" % name)
            yield self._checkbox_from_name(name), callback

        for name in self._iterFields():
            callback = getattr(main_widget, "%s_checkbox_cb" % name)
            yield self._checkbox_from_name(name), callback

    def _checkbox_from_name(self, name):
        return getattr(self, "%s_checkbox" % name)

    def _lineedit_from_name(self, name):
        return getattr(self, "%s_lineedit" % name)

    def _lineedits_and_callbacks(self):
        yield self._lineedit_from_name("bind_dn"), self.set_server_bind_dn
        yield self._lineedit_from_name("name"), self.set_server_name

        for name in """
            bind_pw
            ldapuri
            """.split():

            def callback(text, name=name):
                setattr(self.conf, name, unicode(text))

            yield self._lineedit_from_name(name), callback

        for name in self._iterFields():

            def override_callback(text, name=name):
                u_text = unicode(text)
                domain_value = getattr(self.domain_conf, name)
                if u_text == domain_value:
                    u_text = ""
#                setattr(self.conf, name, u_text)
                if u_text == self.domain_conf.group_attr_name:
                    u_text = ""
#                self.conf.group_attr_name = u_text

            yield self._lineedit_from_name(name), override_callback

    def bindsignals(self, main_widget):
        for button, callback in self._buttons_and_callbacks(main_widget):
            bindbutton(button, callback)

        for lineedit, callback in self._lineedits_and_callbacks():
            bindlineedit(lineedit, callback)

    def set_server_name(self, text):
        self.conf.label = unicode(text)

    def set_server_bind_dn(self, text):
        login_or_bind_dn = unicode(text)
        if login_or_bind_dn.find(',') != -1:
            self.conf.bind_dn = login_or_bind_dn
        else:
            user_base_dn = self.user_base_dn_lineedit.text()
            self.conf.bind_dn = infer_bind_dn(
                login_or_bind_dn,
                user_base_dn)

    def setinitialvalues(self):
        # Overriding fields.

        for name in self._iterFields():
            conf_value = getattr(self.conf, name)
            lineedit = self._lineedit_from_name(name)
            checkbox = self._checkbox_from_name(name)
            if conf_value:
                enabled = True
                written_value = conf_value
            else:
                enabled = False
                written_value = getattr(self.domain_conf, name)

            lineedit.setText(written_value)
            lineedit.setEnabled(enabled)
            checkbox.setChecked(enabled)

                # set bind_dn after user_base_dn, because bind_dn may be computed from
        # the user_base_dn
        use_ldap = (self.domain_conf.type_ in (LDAP, EDIRECTORY))

        bind_dn = self.conf.bind_dn
        if not use_ldap:
            bind_dn = pretty_bind_dn(
                bind_dn, self.conf.user_base_dn)
        self.bind_dn_lineedit.setText(bind_dn)
        self.bind_pw_lineedit.setText(self.conf.bind_pw)

        self.expert_checkbox.setChecked(self._hasCustomParameters())
        # TODO : make backend function that implements thoses info
        self.expert_checkbox.setVisible(False)

        #setting up UI fopr anonymous vs non anonymous bind info
        anonymous = not self.conf.has_bind_info()
        self.anonymous_checkbox.setChecked(anonymous)
        self.bind_dn_lineedit.setDisabled(anonymous)
        self.bind_pw_lineedit.setDisabled(anonymous)

    def set_anonymous(self, anonymous):
        anonymous = bool(anonymous)
        self.anonymous_checkbox.setChecked(anonymous)
        self.bind_dn_lineedit.setDisabled(anonymous)
        self.bind_pw_lineedit.setDisabled(anonymous)
        if anonymous:
            self.bind_dn_lineedit.clear()
            self.bind_pw_lineedit.clear()
            self.conf.bind_dn = ""
            self.conf.bind_pw = ""

    def anonymous_cb(self):
        self.set_anonymous(self.anonymous_checkbox.isChecked())

    def upload_ca_cb(self):
        self.choose_and_upload()

    def _iterCustomfields(self):
        return iter("""
            user_filter
            user_member_attr
            group_attr_name
            group_enum_filter
            group_filter
            group_member_attr
            """.split()
            )

    def _iterFields(self):
        return chain(self._iterCustomfields(), iter("""
                    user_base_dn
                    group_base_dn
        """.split()))

    def _hasCustomParameters(self):
        return any(
               getattr(self.conf, name)
               for name in self._iterCustomfields()
               )

    def server_expert_cb(self):
        widgets = (self.override_user_groupbox, self.override_group_groupbox)
        if self.expert_checkbox.isChecked():
            for widget in widgets:
                widget.show()
        else:
            for widget in widgets:
                widget.hide()

    def choose_and_upload(self):
        # Get filename
        open_caption = tr("Select a CA certificate to upload")
        filename = unicode(
            QFileDialog.getOpenFileName(self, open_caption,))
        if not filename:
            return

        # Check file size (<= 5 MB).
        if os.path.getsize(filename) > 5 * 1024 * 1024:
            error_message = tr(
                "Error: The file you are trying to upload is larger than "
                "5 MB. Are you sure it is a CA certificate?")
            self.main_widget.main_window.addToInfoArea(error_message, category=COLOR_ERROR)
            return False

        # Read content and encode it to base64
        with open(filename, 'rb') as fd:
            content = fd.read()
        content_base64 = encodeFileContent(content)
        content = None
        self.conf.ca_cert = content_base64
        return True

    def _showwidget(self, basename, wtype, isshown):
        widget = getattr(self, "%s_%s" % (basename, wtype))
        widget.setVisible(isshown)

    def initialshowable(self):
        ldap_shown = self.domain_conf.type_ in (LDAP, EDIRECTORY)
        for widget_type in "checkbox lineedit".split():
            for name in "user_base_dn group_base_dn group_member_attr".split():
                self._showwidget(name, widget_type, ldap_shown)
            for name in "user_member_attr group_enum_filter".split():
                self._showwidget(name, widget_type, not ldap_shown)

