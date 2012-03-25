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

from twisted.internet.defer import inlineCallbacks, returnValue

from ufwi_rpcd.backend import Component, tr
from ufwi_rpcd.common.getter import getList

from ufwi_rpcd.core.auth.simple_auth import getPassword, getParameter, getUsername

def getGroup(text):
    return getParameter('group', text, tr("%s is not a valid group name."))

class SimpleAuthComponent(Component):
    NAME = "auth"
    VERSION = "1.0"
    API_VERSION = 2
    ROLES = {'nucentral_admin': set(('addUser', 'delUser',
                                     'editUser', 'getUser',
                                     'listGroups', 'listUsers',
                                     'addGroup', 'delGroup',
                                     'getAuthTypes', 'getAuthParameters',))
    }

    def __init__(self):
        self.auth = None
        self.core = None
        Component.__init__(self)

    def init(self, core):
        self.auth = core.auth
        self.core = core

    @inlineCallbacks
    def service_addUser(self, context, username, method, password, groups):
        username = getUsername(username)
        password = getPassword(password)
        groups = getList(getGroup, groups)
        #method is checked in auth_basemethods.AbstractAuth.hash_password
        if self.auth.addUser(username, method, password, groups):
            self.info(context, "User %s added" % username)
            yield self.modified()
            returnValue(True)
        returnValue(False)

    @inlineCallbacks
    def service_delUser(self, context, username):
        username = getUsername(username)
        if self.auth.delUser(username):
            self.info(context, "User %s deleted" % username)
            yield self.modified()
            returnValue(True)
        returnValue(False)

    @inlineCallbacks
    def service_editUser(self, context, username, method, password, groups):
        """
        Edit a user account.
        password is optional
        """
        username = getUsername(username)
        password = getPassword(password, False)
        groups = getList(getGroup, groups)
        #method is checked in auth_basemethods.AbstractAuth.hash_password
        if self.auth.editUser(username, method, password, groups):
            self.info(context, "User %s modified" % username)
            yield self.modified()
            returnValue(True)
        returnValue(False)

    @inlineCallbacks
    def service_addGroup(self, context, name):
        name = getGroup(name)
        if self.auth.addGroup(name):
            self.info(context, "Group %s added" % name)
            yield self.modified()
            returnValue(True)
        returnValue(False)

    @inlineCallbacks
    def service_delGroup(self, context, name):
        name = getGroup(name)
        if self.auth.delGroup(name):
            self.info(context, "Group %s deleted" % name)
            yield self.modified()
            returnValue(True)
        returnValue(False)

    def service_listGroups(self, context):
        return list(self.auth.getAllGroups())

    def service_listUsers(self, context):
        return self.auth.getUsers()

    def service_getUser(self, context, username):
        username = getUsername(username)
        return self.auth.getUser(username)

    def service_getAuthTypes(self, context):
        return self.auth.getAuthMethods()

    def service_getAuthParameters(self, context, _type):
        return self.auth.getAuthParameters(_type)

    def formatServiceArguments(self, service, arguments):
        arguments = list(arguments)
        if service in ('addUser', 'editUser'):
            # Don't log plain text passwords
            arguments[2] = '***'
        return Component.formatServiceArguments(self, service, arguments)

    def modified(self):
        """
        emit signal only if there is something to export
        """
        if self.auth.primary_auth.getStoragePaths() is not None:
            return self.core.notify.emit(self.NAME, 'configModified')

