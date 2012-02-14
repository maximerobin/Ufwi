#!/usr/bin/env python
# Copyright (c) 2007-8 Qtrac Ltd. All rights reserved.
# This program or module is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as published
# by the Free Software Foundation, either version 2 of the License, or
# version 3 of the License, or (at your option) any later version. It is
# provided for educational purposes and is distributed in the hope that
# it will be useful, but WITHOUT ANY WARRANTY; without even the implied
# warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See
# the GNU General Public License for more details.

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

from PyQt4.QtCore import QDate, QString, Qt, QVariant, SIGNAL
from PyQt4.QtGui import (QComboBox, QDateEdit, QIcon, QItemDelegate, QLineEdit,
    QPushButton, QSpinBox, QStyledItemDelegate)

class ComboBox(QComboBox):
    def __init__(self, parent=None):
        QComboBox.__init__(self, parent)

    def isValid(self):
        return True

class GenericDelegate(QItemDelegate):

    def __init__(self, parent=None):
        super(GenericDelegate, self).__init__(parent)
        self.delegates = {}


    def insertColumnDelegate(self, column, delegate):
        delegate.setParent(self)
        self.delegates[column] = delegate


    def removeColumnDelegate(self, column):
        if column in self.delegates:
            del self.delegates[column]


    def paint(self, painter, option, index):
        delegate = self.delegates.get(index.column())
        if delegate is not None:
            delegate.paint(painter, option, index)
        else:
            QItemDelegate.paint(self, painter, option, index)


    def createEditor(self, parent, option, index):
        delegate = self.delegates.get(index.column())
        if delegate is not None:
            return delegate.createEditor(parent, option, index)
        else:
            return QItemDelegate.createEditor(self, parent, option,
                                              index)


    def setEditorData(self, editor, index):
        delegate = self.delegates.get(index.column())
        if delegate is not None:
            delegate.setEditorData(editor, index)
        else:
            QItemDelegate.setEditorData(self, editor, index)


    def setModelData(self, editor, model, index):
        delegate = self.delegates.get(index.column())
        if delegate is not None:
            delegate.setModelData(editor, model, index)
        else:
            QItemDelegate.setModelData(self, editor, model, index)


class IntegerColumnDelegate(QItemDelegate):

    def __init__(self, minimum=0, maximum=100, parent=None):
        super(IntegerColumnDelegate, self).__init__(parent)
        self.minimum = minimum
        self.maximum = maximum


    def createEditor(self, parent, option, index):
        spinbox = QSpinBox(parent)
        spinbox.setRange(self.minimum, self.maximum)
        spinbox.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        return spinbox


    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toInt()[0]
        editor.setValue(value)


    def setModelData(self, editor, model, index):
        editor.interpretText()
        model.setData(index, QVariant(editor.value()))


class DateColumnDelegate(QItemDelegate):

    def __init__(self, minimum=QDate(), maximum=QDate.currentDate(),
                 format="yyyy-MM-dd", parent=None):
        super(DateColumnDelegate, self).__init__(parent)
        self.minimum = minimum
        self.maximum = maximum
        self.format = QString(format)


    def createEditor(self, parent, option, index):
        dateedit = QDateEdit(parent)
        dateedit.setDateRange(self.minimum, self.maximum)
        dateedit.setAlignment(Qt.AlignRight|Qt.AlignVCenter)
        dateedit.setDisplayFormat(self.format)
        dateedit.setCalendarPopup(True)
        return dateedit


    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toDate()
        editor.setDate(value)


    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.date()))


class PlainTextColumnDelegate(QItemDelegate):
    def __init__(self, parent=None):
        super(PlainTextColumnDelegate, self).__init__(parent)

    def createEditor(self, parent, option, index):
        lineedit = QLineEdit(parent)
        return lineedit

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toString()
        editor.setText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.text()))

class EditColumnDelegate(QItemDelegate):
    def __init__(self, inputType, parent=None):
        super(EditColumnDelegate, self).__init__(parent)
        self.inputType = inputType

    def createEditor(self, parent, option, index):
        edit = self.inputType(parent)
        return edit

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toString()
        editor.setText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.text()), Qt.EditRole)

