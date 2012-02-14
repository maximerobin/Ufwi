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

from PyQt4.QtCore import SIGNAL, Qt, QVariant
from PyQt4.QtGui import QTreeWidgetItem, QIcon, QTreeWidget

from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.tools import (
    QTreeWidget_setCurrentText,
    QTreeWidget_expandAll, unsetFlag,
    getFirstSelected)
from ufwi_rpcc_qt.html import htmlTable

from ufwi_ruleset.common.update import Updates
from ufwi_rulesetqt.menu import Menu
from ufwi_rulesetqt.objects import Group
from ufwi_rulesetqt.tools import getIdentifier
from ufwi_rulesetqt.filter import Filter
from ufwi_rulesetqt.html import htmlTitle
from ufwi_rulesetqt.library_model import LibraryModel

class LibraryActions:
    def __init__(self, library, object):
        read_only = library.ruleset.read_only
        if read_only:
            self.create = False
            self.modify = False
        elif object:
            self.create = object.allowCreate()
            if not library.edit_mode:
                self.modify = object.isEditable()
            else:
                self.modify = False
        else:
            self.create = True
            self.modify = False
        self.delete = self.modify

class LibraryMenu(Menu):
    def __init__(self, library, create_text, modify_text, delete_text):
        Menu.__init__(self)
        self.library = library
        self.create_action = self.add(":/icons/add.png", create_text, library.create)
        self.modify_action = self.add(":/icons/edit.png", modify_text, library.modifyEvent)
        self.delete_action = self.add(":/icons/delete.png", delete_text, library.deleteEvent)

    def display(self, event, actions):
        self.create_action.setEnabled(actions.create)
        self.modify_action.setEnabled(actions.modify)
        self.delete_action.setEnabled(actions.delete)
        self.exec_(event.globalPos())

