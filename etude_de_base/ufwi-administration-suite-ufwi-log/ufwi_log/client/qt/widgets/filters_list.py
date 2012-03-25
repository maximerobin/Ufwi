# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

from PyQt4.QtGui import QWidget, QHBoxLayout, QLabel, \
                        QFrame, QLineEdit, QSpinBox, \
                        QDialog, QComboBox, QDialogButtonBox, \
                        QVBoxLayout
from PyQt4.QtCore import SIGNAL, QObject, QTimer, Qt, QVariant

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.tools import createLink
from ufwi_log.client.qt.args import arg_types
from ufwi_log.client.qt.fetchers.base import GenericFetcher

class EditFilterDialog(QDialog):
    def __init__(self, client, args, filters, parent=None):
        QDialog.__init__(self, parent)

        self.vbox = QVBoxLayout(self)
        self.client = client
        self.args = args
        self.filters = filters
        self.parent = parent

        self.setWindowTitle(self.tr('Add a filter'))

        self.buttonBox = QDialogButtonBox(self)
        self.buttonBox.setEnabled(True)
        self.buttonBox.setOrientation(Qt.Horizontal)
        self.buttonBox.setStandardButtons(QDialogButtonBox.Cancel | QDialogButtonBox.Ok)
        self.connect(self.buttonBox, SIGNAL("accepted()"), self.accept)
        self.connect(self.buttonBox, SIGNAL("rejected()"), self.reject)

        self.filter = QComboBox()
        self.valuebox = None
        self.vbox.addWidget(self.filter)

        for arg in self.filters:
            if not arg in arg_types or self.args.has_key(arg):
                continue
            if not isinstance(arg_types[arg].filter(self.client, arg, '', compatibility=self.parent.compatibility), QWidget):
                print 'warning, ', arg, 'isn\'t a widget'
                continue
            self.filter.addItem(arg_types[arg].label, QVariant(arg))

        index = -1
        if self.filter.count() > 0:
            index = 0
        self.filter.setCurrentIndex(index)
        self.editFilterChanged(index)

        self.connect(self.filter, SIGNAL('currentIndexChanged(int)'), self.editFilterChanged)

        self.vbox.addWidget(self.buttonBox)

    def editFilterChanged(self, index):
        if self.valuebox:
            self.vbox.removeWidget(self.valuebox)
            self.valuebox.hide()

        if index < 0:
            self.valuebox = QLineEdit()
            self.value = self.valuebox
            self.valuebox.setEnabled(False)
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(False)
        else:
            self.buttonBox.button(QDialogButtonBox.Ok).setEnabled(True)
            arg = unicode(self.filter.itemData(index).toString())
            self.value = arg_types[arg].filter(self.client, arg, '', self.parent.compatibility)
            if arg_types[arg].unit:
                self.valuebox = QWidget(self)
                layout = QHBoxLayout(self.valuebox)
                layout.addWidget(self.value)
                layout.addWidget(QLabel(arg_types[arg].unit))
            else:
                self.valuebox = self.value

        self.connect(self, SIGNAL('finished(int)'), self.valuebox.done)
        self.vbox.insertWidget(1, self.valuebox)

    def run(self):
        if self.exec_():
            return self.value
        return None

class FilterWidgetError(Exception):
    pass

