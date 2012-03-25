#coding: utf-8
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

from __future__ import with_statement


from ufwi_rpcd.backend import tr
from ufwi_rpcd.core.conf_files import RPCD_CUSTOM_CONF
from ufwi_rpcd.core.auth.simple_auth import SimpleAuth, getParameter

from .auth_file import AuthFile
from .auth_ldap import AuthLDAP
from .auth_radius import AuthRadius

def getGroup(text):
    return getParameter('group', text, tr("%s is not a valid group name."))

class Auth(SimpleAuth):

    _auth_dict = {
        'file':      AuthFile,
        'ldap':      AuthLDAP,
        'radius':    AuthRadius,
    }

    def __init__(self, core):
        SimpleAuth.__init__(self, core)
        self.secondary_auth = None
        self.configureSecondaryAuth()

    def configureSecondaryAuth(self):
        self.secondary_auth = self.build_auth('secondary_auth', display_error = False)

    def setSecondaryAuth(self, _type, params):
        # FIXME: use writeConfig() from ufwi_rpcd.core.tools
        config = self.core.config

        if not _type:
            self.secondary_auth = None
            config.remove_option('CORE', 'secondary_auth')
        else:
            obj = self.getAuthHandler(_type)

            # Do not catch exceptions to let caller catch them.
            self.secondary_auth = obj(**params)

            sec_name = 'secondary_auth_%s' % _type
            config.set('CORE', 'secondary_auth', sec_name)

            if config.has_section(sec_name):
                config.remove_section(sec_name)

            config.add_section(sec_name)

            config.set(sec_name, 'type', _type)
            for key, value in params.iteritems():
                config.set(sec_name, key, value)

        with open(RPCD_CUSTOM_CONF, 'w') as fp:
            config.write(fp)

    def getAuthParameters(self, _type):
        cls = self.getAuthHandler(_type)
        return cls.PARAMETERS

    def authenticate(self, context, username, password):
        """
        Login with specified username and password.

        @param username  (str)
        @param password  (str)
        @return  (is_logged (bool), groups (list))
        """

        # first, try the primary auth system. If authentication fails,
        # try the secondary auth system, if any.
        logged, groups = SimpleAuth.authenticate(self, context, username, password)
        if logged:
            return logged, groups

        if self.secondary_auth and self.secondary_auth.authenticate(username, password):
            groups = self.secondary_auth.getGroups(username)
            if not groups:
                groups = self.primary_auth.getGroups(username)
            return True, groups

        self.try_emit(context, username)
        return False, []

    def try_emit(self, context, username):
        # TODO
        pass

#        try:
#            event = AuditEvent.fromAuthFailure(context,
#                    u"EAS: Authentication failure for user %s" % username, user=username)
#            self.core.audit.emit(event)
#        except Exception, err:
#            writeError(err)