class ComboBoxColumnDelegate(QItemDelegate):
    def __init__(self, values, parent=None):
        QItemDelegate.__init__(self, parent)
        self.values = []
        self._update(values)

    def _update(self, newValues):
        self.values = [val for val in newValues]

    def createEditor(self, parent, option, index):
        combo_box = ComboBox(parent)
        combo_box.setEditable(False)
        combo_box.addItems(self.values)
        # Call setModelData here to avoid the following problem: if the
        # combobox is untouched (does not get the focus), then an empty string
        # is transmitted instead of the default option.
        self.setModelData(combo_box, index.model(), index)
        return combo_box

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toString()
        if unicode(value) in self.values:
            value_index = self.values.index(unicode(value))
            editor.setCurrentIndex(value_index)

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.currentText()), Qt.EditRole)

class PasswordColumnDelegate(QStyledItemDelegate):
    def __init__(self, inputType, parent=None):
        QStyledItemDelegate.__init__(self, parent)
        self.inputType = inputType

    def createEditor(self, parent, option, index):
        edit = self.inputType(parent)
        return edit

    def setEditorData(self, editor, index):
        value = index.model().data(index, Qt.DisplayRole).toString()
        editor.setText(value)

    def setModelData(self, editor, model, index):
        model.setData(index, QVariant(editor.text()), Qt.EditRole)

    def displayText(self, value, locale):
        """
        always hide data
        """
        try:
            length = len(value.toString())
        except Exception:
            length = 3
        return QString("*" * length)

class BooleanDelegate(QItemDelegate):
    def __init__(self, role, pixmap_on, pixmap_off, text_on, text_off, style_on, style_off, parent=None):
        QItemDelegate.__init__(self, parent)
        self.pixmap_on = pixmap_on
        self.pixmap_off = pixmap_off
        self.text_on = text_on
        self.text_off = text_off
        self.style_on = style_on
        self.style_off = style_off
        self.role = role

        self.icon = QIcon()
        self.icon.addPixmap(pixmap_on, QIcon.Normal, QIcon.On)
        self.icon.addPixmap(pixmap_off, QIcon.Normal, QIcon.Off)

    def createEditor(self, parent, option, index):
        button = QPushButton(self.icon, u'', parent)
        button.setCheckable(True)
        button.setAutoFillBackground(True)
        button.setFocusPolicy(Qt.NoFocus)

        #local function, has knowledge of button (a delegate is stateless).
        def setstyle(checked):
            if checked:
                style = self.style_on
                text = self.text_on
            else:
                style = self.style_off
                text = self.text_off
            button.setStyleSheet(style)
            button.setText(text)

        def emit():
            self.setModelData(button, index.model(), index)

        button.setstyle = setstyle
        self.connect(button, SIGNAL('clicked(bool)'), button.setstyle)
        self.connect(button, SIGNAL('clicked(bool)'), self.setClicked)
        self.connect(button, SIGNAL('toggled(bool)'), emit)

        return button

    def setClicked(self):
        self.emit(SIGNAL("clicked"))

    def setEditorData(self, button, index):
        value = index.model().data(index, self.role).toBool()
        button.setstyle(value)
        if value:
            checkstate = Qt.Checked
        else:
            checkstate = Qt.Unchecked

        button.setChecked(checkstate)

    def setModelData(self, editor, model, index):
        allow = editor.isChecked()
        model.setData(index, QVariant(allow), self.role)

class ActionDelegate(QItemDelegate):
    def __init__(self, role, icon, text, action, parent=None):
        QItemDelegate.__init__(self, parent)
        self.role = role
        self.text = text
        self.action = action
        self.icon = icon

    def createEditor(self, parent, option, index):
        button = QPushButton(self.icon, self.text, parent)
        button.setAutoFillBackground(True)
        button.setFocusPolicy(Qt.NoFocus)
        def forwarder():
            self.action(index)
        self.connect(button, SIGNAL('clicked(bool)'), forwarder)
        return button

    def setEditorData(self, button, index):
        pass

    def setModelData(self, editor, model, index):
        pass


