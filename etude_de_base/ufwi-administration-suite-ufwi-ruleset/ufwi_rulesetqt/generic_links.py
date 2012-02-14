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

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import QTableWidgetItem, QDialog, QIcon

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.multisite import MULTISITE_MASTER
from ufwi_rpcc_qt.tools import getSelectionRows, unsetFlag

from ufwi_ruleset.common.network import INTERFACE_RESTYPE, NETWORK_RESTYPE, HOST_RESTYPE

from ufwi_rulesetqt.generic_links_ui import Ui_Dialog
from ufwi_rulesetqt.generic_links_copy_ui import Ui_Dialog as CopyUiDialog
from ufwi_rulesetqt.dialog import RulesetDialog
from ufwi_rulesetqt.resources import Resource
from ufwi_rulesetqt.user_groups import USER_GROUP_ICON

KEYS = ('interfaces', 'networks', 'hosts', 'user_groups')

ICONS = {
    'interfaces': Resource.ICONS[INTERFACE_RESTYPE],
    'networks': Resource.ICONS[NETWORK_RESTYPE],
    'hosts': Resource.ICONS[HOST_RESTYPE],
    'user_groups': USER_GROUP_ICON}

class GenericLinks(dict):
    def __init__(self, links=None):
        if links:
            self.update(links)
        else:
            for key in KEYS:
                self[key] = {}

