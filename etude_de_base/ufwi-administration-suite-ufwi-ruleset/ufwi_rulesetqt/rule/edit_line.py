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

from PyQt4.QtCore import SIGNAL

from ufwi_rulesetqt.tools import getDragUrl
from ufwi_rulesetqt.rule.tools import showLibrary
from ufwi_rpcc_qt.colors import COLOR_DISABLED

class EditLine:
    """
    QLineEdit using drag & drop. The widget accept only one dropped item.
    """
    def __init__(self, parent, libraries, widget, clear_button):
        self.parent = parent
        self.widget = widget
        self.libraries = libraries
        self.clear_button = clear_button
        self.setupWidgets()
        self.clear()

    def setupWidgets(self):
        self.window = self.parent.window
        self.window.connect(self.clear_button, SIGNAL("clicked()"), self.clear)
        self.widget.mousePressEvent = self.mousePressEvent
        self.widget.dragEnterEvent = self.dragEnterEvent
        self.widget.dropEvent = self.dropEvent

    def clear(self):
        self.object = None
        self.widget.setText(u'')
        self.clear_button.setEnabled(False)

    def getDragObject(self, event):
        url = getDragUrl(event)
        if url is None:
            event.ignore()
            return None
        event.acceptProposedAction()
        for library in self.libraries:
            identifier = library.getUrlIdentifier(url)
            if identifier is None:
                continue
            return library[identifier]
        return None

    def mousePressEvent(self, event):
        self.widget.__class__.mousePressEvent(self.widget, event)
        showLibrary(self.window, self.libraries)

    def dragEnterEvent(self, event):
        object = self.getDragObject(event)
        if object is not None:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        object = self.getDragObject(event)
        if object is None:
            event.ignore()
            return
        event.acceptProposedAction()
        self.setObject(object)

    def save(self, attr):
        for library in self.libraries:
            key = library.REFRESH_DOMAIN
            attr[key] = tuple()
        if self.object:
            key = self.object.library.REFRESH_DOMAIN
            identifier = self.object['id']
            attr[key] = (identifier,)

    def edit(self, acl):
        value = None
        for key in ('periodicities', 'durations'):
            if not acl[key]:
                continue
            value = acl[key][0]
            break
        self.setObject(value)

    def setObject(self, object):
        if object is not None:
            self.object = object
            self.widget.setText(object['id'])
            self.clear_button.setEnabled(True)
        else:
            self.clear()

    def highlight(self, identifier):
        self.widget.setFocus()

    def setEnabled(self, enabled):
        self.widget.setEnabled(enabled)
        if enabled:
            style = u';'
        else:
            style = u'background: %s;' % COLOR_DISABLED
        self.widget.setStyleSheet(style)

