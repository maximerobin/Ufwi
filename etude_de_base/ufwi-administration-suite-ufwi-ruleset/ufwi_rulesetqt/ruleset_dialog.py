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
from os.path import dirname

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import (QDialog, QMessageBox, QTableWidgetItem,
    QFileDialog, QHeaderView)

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.download import encodeFileContent, decodeFileContent

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.html import htmlBold

from ufwi_rulesetqt.ruleset_dialog_ui import Ui_Dialog

class RulesetDialog(QDialog, Ui_Dialog):
    def __init__(self, window):
        QDialog.__init__(self, window)
        self.directory = u""
        self.setupUi(self)
        self.setupDialog(window)
        self.run()

    def setupDialog(self, window):
        self.window = window
        self.ruleset = window.ruleset
        # tab index => file type
        self.filetypes = ['ruleset', 'template']
        self.tables = {
            # file type => table widget
            'ruleset': self.ruleset_table,
            'template': self.template_table}
        self.connect(self.ruleset_tab,
            SIGNAL("currentChanged(int)"), self.tabChanged)
        self.connect(self.create_button,
            SIGNAL("clicked()"), self.createRuleset)
        self.connect(self.download_button,
            SIGNAL("clicked()"), self.downloadRuleset)
        self.connect(self.upload_button,
            SIGNAL("clicked()"), self.uploadRuleset)
        self.connect(self.delete_button,
            SIGNAL("clicked()"), self.deleteRuleset)
        for table in self.tables.itervalues():
            self.setupTable(table)
        if window.read_only:
            for button in (self.create_button, self.upload_button):
                button.setEnabled(False)
        self.current_table = self.ruleset_table
        self.filetype = "ruleset"
        if not self.fillTables():
            return
        self.selectRuleset()

    def run(self):
        ret = self.exec_()
        # on a delete the window is still exited with a cancel
        self.window.EAS_SendMessage('ew4_multisite', 'update_templates')
        if not ret:
            return
        name = self.currentName()
        self.window.rulesetOpen(self.filetype, name)

    def tabChanged(self, tabindex):
        self.filetype = self.filetypes[tabindex]
        self.current_table = self.tables[self.filetype]
        self.selectRuleset()

    def setupTable(self, table):
        table.setSortingEnabled(True)
        table.sortItems(0)
        table.verticalHeader().hide()
        table.horizontalHeader().setStretchLastSection(True)
        self.connect(table,
            SIGNAL("itemSelectionChanged()"), self.selectRuleset)
        self.connect(table,
            SIGNAL("cellDoubleClicked(int, int)"), self.doubleClick)
        table.horizontalHeader().setResizeMode(QHeaderView.ResizeToContents)

    def doubleClick(self, row, cl):
        self.accept()

    def selectRuleset(self):
        name = self.currentName()
        has_name = bool(name)
        self.open_button.setEnabled(has_name)
        self.download_button.setEnabled(has_name)
        enable_delete = (not self.window.read_only) and has_name and (name != self.ruleset.ruleset_name)
        self.delete_button.setEnabled(enable_delete)

    def currentName(self):
        table = self.current_table
        row = table.currentRow()
        try:
            item = table.item(row, 0)
            if not item:
                return None
        except IndexError:
            return None
        return unicode(item.text())

    def uploadRuleset(self):
        # Get the filename
        filename = QFileDialog.getOpenFileName(self.window,
            tr("Select rule set or template to import"),
            self.directory,
            tr("XML files (*.xml)"))
        filename = unicode(filename)
        if not filename:
            return

        # Read file content
        try:
            with open(filename, 'rb') as fp:
                content = fp.read()
        except IOError, err:
            self.window.error(
                tr('Unable to read "%s" file content: %s')
                % (filename, exceptionAsUnicode(err)),
                dialog=True)
            return

        # Send the ruleset content
        content = encodeFileContent(content)
        try:
            name = self.ruleset('rulesetUpload', self.filetype, filename, content)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.directory = dirname(filename)

        if self.filetype == "template":
            text = tr('Template "%s" uploaded.') % name
        else:
            text = tr('Rule set "%s" uploaded.') % name
        self.fillTables()
        self.selectRuleset()
        self.window.information(text, dialog=True)

    def createRuleset(self):
        self.reject()
        self.window.rulesetCreate()

    def downloadRuleset(self):
        # Ask destination filename
        name = self.currentName()
        if self.filetype == "template":
            title = tr('Save template "%s" as') % name
        else:
            title = tr('Save rule set "%s" as') % name
        dialog = QFileDialog(self.window,
            title,
            self.directory,
            tr("XML files (*.xml)"))
        dialog.setAcceptMode(QFileDialog.AcceptSave)
        dialog.setConfirmOverwrite(True)
        dialog.setDefaultSuffix("xml")
        dialog.selectFile(u"%s.xml" % name)
        if not dialog.exec_():
            return
        filename = unicode(dialog.selectedFiles()[0])

        # Retreive the ruleset content
        try:
            content = self.ruleset('rulesetDownload', self.filetype, name)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        content = decodeFileContent(content)

        # Write the ruleset to disk
        with open(filename, 'wb') as fp:
            fp.write(content)
        self.directory = dirname(filename)
        if self.filetype == "template":
            text = tr('Template "%s" saved to %s.') % (name, filename)
        else:
            text = tr('Rule set "%s" saved to %s.') % (name, filename)
        self.reject()
        self.window.information(text, dialog=True)

    def deleteRuleset(self):
        name = self.currentName()
        choice = QMessageBox.question(self,
            tr("Firewall"),
            tr('Do you really want to delete the rule set "%s"?') % htmlBold(name),
            QMessageBox.Yes | QMessageBox.Cancel,
            QMessageBox.Cancel)
        if choice != QMessageBox.Yes:
            return
        try:
            self.ruleset('rulesetDelete', self.filetype, name)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        text = tr('"%s" rule set deleted.') % name
        self.fillTables()
        self.selectRuleset()
        self.window.information(text)

    def fillTable(self, table, filetype):
        if filetype == 'template':
            column_name = tr('Template')
        else:
            column_name = tr('Rule set')
        try:
            rulesets = self.ruleset('rulesetList', filetype)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return False
        table.setSortingEnabled(False)
        table.clear()
        table.setHorizontalHeaderLabels([column_name, tr('Last edited')])
        table.setRowCount(len(rulesets))
        for no, (name, timestamp) in enumerate(rulesets):
            table.setItem(no, 1, QTableWidgetItem(timestamp))
            table.setItem(no, 0, QTableWidgetItem(name))
        table.resizeColumnsToContents()
        table.setSortingEnabled(True)
        return True

    def fillTables(self):
        for filetype, table in self.tables.iteritems():
            if not self.fillTable(table, filetype):
                return False
        return True