class FilterWidget(QFrame):

    KEY_POS, VALUE_POS, UNIT_POS, EDIT_POS, REMOVE_POS = range(5)

    def __init__(self, client, key, value, parent=None):
        QFrame.__init__(self, parent)

        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setContentsMargins(2, 2, 2, 2)

        self.parent_widget = parent

        filterbox = QHBoxLayout(self)
        filterbox.setContentsMargins(1, 1, 1, 1)

        self.client = client
        try:
            self.arg_data = arg_types[key].data(key, value, GenericFetcher(self.client), parent.compatibility)
            self.arg_filter = arg_types[key].filter(self.client, key, value, parent.compatibility)
        except KeyError:
            raise FilterWidgetError()

        if isinstance(self.arg_data.label, QObject):
            raise FilterWidgetError()

        self.arglabel = QLabel('<b>%s</b>' % arg_types[key].label)
        self.argvalue = QLabel('%s' % self.arg_data.label)
        self.argunit = QLabel(arg_types[key].unit)
        filterbox.insertWidget(self.KEY_POS, self.arglabel)
        filterbox.insertWidget(self.VALUE_POS, self.argvalue)
        filterbox.insertWidget(self.UNIT_POS, self.argunit)

        self.argedit = createLink(':/icons-20/edit.png', self.editFilter)
        self.argedit.setStyleSheet('')
        self.argremove = createLink(':/icons-20/wrong.png', self.removeFilter)
        self.argremove.setStyleSheet('')

        if isinstance(self.arg_filter, QLineEdit):
            self.connect(self.arg_filter, SIGNAL('returnPressed()'), self.editFilter)
        elif isinstance(self.arg_filter, QSpinBox):
            self.connect(self.arg_filter, SIGNAL('editingFinished()'), self.editFilter)

        filterbox.insertWidget(self.EDIT_POS, self.argedit)
        filterbox.insertWidget(self.REMOVE_POS, self.argremove)

        self.edditing = False

    def editFilter(self):
        if not self.edditing:
            self.layout().removeWidget(self.argvalue)
            self.argvalue.hide()
            self.layout().insertWidget(self.VALUE_POS, self.arg_filter)
            self.arg_filter.show()
            self.edditing = True
        else:
            self.layout().removeWidget(self.arg_filter)
            self.arg_filter.hide()
            self.layout().insertWidget(self.VALUE_POS, self.argvalue)
            self.argvalue.show()
            self.arg_data = arg_types[self.arg_data.arg].data(self.arg_data.arg, self.arg_filter.getValue(), GenericFetcher(self.client))
            self.argvalue.setText(unicode(self.arg_data.label))
            self.edditing = False
            self.emit(SIGNAL('changeFilter'), self.arg_data.arg, self.arg_filter.getValue())

    def removeFilter(self):
        if not self.edditing:
            self.emit(SIGNAL('removeFilter'), self.arg_data.arg)
        else:
            self.layout().removeWidget(self.arg_filter)
            self.arg_filter.hide()
            self.layout().insertWidget(self.VALUE_POS, self.argvalue)
            self.argvalue.show()
            self.edditing = False

class FiltersListWidget(QWidget):
    def __init__(self, client, parent=None):
        QWidget.__init__(self, parent)

        self.client = client
        self.filtersWidgetsList = []
        self.args = {}
        self.filters = []

        self.filtersWidget = QHBoxLayout(self)
        self.filtersWidget.setContentsMargins(5, 1, 1, 1)

        label = u'<h3>%s</h3>' % tr("Filters:")
        self.filtersWidget.addWidget(QLabel(label))
        self.add_link = createLink(':/icons-20/add.png', self.addFilter)
        self.filtersWidget.addWidget(self.add_link)
        self.filtersWidget.addStretch()

        self.compatibility = None

    def addFilter(self):
        dialog = EditFilterDialog(self.client, self.args, self.filters, parent=self)
        value = dialog.run()
        if value:
            self.filterChanged(value.filter_arg, value.getValue())

    def update(self, args, filters):
        for filterWidget in self.filtersWidgetsList:
            self.filtersWidget.removeWidget(filterWidget)
            filterWidget.setParent(None)
            filterWidget.hide()

        self.args = args
        self.filters = filters
        self.filtersWidgetsList = []

        for key, value in args.items():
            try:
                filterWidget = FilterWidget(self.client, key, value, self)
            except FilterWidgetError:
                continue

            self.connect(filterWidget, SIGNAL('changeFilter'), self.filterChanged)
            self.connect(filterWidget, SIGNAL('removeFilter'), self.removeFilter)
            self.filtersWidget.insertWidget(1, filterWidget)
            self.filtersWidgetsList += [filterWidget]

        available_filters = set(self.filters).difference(set(self.args.iterkeys()))
        if len(available_filters) > 0:
            self.add_link.show()
        else:
            self.add_link.hide()

        if not filters and not self.filtersWidgetsList:
            self.hide()
        else:
            self.show()

    def filterChanged(self, key, value):
        QTimer.singleShot(0, lambda: self.emit(SIGNAL('changeFilter'), key, value))

    def removeFilter(self, key):
        QTimer.singleShot(0, lambda: self.emit(SIGNAL('removeFilter'), key))

    def setCompatibility(self, compatibility):
        self.compatibility = compatibility
