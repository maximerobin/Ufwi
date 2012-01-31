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

from twisted.internet.defer import inlineCallbacks, returnValue
from ConfigParser import NoOptionError, NoSectionError

from ufwi_rpcd.core.auth.simple_component import SimpleAuthComponent

class AuthComponent(SimpleAuthComponent):
    ROLES = {'nucentral_admin': set(('setSecondaryAuth', 'getSecondaryAuth'))}

    @inlineCallbacks
    def service_setSecondaryAuth(self, context, _type, params):
        auth = self.auth.setSecondaryAuth(_type, params)
        yield self.modified()
        returnValue(auth)

    def service_getSecondaryAuth(self, context):
        try:
            authname = self.auth.core.config.get('CORE','secondary_auth')
            authsection = dict(self.auth.core.config.items(authname))
            _type = authsection.pop('type')
            return _type, authsection
        except (NoOptionError, NoSectionError):
            return '', {}

    def modified(self):
        """
        emit signal only if there is something to export
        """
        if (self.auth.primary_auth.getStoragePaths() is not None or
            self.auth.secondary_auth.getStoragePaths() is not None):
            return self.core.notify.emit(self.NAME, 'configModified')

    def service_runtimeFiles(self, context):
        """
        list paths which need to be exported
        """
        files = []

        primary_data = None
        if self.auth.primary_auth is not None:
            primary_data = self.auth.primary_auth.getStoragePaths()

        secondary_data = None
        if self.auth.secondary_auth is not None:
            secondary_data = self.auth.secondary_auth.getStoragePaths()

        for data in primary_data, secondary_data:
            if data is not None:
                for path in data:
                    files.append((path, 'file'))
        return {
            'deleted': (),
            'added' : files,
            }

    def service_runtimeFilesModified(self, context):
        """
        reload configuration
        """
        self.auth.configurePrimaryAuth()
        self.auth.configureSecondaryAuth()

