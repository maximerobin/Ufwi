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

from ufwi_rpcd.backend import tr

from ufwi_ruleset.common.nufw import MIN_GROUP, MAX_GROUP

from ufwi_ruleset.forward.attribute import Integer, Unicode
from ufwi_ruleset.forward.object import Object
from ufwi_ruleset.forward.library import Library
from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.group import Group

# Windows maximum length:
# http://technet.microsoft.com/fr-fr/library/active-directory-maximum-limits-scalability(WS.10).aspx
#
# POSIX: "getconf -a|grep _POSIX_MAX_CANON" is 255 (bytes)
MAX_GROUP_NAME_LENGTH = 1000   # characters

def getUserGroupNumber(group):
    try:
        group = int(group)
    except ValueError:
        raise RulesetError(
            tr("Invalid user group: %s"),
            unicode(group))
    if not(MIN_GROUP <= group <= MAX_GROUP):
        raise RulesetError(tr("Invalid user group number: %s"), group)
    return group

class GroupNumber(Integer):
    def __init__(self, optional=False):
        Integer.__init__(self, min=MIN_GROUP, max=MAX_GROUP, optional=optional)

class GroupName(Unicode):
    def getter(self, rule, attr_name, name):
        name = Unicode.getter(self, rule, attr_name, name)
        if name is None:
            return None
        if MAX_GROUP_NAME_LENGTH < len(name):
            raise RulesetError(
                tr("The group name is too long (%s characters), the maximum is %s characters"),
                len(name), MAX_GROUP_NAME_LENGTH)
        for character in name:
            code = ord(character)
            if (32 <= code):
                continue
            raise RulesetError(
                tr("Invalid character in the group name: %s (code %s)"),
                repr(character), code)
        return name

class UserGroup(Object):
    XML_TAG = 'user_group'
    UPDATE_DOMAIN = 'user_groups'
    group = GroupNumber(optional=True)
    name = GroupName(optional=True)

    def __init__(self, user_groups, values, loader_context=None):
        self.ruleset = user_groups.ruleset
        Object.__init__(self, values, loader_context)

    def templatize(self, attr):
        attr['group'] = None
        attr['name'] = None

    def isGeneric(self, recursive=False):
        return (self.group is None) and (self.name is None)

    def __unicode__(self):
        if self.group is not None:
            return tr('The user group %s (%s)') % (self.formatID(), self.group)
        else:
            return tr('The generic user group %s') % self.formatID()

    def setPhysical(self, physical):
        if isinstance(physical, unicode):
            self.name = physical
        else:
            self.group = physical

    def setGeneric(self):
        self.group = None
        self.name = None

    def match(self, other):
        if not isinstance(other, UserGroup):
            return False
        return (self.group == other.group)

    def _removeTemplate(self, action, template_name):
        Object._removeTemplate(self, action, template_name)
        if self.isGeneric():
            self.ruleset.generic_links.removeTemplateAction(
                action, template_name, 'user_groups', self,
                tr('Unable to delete the template "%s": the generic user group %s is not defined'))

class UserGroups(Library):
    NAME = 'user_groups'
    ACL_ATTRIBUTE = 'user_groups'
    XML_TAG = "user_groups"
    CHILD_CLASSES = (UserGroup,)

    def getUserGroup(self, number):
        for user_group in self:
            if isinstance(user_group, Group):
                continue
            if user_group.group == number:
                return user_group
        return None

    def exportXMLRPC(self, fusion):
        user_groups = Library.exportXMLRPC(self, fusion)
        if not fusion:
            return user_groups
        user_groups = dict((group['id'], group)
            for group in user_groups)
        for identifier, group in user_groups.items():
            if 'physical_id' not in group:
                continue
            del user_groups[identifier]
        return user_groups.values()

