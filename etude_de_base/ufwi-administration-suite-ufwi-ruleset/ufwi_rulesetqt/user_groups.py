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

from ufwi_rpcd.common import tr

from ufwi_rulesetqt.create_user_group import CreateUserGroup
from ufwi_rulesetqt.library import Library, LibraryMenu, LibraryActions
from ufwi_rulesetqt.objects import Object, Group
from ufwi_rulesetqt.filter import Filter

USER_GROUP_ICON = ":/icons-32/users"

class UserGroupActions(LibraryActions):
    def __init__(self, library, object):
        LibraryActions.__init__(self, library, object)
        ruleset = library.ruleset
        self.template = (
            (not ruleset.read_only)
            and ruleset.is_template
            and bool(object)
            and object.isEditable()
            and (not isinstance(object, Group))
            and (not object.isGeneric()))

class UserGroupMenu(LibraryMenu):
    def __init__(self, library, create_text, modify_text, delete_text):
        LibraryMenu.__init__(self, library, create_text, modify_text, delete_text)
        self.templatize_action = self.add(None,
            tr("Convert to generic user group"),
            library.templatizeEvent)

    def display(self, event, actions):
        self.templatize_action.setEnabled(actions.template)
        LibraryMenu.display(self, event, actions)

class UserGroup(Object):
    def __init__(self, library, item):
        try:
            item['group'] = int(item['group'])
        except KeyError:
            pass
        Object.__init__(self, library, item)

    def getToolTip(self):
        attr = []
        if 'group' in self:
            attr.append(tr('number=%s') % self['group'])
        if 'name' in self:
            name = u'"%s"' % self['name']
            attr.append(tr('name=%s') % name)
        if attr:
            return tr("User group: %s") % u', '.join(attr)
        else:
            return tr('Generic user group "%s"') % self['id']

    def getIcon(self):
        return USER_GROUP_ICON

    def getBackground(self):
        return ":/backgrounds/users"

    def isGeneric(self):
        if 'group' in self:
            return False
        if 'name' in self:
            return False
        return True

    def createInformation(self):
        if self.isGeneric():
            title = tr('Generic User Group')
        else:
            title = tr('User Group')
        options = [(tr('Identifier'), self['id'])]
        if 'group' in self:
            options.append((tr('Group number'), unicode(self['group'])))
        if 'name' in self:
            options.append((tr('Group name'), unicode(self['name'])))
        options.append((tr('References'), self.createReferencesHTML()))
        return (title, options)

class UserGroupFilter(Filter):
    def matchGroup(self, group):
        text = unicode(group)
        return text.startswith(self.pattern)

    def match(self, object):
        if Filter.match(self, object):
            return True
        if ('group' in object) \
        and self.matchGroup(object['group']):
            return True
        return False

class UserGroups(Library):
    REFRESH_DOMAIN = u"user_groups"
    URL_FORMAT = u"user_group:%s"
    RULESET_ATTRIBUTE = "user_groups"
    CHILD_CLASS = UserGroup
    ACTIONS = UserGroupActions

    def __init__(self, window):
        Library.__init__(self, window, "group")
        self.dialog = CreateUserGroup(window)
        self.list = window.group_list
        self.setupWindow()
        self.filter = UserGroupFilter()

    def setupWindow(self):
        self.setButtons()
        self.setContainer(self.list)
        self.setMenu(UserGroupMenu(self,
            tr("New user group"),
            tr("Edit this user group"),
            tr("Delete this user group")))

    def getTreeKey(self, user_group):
        return u"group"

    def createTreeKeyLabel(self, key):
        return tr("User groups")

