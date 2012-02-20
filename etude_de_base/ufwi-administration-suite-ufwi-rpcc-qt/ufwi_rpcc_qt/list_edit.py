#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

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

"""
TODO class ListEdit
* validation when editInPopup is False
* merge ListEdit and ListEditModel, ListEditModel should inherit QStandardItemModel
* _data[][] store only QVariant, a class like qstandarditem
  should be created in order to store role and flags per
  item
"""

from copy import deepcopy
from itertools import repeat

from PyQt4.QtCore import (pyqtProperty, Qt, QAbstractTableModel, QAbstractItemModel,
    QVariant, SIGNAL, QModelIndex, Q_ENUMS)
from PyQt4.QtGui import (QWidget, QFrame, QGridLayout, QTableView, QHeaderView,
    QVBoxLayout, QHBoxLayout, QDialog, QAbstractItemView, QPushButton, QTextEdit,
    QIcon)

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.genericdelegates import GenericDelegate, PlainTextColumnDelegate
from ufwi_rpcc_qt.input_widgets import AddButton, RemButton, UpButton, DownButton
from ufwi_rpcc_qt.tools import QVariant_toPyObject

class ListEdit(QWidget):
    def __init__(self, parent=None, isChild=False):
        QWidget.__init__(self, parent)
        QGridLayout(self)

        # FIXME: call self.setLayout(layout)?
        self._readonly = False

        self.up_down = QFrame()
        self.up = UpButton()
        self.down = DownButton()
        self.add = AddButton()
        self.rem = RemButton()
        self.listEditView = ListEditView(isChild, parent=self)

        self.connect(self.listEditView, SIGNAL('itemAdded'), SIGNAL('itemAdded'))
        self.connect(self.listEditView, SIGNAL('itemModified'), SIGNAL('itemModified'))
        self.connect(self.listEditView.model, SIGNAL('dataChanged(QModelIndex,QModelIndex)'),
            SIGNAL('dataChanged(QModelIndex,QModelIndex)'))
        self.connect(self.listEditView.model, SIGNAL('rowsRemoved(QModelIndex,int,int)'),
            SIGNAL('rowsRemoved(QModelIndex,int,int)'))
        self.connect(self.listEditView.model, SIGNAL('headerDataChanged(Qt::Orientation,int,int)'),
            SIGNAL('headerDataChanged(Qt::Orientation,int,int)'))
        self.connect(self.listEditView, SIGNAL('itemDeleted'), SIGNAL('itemDeleted'))
        self.connect(self.listEditView, SIGNAL('itemSorted'), SIGNAL('itemSorted'))
        self.connect(self.listEditView.horizontalHeader(), SIGNAL('sectionClicked(int)'),
            SIGNAL('sectionClicked(int)'))
        self.connect(self.listEditView, SIGNAL('clicked(QModelIndex)'),
            SIGNAL('clicked(QModelIndex)'))

        self.layout().addWidget(self.listEditView, 0, 0)

        self.buildUpDown()
        if not isChild:
            self.buildAddRem()
        self.setDisplayUpDown(False)
        self.setReadOnly(False)

    # Qt Properties ...
    def getReadOnly(self):
        return self._readonly

    def setReadOnly(self, readonly):
        self._readonly = readonly
        self.up.setEnabled(not self.readOnly)
        self.down.setEnabled(not self.readOnly)
        self.add.setEnabled(not self.readOnly)
        self.rem.setEnabled(not self.readOnly)
        self.listEditView.setReadOnly(self.readOnly)

    def resetReadOnly(self):
        self._readonly = False

    readOnly = pyqtProperty('bool', getReadOnly, setReadOnly, resetReadOnly)


    def getAcceptDrops(self):
        return self.listEditView.acceptDrops()

    def setAcceptDrops(self, mode):
        self.listEditView.setAcceptDrops(mode)
        flags = self.listEditView.model.getFlags()
        if mode:
            flags |= Qt.ItemIsDropEnabled
        else:
            flags &= ~Qt.ItemIsDropEnabled
        self.listEditView.model.setFlags(flags)

    def resetAcceptDrops(self):
        self.setAcceptDrops(False)

    acceptDrops = pyqtProperty('bool', getAcceptDrops, setAcceptDrops,
        resetAcceptDrops)


    def getDragDropMode(self):
        return self.listEditView.dragDropMode()

    Q_ENUMS('QAbstractItemView.DragDropMode')
    def setDragDropMode(self, mode):
        self.listEditView.setDragDropMode(mode)

    def resetDragDropMode(self):
        self.listEditView.setDragDropMode(QAbstractItemView.NoDragDrop)

    dragDropMode = pyqtProperty('QAbstractItemView::DragDropMode',
        getDragDropMode, setDragDropMode, resetDragDropMode)


    def getShowDropIndicator(self):
        return self.listEditView.showDropIndicator()

    def setShowDropIndicator(self, mode):
        self.listEditView.setShowDropIndicator(mode)

    def resetShowDropIndicator(self):
        self.listEditView.setShowDropIndicator(False)

    showDropIndicator = pyqtProperty('bool', getShowDropIndicator,
        setShowDropIndicator, resetShowDropIndicator)


    def getDisplayUpDown(self):
        return self.up_down.isVisible()

    def setDisplayUpDown(self, displayUpDown):
        self.up_down.setVisible(displayUpDown)

    def resetDisplayUpDown(self):
        self.up_down.setVisible(False)

    displayUpDown = pyqtProperty('bool', getDisplayUpDown, setDisplayUpDown,
        resetDisplayUpDown)


    def getEditBoxDescription(self):
        return self.listEditView.getEditBoxDescription()

    def setEditBoxDescription(self, description):
        self.listEditView.setEditBoxDescription(description)

    def resetEditBoxDescription(self):
        self.listEditView.resetEditBoxDescription()

    editBoxDescription = pyqtProperty('QString', getEditBoxDescription,
        setEditBoxDescription, resetEditBoxDescription)


    def getHeaders(self):
        return self.listEditView.getHeaders()

    def setHeaders(self, headers):
        self.listEditView.setHeaders(headers)

    def resetHeaders(self):
        self.listEditView.resetHeaders()

    headers = pyqtProperty('QStringList', getHeaders, setHeaders, resetHeaders)


    def getEditInPopup(self):
        return self.listEditView.editInPopup

    def setEditInPopup(self, in_popup):
        self.listEditView.editInPopup = in_popup

    def resetEditInPopup(self):
        self.listEditView.editInPopup = True

    editInPopup = pyqtProperty('bool', getEditInPopup, setEditInPopup,
        resetEditInPopup)

    def getEditInPlace(self):
        return self.listEditView.editInPlace

    def setEditInPlace(self, edit_in_place):
        self.listEditView.editInPlace = edit_in_place

    def resetEditInPlace(self):
        self.listEditView.editInPlace = False

    editInPlace = pyqtProperty('bool', getEditInPlace, setEditInPlace,
        resetEditInPlace)

    # ... Qt Properties

    def setDropMimeData(self, callback):
        self.listEditView.model.dropMimeData_cb = callback

    def setEditBox(self, editBox):
        """allow to customize edit popup"""
        #   box = editBox([row1, row2, row3], listEditOption, windowTitle)
        #   ret = box.exec_()
        #   if QDialog.Accepted == ret:
        #       newData = box.getData()
        #       # newData : [ modifiedRow1, modifiedRow2, modifiedRow3 ]
        # box must return QDialog.Accepted if data have been modified / created
        # then data must be returned by box.getData()
        self.listEditView.editBox = editBox

    def setColDelegate(self, callback):
        """callback prototype: createDelegate(view, column)"""
        self.listEditView.setColDelegate(callback)

    def buildUpDown(self):
        up_down_layout = QVBoxLayout(self.up_down)
        up_down_layout.addWidget(self.up)
        up_down_layout.addWidget(self.down)
        up_down_layout.insertStretch(0)
        up_down_layout.insertStretch(-1)
        self.layout().addWidget(self.up_down, 0, 1)
        self.connect(self.up, SIGNAL('clicked()'), self.listEditView.upItem)
        self.connect(self.down, SIGNAL('clicked()'), self.listEditView.downItem)

    def buildAddRem(self):
        buttons = QFrame()
        buttons_layout = QHBoxLayout(buttons)
        buttons_layout.insertStretch(1)
        self.connect(self.add, SIGNAL('clicked()'), self.listEditView.addItem)
        self.connect(self.rem, SIGNAL('clicked()'), self.listEditView.removeItem)
        buttons_layout.addWidget(self.add)
        buttons_layout.addWidget(self.rem)
        self.layout().addWidget(buttons, 1, 0)

    def hideRow(self, row):
        self.listEditView.verticalHeader().setSectionHidden(row, True)

    def showRow(self, row):
        self.listEditView.verticalHeader().setSectionHidden(row, False)

    def hideColumn(self, col):
        self.listEditView.horizontalHeader().setSectionHidden(col, True)

    def showColumn(self, col):
        self.listEditView.horizontalHeader().setSectionHidden(col, False)

    def reset(self, data):
        """
        TODO call clean & setData & reset
        """
        self.listEditView.model.newData(data)
        self.listEditView.model.emit(SIGNAL("modelReset()"))

    def rawData(self):
        # TODO use model.data(...)
        return deepcopy(self.listEditView.model._data)

