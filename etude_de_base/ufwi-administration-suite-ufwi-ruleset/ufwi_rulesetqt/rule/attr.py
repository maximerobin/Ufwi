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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QWidget, QLabel, QSizePolicy, QHBoxLayout, QVBoxLayout
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.html import htmlImage, htmlParagraph, Html, NBSP

LOG_ICON = ":/icons-32/edit.png"

class AclAttribute:
    def mousePressEvent(self, event):
        event.ignore()

    def mouseReleaseEvent(self, event):
        event.ignore()

    def mouseMoveEvent(self, event):
        event.ignore()

    def copyToolTip(self, object):
        tooltip = object.getToolTip()
        if not tooltip:
            return
        self.setToolTip(tooltip)

class AclLayout(QVBoxLayout):
    def __init__(self):
        QVBoxLayout.__init__(self)
        self.setSpacing(0)
        self.setContentsMargins(11, 1, 11, 1)

class AclWidget(AclAttribute, QWidget):
    def __init__(self):
        QWidget.__init__(self)

class AclLabel(AclAttribute, QLabel):
    def __init__(self, text, format=Qt.RichText):
        QLabel.__init__(self)
        self.setTextFormat(format)
        self.setText(text)

class ClickableLabel(AclLabel):
    def __init__(self, text, object, rule_list, rule_id, edit_key, format=Qt.RichText):
        AclLabel.__init__(self, unicode(text), format)
        self.rule_list = rule_list
        self.rule_id = rule_id
        self.edit_key = edit_key
        if object:
            self.identifier = object['id']
            self.copyToolTip(object)
        else:
            self.identifier = None

    def mouseDoubleClickEvent(self, event):
        if not self.edit_key:
            event.ignore()
            return
        self.rule_list.edit(self.rule_id, highlight=(self.edit_key, self.identifier))
        event.accept()

class AclNetwork(ClickableLabel):
    def __init__(self, rule_list, rule_id, edit_key, network, align_right):
        icon = network.getIcon()
        icon = htmlImage(icon, align="middle")
        identifier = network.formatID()
        if align_right:
            html = icon + NBSP + Html(identifier)
        else:
            html = Html(identifier) + NBSP + icon
        html = htmlParagraph(html)
        ClickableLabel.__init__(self, html, network, rule_list, rule_id, edit_key)
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(policy )
        align = Qt.AlignVCenter
        if align_right:
            align |= Qt.AlignRight
        else:
            align |= Qt.AlignLeft
        self.setAlignment(align)

class AclNetworks(AclWidget):
    def __init__(self, rule_list, rule_id, edit_key, networks, align_right):
        AclWidget.__init__(self)
        layout = AclLayout()
        for network in networks:
            label = AclNetwork(rule_list, rule_id, edit_key, network, align_right)
            layout.addWidget(label)
        self.setLayout(layout)

class AclUser(ClickableLabel):
    def __init__(self, rule_list, rule_id, edit_key, user_group):
        html = user_group.createHTML(link=False)
        ClickableLabel.__init__(self, html, user_group, rule_list, rule_id, edit_key)
        policy = self.sizePolicy()
        policy.setHorizontalPolicy(QSizePolicy.Expanding)
        self.setSizePolicy(policy )
        align = Qt.AlignVCenter | Qt.AlignHCenter
        self.setAlignment(align)

class AclUsers(AclWidget):
    def __init__(self, rule_list, rule_id, edit_key, user_groups):
        AclWidget.__init__(self)
        layout = AclLayout()
        for user_group in user_groups:
            label = AclUser(rule_list, rule_id, edit_key, user_group)
            layout.addWidget(label)
        self.setLayout(layout)

class AclProtocol(ClickableLabel):
    def __init__(self, rule_list, rule_id, edit_key, protocol):
        html = protocol.createHTML(icon=False, link=False)
        ClickableLabel.__init__(self, html, protocol,
            rule_list, rule_id, edit_key)
        self.setAlignment(Qt.AlignCenter)

class AclDecision(AclLabel):
    def __init__(self, icon, tooltip=None):
        html = htmlImage(icon)
        AclLabel.__init__(self, unicode(html))
        self.setAlignment(Qt.AlignCenter)
        if tooltip:
            self.setToolTip(tooltip)

class AclFilters(AclWidget):
    def __init__(self, rule_list, rule_id, edit_key,
    filters, decision_icon, decision_tooltip=None):
        AclWidget.__init__(self)
        layout = AclLayout()
        index = len(filters) // 2
        for filter in filters[:index]:
            label = AclProtocol(rule_list, rule_id, edit_key, filter)
            layout.addWidget(label)
        decision = AclDecision(decision_icon, decision_tooltip)
        layout.addWidget(decision)
        for filter in filters[index:]:
            label = AclProtocol(rule_list, rule_id, edit_key, filter)
            layout.addWidget(label)
        self.setLayout(layout)

class AclOption(ClickableLabel):
    def __init__(self, rule_list, rule_id, edit_key, object):
        html = object.createHTML(text=False, link=False)
        ClickableLabel.__init__(self, html, object,
            rule_list, rule_id, edit_key)

class AclOptions(AclWidget):
    def __init__(self, rule_list, acl):
        AclWidget.__init__(self)
        self.layout = QHBoxLayout()
        if acl['log']:
            html = htmlImage(LOG_ICON)
            log = AclLabel(unicode(html))
            if 'log_prefix' in acl:
                tooltip = tr('Log connections: "%s"') % acl['log_prefix']
            else:
                tooltip = tr("Log connections")
            log.setToolTip(tooltip)
            self.layout.addWidget(log)
        for edit_key, objects in (
            ('applications', acl['applications']),
            ('operating_systems', acl['operating_systems']),
            ('periodicities', acl['periodicities']),
            ('durations', acl['durations']),
        ):
            for object in objects:
                label = AclOption(rule_list, acl['id'], edit_key, object)
                self.layout.addWidget(label)
        self.setLayout(self.layout)

class AclComment(ClickableLabel):
    def __init__(self, rule_list, acl):
        if 'comment' in acl:
            text = acl['comment']
        else:
            text = u''
        ClickableLabel.__init__(self, text, None, rule_list, acl['id'], 'comment', format=Qt.PlainText)
        self.setWordWrap(True)

