
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

from datetime import datetime
from PyQt4.QtCore import Qt, QSize, QVariant
from PyQt4.QtGui import QTabBar, QColor

def QTabWidget_setCurrentText(tab, text):
    """
    Select an item of a text of a QTabWidget.
    """
    for index in xrange(tab.count()):
        tab_text = unicode(tab.tabText(index))
        if tab_text == text:
            tab.setCurrentIndex(index)
            return True
    return False

def QComboBox_setCurrentText(combo, text):
    """
    Select an item of a QComboBox by its name.
    """
    index = combo.findText(text)
    if index < 0:
        return False
    combo.setCurrentIndex(index)
    return True

def QListWidget_currentText(widget):
    """
    Get the text if the current selected item as an unicode string.
    Return None if no item is selected.
    """
    item = widget.currentItem()
    if not item:
        return None
    return unicode(item.text())

def QListWidget_setCurrentText(widget, text):
    """
    Select an item of a QListWidget by its text.
    """
    for row in xrange(widget.count()):
        item_text = unicode(widget.item(row).text())
        if item_text == text:
            widget.setCurrentRow(row)
            return True
    return False

def QTreeWidget_iteritems(widget):
    """
    Iterate on each item of a QTreeWidget.
    The function is a generator.
    """
    for index in xrange(widget.topLevelItemCount()):
        yield widget.topLevelItem(index)

def QTreeWidgetItem_iterchildren(item):
    """
    Iterate on each child of a QTreeWidget.
    The function is a generator.
    """
    for index in xrange(item.childCount()):
        yield item.child(index)

def _QTreeWidget_findItem(items, text):
    for item in items:
        if item.text(0) == text:
            yield item
        children = QTreeWidgetItem_iterchildren(item)
        for match in _QTreeWidget_findItem(children, text):
            yield match

def QTreeWidget_setCurrentText(widget, text):
    """
    Select an item of a QTreeWidet by its text. Return True if the
    selection changed, False if the item was already selected.
    """
    items = QTreeWidget_iteritems(widget)
    for item in _QTreeWidget_findItem(items, text):
        if not bool(item.flags() & Qt.ItemIsSelectable):
            continue
        current_item = widget.currentItem()
        if item != current_item:
            widget.setCurrentItem(item)
            return True
        else:
            return False

def QTreeWidget_expandAll(widget):
    """
    Expand all items (children) of a QTreeWidget.
    """
    for item in QTreeWidget_iteritems(widget):
        QTreeWidgetItem_expandAll(item)

def QTreeWidgetItem_expandAll(item):
    """
    Expand all items (children) of a QTreeWidgetItem.
    """
    item.setExpanded(True)
    for child in QTreeWidgetItem_iterchildren(item):
        child.setExpanded(True)
        QTreeWidgetItem_expandAll(child)

def QListWidget_getAll(widget):
    """
    Get all items as an unicode text list.
    """
    data = []
    for row in xrange(widget.count()):
        item = widget.item(row)
        text = unicode(item.text())
        data.append(text)
    return data

def QListWidget_getSelection(widget):
    """
    Get the selected texts of a QListWidget.
    This function is a generator.
    """
    for item in widget.selectedItems():
        yield unicode(item.text())

def QDockWidget_setTab(dock):
    """
    For a QDockWidget which included in QTabBar,
    select the tab which includes the dock.

    Return True if the tab is changed, False if it's not possible
    to find the right tab.
    """
    title = unicode(dock.windowTitle())
    parent = dock.parentWidget()
    for tabbar in parent.findChildren(QTabBar):
        if QTabWidget_setCurrentText(tabbar, title):
            return True
    return False

def QTableWidget_resizeWidgets(table):
    """
    Resize QTableWidget columns and rows using the cell widgets size.
    Ignore columns using span.
    """
    max_width = [0] * table.columnCount()
    for row in xrange(table.rowCount()):
        max_height = 0
        ignore_columns = set()
        for col in xrange(table.columnCount()):
            if col in ignore_columns:
                continue
            span = table.columnSpan(row, col)
            if span != 1:
                ignore_columns |= set(xrange(col, col + span))
                continue
            widget = table.cellWidget(row, col)
            if not widget:
                continue
            size = widget.sizeHint()
            width = size.width()
            max_width[col] = max(width, max_width[col])
            height = size.height()
            max_height = max(height, max_height)
        max_height = max(table.verticalHeader().sectionSizeHint(row), max_height)
        table.setRowHeight(row, max_height)
    for col, width in enumerate(max_width):
        width = max(table.horizontalHeader().sectionSizeHint(col), width)
        table.setColumnWidth(col, width)

