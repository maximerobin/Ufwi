from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QDialog, QButtonGroup, QMessageBox, QHeaderView, QTableWidgetItem

from ufwi_rpcd.common import tr
from ufwi_conf.common.user_dir.base import NND_DIRTYPES, AD, LDAP, EDIRECTORY

from .nnd_base import (
    bindbutton,
    bindlineedit,
    DEFAULT_PARAMS,
    get_default_param,
    infer_bind_dn,
    infer_login,
    NndDialog,
    pretty_bind_dn,
    SHOW_CONTROLS,
    )
from .nnd_domain_ui import Ui_NndDomain

class DomainDialog(NndDialog, Ui_NndDomain):
    def __init__(self, nnd_widget, conf, name=""):
        NndDialog.__init__(self, nnd_widget, conf, title=tr("Domain"), name=name)

        self.typeselectors = QButtonGroup()
        for index, item in enumerate(NND_DIRTYPES):
            button = getattr(self, "type_%s_radiobutton" % item)
            self.typeselectors.addButton(button, index)

    def fail(self, message):
        QMessageBox.warning(self, tr("Invalid domain name"), message)
        return False

    def accept(self):
        label = unicode(self.conf.label)
        if not label:
            return self.fail(tr("The domain name must not be empty"))
        if self.name != label and label in self.nnd_widget.specific_config.domains:
            return self.fail(tr("This domain name already exists"))

        self.updateBindDn()

        valid, msg = self.conf.isValidWithMsg()
        if not valid:
            return self.fail(msg)

        self.setResult(QDialog.Accepted)
        self.done(True)

    def domain_expert_cb(self):
        show = self.expert_checkbox.isChecked()
        self.showHideExpertDomain(show)

    def domain_group_attr_name_cb(self):
        checked = self.group_attr_name_checkbox.isChecked()
        self.group_attr_name_lineedit.setDisabled(not checked)
        if not checked:
            self.reset_field("group_attr_name")

    def domain_group_enum_filter_cb(self):
        checked = self.group_enum_filter_checkbox.isChecked()
        self.group_enum_filter_lineedit.setDisabled(not checked)
        if not checked:
            self.reset_field("group_enum_filter")

    def domain_group_member_attr_cb(self):
        checked = self.group_member_attr_checkbox.isChecked()
        self.group_member_attr_lineedit.setDisabled(not checked)
        if not checked:
            self.reset_field("member_attr")

    def domain_group_filter_cb(self):
        checked = self.group_filter_checkbox.isChecked()
        self.group_filter_lineedit.setDisabled(not checked)
        if not checked:
            self.reset_field("group_filter")

    def showHideExpertDomain(self, show):
        layout = self.expert_widget
        for index in xrange(layout.count()):
            item = layout.itemAt(index)
            widget = item.widget()
            if show:
                widget.show()
            else:
                widget.hide()

    def updateDomainView(self):
        self.server_table.setRowCount(
            len(self.conf.servers))

        expert = self.isExpert()
        self.expert_checkbox.setChecked(expert)
        self.showHideExpertDomain(expert)
        for row, server in enumerate(self.conf.servers):
            self.server_table.setItem(
                row, 0, QTableWidgetItem(server.label))
            self.server_table.setItem(
                row, 1, QTableWidgetItem(server.ldapuri))
        self.server_table.horizontalHeader().setResizeMode(
            QHeaderView.ResizeToContents)

    def bindsignals(self, main_widget):
        bindbutton(self.add_button, self.add_server_cb)
        bindbutton(self.delete_button, self.delete_server_cb)
        bindbutton(self.edit_button, self.edit_server_cb)

        for name in """
            expert
            group_attr_name
            group_enum_filter
            group_filter
            group_member_attr""".split():
                #factor:
                #bindbutton(self.expert_checkbox, main_widget.domain_expert_cb)
                checkbox = getattr(self, "%s_checkbox" % name)
                callback = getattr(self, "domain_%s_cb" % name)
                bindbutton(checkbox, callback)

        bindbutton(self.move_down_button, self.move_server_down_cb)
        bindbutton(self.move_up_button, self.move_server_up_cb)
        bindbutton(self.type_AD_radiobutton, self.set_type_AD_cb)
        bindbutton(self.type_edirectory_radiobutton, self.set_type_edirectory_cb)
        bindbutton(self.type_LDAP_radiobutton, self.set_type_LDAP_cb)
        bindbutton(self.user_filter_checkbox, main_widget.domain_user_filter_cb)
        bindbutton(self.user_member_attr_checkbox, main_widget.domain_user_member_attr_cb)

        for name in DEFAULT_PARAMS:
                #factor:
                #bindlineedit(self.group_attr_name_lineedit, main_widget.set_group_attr_name_cb)
                lineedit = getattr(self, "%s_lineedit" % name)
                callback = getattr(main_widget, "set_%s_cb" % name)
                bindlineedit(lineedit, callback)

        bindlineedit(self.name_lineedit, main_widget.set_domain_name_cb)
        bindlineedit(self.realm_lineedit, main_widget.set_realm_cb)

        self.connect(self.server_table, SIGNAL("cellDoubleClicked(int, int)"), self.edit_server_cb)

        self.connect(self.server_table, SIGNAL("itemSelectionChanged()"),
                     main_widget.domain_select_current_row)

    def set_type_AD_cb(self):
        self._set_type(AD)

    def set_type_LDAP_cb(self):
        self._set_type(LDAP)

    def set_type_edirectory_cb(self):
        self._set_type(EDIRECTORY)

    def _set_type(self, dirtype):
        self.conf.type_ = dirtype
        self.show_edits(self.conf.type_)
        self.set_default_params()
        self.showdn_s()

    def set_default_params(self):

        for name in """
                user_filter
                user_member_attr
                group_attr_name
                group_enum_filter
                group_filter
                group_member_attr
                """.split():
            value = getattr(self.conf, name).strip()

            if not value or value == get_default_param(name, self.conf.type_):
                self.reset_field(name)
            else:
                self.set_field(name, value)

    def _getLineEdit(self, field):
        return getattr(self, "%s_lineedit" % field)

    def _getCheckbox(self, field):
        return getattr(self, "%s_checkbox" % field)

    def set_field(self, field, value):
        lineedit = lineedit = self._getLineEdit(field)
        lineedit.setEnabled(True)
        lineedit.setText(value)

        checkbox = self._getCheckbox(field)
        checkbox.setChecked(True)

    def reset_field(self, field):
        text = get_default_param(field, self.conf.type_)
        setattr(self.conf, field, text)  # No empty value in the conf.
        lineedit = self._getLineEdit(field)
        lineedit.setEnabled(False)
        lineedit.setText(text)

        checkbox = self._getCheckbox(field)
        checkbox.setChecked(False)

    def showdn_s(self):
        customizable_dn_s = self.conf.type_ != AD
        for entity in "user", "group":
            for widget_type in "label", "lineedit":
                widget = getattr(self, "%s_base_dn_%s" % (entity, widget_type))
                widget.setVisible(customizable_dn_s)

    def select_type(self, dirtype):
        button = getattr(self, "type_%s_radiobutton" % dirtype)
        button.setChecked(Qt.Checked)


    def fill(self, conf):
        self.name_lineedit.setText(conf.label)
        self.realm_lineedit.setText(conf.realm)
        self.select_type(conf.type_)
        self._set_type(conf.type_)

        for name in DEFAULT_PARAMS:
            lineedit = getattr(self, "%s_lineedit" % name)
            value = self._getValueOrDefault(name)
            lineedit.setText(value)

    def _getValueOrDefault(self, field):
        value = getattr(self.conf, field)
        if not value:
            value = get_default_param(field, self.conf.type_)

        return value

    def filldefaults(self, conf):
        type_ = AD
        conf.type_ = type_
        self.select_type(type_)
        self._set_type(conf.type_)

        for name in DEFAULT_PARAMS:
            #factor:
            #self.user_filter_lineedit.setText(
            #    get_default_param("user_filter", type_))
            lineedit = getattr(self, "%s_lineedit" % name)
            value = get_default_param(name, type_)
            lineedit.setText(value)


    def show_edits(self, dirtype):
        shown = SHOW_CONTROLS[dirtype]
        always = SHOW_CONTROLS["Always"]
        for name in DEFAULT_PARAMS:
            if name in always:
                continue
            for widgettype in "lineedit", "checkbox":
                widget = getattr(self, "%s_%s" % (name, widgettype))
                widget.setVisible(name in shown)

    def updateBindDn(self):
        for server in self.conf.servers:
            use_ldap = self.conf.type_ in (
                LDAP, EDIRECTORY)
            if server.bind_dn and not use_ldap:
                # Restore the bind_dn as the login if it was previously
                # derived from the user_base_dn.
                login = infer_login(server.bind_dn)
                previous_login_or_bind_dn = pretty_bind_dn(
                    server.bind_dn, self.nnd_widget.original_user_base_dn)
                if previous_login_or_bind_dn == login:
                    server.bind_dn = infer_bind_dn(
                        login, self.conf.user_base_dn)
        self.nnd_widget.original_user_base_dn = \
            self.conf.user_base_dn

    def delete_server(self, index):
        del self.conf.servers[index]

    def delete_server_cb(self):
        currentRow = self.server_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_server()
            return
        really = QMessageBox.question(
            self,
            tr("Confirm server deletion"),
            tr("Do you really want to delete this server?"),
            QMessageBox.Yes | QMessageBox.No
            )
        if really != QMessageBox.Yes:
            return

        self.delete_server(currentRow)
        self.server_table.removeRow(currentRow)

    def error_no_selected_server(self):
        self.nnd_widget.logwarning(tr(
            "Please select a server from the list to edit or delete it"
            ))

    def isExpert(self):
        return any(item.isChecked() for item in self.itercheckboxes())

    def itercheckboxes(self):
        yield self.user_filter_checkbox
        yield self.user_member_attr_checkbox
        yield self.group_attr_name_checkbox
        yield self.group_enum_filter_checkbox
        yield self.group_filter_checkbox
        yield self.group_member_attr_checkbox

    def edit_server_cb(self):
        currentRow = self.server_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_server()
            return
        self.nnd_widget.buildNndServerDialog(currentRow)

    def add_server_cb(self):
        self.nnd_widget.buildNndServerDialog()

    def move_server_down_cb(self):
        currentRow = self.server_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_server()
            return
        if currentRow < len(self.conf.servers) - 1:
            self.swap_servers(currentRow + 1, currentRow)

    def move_server_up_cb(self):
        currentRow = self.server_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_server()
            return
        if currentRow >= 1:
            self.swap_servers(currentRow - 1, currentRow)

    def swap_servers(self, new_index, old_index):
        tmp_server = self.conf.servers[new_index]
        self.conf.servers[new_index] = \
            self.conf.servers[old_index]
        self.conf.servers[old_index] = tmp_server
        self.nnd_widget.updateDomainView()
        self.server_table.setCurrentCell(new_index, 0)