class ListEditModel(QAbstractTableModel):
    def __init__(self, parent=None):
        QAbstractTableModel.__init__(self, parent)
        self._data = []
        self.headers = []
        self._flags = Qt.ItemIsSelectable
        self.dropMimeData_cb = None

    def rowCount(self, index=QModelIndex()):
        return len(self._data)

    def columnCount(self, index=QModelIndex()):
        return len(self.headers)

    def newData(self, data):
        self._data = deepcopy(data)

    # TODO flags should be handled at item level, not at model level
    def setFlags(self, flags):
        self._flags = flags

    def getFlags(self):
        return self._flags

    def resetFlags(self):
        self._flags = Qt.ItemIsSelectable

    def data(self, index, role):
        if not index.isValid():
            return QVariant()

        if index.row() >= len(self._data):
            return QVariant()
        if index.column() >= len(self.headers):
            return QVariant()

        if role == Qt.DisplayRole:
            return QVariant(self._data[index.row()][index.column()])

        return QVariant()

    def setData(self, index, value, role=Qt.EditRole):
        if index.isValid() and role == Qt.EditRole:
            self._data[index.row()][index.column()] = QVariant_toPyObject(value)
            self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'), index, index)
            return True
        return False

    def headerData(self, section, orientation, role):
        if role == Qt.TextAlignmentRole:
            return QVariant(Qt.AlignHCenter)

        if Qt.SizeHintRole == role and orientation == Qt.Vertical:
            return QVariant(int(0))

        if Qt.DisplayRole == role and orientation == Qt.Horizontal:
            return QVariant(self.headers[section])

        return QVariant()

    def setHeaderData(self, section, orientation, value, role=Qt.EditRole):
        """ section is 0 based """
        curr_nb = len(self.headers)
        if section < 0 or section >= curr_nb:
            return False

        if Qt.EditRole == role and orientation == Qt.Horizontal:
            self.headers[section] = unicode(value.toString())
            self.emit(SIGNAL('headerDataChanged(Qt::Orientation,int,int)'), orientation, section, 1)
            return True

        return False

    def flags(self, index):
        if not index.isValid():
            return QAbstractItemModel.flags(self, index) | Qt.ItemIsEnabled

        return self._flags | Qt.ItemIsEnabled

    def supportedDropActions(self):
        # TODO copy needed ?
        return Qt.CopyAction | Qt.MoveAction

    def insertRows(self, row, count, parent=QModelIndex()):
        """
        append rows
        """
        self.beginInsertRows(parent, self.rowCount(), row + count - 1)
        new_line = list(repeat('', self.columnCount()))
        new_lines = repeat(new_line, count)
        self._data.extend(new_lines)
        self.endInsertRows()
        return True

    def removeRows(self, row, count, parent=QModelIndex()):
        """row is 0 based"""
        self.beginRemoveRows(parent, row, row + count - 1)
        for i in range(count-1, -1, -1):
            del self._data[row + i]
        self.endRemoveRows()
        return True

    def insertColumns(self, column, count, parent=QModelIndex()):
        """column is 0 based"""
        # TODO prepend and append are implemented but not insert
        if column < 0 or column > self.columnCount():
            return

        self.beginInsertColumns(parent, column, column + count - 1)
        if column == 0:
            # prepend
            self.headers[0:0] = list(repeat('', count))
            for line in self._data:
                line[0:0] = list(repeat('', count))
        else:
            # append
            self.headers.extend(list(repeat('', count)))
            for line in self._data:
                line.extend(list(repeat('', count)))
        self.endInsertColumns()

    def removeColumns(self, column, count, parent=QModelIndex()):
        """column is 0 based"""
        self.beginRemoveColumns(parent, column, column + count - 1)
        for col in range(column, count):
            del self.headers[col:col+1]
            for row in self._data:
                # remove column number 'col'
                del row[col:col+1]
        self.endRemoveColumns()

    def removeAllColumns(self):
        """remove all columns in model"""
        nb_col = self.columnCount()
        self.removeColumns(0, nb_col, parent=QModelIndex())

    def setColumnsCount(self, nb_columns):
        """convenient method which use insertColumns / removeColumns"""
        curr_nb = self.columnCount()
        if nb_columns == curr_nb:
            return
        elif nb_columns > curr_nb:
            self.insertColumns(curr_nb, nb_columns - curr_nb)
        else:
            self.removeColumns(curr_nb - 1, nb_columns - curr_nb)

    def swapItem(self, from_row_index, to_row_index):
        self._data[from_row_index], self._data[to_row_index] =\
            self._data[to_row_index], self._data[from_row_index]
        top_left = self.createIndex(min(from_row_index, to_row_index), 0)
        bottom_right = self.createIndex(max(from_row_index, to_row_index), self.columnCount()-1)
        self.emit(SIGNAL('dataChanged(QModelIndex,QModelIndex)'), top_left, bottom_right)

    def dropMimeData(self, mime_data, action, row, column, index):
        if callable(self.dropMimeData_cb):
            return self.dropMimeData_cb(self, mime_data, action, row, column, index)
        else:
            return False