def QTableWidget_totalSize(table):
    total_height = 0
    total_width = 0
    max_width = [0] * table.columnCount()
    for row in xrange(table.rowCount()):
        max_height = 0
        for col in xrange(table.columnCount()):
            widget = table.cellWidget(row, col)
            if not widget:
                continue
            size = widget.sizeHint()
            width = size.width()
            max_width[col] = max(width, max_width[col])
            height = size.height()
            max_height = max(height, max_height)
        max_height = max(table.verticalHeader().sectionSizeHint(row), max_height)
        total_height += max_height + 10
    for col, width in enumerate(max_width):
        width = max(table.horizontalHeader().sectionSizeHint(col), width)
        total_width += width + 10
    return QSize(total_width, total_height)

def unsetFlag(object, flag):
    flags = object.flags()
    flags &= ~flag
    object.setFlags(flags)

def getSelectionRows(selections):
    """
    Get the list of selected rows.
    """
    if not selections:
        return tuple()
    rows = set()
    for selection in selections:
        for index in selection.indexes():
            row = index.row()
            rows.add(row)
    rows = list(rows)
    rows.sort()
    return rows

def getFirstSelected(selection, role=Qt.DisplayRole):
    """
    Get first item from a selection.
    Return None for empty selection.
    """
    if not selection:
        # None or empty line
        return None
    selection = selection[0]
    indexes = selection.indexes()
    if not len(indexes):
        return None
    model = selection.model()
    return model.data(indexes[0], role)

def QDateTime_as_datetime(timestamp):
    """
    >>> from PyQt4.QtCore import QDateTime, QDate, QTime
    >>> QDateTime_as_datetime(QDateTime(QDate(2009, 7, 6), QTime(20, 10, 3, 125)))
    datetime.datetime(2009, 7, 6, 20, 10, 3, 125000)
    >>> print QDateTime_as_datetime(QDateTime.fromString("2009-07-01 20:10:03.125", "yyyy-MM-dd HH:mm:ss.z"))
    2009-07-01 20:10:03.125000
    """
    date = timestamp.date()
    time = timestamp.time()
    return datetime(date.year(), date.month(), date.day(), time.hour(), time.minute(), time.second(), time.msec()*1000)

def QVariant_toPyObject(obj):
    # Old versions of PyQt crashs on .toPyObject()
    # This function is supposed to avoid such crashs
    #
    # QVariant has been modified 3 times:
    #  - PyQt 4.8: QVariantList
    #  - PyQt 4.7.1: sub-classes of standard Python types (eg. float)
    #  - PyQt 4.5: sub-classes of certain Qt classes (eg. QSize), datetime,
    #    date, time objects
    #
    # http://www.riverbankcomputing.co.uk/static/Docs/
    # PyQt4/pyqt4ref.html#potential-incompatibilities-with-earlier-versions
    if obj.type() == QVariant.String:
        return obj.toString()
    elif obj.type() == QVariant.Double:
        return obj.toDouble()[0]
    elif obj.type() == QVariant.Color:
        return QColor(obj)
    else:
        return obj.toPyObject()

def CreateQVariantList(items):
    """Check that all items are QVariant
       and return QVariant object that contains items
    """
    for item in items:
        if not isinstance(item, QVariant):
            raise NotImplementedError("'%s' must be wrapped in 'QVariant'"
                % type(item))

    if hasattr(QVariant, "fromList"):
        # With PyQt >= 4.4.3, QVariant(list of QVariant) behaviour changed:
        # QVariant.fromList() should be used instead to get the same behaviour
        # than QVariant(list of QVariant) with PyQt 4.4.2.
        return QVariant.fromList(items)
    else:
        # PyQt <= 4.4.2
        return QVariant(items)
