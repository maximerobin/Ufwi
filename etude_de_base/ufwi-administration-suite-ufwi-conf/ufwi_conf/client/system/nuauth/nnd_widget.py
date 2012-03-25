# -*- coding: utf-8 -*-

"""
Copyright (C) 2010-2011 EdenWall Technologies

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
from PyQt4.QtGui import (
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
    QTableWidgetSelectionRange,
    QWidget,
    )
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.colors import COLOR_WARNING
from ufwi_conf.common.user_dir.base import (
        NndDomain, NndServer, AD
        )
from .directory_widget import DirectoryWidget
from .nnd_base import infer_user_base_dn
from .nnd_domain import DomainDialog
from .nnd_global_ui import Ui_NndGlobal
from .nnd_server import ServerDialog

class NndWidget(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        DirectoryWidget.__init__(self, config, specific_config, mainwindow,
                                 parent=None)
        self.main_window = mainwindow
        self.changing_selectedRange = False
        self.buildInterface(config)
        self.updateView()

    def domain_summary(self, domain):
        return "%s %s" % (domain.type_, domain.realm)

    def updateView(self, config=None):
        if config is None:
            config = self.specific_config

        self.nnd_global.domain_table.setRowCount(len(config.domains))
        for row, (name, domain) in enumerate(sorted(config.domains.items())):
            self.nnd_global.domain_table.setItem(
                row, 0, QTableWidgetItem(name))
            if domain.label == self.specific_config.default_domain:
                self.nnd_global.domain_table.setItem(
                    row, 1, QTableWidgetItem(tr("Yes")))
            else:
                self.nnd_global.domain_table.setItem(
                    row, 1, QTableWidgetItem(""))
            self.nnd_global.domain_table.setItem(
                row, 2, QTableWidgetItem(self.domain_summary(domain)))
        self.nnd_global.domain_table.horizontalHeader().setResizeMode(
            QHeaderView.ResizeToContents)

    def buildInterface(self, config):
        widget = QWidget(self)
        self.nnd_global = Ui_NndGlobal()
        self.nnd_global.setupUi(widget)
        self.form.addRow(widget)

        for (button, callback) in (
            (self.nnd_global.add_button, self.add_domain_cb),
            (self.nnd_global.define_as_default_button, self.define_as_default_cb),
            (self.nnd_global.delete_button, self.delete_domain_cb),
            (self.nnd_global.edit_button, self.edit_domain_cb),
            ):
            self.connect(button, SIGNAL("clicked()"), callback)
        self.connect(
            self.nnd_global.domain_table,
            SIGNAL("cellDoubleClicked(int, int)"), self.edit_domain_cb)

        self.connect(self.nnd_global.domain_table,
                     SIGNAL("itemSelectionChanged()"),
                     self.global_select_current_row)

    # Domain dialog

    def buildNndDomainDialog(self, domain_key=None):
        if domain_key is None:
            self.tmp_domain_conf = NndDomain()
            name = ""
        else:
            self.tmp_domain_conf = self.specific_config.domains.get(
                domain_key, NndDomain()).copy()
            name = domain_key
        self.original_user_base_dn = self.tmp_domain_conf.user_base_dn
        self.nnd_domain = DomainDialog(self, self.tmp_domain_conf, name=name)
        domaingui = self.nnd_domain

        for name, lineedit in self._iterDomainNamesAndLineEdits():
            value = getattr(self.tmp_domain_conf, name)
            lineedit.setText(value)

        # Pre-fill form if editing a domain.

        if domain_key is not None:
            self.nnd_domain.fill(self.tmp_domain_conf)
        else:
            self.nnd_domain.filldefaults(self.tmp_domain_conf)

        self.nnd_domain.updateDomainView()
        domain_validation = domaingui.exec_()
        if domain_validation:
            self.update_domain(domain_key)
        self.nnd_domain = domaingui

    def delete_domain(self, domain_key):
        del(self.specific_config.domains[domain_key])
        # If this was the default domain, choose any remaining domain as the
        # default domain (if there is no more domain, then do not do anything,
        # the next domain added will be the default domain, and the admin
        # cannot save a config with no domain).
        if self.specific_config.default_domain == domain_key:
            self.specific_config.default_domain = ""
            for domain_name in self.specific_config.domains.keys():
                self.specific_config.default_domain = domain_name
                self.updateView()
                break

    def _iterDomainNamesAndLineEdits(self):
        for name in """
              user_filter
              user_member_attr
              group_attr_name
              group_enum_filter
              group_filter
              group_member_attr
              """.split():
          lineedit_name = "%s_lineedit" % name
          lineedit = getattr(self.nnd_domain, lineedit_name)
          yield name, lineedit

    def update_domain(self, domain_key):
        self.tmp_domain_conf.label = self.tmp_domain_conf.label.strip()
        # In case the domain is renamed.
        if (not self.specific_config.default_domain or
            self.specific_config.default_domain == domain_key):
            self.specific_config.default_domain = self.tmp_domain_conf.label

        for name, lineedit in self._iterDomainNamesAndLineEdits():
            value = unicode(lineedit.text())
            checkbox = self.nnd_domain._getCheckbox(name)
            if checkbox.isChecked():
                setattr(self.tmp_domain_conf, name, value)


        if not domain_key:
            if not self.specific_config.domains:
                # This domain is the first, so it is the default one.
                self.specific_config.default_domain = \
                    self.tmp_domain_conf.label
        else:
            if domain_key != self.tmp_domain_conf.label:
                self.delete_domain(domain_key)
        self.specific_config.domains[self.tmp_domain_conf.label] = \
            self.tmp_domain_conf
        self.signalModified()
        self.updateView()

    def error_no_selected_domain(self):
        self.logwarning(
            tr("Please select a domain from the list to edit or "
               "delete it")
            )

    # Server dialog

    def buildNndServerDialog(self, index=None):
        self.nnd_domain.updateBindDn()
        uncheck_anonymous = False
        if index is None:
            nnd_server = NndServer()
            if self.tmp_domain_conf.type_ == "AD":
                supposed_port = 3268
                uncheck_anonymous = True
            else:
                supposed_port = None
            nnd_server.supposed_port = supposed_port
            self.tmp_server_conf = nnd_server
        else:
            self.tmp_server_conf = self.tmp_domain_conf.servers[index].copy()

        name = self.tmp_server_conf.label
        self.nnd_server = nnd_server_dialog = ServerDialog(
            self,
            self.tmp_server_conf,
            self.tmp_domain_conf,
            name=name,
            )

        # Pre-fill form if editing a server.
        self.nnd_server.tls_checkbox.setChecked(self.tmp_server_conf.tls)
        self.nnd_server.check_cert_checkbox.setChecked(
            self.tmp_server_conf.checkcert)
        self.nnd_server.upload_ca_button.setDisabled(
            not self.tmp_server_conf.checkcert)

        if index is not None:
            self.nnd_server.name_lineedit.setText(
                self.tmp_server_conf.label)
            self.nnd_server.ldapuri_lineedit.setText(
                self.tmp_server_conf.ldapuri)

        # Show/hide widgets
        self.nnd_server.initialshowable()

        server_validation = nnd_server_dialog.exec_()
        if server_validation:
            self.update_server(index)
        self.nnd_domain.updateDomainView()

    def update_server(self, index):
        self.tmp_server_conf.label = self.tmp_server_conf.label.strip()
        if index is None:
            self.tmp_domain_conf.servers.append(self.tmp_server_conf)
        else:
            self.tmp_domain_conf.servers[index] = self.tmp_server_conf
        self.nnd_domain.updateDomainView()

    def select_current_row(self, table):
        if self.changing_selectedRange:
            return
        currentRow = table.currentRow()
        last_column_index = table.columnCount() - 1
        self.changing_selectedRange = True
        last_row_index = table.rowCount() - 1
        table.setRangeSelected(
            QTableWidgetSelectionRange(
                0, 0, last_row_index, last_column_index),
            False)
        table.setRangeSelected(
            QTableWidgetSelectionRange(
                currentRow, 0, currentRow, last_column_index),
            True)
        self.changing_selectedRange = False

    #############
    # Callbacks #
    #############

    # NND global

    def add_domain_cb(self):
        self.buildNndDomainDialog()

    def define_as_default_cb(self):
        currentRow = self.nnd_global.domain_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_domain()
            return
        key = self.nnd_global.domain_table.item(currentRow, 0)
        if key is None:  # Should not happen.
            self.error_no_selected_domain()
            return
        self.specific_config.default_domain = unicode(key.text())
        self.signalModified()
        self.updateView()

    def delete_domain_cb(self):
        currentRow = self.nnd_global.domain_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_domain()
            return
        key = self.nnd_global.domain_table.item(currentRow, 0)
        if key is None:  # Should not happen.
            self.error_no_selected_domain()
            return
        really = QMessageBox.question(
            self,
            tr("Confirm domain deletion"),
            tr("Do you really want to delete this domain?"),
            QMessageBox.Yes | QMessageBox.No
            )
        if really != QMessageBox.Yes:
            return
        self.delete_domain(unicode(key.text()))
        self.signalModified()
        self.updateView()

    def global_select_current_row(self, *unused):
        self.select_current_row(self.nnd_global.domain_table)

    def edit_domain_cb(self, *unused):
        currentRow = self.nnd_global.domain_table.currentRow()
        if currentRow < 0:
            self.error_no_selected_domain()
            return
        key = self.nnd_global.domain_table.item(currentRow, 0)
        if key is None:  # Should not happen.
            self.error_no_selected_domain()
            return
        self.buildNndDomainDialog(unicode(key.text()))

    # NND domain

    def domain_user_filter_cb(self):
        checked = self.nnd_domain.user_filter_checkbox.isChecked()
        self.nnd_domain.user_filter_lineedit.setDisabled(not checked)
        if not checked:
            self.nnd_domain.reset_field("user_filter")

    def domain_user_member_attr_cb(self):
        checked = self.nnd_domain.user_member_attr_checkbox.isChecked()
        self.nnd_domain.user_member_attr_lineedit.setDisabled(not checked)
        if not checked:
            self.nnd_domain.reset_field("user_member_attr")

    def domain_select_current_row(self, *unused):
        self.select_current_row(self.nnd_domain.server_table)

    def set_domain_name_cb(self, text):
        self.tmp_domain_conf.label = unicode(text)

    def set_realm_cb(self, text):
        self.tmp_domain_conf.realm = unicode(text)
        # We must infer user_base_dn at once so that it is available when
        # creating a server (which will "save" its user_bind_dn according to
        # the user_base_dn we infer before the domain dialog is validated).
        if self.tmp_domain_conf.type_ == AD:
            user_base_dn = infer_user_base_dn(
                self.tmp_domain_conf.realm)
            self.tmp_domain_conf.user_base_dn = user_base_dn
            # We use user_base_dn for group base DN too.
            self.tmp_domain_conf.group_base_dn = user_base_dn

    def set_user_base_dn_cb(self, text):
        self.tmp_domain_conf.user_base_dn = unicode(text)

    def set_user_filter_cb(self, text):
        self.tmp_domain_conf.user_filter = unicode(text)

    def set_user_member_attr_cb(self, text):
        self.tmp_domain_conf.user_member_attr = unicode(text)

    def set_group_attr_name_cb(self, text):
        self.tmp_domain_conf.group_attr_name = unicode(text)

    def set_group_base_dn_cb(self, text):
        self.tmp_domain_conf.group_base_dn = unicode(text)

    def set_group_enum_filter_cb(self, text):
        self.tmp_domain_conf.group_enum_filter = unicode(text)

    def set_group_filter_cb(self, text):
        self.tmp_domain_conf.group_filter = unicode(text)

    def set_group_member_attr_cb(self, text):
        self.tmp_domain_conf.group_member_attr = unicode(text)

    # NND server

    def set_server_tls_cb(self):
        self.tmp_server_conf.tls = bool(
            self.nnd_server.tls_checkbox.isChecked())

    def set_server_check_cert_cb(self):
        self.tmp_server_conf.checkcert = bool(
            self.nnd_server.check_cert_checkbox.isChecked())
        self.nnd_server.upload_ca_button.setDisabled(
            not self.nnd_server.check_cert_checkbox.isChecked())

    def user_base_dn_checkbox_cb(self):
        if self.nnd_server.user_base_dn_checkbox.isChecked():
            self.nnd_server.user_base_dn_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.user_base_dn = ""
            self.nnd_server.user_base_dn_lineedit.setText(
                self.tmp_domain_conf.user_base_dn)
            self.nnd_server.user_base_dn_lineedit.setDisabled(True)

    def user_filter_checkbox_cb(self):
        if self.nnd_server.user_filter_checkbox.isChecked():
            self.nnd_server.user_filter_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.user_filter = ""
            self.nnd_server.user_filter_lineedit.setText(
                self.tmp_domain_conf.user_filter)
            self.nnd_server.user_filter_lineedit.setDisabled(True)

    def user_member_attr_checkbox_cb(self):
        if self.nnd_server.user_member_attr_checkbox.isChecked():
            self.nnd_server.user_member_attr_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.user_member_attr = ""
            self.nnd_server.user_member_attr_lineedit.setText(
                self.tmp_domain_conf.user_member_attr)
            self.nnd_server.user_member_attr_lineedit.setDisabled(True)

    def group_attr_name_checkbox_cb(self):
        if self.nnd_server.group_attr_name_checkbox.isChecked():
            self.nnd_server.group_attr_name_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.group_attr_name = ""
            self.nnd_server.group_attr_name_lineedit.setText(
                self.tmp_domain_conf.group_attr_name)
            self.nnd_server.group_attr_name_lineedit.setDisabled(True)

    def group_base_dn_checkbox_cb(self):
        if self.nnd_server.group_base_dn_checkbox.isChecked():
            self.nnd_server.group_base_dn_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.group_base_dn = ""
            self.nnd_server.group_base_dn_lineedit.setText(
                self.tmp_domain_conf.group_base_dn)
            self.nnd_server.group_base_dn_lineedit.setDisabled(True)

    def group_enum_filter_checkbox_cb(self):
        if self.nnd_server.group_enum_filter_checkbox.isChecked():
            self.nnd_server.group_enum_filter_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.group_enum_filter = ""
            self.nnd_server.group_enum_filter_lineedit.setText(
                self.tmp_domain_conf.group_enum_filter)
            self.nnd_server.group_enum_filter_lineedit.setDisabled(True)

    def group_filter_checkbox_cb(self):
        if self.nnd_server.group_filter_checkbox.isChecked():
            self.nnd_server.group_filter_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.group_filter = ""
            self.nnd_server.group_filter_lineedit.setText(
                self.tmp_domain_conf.group_filter)
            self.nnd_server.group_filter_lineedit.setDisabled(True)

    def group_member_attr_checkbox_cb(self):
        if self.nnd_server.group_member_attr_checkbox.isChecked():
            self.nnd_server.group_member_attr_lineedit.setDisabled(False)
        else:
            self.tmp_server_conf.group_member_attr = ""
            self.nnd_server.group_member_attr_lineedit.setText(
                self.tmp_domain_conf.group_member_attr)
            self.nnd_server.group_member_attr_lineedit.setDisabled(True)

    def logwarning(self, message):
        self.main_window.addToInfoArea(message, category=COLOR_WARNING)

