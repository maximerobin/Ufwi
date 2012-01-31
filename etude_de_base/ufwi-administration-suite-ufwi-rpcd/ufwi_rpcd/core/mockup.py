
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

from ConfigParser import SafeConfigParser, NoSectionError

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.core.conf_files import RPCD_CONF_FILES, get_var_or_default

from .context import Context as OrigContext

class NullLogger:
    def debug(self, *args, **kw):
        pass

    def info(self, *args, **kw):
        pass

    def warning(self, *args, **kw):
        pass

    def error(self, *args, **kw):
        pass

    def critical(self, *args, **kw):
        pass

    def writeError(self, *args, **kw):
        pass

class Config(object):
    def get(self, section, key):
        raise NoSectionError(section)

class ConfigManager(object):

    def noop(self, *args, **kwargs):
        pass

    def __getattr__(self, item):
        return self.noop

    def get(*path):
        raise ConfigError("Nothing in mockup config")

class Core(object):
    def __init__(self):
        self.config = SafeConfigParser()
        self.config.read(RPCD_CONF_FILES)
        self.config_manager = ConfigManager()

    def conf_get_var_or_default(self, section, value, default=None, type=None):
        return get_var_or_default(self.config, section, value, default, type)

class Session(object):
    pass

class Component(object):
    name = "mockcomponent"
    session = Session()
    def getAcls(self):
        return frozenset()

_component = Component()

class Context(object):
    @staticmethod
    def make_user():
        return OrigContext(user="fake user")

    @staticmethod
    def make_component():
        return OrigContext(component=Component())

