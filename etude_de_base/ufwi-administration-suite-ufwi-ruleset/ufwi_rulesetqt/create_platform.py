"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Victor Stinner <vstinner AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

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

from new import instancemethod

from PyQt4.QtCore import Qt, QVariant, SIGNAL

from ufwi_rpcc_qt.list_edit import ListEditView
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX
from ufwi_rulesetqt.tools import getDragUrlFromMimeData

NETWORK_COLUMN = 0
PROTOCOL_COLUMN = 1

def dropMimeData(model, mime_data, action, row, column, index):
    if action == Qt.IgnoreAction:
        return True

    if index.isValid() and mime_data.hasFormat("text/plain"):
        # format is "type:id"
        item = getDragUrlFromMimeData(mime_data)
        item_type, identifier = item.split(':', 1)
        # horizontal headers in list: [Network, Protocol]
        if ((index.column() == NETWORK_COLUMN and item_type == 'resource')
         or (index.column() == PROTOCOL_COLUMN and item_type == 'protocol')):
            data = QVariant(identifier)
            model.setData(index, data, role=Qt.EditRole)
        return True

    return False

def acceptableInput(view):
    model = view.model
    rows = model.rowCount()
    if rows < 1:
        return False

    columns = model.columnCount()

    for row in range(rows):
        for col in range(columns):
            index = model.index(row, col)
            data = model.data(index, Qt.DisplayRole)
            if data.toString().isEmpty():
                return False

    return True

class CreatePlatform(RulesetDialog):
    PLATFORM_STACK_INDEX = 4
    def __init__(self, window):
        RulesetDialog.__init__(self, window, accept=self.save)
        self.object_id = None
        self.widget_prefix = 'platform_edit'
        self.identifier = self.getWidget('identifier_text')
        self.setRegExpValidator(self.identifier, IDENTIFIER_REGEX)

        self.connectOkButton(self.getWidget('save_button'))
        self.window.connect(self.getWidget('cancel_button'), SIGNAL("clicked()"), self.stopEdit)

        # Configure objects
        edit_list = self.getWidget('list')
        edit_list.setDropMimeData(dropMimeData)
        edit_list.listEditView.acceptableInput = instancemethod(acceptableInput,
            edit_list.listEditView, ListEditView)
        self.connect(edit_list, SIGNAL('sectionClicked(int)'), self.platformEditHeaderClicked)
        self.connect(edit_list, SIGNAL('clicked(QModelIndex)'), self.platformEditItemClicked)
        self.connect(edit_list, SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
            lambda xindex, yindex: self.updateWidget(self.getWidget('list').listEditView))
        self.connect(edit_list, SIGNAL('rowsRemoved(QModelIndex,int,int)'),
            lambda parent, xindex, yindex: self.updateWidget(self.getWidget('list').listEditView))
        self.addInputWidget(edit_list.listEditView)

    def getWidget(self, name):
        name = self.widget_prefix + '_' + name
        return getattr(self.window, name)

    def create(self):
        self.object_id = None

        self.identifier.setText(u'')
        self.identifier.setFocus()
        self.getWidget('list').reset([])

        self.startEdit()

    def modify(self, obj):
        self.object_id = obj['id']

        self.identifier.setText(self.object_id)
        self.identifier.setFocus()
        data = []
        for item in obj['items']:
            data.append([item['network'], item['protocol']])
        self.getWidget('list').reset(data)

        self.startEdit()

    def save(self):
        identifier = unicode(self.identifier.text())
        items = []
        data = self.getWidget('list').rawData()
        for row in data:
            network, protocol = row
            item = {'network': unicode(network), 'protocol': unicode(protocol)}
            items.append(item)

        ok = self.saveObject(identifier, 'platforms', {'items': items})
        if ok:
            self.stopEdit()

    def startEdit(self):
        self.window.setEditMode(True)
        self.window.acl_stack.setCurrentIndex(self.PLATFORM_STACK_INDEX)

    def stopEdit(self):
        self.window.setEditMode(False)

    def platformEditHeaderClicked(self, section):
        """Select library when header is clicked"""
        self.platformSelectToolBox(section)

    def platformEditItemClicked(self, index):
        """Select library when item is clicked (index is valid)"""
        self.platformSelectToolBox(index.column())

    def platformSelectToolBox(self, index):
        if index == NETWORK_COLUMN:
            self.window.getLibrary('resources').showToolbox()
        elif index == PROTOCOL_COLUMN:
            self.window.getLibrary('protocols').showToolbox()

