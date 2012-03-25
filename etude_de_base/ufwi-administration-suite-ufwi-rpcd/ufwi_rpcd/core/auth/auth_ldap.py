# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

from ufwi_rpcd.backend import tr, AuthError
from ufwi_rpcd.core.error import AUTH_LDAP_ERROR
from .auth_basemethods import AbstractAuth

try:
    import ldap
    HAVE_LDAP = True
except ImportError:
    HAVE_LDAP = False

class AuthLDAP(AbstractAuth):
    """ Basic authentication, using an LDAP directory
    """

    PARAMETERS = ['uri', 'basedn', 'login', 'group_attribute', 'binddn', 'bindpw', 'additional_filter']

    def __init__(self,*args,**kwargs):
        AbstractAuth.__init__(self)

        if not HAVE_LDAP:
            raise AuthError(AUTH_LDAP_ERROR, tr("LDAP support isn't activated"))

        # required options
        try:
            self.uri = kwargs['uri']
            self.basedn = kwargs['basedn']
            self.login = kwargs['login']
            self.group_attribute = kwargs['group_attribute']
        except KeyError, err:
            raise AuthError(AUTH_LDAP_ERROR,
                tr("Missing parameters to build LDAP object: %s"),
                err)
        # these are optional
        self.binddn = ""
        self.bindpw = ""
        self.additional_filter = None
        self.binddn = kwargs.get('binddn',"")
        self.bindpw = kwargs.get('bindpw',"")
        self.additional_filter = kwargs.get('additional_filter',"")

    def addUser(self, username, method, password, groups):
        try:
            l = ldap.initialize(self.uri)
            l.simple_bind_s(self.binddn, self.bindpw)

            filter = "(%s=%s)" % (self.login, username)
            if self.additional_filter:
                filter = "(&(%s)%s)" % (self.additional_filter,filter)

            results = l.search_s(self.basedn, ldap.SCOPE_SUBTREE, filter)
            if len(results) > 0:
                return False

        except ldap.LDAPError, e:
            self.error("ldap bind failed: %s" % e)

        # adds user in the dict
        return AbstractAuth.addUser(self, username, method, password, groups)

    def authenticate(self, username, challenge):
        if AbstractAuth.authenticate(self, username, challenge):
            return True

        try:
            l = ldap.initialize(self.uri)
            l.simple_bind_s(self.binddn, self.bindpw)

            filter = "(%s=%s)" % (self.login,username)  # warning: no space between name and =
            if self.additional_filter:
                filter = "(&(%s)%s)" % (self.additional_filter,filter)

            results = l.search_s(self.basedn, ldap.SCOPE_SUBTREE, filter)
            if len(results) == 0:
                return False
            if len(results) > 1:
                self.warning("ldap search (filter: %s) returned more than 1 result" % filter)
                return False
            (dn,attributes) = results[0]

            l.simple_bind_s(dn, challenge)
        except ldap.LDAPError,e:
            self.error("ldap bind failed: %s" % e)
            return False

        # user was succesfully authenticated
        l.unbind_s()
        return True

    def getGroups(self, username):
        groups = AbstractAuth.getGroups(self, username)
        if groups:
            return groups

        try:
            l = ldap.initialize(self.uri)
            l.simple_bind_s(self.binddn, self.bindpw)

            filter = "(%s=%s)" % (self.group_attribute,username)  # warning: no space between name and =
            #if self.additional_filter:
            #    filter = "(&(%s)%s)" % (self.additional_filter,filter)

            ldap_results = l.search_s(self.basedn, ldap.SCOPE_SUBTREE, filter)
            if len(ldap_results) == 0:
                return []
            result = []
            for (dn,attributes) in ldap_results:
                result.append( attributes['displayName'][0] )

            #l.simple_bind_s(dn, challenge)
        except ldap.LDAPError,e:
            self.error("ldap bind failed: %s" % e)
            return []

        # user was succesfully authenticated
        l.unbind_s()
        return result

    def getAllGroups(self):
        return []

    def getStoragePaths(self):
        """
        storage is external
        """
        pass
