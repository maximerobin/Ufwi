# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies

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

from __future__ import with_statement

from ufwi_rpcd.backend import tr, AuthError
from ufwi_rpcd.core.error import AUTH_CONFIG_ERROR

from .auth_basemethods import AbstractAuth

class AuthFile(AbstractAuth):
    """ Basic authentication, using a file containing login:passwords couples
    """

    PARAMETERS = ['authfile', 'groupfile']

    def __init__(self,*args,**kwargs):
        AbstractAuth.__init__(self)
        try:
            self.authfile = kwargs['authfile']
            self.groupfile = kwargs['groupfile']
        except KeyError, err:
            raise AuthError(AUTH_CONFIG_ERROR,
                tr("%s key is missing in configuration"), err)

        self.ReadAuthFile(self.authfile)
        self.ReadGroupFile(self.groupfile)

    def _rewriteFiles(self):
        try:
            with open(self.authfile, "w") as f:
                for username, password in self.users.iteritems():
                    f.write("%s:%s\n" % (username, self.users[username]))
        except IOError, err:
            self.writeError(err, "Unable to write in user file")
            return False

        try:
            with open(self.groupfile, "w") as f:
                for group, users in self.groups.iteritems():
                    f.write('%s:%s\n' % (group, ','.join(users)))
        except IOError, err:
            self.writeError(err, "Unable to write in group file: %s" % err)
            return False

        return True

    def addUser(self, username, method, password, groups):
        if not AbstractAuth.addUser(self, username, method, password, groups):
            return False
        return self._rewriteFiles()

    def delUser(self, username):
        if not AbstractAuth.delUser(self, username):
            return False
        return self._rewriteFiles()

    def editUser(self, username, method, password, groups):
        if not AbstractAuth.editUser(self, username, method, password, groups):
            return False
        return self._rewriteFiles()

    def addGroup(self, name):
        return AbstractAuth.addGroup(self, name) and self._rewriteFiles()

    def delGroup(self, name):
        return AbstractAuth.delGroup(self, name) and self._rewriteFiles()

    def ReadAuthFile(self,filename):
        try:
            _f = open(filename,"r")
            for line in _f.readlines():
                line = line.strip()
                if not line:
                    continue
                (login,passwd) = line.split(':', 1)
                login = login.strip()
                passwd = passwd.strip()
                self.users[login] = passwd
            _f.close()
        except Exception, err:
            self.writeError(err, "Could not parse authentication file %s" % filename)
            return False

    def ReadGroupFile(self,filename):
        try:
            _f = open(filename,"r")
            for line in _f.readlines():
                line = line.strip()
                if not line:
                    continue
                group, users = line.split(':', 1)
                group = group.strip()
                users = users.strip().split(',')
                self.groups[group] = users
            _f.close()
        except Exception, err:
            self.writeError(err, "Could not parse group file %s" % filename)
            return False

    def getStoragePaths(self):
        """
        return a tuple of path
        """
        return self.authfile, self.groupfile