class ListEditView(QTableView):
    def __init__(self, isChild=False, parent=None):
        QTableView.__init__(self, parent)
        self.model = ListEditModel(parent=self)
        self.setModel(self.model)

        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)

        self.getColDelegate = self.simpleGetColDelegate

        self.setHeaders([])
        self._editInPopup = True
        self._editInPlace = True
        self.isChild = isChild
        self.editBox = None
        self._editBoxDescription = ''

        self.connect(self.model, SIGNAL("modelReset()"), self.model_reset)

    def model_reset(self):
        if self.isChild:
            for i in range(len(self.getHeaders())):
                self.openPersistentEditor(self.model.createIndex(0, i))
            self.setMaximumHeight(2*self.rowHeight(0))

    def getEditBoxDescription(self):
        return self._editBoxDescription

    def setEditBoxDescription(self, description):
        self._editBoxDescription = description

    def resetEditBoxDescription(self):
        self._editBoxDescription = ''

    def setReadOnly(self, readonly):
        if self.isChild:
            # child allow edition
            readonly = False

        self.disconnect(self, SIGNAL("doubleClicked(QModelIndex)"), self.editItem)
        if not readonly and self.editInPopup:
            self.connect(self, SIGNAL("doubleClicked(QModelIndex)"), self.editItem)

    def getEditInPopup(self):
        return self._editInPopup

    def setEditInPopup(self, in_popup):
        self._editInPopup = in_popup

        self.disconnect(self, SIGNAL("doubleClicked(QModelIndex)"), self.editItem)
        if in_popup and self.isEnabled():
            self.connect(self, SIGNAL("doubleClicked(QModelIndex)"), self.editItem)

    def resetEditInPopup(self):
        self._editInPopup = True

    editInPopup = pyqtProperty('bool', getEditInPopup, setEditInPopup,
        resetEditInPopup)


    def getEditInPlace(self):
        return self._editInPlace

    def setEditInPlace(self, edit_in_place):
        flags = self.model.getFlags()
        if edit_in_place:
            flags |= Qt.ItemIsEditable
        else:
            flags &= ~Qt.ItemIsEditable
        self.model.setFlags(flags)

        self._editInPlace = edit_in_place

    def resetEditInPlace(self):
        self.setEditInPlace(False)

    editInPlace = pyqtProperty('bool', getEditInPlace, setEditInPlace,
        resetEditInPlace)

    # headers
    def getHeaders(self):
        headers = []
        nb_col = self.model.columnCount()
        for index in range(0, nb_col):
            header = self.model.headerData(index, Qt.Horizontal, role=Qt.DisplayRole)
            headers.append(unicode(header.toString()))
        return headers

    def setHeaders(self, headers):
        self.model.removeAllColumns()

        self.model.setColumnsCount(len(headers))
        for index, header in enumerate(headers):
            self.model.setHeaderData(index, Qt.Horizontal, QVariant(header),\
                role=Qt.EditRole)

        delegate = GenericDelegate(self)
        for index in range(len(headers)):
            deleg_col = self.getColDelegate(index)
            delegate.insertColumnDelegate(index, deleg_col)
        self.setItemDelegate(delegate)

        self.horizontalHeader().setResizeMode(QHeaderView.Stretch)

    def resetHeaders(self):
        self.setHeaders([])
    #

    def setColDelegate(self, callback):
        """callback prototype: createDelegate(view, column)"""
        self.getColDelegate = callback
        delegate = GenericDelegate(self)
        for index in range(self.model.columnCount()):
            deleg_col = self.getColDelegate(index)
            delegate.insertColumnDelegate(index, deleg_col)

        # setItemDelegate don't delete previous delegate
        old_delegate = self.itemDelegate()
        self.setItemDelegate(delegate)
        old_delegate.deleteLater()

    def addItem(self):
        next_row = self.model.rowCount()
        if self.editInPopup:
            newLine = list(repeat('', self.model.columnCount()))
            box = self.createEditBox(newLine, tr("Edit"))
            ret = box.exec_()
            if QDialog.Accepted == ret:
                # insert row in model and fill it
                new_data = box.getData()
                self.model.insertRow(next_row)
                for index_col, data in enumerate(new_data):
                    data = QVariant(data)
                    index = self.model.index(next_row, index_col)
                    self.model.setData(index, data, role=Qt.EditRole)
                self.emit(SIGNAL('itemAdded'))
            else:
                return False
        else:
            # insert empty row in model
            self.model.insertRow(next_row)
            for index_col in range(self.model.columnCount()):
                data = QVariant('')
                index = self.model.index(next_row, index_col)
                self.model.setData(index, data, role=Qt.EditRole)
            self.emit(SIGNAL('itemAdded'))
        return True

    def editItem(self, line_index):
        if line_index.isValid():
            newLine = []
            for col in range(self.model.columnCount()):
                index = self.model.index(line_index.row(), col)
                data = self.model.data(index, role = Qt.DisplayRole)
                newLine.append(QVariant_toPyObject(data))

            box = self.createEditBox(newLine, tr("Edit"))
            ret = box.exec_()
            if QDialog.Accepted == ret:
                dataModified = box.getData()
                for col in range(self.model.columnCount()):
                    index = self.model.index(line_index.row(), col)
                    data = QVariant(dataModified[col])
                    self.model.setData(index, data, role=Qt.EditRole)
                self.emit(SIGNAL('itemModified'))

    def createEditBox(self, line, title):
        description = self.getEditBoxDescription()
        if self.editBox is None:
            return EditBox(line, title, description, parent=self)
        else:
            return self.editBox(line, title, description, parent=self)

    def removeItem(self):
        indexes = self.selectedIndexes()
        rows = []
        for index in indexes:
            if index.row() not in rows:
                rows.append(index.row())

        rows.sort(reverse=True)

        for row in rows:
            self.model.removeRow(row)
            self.emit(SIGNAL('itemDeleted'))

        return rows

    def upItem(self):
        """
        single selection only supported
        """
        indexes = self.selectedIndexes()
        if 1 == len(indexes) and indexes[0].isValid() and indexes[0].row() > 0:
            self.model.swapItem(indexes[0].row(), indexes[0].row()-1)
            self.selectRow(indexes[0].row()-1)
            self.emit(SIGNAL('itemSorted'))

    def downItem(self):
        """
        single selection only supported
        """
        indexes = self.selectedIndexes()
        if 1 == len(indexes) and indexes[0].isValid() and indexes[0].row() < (self.model.rowCount() - 1):
            self.model.swapItem(indexes[0].row(), indexes[0].row()+1)
            self.selectRow(indexes[0].row()+1)
            self.emit(SIGNAL('itemSorted'))

    def simpleGetColDelegate(self, col):
        """create LineEdit Factory"""
        return PlainTextColumnDelegate()

    def dragMoveEvent(self, event):
        event.accept()

    def dragEnterEvent(self, event):
        """accept all drag event"""
        event.acceptProposedAction()

