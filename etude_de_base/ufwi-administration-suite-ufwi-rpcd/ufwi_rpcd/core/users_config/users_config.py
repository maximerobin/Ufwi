
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

from os.path import join as pathjoin, exists

from ufwi_rpcd.common import tr
from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_rpcd.backend.error import ComponentError

class UserConfigError(ComponentError):
    pass

class UsersConfigManager(Component):
    NAME = 'users_config'
    API_VERSION = 2
    VERSION = '1.0'

    def __init__(self):
        Component.__init__(self)
        self.config_managers = {}

    def init(self, core):
        self.user_conf_dir = pathjoin(core.var_dir, 'user_configurations')

    def _getXMLName(self, user_name):
        return '%s.xml' % pathjoin(self.user_conf_dir, user_name)

    def _getConfigManager(self, user_name):
        if user_name not in self.config_managers:
            cm = VariablesStore()
            filename = self._getXMLName(user_name)
            if exists(filename):
                cm.load(filename)
            self.config_managers[user_name] = cm
        return self.config_managers[user_name]

    def service_get(self, context, *path, **kw):
        user_name = context.user.login
        return self._getConfigManager(user_name).get(*path, **kw)

    def service_set(self, context, *path):
        user_name = context.user.login
        return self._getConfigManager(user_name).set(*path)

    def service_delete(self, context, *path):
        """
        Delete specified path.
        Raise an error if the path doesn't exist.
        """
        user_name = context.user.login
        self._getConfigManager(user_name).delete(*path)

    def service_save(self, context):
        """
        Write changes into the XML file.
        """
        user_name = context.user.login
        cm = self._getConfigManager(user_name)
        filename = self._getXMLName(user_name)
        cm.save(filename)

    def service_close(self, context):
        """
        Close the configuration without saving the changes.
        """
        user_name = context.user.login
        try:
            del self.config_managers[user_name ]
            return True
        except KeyError:
            return False

    def checkServiceCall(self, context, service_name):
        if (not context.user) or (not context.user.login):
            raise UserConfigError(
                tr("Only an authenticated user can use the users_config component."))