class Library(object):
    REFRESH_DOMAIN = u"object"
    URL_FORMAT = u"object:%s"
    RULESET_ATTRIBUTE = "object"
    ACTIONS = LibraryActions
    GROUP_CLASS = Group
    MODEL_CLASS = LibraryModel

    # Abstract attributes
    CHILD_CLASS = None

    def __init__(self, window, widget_prefix):
        self.window = window
        self.model = self.MODEL_CLASS(self)
        self.widget_prefix = widget_prefix + "_"
        self.ui = window
        self.ruleset = window.ruleset
        self.container = None
        self.menu = None
        self.toolbox = None
        self.toolbox_index = None
        self.url_prefix = self.URL_FORMAT[:-2]
        self.drag_format = self.URL_FORMAT
        self.highlight_format = u"highlight:%s" % self.URL_FORMAT
        self.filter = Filter()
        self.create_button = self.getWidget("create_button")
        self.modify_button = self.getWidget("modify_button")
        self.delete_button = self.getWidget("delete_button")
        self.create_grp_button = self.getWidget("creategrp_button", True)
        self.edit_mode = False

        # abstract attributes
        self.dialog = None

        # disable drag/drop on filter
        filter_text = self.getWidget('filter_text')
        filter_text.setAcceptDrops(False)

        index = window.LIBRARIES.index(type(self))
        self.setToolbox(window.object_library, index)

    def setToolbox(self, toolbox, index):
        self.toolbox = toolbox
        self.toolbox_index = index

    def setButtons(self):
        window = self.window
        window.connect(self.create_button, SIGNAL("clicked()"), self.create)
        window.connect(self.modify_button, SIGNAL("clicked()"), self.modifyEvent)
        window.connect(self.delete_button, SIGNAL("clicked()"), self.deleteEvent)
        if self.create_grp_button:
            window.connect(self.create_grp_button, SIGNAL("clicked()"), self.createGroup)
        window.connect(self.getWidget('filter_text'), SIGNAL('textChanged(const QString&)'), self.filterChanged)

    def getWidget(self, name, use_none=False):
        try:
            return getattr(self.ui, self.widget_prefix + name)
        except AttributeError:
            if use_none:
                return None
            else:
                raise

    def filterChanged(self, text):
        text = unicode(text)
        self.filter.setText(text)
        self.display(Updates())

    def setContainer(self, container):
        self.container = container
        self.container.header().hide()
        container.setDragEnabled(True)
        container.startDrag = self.startDrag
        container.setAlternatingRowColors(True)
        self.window.selection_widgets.append(container)

        self.window.connect(
            container.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.selectEvent)
        signal = SIGNAL("itemActivated(QTreeWidgetItem*,int)")
        self.window.connect(container, signal, self.modifyEvent)
        container.keyPressEvent = self.keyHandler
        self.selectEvent(None, None)

    def setMenu(self, menu):
        self.menu = menu
        self.container.contextMenuEvent = self.contextMenuEvent

    def keyHandler(self, event):
        if not self.edit_mode \
        and event.key() == Qt.Key_Delete:
            self.deleteEvent()
            event.accept()
            return
        QTreeWidget.keyPressEvent(self.container, event)

    def currentItem(self):
        return self.container.currentItem()

    def currentIdentifier(self):
        item = self.currentItem()
        if not item:
            return None
        if not bool(item.flags() & Qt.ItemIsSelectable):
            return
        text = item.data(0, Qt.UserRole)
        text = unicode(text.toString())
        return text

    def __getitem__(self, identifier):
        return self.model[identifier]

    def __iter__(self):
        return iter(self.model)

    def currentObject(self):
        identifier = self.currentIdentifier()
        if identifier:
            return self[identifier]
        else:
            return None

    def modifyEvent(self, *unused):
        if self.ruleset.read_only or self.edit_mode:
            return
        identifier = self.currentIdentifier()
        if not identifier:
            return
        object = self[identifier]
        if not object.isEditable():
            return
        if isinstance(object, Group):
            self.window.objgroup.editGroup(object, self)
        else:
            self.modify(object)

    def deleteEvent(self):
        identifier = self.currentIdentifier()
        if not identifier:
            return
        object = self[identifier]
        if not object.isEditable():
            return
        if object['references']:
            references = object.createReferencesHTML(glue=', ', icon=False)
            self.window.error(
                tr("Unable to delete the object: it is used by %s") % references,
                escape=False)
            return
        try:
            updates = self.model.delete(object)
        except Exception, err:
            self.window.exception(err)
            return
        self.window.refresh(updates)
        self.window.setInfo('')

    def _updateButtons(self, object):
        actions = self.ACTIONS(self, object)
        self.create_button.setEnabled(actions.create)
        self.modify_button.setEnabled(actions.modify)
        self.delete_button.setEnabled(actions.delete)
        if object is not None:
            for widget in self.window.selection_widgets:
                if widget is self.container:
                    continue
                widget.clearSelection()

    def selectEvent(self, selected, deselected):
        node = getFirstSelected(selected, Qt.UserRole)
        if node:
            identifier = unicode(node.toString())
            object = self[identifier]
            object.information(highlight=False)
        else:
            object = None
        self._updateButtons(object)

    def informationID(self, identifier, highlight=True):
        object = self[identifier]
        object.information(highlight=highlight)

    def startDrag(self, event):
        object = self.currentObject()
        if not object:
            return
        icon = object.getIcon()
        if icon:
            icon = QIcon(icon)
        text = self.drag_format % object['id']
        self.window.startDragText(self.container, text, icon)

    def contextMenuEvent(self, event):
        object = self.currentObject()
        actions = self.ACTIONS(self, object)
        self.menu.display(event, actions)

    def createTreeItem(self, object):
        icon = object.getIcon()
        label = object.formatID()
        tree = QTreeWidgetItem([label])
        tree.setData(0, Qt.UserRole, QVariant(object['id']))
        tooltip = object.getToolTip()
        if tooltip:
            tree.setToolTip(0, tooltip)
        if icon:
            tree.setIcon(0, QIcon(icon))
        font = tree.font(0)
        if object['editable']:
            font.setBold(True)
        if not object['references']:
            font.setItalic(True)
        tree.setFont(0, font)
        if not object['editable']:
            unsetFlag(tree, Qt.ItemIsEditable)
        return tree

    def createTreeKeyLabel(self, key):
        return key

    def createTree(self):
        objects = list(self.model)
        objects = [object for object in objects
            if self.filter.match(object)]
        objects.sort(key=getIdentifier)
        groups = {}
        for object in objects:
            if isinstance(object, Group):
                key = None
            else:
                key = self.getTreeKey(object)
            if key in groups:
                groups[key].append(object)
            else:
                groups[key] = [object]
        root = []
        for key in sorted(groups.keys()):
            if key:
                label = self.createTreeKeyLabel(key)
            else:
                label = tr('Groups')
            tree = QTreeWidgetItem([label])
            unsetFlag(tree, Qt.ItemIsSelectable)
            for object in groups[key]:
                node = self.createTreeItem(object)
                tree.addChild(node)
            root.append(tree)
        return root

    def fill(self):
        self.container.clear()
        tree = self.createTree()
        self.container.addTopLevelItems(tree)
        QTreeWidget_expandAll(self.container)

    def toolboxVisible(self):
        return (self.toolbox.currentIndex() == self.toolbox_index)

    def showToolbox(self):
        self.toolbox.setCurrentIndex(self.toolbox_index)

    def highlight(self, identifier, information=True):
        self.showToolbox()
        selection_changed = QTreeWidget_setCurrentText(self.container, identifier)
        if information and (not selection_changed):
            self.informationID(identifier, highlight=False)

    def refresh(self, all_updates, updates):
        self.model.refresh(all_updates, updates)

    def display(self, updates, highlight=False):
        self.fill()
        if highlight:
            identifier = updates.getHighlightId()
            if identifier:
                self.informationID(identifier)

    def createGroup(self):
        self.window.objgroup.editGroup(None, self)

    def create(self):
        self.dialog.create()

    def modify(self, object):
        self.dialog.modify(object)

    def getIcon(self, object):
        return None

    def templatizeEvent(self):
        identifier = self.currentIdentifier()
        try:
            updates = self.model.templatize(identifier)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        self.window.refresh(updates)

    def getUrlIdentifier(self, url):
        prefix = self.url_prefix
        if not url.startswith(prefix):
            return None
        return url[len(prefix):]

    def information(self, object, highlight=True):
        if highlight:
            self.highlight(object['id'])
        icon = object.getIcon()
        title, options = object.createInformation()
        title = tr('%s:') % title
        if self.window.debug:
            object.createDebugOptions(options)
        html = htmlTitle(title, icon) + htmlTable(options)
        self.window.setInfo(html,
            background=object.getBackground())

    def useFusion(self):
        return self.window.useFusion()

    def setReadOnly(self, read_only):
        for button in (self.create_button, self.modify_button,
        self.delete_button, self.create_grp_button):
            if not button:
                continue
            if read_only:
                button.hide()
            else:
                button.show()

    def setEditMode(self, edit):
        self.edit_mode = edit
        self._updateButtons(self.currentObject())
        if self.create_grp_button:
            self.create_grp_button.setEnabled(not edit)

    #--- Abstract methods ---
    @abstractmethod
    def getTreeKey(self, object):
        pass

