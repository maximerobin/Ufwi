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

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QLabel, QHBoxLayout, QFrame, QSizePolicy, QPalette

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.tools import abstractmethod, formatList
from ufwi_rpcc_qt.html import htmlImage, htmlLink

from ufwi_ruleset.common.update import Updates
from ufwi_rulesetqt.objects import Group

class FilterWidget(QFrame):
    def __init__(self, parent, html, tooltip, widget_key):
        QFrame.__init__(self, parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setContentsMargins(2, 2, 2, 2)
        self.setSizePolicy(QSizePolicy(QSizePolicy.Maximum, QSizePolicy.Maximum))

        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(layout)

        label = QLabel(html)
        if tooltip:
            label.setToolTip(tooltip)
        layout.addWidget(label)

        html = htmlImage(":/icons-32/wrong.png")
        html = htmlLink(widget_key, html)
        label = QLabel(unicode(html))
        label.setCursor(Qt.PointingHandCursor)
        label.setTextInteractionFlags(
            Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
        layout.addWidget(label)
        self.delete_widget = label

class Filter:
    def __init__(self, parent):
        self.parent = parent
        self.rules = parent.rules
        self.frame = parent.frame
        self.layout = parent.layout

    @abstractmethod
    def match(self, rule, exact):
        # return :
        # - None: show the rule, but test next filter
        # - True: show the rule, stop the filter
        # - False: hide the rule
        pass

    def clear(self):
        return False

    @abstractmethod
    def isEmpty(self):
        pass

    def _appendWidget(self, widget):
        # add the new widget before the stretch (QSpacerItem)
        pos = self.layout.count() - 1
        self.layout.insertWidget(pos, widget)

    def _removeWidget(self, widget):
        self.layout.removeWidget(widget)
        widget.setParent(None)
        widget.hide()
        widget.deleteLater()

    def getUrlIdentifier(self, object):
        return None

class ConsistencyFilter(Filter):
    def __init__(self, parent):
        Filter.__init__(self, parent)
        self.widget = FilterWidget(self.frame,
            tr("Consistency errors"),
            tr("Show only conflicting rules"),
            '1')
        self.frame.connect(self.widget.delete_widget, SIGNAL('linkActivated(const QString&)'), self.deleteWidget)
        self._appendWidget(self.widget)
        self.widget.hide()
        self.display_widget = False
        self.identifiers = set()  # rule identifiers (int)
        self.clear()

    def isEmpty(self):
        return (not self.identifiers)

    def match(self, rule, exact):
        if not self.identifiers:
            return True
        return (rule['id'] in self.identifiers)

    def showWidget(self):
        self.widget.show()

    def hideWidget(self):
        self.widget.hide()

    def deleteWidget(self, widget_key):
        self.clear()
        self.parent.updateHelp()
        updates = Updates()
        self.rules.display(updates)

    def clear(self):
        updated = (len(self.identifiers) != 0)
        self.identifiers.clear()
        self.hideWidget()
        return updated

    def setIdentifiers(self, identifiers):
        old_identifiers = self.identifiers
        self.identifiers = set(identifiers)
        updated = (old_identifiers != self.identifiers)
        if self.identifiers:
            self.showWidget()
        else:
            self.hideWidget()
        return updated

class AttributeFilter(Filter):
    def __init__(self, parent, library, *attributes):
        Filter.__init__(self, parent)
        self.library = library
        self.attributes = attributes
        self.identifiers = set()
        self.parents = set()
        self.widgets = {}
        self.next_widget_key = 1

    def add(self, object):
        identifier = object['id']
        if identifier in self.identifiers:
            return False
        self.identifiers.add(identifier)
        try:
            object = self.library[identifier]
            parents = object.getParents() | object.getChildren()
            self.parents |= parents
        except KeyError:
            # Invalid identifier: ignore the parents
            parents = set()

        # Create HTML view
        html = object.createHTML()
        if parents:
            text = formatList(sorted(parents), u",\n", 200)
            tooltip = tr("Parents:\n%s") % text
        else:
            tooltip = None

        # Create widget
        widget_key = unicode(self.next_widget_key)
        self.next_widget_key += 1
        widget = FilterWidget(self.frame, unicode(html), tooltip, widget_key)
        widget.parents = parents
        self.frame.connect(widget.delete_widget, SIGNAL('linkActivated(const QString&)'), self.deleteWidget)
        self.widgets[widget_key] = (widget, identifier)
        self._appendWidget(widget)
        return True

    def deleteWidget(self, widget_key):
        widget_key = unicode(widget_key)
        widget, identifier = self.widgets.pop(widget_key)
        self._removeWidget(widget)
        self.identifiers.remove(identifier)
        self.parents -= widget.parents
        self.parent.updateHelp()
        updates = Updates()
        self.rules.display(updates)

    def match(self, rule, exact):
        if not self.identifiers:
            return True
        identifiers = set()
        for attribute in self.attributes:
            for object in rule[attribute]:
                identifiers.add(object['id'])
                if (not exact) and isinstance(object, Group):
                    identifiers |= set(object['objects'])
        if exact:
            intersection = identifiers & self.identifiers
        else:
            intersection = identifiers & (self.identifiers | self.parents)
        return bool(intersection)

    def clear(self):
        updated = (len(self.identifiers) != 0)
        self.identifiers.clear()
        self.parents.clear()
        for widget, identifier in self.widgets.itervalues():
            self._removeWidget(widget)
        self.widgets.clear()
        return updated

    def isEmpty(self):
        return (not self.identifiers)

    def getUrlIdentifier(self, object):
        return self.library.getUrlIdentifier(object)

class RuleFilter:
    def __init__(self, rules, help_text):
        window = rules.window
        self.rules = rules
        self.exact_widget = rules.getWidget('filter_exact')
        self.layout = rules.filter_layout
        self.frame = rules.filter_frame
        window.connect(self.exact_widget, SIGNAL("toggled(bool)"), self.toggleExact)
        self.consistency_filter = ConsistencyFilter(self)
        self.filters = [self.consistency_filter]

        # Help widget
        self.help_widget = QLabel(help_text)
        self.help_widget.setForegroundRole(QPalette.Dark)
        self.help_widget.setWordWrap(True)
        pos = self.layout.count() - 1
        self.layout.insertWidget(pos, self.help_widget)

    def toggleExact(self, exact):
        updates = Updates()
        if any((not filter.isEmpty()) for filter in self.filters):
            self.rules.display(updates)

    def clear(self):
        for filter in self.filters:
            filter.clear()
        self.help_widget.show()

    def updateHelp(self):
        if any((not filter.isEmpty()) for filter in self.filters):
            # at least one filter is displayed
            self.help_widget.hide()
        else:
            self.help_widget.show()

    def match(self, acl):
        exact = self.exact_widget.isChecked()
        for filter in self.filters:
            match = filter.match(acl, exact )
            if match == False:
                return False
        return True

    def dragEnter(self, url):
        for filter in self.filters:
            if filter.getUrlIdentifier(url):
                return True
        return False

    def drop(self, url):
        updates = Updates()
        for filter in self.filters:
            identifier = filter.getUrlIdentifier(url)
            if not identifier:
                continue
            object = filter.library[identifier]
            if not filter.add(object):
                # Duplicate filter: do nothing
                return True
            self.help_widget.hide()
            self.rules.display(updates)
            return True
        return False

    def setConsistencyFilter(self, identifiers):
        updated = False
        if identifiers:
            for filter in self.filters:
                if filter is self.consistency_filter:
                    continue
                updated |= filter.clear()
        updated |= self.consistency_filter.setIdentifiers(identifiers)
        self.updateHelp()
        if updated:
            updates = Updates()
            self.rules.display(updates)

