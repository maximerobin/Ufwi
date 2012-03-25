#coding: utf-8
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


from PyQt4.QtCore import Qt, SIGNAL, QObject
from PyQt4.QtGui import QFrame, QHBoxLayout, QIcon, QLabel, QVBoxLayout, QWidget

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.input_widgets import Button
from ufwi_conf.client.qt.input_widgets import EditButton, NoopButton

class FoldButton(Button):
    _ICONS = None
    _TOOLTIPS = None

    @staticmethod
    def _mkStatics():
        FoldButton._ICONS = {
            True: QIcon(":/icons/fold"),
            False: QIcon(":/icons/unfold")
        }
        FoldButton._TOOLTIPS = {
            True: tr("Click to fold"),
            False: tr("Click to unfold")
        }

    def __init__(self, parent=None):
        Button.__init__(self, parent)
        if FoldButton._ICONS is None:
            FoldButton._mkStatics()
        self.expanded = False
        self.connect(self, SIGNAL('clicked()'), self.clicked)
        self.updateView()


    def clicked(self):
        self.toggle()
        self.updateView()

    def toggle(self):
        self.expanded = not self.expanded
        self.emit(SIGNAL('changed'), self.expanded)

    def updateView(self):
        self.setIcon(FoldButton._ICONS[self.expanded])
        self.setToolTip(FoldButton._TOOLTIPS[self.expanded])

    def status(self):
        return self.expanded

class FoldableData(QObject):
    """
    You are likely to want to subclass this.
    abstract must have an update() method if we are to receive a 'modified' signal
    """
    def __init__(self, content, name='', abstract=None, menu=None, parent=None):
        QObject.__init__(self, parent)
        self.closing = False
        self.connect(self, SIGNAL('destroyed()'), self.setClosed)
        assert isinstance(content, QWidget)
        assert isinstance(abstract, QWidget), "%s is not a QWidget but a %s" % \
            (abstract, (abstract.__class__))
        self.content = content
        self.name = name
        self.abstract = abstract
        self.menu = menu

        self.connect(self.content, SIGNAL('modified'), self._reemit)

    def setClosed(self):
        self.closing = True

    def setName(self, name):
        self.name = name
        self.emit(SIGNAL('name changed'), name)

    def setMenu(self, menu):
        self.menu = menu
        self.emit(SIGNAL('menu changed'), menu)

    def _reemit(self, *args):
        self.abstract.update()
        self.emit(SIGNAL('modified'), *args)

class Title(QWidget):
    def __init__(self, foldable_data, parent=None):
        QWidget.__init__(self, parent)

        self.foldable = False

        #Contained widgets
        self.fold_button = FoldButton()
        self.noop_button = NoopButton()
        self.name = QLabel()
        self.abstract = foldable_data.abstract
        self.edit_button = EditButton()

        #Layout
        box = QHBoxLayout(self)
        box.setMargin(0)
        box.setAlignment(Qt.AlignLeft)
        box.addWidget(self.fold_button)
        box.addWidget(self.noop_button)
        box.addWidget(self.name)
        box.addWidget(self.abstract)
        box.addStretch()
        box.addWidget(self.edit_button)
        self.setFoldable(True)

        #SIGNALS to update content
        self.connect(foldable_data, SIGNAL('name changed'), self.setName)
        self.connect(foldable_data, SIGNAL('menu changed'), self.setMenu)

        #Initialize content
        self.setName(foldable_data.name)
        self.setMenu(foldable_data.menu)

    def setName(self, name):
        self.name.setText('<h2>%s</h2>' % name)

    def setMenu(self, menu):
        self.edit_button.setMenu(menu)

    def mouseDoubleClickEvent(self, event):
        """
        double clicking on elements' title bar has the same effect
        as clicking on expand/collapse button
        """
        if not self.foldable:
            return
        self.fold_button.emit(SIGNAL('clicked()'))

    def setFoldable(self, foldable):
        if foldable == self.foldable:
            return

        self.foldable = foldable

        if foldable:
            self.fold_button.show()
            self.noop_button.hide()
            return
        self.fold_button.hide()
        self.noop_button.show()

class FoldableWidget(QFrame):
    def __init__(self, foldable_data, start_folded=True, parent=None):
        QFrame.__init__(self, parent)

        self.closing = False
        self.foldable_data = foldable_data

        self.foldable = True
        self.setHideable(True)

        self.title = Title(foldable_data)
        self.content = foldable_data.content

        self.setFrameStyle(QFrame.StyledPanel | QFrame.Raised)
        box = QVBoxLayout(self)
        box.setMargin(0)
        for item in (self.title, self.content):
            box.addWidget(item)

        #SIGNAL to update folding
        self.connect(self.title.fold_button, SIGNAL('changed'), self.updateFold)

        self.updateFold(not start_folded)
        self.connect(self.foldable_data, SIGNAL('modified'), self._reemit)

    def updateFold(self, expanded):
        if self.title.fold_button.status() != expanded:
            self.title.fold_button.clicked()
        if expanded:
            self.expand()
            return
        self.fold()

    def fold(self):
        self.content.hide()
        self.title.abstract.show()
        self.emit(SIGNAL('folded'))

    def expand(self):
        self.content.show()
        self.title.abstract.hide()
        self.emit(SIGNAL('expanded'))

    def setFoldable(self, foldable):
        if foldable == self.foldable:
            return

        self.foldable = foldable
        self.title.setFoldable(foldable)

        if not foldable:
            """
            Paradoxal ?
            Actually we hide the contents widget
            """
            self.fold()

    def setImmutableVisibility(self, boolean):
        """
        If the widget is foldable, does nothing
        """
        if self.foldable or (not self.hideable):
            return

        self.setVisible(boolean)

    def setHideable(self, boolean):
        self.hideable = boolean

    def _reemit(self, *args):
        self.emit(SIGNAL('modified'), *args)

    def closeEvent(self, closeEvent):
        self.closing = True
        QFrame.closeEvent(self, closeEvent)


