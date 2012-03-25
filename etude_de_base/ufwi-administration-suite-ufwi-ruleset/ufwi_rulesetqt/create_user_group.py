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

from PyQt4.QtCore import Qt, SIGNAL, QVariant
from PyQt4.QtGui import QListWidgetItem
from operator import itemgetter
from functools import partial

from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError

from ufwi_rulesetqt.create_user_group_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX
from ufwi_rulesetqt.filter import normalizeTextPattern, unescapegroupname

NUMBER_ROLE = Qt.UserRole
NAME_ROLE = NUMBER_ROLE + 1


class CreateUserGroup(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.compatibility = window.compatibility
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.object_id = None
        self.all_groups = None   # list of (name, gid)
        self.connect(self.search_button, SIGNAL("clicked()"), self.searchEvent)
        self.connect(self.refresh_button, SIGNAL("clicked()"), self.refreshEvent)
        self.connect(self.name_list.selectionModel(),
            SIGNAL("selectionChanged(QItemSelection, QItemSelection)"),
            self.nameChanged)
        self.autofill_identifier = True

        self.setRegExpValidator(self.id_text, IDENTIFIER_REGEX)
        if not self.compatibility.user_group_name:
            self.setNonEmptyValidator(self.number_text)
        self.setNonEmptyValidator(self.name_text)

    def nameChanged(self, selected, deselected):
        item = self.name_list.currentItem()
        if not item:
            return
        name = unicode(item.data(NAME_ROLE).toString())
        self.name_text.setText(name)
        if self.autofill_identifier:
            self.id_text.setText(name)
        number, ok = item.data(NUMBER_ROLE).toUInt()
        if ok:
            self.number_text.setText(unicode(number))

    def startEditing(self):
        self.id_text.setFocus()
        self.refresh_button.setEnabled(False)
        self.execLoop()

    def resetSearch(self):
        self.name_list.clear()
        self.name_list.addItem(tr("Enter first characters of group name,"))
        self.name_list.addItem(tr("click on Search,"))
        self.name_list.addItem(tr("and select an user group"))

    def create(self):
        self.id_text.setText(u'')
        self.autofill_identifier = True
        self.object_id = None
        self.name_text.setText(u'')
        self.resetSearch()
        self.number_text.setText(u'')
        self.startEditing()

    def modify(self, object):
        self.object_id = object['id']
        self.id_text.setText(self.object_id)
        self.autofill_identifier = False
        if 'group' in object:
            number = unicode(object['group'])
        else:
            number = u''
        self.number_text.setText(number)
        name = object.get('name', u'')
        if not name:
            # Backward compatibility with ruleset created by ufwi_ruleset < 3.0.4:
            # use the identifier as the group name (both should be equal most
            # of the time)
            name = object['id']
        self.name_text.setText(name)
        if name:
            self.searchEvent()
        else:
            self.resetSearch()
        self.startEditing()

    def refreshEvent(self):
        self.refresh(use_cache=False, update_search=True)

    def _refreshDone(self):
        self.window.unfreeze()

    def _refreshSuccess(self, update_search, groups):
        self.all_groups = [(name, int(number) if number else None) for name, number in groups]
        self.all_groups.sort(key=itemgetter(0))
        if update_search:
            self.searchEvent(refresh=False)
        self._refreshDone()

    def _refreshError(self, err):
        self._refreshDone()
        self.window.exception(err,
            tr("Error on getting all user groups!"),
            dialog=True)

    def refresh(self, use_cache, update_search=False):
        self.window.freeze(tr("Getting user groups ..."))
        async = self.window.ruleset.client.async()
        async.call('system', 'getUserGroups', use_cache,
            callback=partial(self._refreshSuccess, update_search),
            errback=self._refreshError)

    def searchEvent(self, refresh=True):
        name = unicode(self.name_text.text())
        self.searchByName(name, refresh=refresh)

    def searchByName(self, name_pattern, refresh=True):
        if self.all_groups is None:
            if refresh:
                self.refresh(use_cache=True, update_search=True)
            return
        name_pattern = normalizeTextPattern(name_pattern)
        self.name_list.clear()
        for name, number in self.all_groups:
            if name_pattern not in normalizeTextPattern(name):
                continue
            if number is not None:
                label = u"%s (%s)" % (name, number)
            else:
                label = name
            item = QListWidgetItem(unescapegroupname(label))
            item.setData(NUMBER_ROLE, QVariant(number))
            item.setData(NAME_ROLE, QVariant(name))
            self.name_list.addItem(item)
        self.refresh_button.setEnabled(True)

    def save(self):
        identifier = unicode(self.id_text.text())
        attr = {}
        number = unicode(self.number_text.text())
        if number:
            attr['group'] = int(number)
        if self.compatibility.user_group_name:
            attr['name'] = unicode(self.name_text.text())
        return self.saveObject(identifier, 'user_groups', attr)

