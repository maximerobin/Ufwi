# -*- coding: utf-8 -*-

# $Id$

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
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcd.backend import Component
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core.lock import LockError

class AbstractNuConfComponent(Component):
    """
    base class for all ufwi_conf components
    """
    API_VERSION = 2

    ACLS = {
        'ufwi_conf': set(('takeWriteRole', 'endUsingWriteRole',)),
    }

    ROLES = {
        'conf_read': set(),
        'conf_write': set(('@conf_read',)),
    }

    def __init__(self):
        self.CONFIG_FILES = {}
        self.core = None
        self.TEMPLATE_PATH = None
        Component.__init__(self)

    def init(self, core):
        Component.init(self, core)
        self.core = core
        self.createSubscriptions()
        self.read_config(None)

    def checkServiceCall(self, context, service_name):
        """
        if called by a user and service modify configuration then
        check user have acquired 'ufwi_conf_write' lock. See session.acquire(...).
        Lock is acquired with ufwi_conf.takeWriteRole().
        """
        component_ctx = Context.fromComponent(self)
        if 'ufwi_conf' not in self.core.getComponentList(component_ctx):
            # Lock must be acquired by calling ufwi_conf.takeWriteRole(). If ufwi_conf
            # component is missing user will not be able to acquire the lock,
            # therefore lock checking is disabled if ufwi_conf component is not
            # loaded
            self.warning("Could not find ufwi_conf component: "
                "sessions are able to modify configuration concurrently")
            return

        if (service_name in self.roles['ufwi_conf_read']) \
        or (service_name not in self.roles['ufwi_conf_write']):
            # Only check the lock for editing services
            return

        # Check if the user has the lock
        if not self.core.lock_manager.contextHasLock(context, 'ufwi_conf_write'):
            service = "%s.%s()" % (self.name, service_name)
            raise LockError(
                tr("You need ufwi_conf lock to call the %s service: call ufwi_conf.takeWriteRole()"),
                service)

    @classmethod
    def getConfigDepends(cls):
        """return names of required modules for cls
        Current module will be reconfigured when any of module in CONFIG_DEPENDS
        is (re)configured. (Re)configuration is done by calling the apply
        callback.
        """
        return cls.getTag('CONFIG_DEPENDS', AbstractNuConfComponent)

    def createSubscriptions(self):
        """
        This default implementation requires a class attribute CONFIG_DEPENDS.
        """
        if not hasattr(self.__class__, 'CONFIG_DEPENDS'):
            raise NotImplementedError(
                "This component class needs "
                "a 'CONFIG_DEPENDS' attribute (iterable of components names)."
                "See %s/%s" % (self.__module__, self.__class__.__name__)
                )

        if hasattr(self, 'rollback_config'):
            rollback = self.rollback_config
        else:
            rollback = self.apply_config

        self.core.config_manager.registerConfigComponent(self, self.read_config,
            self.apply_config, rollback)

    @abstractmethod
    def read_config(self, responsible, *args, **kwargs):
        pass

    @abstractmethod
    def apply_config(self, responsible, *unused):
        pass

    @abstractmethod
    def apply_success(self, *unused):
        pass

    def addConfFile(self, template_path, owner, mode, dest=None):
        """
        templates are located in: /usr/share/ufwi_rpcd/templates
        You must specify dest path if it is different from template path.
        """
        if dest is None:
            dest = template_path
        self.CONFIG_FILES[dest] = (owner, mode, template_path)

    #FIXME: rename to generate_templates and fix children classes
    #FIXME: instead of calling self.generateTemplates, call parent class'
    def generate_configfile(self, template_variables, confFiles=None, prefix=''):
        """
        default all config files are generated
        """
        if confFiles is None:
            templates = self.CONFIG_FILES
        else:
            templates = {}
            for template in confFiles:
                templates[template] = self.CONFIG_FILES[template]
        self.generateTemplates(template_variables, templates, prefix)

