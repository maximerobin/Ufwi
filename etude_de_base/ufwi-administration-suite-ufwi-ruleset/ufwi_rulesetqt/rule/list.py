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

from itertools import izip

from PyQt4.QtCore import SIGNAL, Qt
from PyQt4.QtGui import (QAbstractItemView, QHBoxLayout,
    QTableWidget, QTableWidgetItem)

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.tools import QTableWidget_resizeWidgets, getSelectionRows
from ufwi_rpcc_qt.html import htmlTable, htmlLink

from ufwi_rulesetqt.rule.iptables_dialog import IptablesDialog, LdapDialog
from ufwi_rulesetqt.rule.menu import RuleMenu
from ufwi_rulesetqt.tools import getDragUrl
from ufwi_rulesetqt.html import htmlTitle

class RulesList:
    RULES_STACK_INDEX = None
    EDIT_STACK_INDEX = None

    def __init__(self, window, model, table, rule_type, widget_prefix, edit):
        self.window = window
        self.model = model
        self.ui = window.ui
        self.resources = window.getLibrary('resources')
        self.protocols = window.getLibrary('protocols')
        self.ruleset = window.ruleset
        self.move_rule_dialog = window.move_rule_dialog
        self.rule_type = rule_type
        self.widget_prefix = widget_prefix
        self._edit = edit
        self.iptables = IptablesDialog(window)
        self.ldap = LdapDialog(window)
        self.table = table
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.window.selection_widgets.append(self.table)
        self.menu = RuleMenu(self)
        self.acl_headers = {} # row => Chain object
        self.acl_row2id = {} # row => acl identifier (int)
        self.acl_id2row = {} # acl identifier (int) => row
        self.acl_id2line = {} # acl identifier (int) => line number
        self.row_count = None

        self.filter_frame = self.getWidget('filter_layout')
        self.filter_layout = QHBoxLayout(self.filter_frame)
        self.filter_layout.setContentsMargins(0, 0, 0, 0)
        self.filter_layout.addStretch()
        self.filter_frame.setLayout(self.filter_layout)
        self.filter_frame.setContentsMargins(0, 0, 0, 0)
        self.filter = None   # RuleFilter
        self.setupWindow()
        self.setButtonsEnabled()

        self.url_prefix = self.rule_type + u":"
        self.edit_format = "edit:" + self.url_prefix + "%s"
        self.highlight_format = "highlight:" + self.url_prefix + "%s"

        if self.window.compatibility.has_move_rule:
            self.table.setDragEnabled(True)
            self.table.setAcceptDrops(True)
            self.table.startDrag = self.startDrag
            self.table.dragEnterEvent = self.dragEnterEvent
            self.table.dragMoveEvent = self.dragMoveEvent
            self.table.dropEvent = self.dropEvent

    def getUrlIdentifier(self, url):
        prefix = self.url_prefix
        if not url.startswith(prefix):
            return
        return int(url[len(prefix):])

    def getWidget(self, name):
        return getattr(self.ui, "%s_%s" % (self.widget_prefix, name))

    def getButton(self, name):
        return self.getWidget("%s_button" % name)

    def connectButtonSignal(self, widget_name, function):
        widget = self.getButton(widget_name)
        self.window.connect(widget, SIGNAL("clicked()"), function)

    def setupWindow(self):
        self.connectButtonSignal("create", self.create)
        self.connectButtonSignal("delete", self.delete)
        self.connectButtonSignal("up", self.moveUp)
        self.connectButtonSignal("down", self.moveDown)
        self.connectButtonSignal("edit", self.edit)
        self.connectButtonSignal("clone", self.clone)

        self.table.connect(self.table, SIGNAL("cellDoubleClicked (int, int)"), self.doubleClick)
        self.window.connect(
            self.table.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selectionChanged)

        self.table.keyPressEvent = self.keyHandler
        self.table.contextMenuEvent = self.contextMenuEvent

        # Filter
        widget = self.filter_frame
        widget.dropEvent = self.filterDropEvent
        widget.dragEnterEvent = self.filterDragEnterEvent
        widget.dragMoveEvent = self.filterDragMoveEvent
        widget.setAcceptDrops(True)

    def filterDragEnterEvent(self, event):
        url = getDragUrl(event)
        if url is None:
            event.ignore()
            return
        if self.filter.dragEnter(url):
            event.accept()
        else:
            event.ignore()

    def filterDragMoveEvent(self, event):
        event.accept()

    def filterDropEvent(self, event):
        url = getDragUrl(event)
        if url is None:
            event.ignore()
            return
        if self.filter.drop(url):
            event.accept()
        else:
            event.ignore()

    def selectionChanged(self, row=None, col=None):
        identifiers = self.currentAcls()
        if 0 < len(identifiers):
            self.information(identifiers[0], highlight=False)
        self.setButtonsEnabled(identifiers)
        if 0 < len(identifiers):
            for widget in self.window.selection_widgets:
                if widget is self.table:
                    continue
                widget.clearSelection()

    def doubleClick(self, row, column):
        if self.ruleset.read_only:
            return
        if row in self.acl_row2id:
            acl_id = self.acl_row2id[row]
            self.edit(acl_id)
        elif row in self.acl_headers:
            if not self.window.compatibility.default_decisions:
                # default decisions are not supported by the server
                return
            chain = self.acl_headers[row]
            chain.editDefaultDecision(self.window, self)

    def keyHandler(self, event):
        if event.key() == Qt.Key_Return:
            self.edit()
            event.accept()
            return
        elif event.key() == Qt.Key_Delete:
            self.delete()
            event.accept()
            return

        QTableWidget.keyPressEvent(self.table, event)

    def edit(self, acl_id=None, highlight=None):
        if self.ruleset.read_only:
            return
        acl_stack = self.window.acl_stack
        if acl_stack.currentIndex() == self.EDIT_STACK_INDEX:
            return
        if acl_id is None:
            acl_ids = self.currentAcls()
            if len(acl_ids) != 1:
                return
            acl_id = acl_ids[0]
        acl = self[acl_id]
        if not acl['editable']:
            return
        self._edit.editRule(self, acl, highlight)
        acl_stack.setCurrentIndex(self.EDIT_STACK_INDEX)

    def updateDict(self):
        self.acl_headers.clear()
        self.acl_row2id.clear()
        self.acl_id2row.clear()
        self.acl_id2line.clear()
        chains = self.getChains()
        row = 0
        for chain in chains.itervalues():
            ignore_list = [(not self.filter.match(rule))
                for rule in chain]
            if not all(ignore_list):
                self.acl_headers[row] = chain
                row += 1
            acl_line = 0
            for rule, ignore in izip(chain, ignore_list):
                acl_line += 1
                if ignore:
                    continue
                rule_id = rule['id']
                self.acl_row2id[row] = rule_id
                self.acl_id2row[rule_id] = row
                self.acl_id2line[rule_id] = acl_line
                row += 1
        self.row_count = row

    def refresh(self, all_updates, updates):
        identifiers = updates.partialUpdate()
        if identifiers:
            for acl_id in identifiers:
                self.model.refreshRule(acl_id)
        else:
            self.model.refresh(all_updates, updates)

    def display(self, updates, highlight=False):
        identifiers = updates.partialUpdate()
        if identifiers:
            for acl_id in identifiers:
                acl = self[acl_id]
                try:
                    row = self.acl_id2row[acl_id]
                except KeyError:
                    # Hidden rule: nothing to do
                    continue
                acl_line = self.acl_id2line[acl_id]
                item = QTableWidgetItem(unicode(acl_line))
                self.table.setVerticalHeaderItem(row, item)
                self.fillAclRow(row, acl)
            QTableWidget_resizeWidgets(self.table)
        else:
            self.fill()
        if highlight:
            identifier = updates.getHighlightId()
            if identifier:
                self.information(identifier, highlight=True)

    def fill(self):
        self.updateDict()
        self.table.clear()
        self.table.clearSpans()
        columns = self.getColumns()
        self.table.setColumnCount(len(columns))
        self.table.setHorizontalHeaderLabels(columns)
        self.table.setRowCount(self.row_count)
        for row, chain in self.acl_headers.iteritems():
            self.table.setVerticalHeaderItem(row, QTableWidgetItem(u""))
            self.fillHeader(row, chain)
        for row, rule_id in self.acl_row2id.iteritems():
            rule = self[rule_id]
            if not self.filter.match(rule):
                continue
            acl_line = self.acl_id2line[rule_id]
            item = QTableWidgetItem(unicode(acl_line))
            self.table.setVerticalHeaderItem(row, item)
            self.fillAclRow(row, rule)
        QTableWidget_resizeWidgets(self.table)
        self.setButtonsEnabled()

    def information(self, rule_id, highlight=True):
        try:
            rule = self[rule_id]
        except KeyError:
            return
        title, options = rule.createInformation()
        title = tr('%s:') % title
        if self.window.debug:
            rule.createDebugOptions(options)
        if rule['editable']:
            url = self.edit_format % rule['id']
            title = htmlLink(url, title)
        html = htmlTitle(title) + htmlTable(options)
        self.window.setInfo(html, background=rule.getBackground())
        if highlight:
            self.highlight(rule_id, information=False)

    def fillHeader(self, row, chain):
        self.table.setSpan(row, 0, 1, self.table.columnCount())
        item = chain.createTableWidgetItem()
        self.table.setItem(row, 0, item)

    def currentAcls(self):
        selections = self.table.selectionModel().selection()
        acls = []
        for row in getSelectionRows(selections):
            try:
                acl_id = self.acl_row2id[row]
            except KeyError:
                # It's an header: skip it
                continue
            acls.append(acl_id)
        return acls

    def create(self, position=None):
        self.window.acl_stack.setCurrentIndex(self.EDIT_STACK_INDEX)
        self._edit.create(self, position)

    def clone(self):
        acl_ids = self.currentAcls()
        if len(acl_ids) != 1:
            return
        self.cloneAcl(acl_ids[0])

    def cloneAcl(self, old_id):
        try:
            updates = self.ruleset('ruleClone', self.rule_type, old_id)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)

    def moveUp(self, rule_id=None):
        self._moveAcl(rule_id, 'ruleUp')

    def moveDown(self, rule_id=None):
        self._moveAcl(rule_id, 'ruleDown')

    def moveAt(self, rule_id):
        rule = self[rule_id]
        self.move_rule_dialog.moveRule(self.rule_type, rule)

    def _moveAcl(self, rule_id, service):
        if self.window.useFusion():
            self.window.error(
                tr("It is not possible to move rules if fusion is enabled."))
            return
        if rule_id is None:
            rule_ids = self.currentAcls()
            if len(rule_ids) != 1:
                return
            rule_id = rule_ids[0]
        try:
            updates = self.ruleset(service, self.rule_type, rule_id)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)

    def delete(self, acl_ids=None):
        if not acl_ids:
            acl_ids = self.currentAcls()
        if not acl_ids:
            return
        try:
            updates = self.ruleset('ruleDelete', self.rule_type, acl_ids)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)

    def _getIdentifiers(self, identifiers=None):
        if not identifiers:
            identifiers = self.currentAcls()
        if not identifiers:
            identifiers = tuple()
        return identifiers

    def iptablesRules(self, identifiers=None):
        identifiers = self._getIdentifiers(identifiers)
        self.iptables.displayRules(self.rule_type, identifiers)

    def ldapRules(self, identifiers=None):
        identifiers = self._getIdentifiers(identifiers)
        self.ldap.displayRules(self.rule_type, identifiers)

    def contextMenuEvent(self, event):
        acl_ids = self.currentAcls()
        self.menu.display(event, acl_ids, self.rule_type == 'nat')

    def highlight(self, acl_id, information=True):
        self.window.main_tab.setCurrentIndex(self.RULES_STACK_INDEX)
        try:
            row = self.acl_id2row[acl_id]
        except KeyError:
            return False
        self.table.setCurrentCell(row, 0)
        if information:
            self.information(acl_id, highlight=False)
        return True

    def displayChain(self, updates, highlight=False):
        self.fill()
        if highlight:
            rule_id = updates.getHighlightId()
            if rule_id:
                self.information(rule_id)

    def __getitem__(self, identifier):
        return self.model[identifier]

    def getChain(self, acl):
        return self.model.getChain(acl)

    def getChains(self):
        return self.model.chains

    def setReadOnly(self, read_only):
        for name in ("create", "delete", "edit", "up", "down", "clone"):
            button = self.getButton(name)
            if read_only:
                button.hide()
            else:
                button.show()

    def startDrag(self, event):
        identifiers = self.currentAcls()
        if len(identifiers) != 1:
            return
        identifier = identifiers[0]
        rule = self[identifier]
        if not rule['editable']:
            return
        text = u"%s:%s" % (self.rule_type, identifier)
        icon = None
        self.window.startDragText(self.table, text, icon)

    def _getDragIdentifier(self, event):
        url = getDragUrl(event)
        if url is None:
            return None
        if not url.startswith(self.rule_type+':'):
            return None
        ignore = len(self.rule_type) + 1
        return int(url[ignore:])

    def dragEnterEvent(self, event):
        if self.window.read_only:
            event.ignore()
            return
        identifier = self._getDragIdentifier(event)
        if identifier is None:
            event.ignore()
        else:
            event.accept()

    def _getDragRules(self, event):
        src_id = self._getDragIdentifier(event)
        index = self.table.indexAt(event.pos())
        row = index.row()
        try:
            dst_id = self.acl_row2id[row]
        except KeyError:
            return None
        if src_id == dst_id:
            return None
        dst = self[dst_id]
        if not dst['editable']:
            return None
        src = self[src_id]
        if src.getChain() != dst.getChain():
            return None
        return (src, dst)

    def dragMoveEvent(self, event):
        src_dst = self._getDragRules(event)
        if src_dst is None:
            event.ignore()
            return
        event.accept()

    def dropEvent(self, event):
        src, dst = self._getDragRules(event)
        src_order = src.getOrder()
        dst_order = dst.getOrder()
        event.acceptProposedAction()
        try:
            updates = self.ruleset('moveRule', self.rule_type, src['id'], dst_order)
        except Exception, err:
            self.window.exception(err)
            return
        self.window.refresh(updates)

    # --- abstract methods -------------------

    @abstractmethod
    def setButtonsEnabled(self, identifiers=None):
        pass

    @abstractmethod
    def refreshChain(self, all_updates, updates):
        pass

    @abstractmethod
    def fillAclRow(self, row, rule):
        pass