class GenericLinksDialog(RulesetDialog):
    def __init__(self, window, save_callback):
        self.ui = Ui_Dialog()
        RulesetDialog.__init__(self, window)
        self.ui.setupUi(self)
        self.setupDialog()
        self.save_callback = save_callback

    def setupDialog(self):
        self.ui.table.verticalHeader().hide()
        self.connectButtons(self.ui.buttonBox)
        self.connect(self.ui.table.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selectionChanged)
        self.connect(self.ui.delete_button, SIGNAL("clicked()"), self.delete)
        self.connect(self.ui.copyto_button, SIGNAL("clicked()"), self.copyLinks)
        self.connect(self.ui.hide_defined, SIGNAL("clicked()"), self.showHideDefined)
        self.connect(self.ui.table, SIGNAL("cellChanged(int, int)"), self.cellChanged)

        if self.window.multisite_type == MULTISITE_MASTER:
            self.connect(self.ui.hosts_combo, SIGNAL("currentIndexChanged ( int )"), self.currentHostChanged)
        else:
            self.ui.table.hideColumn(0)
            self.ui.hosts_combo.setVisible(False)
            self.ui.copyto_button.setVisible(False)

    def cellChanged(self, row, column):
        # Select the next row when we are finished editing the current one
        row += 1
        while row < self.ui.table.rowCount() and self.ui.table.isRowHidden(row):
            row += 1
        if row < self.ui.table.rowCount():
            self.ui.table.setCurrentCell(row, column)

    def selectionChanged(self, selected=None, deselected=None):
        rows = getSelectionRows(selected)
        self.ui.delete_button.setEnabled(bool(rows))

    def saveTableLinks(self):
        table_entries = self.getCurrentLinks()

        for host in table_entries.iterkeys():
            for type, links in table_entries[host].iteritems():
                if type not in self.links_list[host]:
                    self.links_list[host][type] = {}
                self.links_list[host][type].update(links)

    def currentHostChanged(self, index):
        if index == -1:
            return

        if index == 0:
            self.ui.copyto_button.setEnabled(False)
        else:
            self.ui.copyto_button.setEnabled(True)
        self.saveTableLinks()
        self.fillTable()

    def showHideDefined(self):
        if self.window.multisite_type == MULTISITE_MASTER:
            new_links = self.getCurrentLinks()
        self.saveTableLinks()
        self.fillTable()

    def delete(self):
        table = self.ui.table
        selection = table.selectionModel().selection()
        rows = getSelectionRows(selection)
        row = rows[0]
        self.saveTableLinks()
        host = unicode(table.item(row, 0).text())
        type = unicode(table.item(row, 1).text())
        generic = unicode(table.item(row, 2).text())
        del self.links_list[host][type][generic]
        self.fillTable()

    def fill(self):
        self.ui.hosts_combo.clear()
        if self.window.multisite_type == MULTISITE_MASTER:
            # Fill the host combo box
            lst = self.links_list.keys()
            lst.sort()
            self.ui.hosts_combo.addItem(tr("All firewalls"))
            for links in lst:
                self.ui.hosts_combo.addItem(links)
        self.fillTable()

    def fillTable(self):
        table = self.ui.table

        table.clear()
        columns = [tr("Host"), tr("Type"), tr("Generic"), tr("Physical")]
        table.setColumnCount(len(columns))
        table.setHorizontalHeaderLabels(columns)

        table_entries = {}
        if self.window.multisite_type == MULTISITE_MASTER:
            if self.ui.hosts_combo.currentIndex() == 0:
                table.showColumn(0)
                table_entries = self.links_list
            else:
                table.hideColumn(0)
                table_entries = { unicode(self.ui.hosts_combo.currentText()) : self.links_list[unicode(self.ui.hosts_combo.currentText())] }
        else:
            table_entries = self.links_list

        count = 0
        for host in table_entries.iterkeys():
            count += sum(len(type_links) for type_links in table_entries[host].itervalues())
        table.setRowCount(count)
        row = 0

        for host in table_entries.iterkeys():
            for type, links in table_entries[host].iteritems():
                for generic_id, physical in links.iteritems():
                    # Hostname
                    item = QTableWidgetItem(QIcon(Resource.ICONS[HOST_RESTYPE]), host)
                    unsetFlag(item, Qt.ItemIsEditable)
                    table.setItem(row, 0, item)

                    # Type
                    item = QTableWidgetItem(QIcon(ICONS[type]), type)
                    unsetFlag(item, Qt.ItemIsEditable)
                    table.setItem(row, 1, item)

                    # Generic ID
                    item = QTableWidgetItem(generic_id)
                    unsetFlag(item, Qt.ItemIsEditable)
                    table.setItem(row, 2, item)

                    # Physical ID
                    item = QTableWidgetItem(physical)
                    table.setItem(row, 3, item)

                    # Hide the row if the value is set
                    if self.ui.hide_defined.isChecked() and physical:
                        table.hideRow(row)
                    else:
                        table.showRow(row)
                    row += 1
        table.resizeColumnsToContents()

    def modify(self, links, fw = None):
        if self.window.multisite_type == MULTISITE_MASTER:
            self.links_list = links
        else:
            self.links_list = {u'local' : links}

        self.fill()

        if fw is not None:
            index = self.ui.hosts_combo.findText(fw)
            if index != -1:
                self.ui.hosts_combo.setCurrentIndex(index)
        self.selectionChanged()
        self.execLoop()

    def save(self):
        return self.save_callback()

    def getCurrentLinks(self):
        links = GenericLinks()
        table = self.ui.table
        for row in xrange(table.rowCount()):
            host = unicode(table.item(row, 0).text())
            type = unicode(table.item(row, 1).text())
            generic = unicode(table.item(row, 2).text())
            physical = unicode(table.item(row, 3).text())
            if type not in links:
                raise Exception("Unknown link type: %s" % type)
            if host not in links:
                links[host] = GenericLinks()
            links[host][type][generic] = physical
        return links

    def refresh(self, all_updates, updates):
        pass

    def display(self, updates, highlight=False):
        pass

    def getLinks(self):
        # save the current table
        self.saveTableLinks()
        if self.window.multisite_type == MULTISITE_MASTER:
            return self.links_list
        return self.links_list['local']

    def copyLinks(self):
        dlg = QDialog(self)
        copy_dlg = CopyUiDialog()
        copy_dlg.setupUi(dlg)
        copy_dlg.copyto_label.setText(tr("Copy the generic links from the %s host to the host:") % self.ui.hosts_combo.currentText())
        copy_dlg.copyto_combo.clear()
        for host_no, host in enumerate(self.links_list.keys()):
            if host != unicode(self.ui.hosts_combo.currentText()):
                copy_dlg.copyto_combo.addItem(host)

        if dlg.exec_():
            src_links = unicode(self.ui.hosts_combo.currentText())
            dst_links = unicode(copy_dlg.copyto_combo.currentText())
            self.links_list[dst_links] = self.links_list[src_links]
