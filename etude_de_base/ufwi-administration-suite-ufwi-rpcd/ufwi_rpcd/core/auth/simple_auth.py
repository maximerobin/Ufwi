
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

from ConfigParser import NoOptionError, NoSectionError
from logging import error
import re

from ufwi_rpcd.backend import tr, AuthError
from ufwi_rpcd.core.getter import getUnicode
from ufwi_rpcd.core.error import AUTH_CONFIG_ERROR, AUTH_INVALID_PARAMETER

from .auth_file import AuthFile

PASSWORD_REGEX = NAME_REGEX = re.compile(u'^[\x20-\uffff]+$')

def getPassword(password, mandatory=True):
    if (not mandatory) \
    and (not password):
        return None
    password = getUnicode("password", password, 1, 100)
    if not PASSWORD_REGEX.match(password):
        raise AuthError(
            AUTH_INVALID_PARAMETER,
            tr("The password you entered is not valid.")
            )
    return password

def getParameter(name, value, error_message):
    name = getUnicode(name, value, 1, 100)
    if not NAME_REGEX.match(value):
        raise AuthError(
            AUTH_INVALID_PARAMETER,
            error_message,
            repr(name)
            )
    return name

def getUsername(text):
    return getParameter('username', text, tr("%s is not a valid user name."))

class SimpleAuth(object):

    _auth_dict = { 'file': AuthFile, }

    def getAuthMethods(self):
        return self._auth_dict.keys()

    def getAuthHandler(self, auth_type):
        try:
            return self._auth_dict[auth_type]
        except KeyError:
            raise AuthError(AUTH_CONFIG_ERROR, tr("%s is not a valid type"), auth_type)

    def __init__(self, core):
        self.core = core
        self.primary_auth = None
        self.configurePrimaryAuth()

    def configurePrimaryAuth(self):
        # primary auth is named 'auth' in configuration to keep backward
        # compatibility.
        self.primary_auth = self.build_auth('auth', display_error = True)

    def build_auth(self, name, display_error):
        try:
            authname = self.core.config.get('CORE', name)
            authsection = dict(self.core.config.items(authname))

            try:
                _type = authsection.pop('type')
            except KeyError, err:
                self.core.writeError(err, "Section %s doesn't contain any 'type' attribute")
                return None

            try:
                obj = self.getAuthHandler(_type)
            except AuthError, err:
                self.core.writeError(err, "Could not build authentication object of type %r" % _type)
                return None

            try:
                return obj(**authsection)
            except (AuthError, RuntimeError), err:
                self.core.writeError(err, "Could not build authentication object")
                return None

        except (NoOptionError, NoSectionError), err:
            if display_error:
                error("No authentication configured: %s" % err)
            return None

    def login(self, context, username, password):
        """
        Login with specified username and password.

        @param username  (str)
        @param password  (str)
        @return  (is_logged (bool), groups (list))
        """
        if not self.primary_auth:
            # primary is mandatory
            return False, []

        username = getUsername(username)
        if not password:
            raise TypeError(tr("password cannot be empty"))
        password = getPassword(password)

        return self.authenticate(context, username, password)

    def authenticate(self, context, username, password):

        # first, try the primary auth system. If authentication fails,
        # try the secondary auth system, if any.
        if self.primary_auth.authenticate(username, password):
            return True, self.primary_auth.getGroups(username)
        else:
            return False, []

    def addUser(self, username, method, password, groups):
        return self.primary_auth.addUser(username, method, password, groups)

    def delUser(self, username):
        return self.primary_auth.delUser(username)

    def editUser(self, username, method, password, groups):
        return self.primary_auth.editUser(username, method, password, groups)

    def addGroup(self, name):
        return self.primary_auth.addGroup(name)

    def delGroup(self, name):
        return self.primary_auth.delGroup(name)

    def getAllGroups(self):
        return self.primary_auth.getAllGroups()

    def getUsers(self):
        return self.primary_auth.getUsers()

    def getUser(self, username):
        return self.primary_auth.getUser(username)

