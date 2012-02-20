"""
Copyright (C) 2009-2011 EdenWall Technologies

Written by Victor Stinner <vstinner AT edenwall.com>
Modified by Pierre-Louis Bonicoli <bonicoli@edenwall.com>

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
from PyQt4.QtGui import QListWidget, QListWidgetItem, QIcon, QMenu

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.tools import getSelectionRows, QListWidget_setCurrentText
from ufwi_rpcc_qt.colors import COLOR_DISABLED

from ufwi_rulesetqt.tools import getIdentifiers, getDragUrl
from ufwi_rulesetqt.objects import Group
from ufwi_rulesetqt.platform import Platform
from ufwi_rulesetqt.rule.tools import showLibrary

class EditMenu(QMenu):
    def __init__(self, widget, delete_handler):
        QMenu.__init__(self)
        self.delete_action = self.addAction(tr("Delete"))
        widget.connect(self.delete_action, SIGNAL("triggered()"), delete_handler)

    def display(self, event, can_delete):
        self.delete_action.setEnabled(can_delete)
        self.exec_(event.globalPos())

class EditList(object):
    """
    Manage a list of objects (eg. list of protocols).
    """
    def __init__(self, parent, widget, use_validator, object_list, accept_groups, *libraries):
        self.parent = parent
        self.widget = widget
        self.object_list = object_list
        self.libraries = libraries
        self.use_validator = use_validator
        self.window = self.parent.window
        self.window.connect(widget.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selectionChanged)
        widget.setAcceptDrops(True)
        widget.mousePressEvent = self.mousePressEvent
        widget.dragEnterEvent = self.dragEnterEvent
        widget.dragMoveEvent = self.dragMoveEvent
        widget.dropEvent = self.dropEvent
        widget.keyPressEvent = self.keyHandler
        self.objects = []
        self.menu = EditMenu(widget, self.removeRow)
        widget.contextMenuEvent = self.contextMenuEvent
        self.accept_groups = accept_groups
        self.delete_button = None
        self.empty_allowed = False

    def setEmptyAllowed(self, empty_allowed):
        self.empty_allowed = empty_allowed

    def setDeleteButton(self, button):
        self.delete_button = button
        button.connect(button, SIGNAL("clicked()"), self.removeRow)
        can_delete = (0 <= self.widget.currentRow())
        self.delete_button.setEnabled(can_delete)

    def acceptableInput(self):
        """True is the list contains at least one object or if empty allowed"""
        return self.empty_allowed or bool(self.objects)

    def keyHandler(self, event):
        if event.key() == Qt.Key_Delete:
            self.menu.delete_action.trigger()
            event.accept()
            return
        QListWidget.keyPressEvent(self.widget, event)

    def mousePressEvent(self, event):
        self.widget.__class__.mousePressEvent(self.widget, event)
        selection = self.widget.selectedItems()
        if selection:
            return
        showLibrary(self.window, self.libraries)

    def contextMenuEvent(self, event):
        if self.delete_button:
            return
        can_delete = (0 <= self.widget.currentRow())
        self.menu.display(event, can_delete)

    def dragEnterEvent(self, event):
        url = getDragUrl(event)
        if url is None:
            event.ignore()
            return
        for library in self.libraries:
            identifier = library.getUrlIdentifier(url)
            if identifier is not None:
                event.accept()
                return
        event.ignore()

    def dragMoveEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        url = getDragUrl(event)
        if url is None:
            event.ignore()
            return
        event.acceptProposedAction()
        for library in self.libraries:
            identifier = library.getUrlIdentifier(url)
            if identifier is None:
                continue
            object = library[identifier]

            if isinstance(object, Group) and not self.accept_groups:
                return
            break
        if object in self.objects:
            return
        self.objects.append(object)
        icon = object.getIcon()
        if icon:
            item = QListWidgetItem(QIcon(icon), identifier)
        else:
            item = QListWidgetItem(identifier)
        self.widget.addItem(item)
        self.widget.emit(SIGNAL('objectDrop()'))
        self._updateValidator()

    def _getSelectionObject(self, selected):
        rows = getSelectionRows(selected)
        if not rows:
            return None
        row = rows[0]
        try:
            return self.objects[row]
        except IndexError:
            # Invalid index: ignore
            return None

    def selectionChanged(self, selected, unselected):
        object = self._getSelectionObject(selected)
        if object is None:
            if self.delete_button:
                self.delete_button.setEnabled(False)
            return
        object.information()
        for edit_list in self.object_list.itervalues():
            if edit_list is self:
                continue
            edit_list.widget.clearSelection()
        if self.delete_button:
            self.delete_button.setEnabled(True)

    def fill(self, objects):
        """clear list and append objects"""
        del self.objects[:]
        self.widget.clear()
        self.append(objects)

    def append(self, objects):
        """append objects"""
        self.objects.extend(objects)
        for obj in objects:
            identifier = obj['id']
            icon = obj.getIcon()
            if icon:
                item = QListWidgetItem(QIcon(icon), identifier)
            else:
                item = QListWidgetItem(identifier)
            self.widget.addItem(item)
        self._updateValidator()

    def _updateValidator(self):
        if not self.use_validator:
            return
        self.parent.updateWidget(self.widget)

    def removeRow(self):
        row = self.widget.currentRow()
        if row < 0:
            return
        del self.objects[row]
        self.widget.clearSelection()
        model = self.widget.model()
        model.removeRow(row)
        self._updateValidator()

    def getAll(self):
        return getIdentifiers(self.objects)

    def getFromLibrary(self, library):
        return getIdentifiers( obj for obj in self.objects if obj.library == library )

    def clear(self):
        self.objects = []
        self.widget.clear()
        self._updateValidator()

    def highlight(self, identifier):
        QListWidget_setCurrentText(self.widget, identifier)

    def setEnabled(self, enabled):
        widget = self.widget
        if self.use_validator:
            self.parent.widgetSetEnabled(widget, enabled)
        else:
            widget.setEnabled(enabled)
        if enabled:
            if not self.use_validator:
                # Don't use empty string to avoid a strange bug:
                # setStyleSheet(u'') does not always update the style
                widget.setStyleSheet(u';')
        else:
            style = u'background: %s;' % COLOR_DISABLED
            widget.setStyleSheet(style)


class ProtocolEditList(EditList):
    def acceptableInput(self):
        """Protocol must not be specified if platform is used in src or dest"""
        platforms_used = False
        objects = []
        for networks in ['sources', 'destinations']:
            if networks in self.parent.object_list:
                objects += self.parent.object_list[networks].objects

        for obj in objects:
            if isinstance(obj, Platform):
                platforms_used = True
                break

        return bool(self.objects) ^ platforms_used


class NetworkEditList(EditList):
    def _updateValidator(self):
        """update protocol widget too"""
        self.parent.updateWidget(self.parent.object_list['protocols'].widget)
        EditList._updateValidator(self)