class EditBox(QDialog):
    def __init__(self, data, title, description=None, parent=None):
        QDialog.__init__(self, parent)
        self.setWindowTitle(title)
        self.setWindowModality(Qt.ApplicationModal)

        QVBoxLayout(self)
        self.list = ListEdit(parent=parent, isChild=True)
        self.list.displayUpDown = False
        self.list.editInPopup = False
        self.list.headers = parent.getHeaders()
        self.list.setColDelegate(parent.getColDelegate)
        self.list.reset([data])
        self.info = QTextEdit()
        self.error = QTextEdit()
        self.grid = None

        self.build(description)

    def build(self, description):
        self.layout().addWidget(self.list)

        cancel = QPushButton(QIcon(":/icons/wrong.png"), tr("Cancel"), self)
        save = QPushButton(QIcon(":/icons/apply.png"), tr("OK"), self)
        save.setDefault(True)

        self.connect(cancel, SIGNAL("clicked()"), self.doClose)
        self.connect(save, SIGNAL("clicked()"), self.doSave)

        self.grid = QWidget(self)
        self.setMinimumWidth(700)
        QGridLayout(self.grid)
        self.grid.layout().addWidget(save, 0, 0, Qt.AlignHCenter)
        self.grid.layout().addWidget(cancel, 0, 1, Qt.AlignHCenter)
        self.layout().addWidget(self.grid)

        self.info.setReadOnly(True)
        if description:
            self.info.append(description)
        else:
            self.info.setVisible(False)

        self.error.setReadOnly(True)
        self.error.setVisible(False)

        self.grid.layout().addWidget(self.info, 1, 0, 1, 0, Qt.AlignHCenter)
        self.grid.layout().addWidget(self.error, 2, 0, 1, 0, Qt.AlignHCenter)

    def doClose(self):
        self.reject()
        self.close()

    def doSave(self):
        self.error.clear()
        hasInvalidData = False
        for col in range(self.list.listEditView.model.columnCount()):
            index = self.list.listEditView.model.index(0, col)
            input_edit = self.list.listEditView.indexWidget(index)
            if not input_edit.isValid():
                col_name = self.list.listEditView.model.headerData(col, Qt.Horizontal, Qt.DisplayRole)
                col_name = unicode(col_name.toString())
                self.error.append(tr("Column '%s': must be '%s'") % (col_name,
                    input_edit.getFieldInfo()))
                hasInvalidData = True

        if hasInvalidData:
            self.error.setVisible(True)
        else:
            self.accept()
            self.close()

    def getData(self):
        """
        single selection only supported
        """
        return self.list.rawData()[0]

