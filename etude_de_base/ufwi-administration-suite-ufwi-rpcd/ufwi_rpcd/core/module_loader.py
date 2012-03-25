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

import os
from os.path import join as path_join, basename
import sys
from ConfigParser import NoSectionError
from inspect import isclass
from logging import CRITICAL
from twisted.internet.defer import succeed

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend import tr, RpcdError, Component

class ModuleLoaderError(RpcdError):
    pass

class ModuleLoader(Logger):
    def __init__(self, core):
        Logger.__init__(self, "module_loader", parent=core)
        self.core = core

    def run(self):
        """ Parse configuration to register modules.

        modules must present in a directory (or using a symbolic link). This directory
        is configured in the module section, and is relative to [CORE]/vardir, unless
        an absolute path is given.

        [modules]
        dir = mods-enabled
        """
        try:
            modules_dir = self.core.config.get('modules','dir')
        except NoSectionError:
            raise ModuleLoaderError(tr("Unable to read '[modules]' section in the configuration"))

        if not modules_dir.startswith('/'):
            modules_dir = os.path.join(self.core.config.get('CORE','vardir'), modules_dir)

        if not os.path.exists(modules_dir):
            self.warning("Modules directory '%s' does not exist - no modules will be loaded" % modules_dir)
            return succeed(None)

        components = []
        old_path = list(sys.path)
        try:
            sys.path.insert(0, modules_dir)

            contents = os.listdir(modules_dir)
            for name in contents:
                self.debug('Load module %s' % name)
                components_found = self.searchComponents(modules_dir, name)
                components.extend(components_found)
        finally:
            sys.path = old_path
        if not components:
            return succeed(None)
        return self.deferredLoad(components)

    def checkRequires(self, component):
        for name in component.getRequires():
            if not self.core._hasComponent(name) \
            and (name not in self.core.broken_components):
                return False
        return True

    def showMissingRequires(self, component_class):
        missing = []
        for name in component_class.getRequires():
            if name in self.core.broken_components:
                missing.append(name)
        if len(missing):
            self.warning('Loading components %s with broken requirements : %s' %
                (component_class.__name__, ', '.join(missing)))

    def searchComponents(self, modules_dir, name):
        """return list of components inside a module"""
        components = []
        module_path = name
        try:
            module = __import__(module_path)
            for attrname in dir(module):
                attr = getattr(module, attrname)
                if not isclass(attr) \
                or not issubclass(attr, Component) \
                or attr == Component:
                    continue
                components.append(attr)
        except Exception, err:
            self.writeError(err, "Error on loading module %s" % name,
                log_level=CRITICAL)
            self.core.broken_components.append(name)
            return components
        if not components:
            self.error("The module %s doesn't contain any component!" % module_path)
        return components

    def loadError(self, failure, component_class):
        self.writeError(failure, "Error on loading the component %s" %
            component_class.__name__)
        # continue to load next modules

    def deferredLoad(self, components):
        """ load each component in components"""

        wk_copy = components[:]
        for cls in wk_copy:
            if not self.checkRequires(cls):
                continue
            self.showMissingRequires(cls)
            wk_copy.remove(cls)
            try:
                defer = self.core.loadComponent(cls)
                defer.addErrback(self.loadError, cls)
            except Exception, err:
                self.loadError(err, cls)
                defer = succeed(None)
            defer.addCallback(lambda x: wk_copy)
            if wk_copy:
                defer.addCallback(self.deferredLoad)
            return defer

        components = wk_copy

        # There are still some modules with missing requirements
        for component in components:
            requires = (require
                for require in component.getRequires()
                if not self.core._hasComponent(require))
            requires = ', '.join(requires)
            self.error('Cannot load component "%s": missing requires (%s)'
                % (component.NAME, requires))
        return succeed(components)

