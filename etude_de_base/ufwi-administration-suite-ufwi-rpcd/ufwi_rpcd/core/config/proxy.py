
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

from ufwi_rpcd.backend.exceptions import ConfigError

class Proxy(object):
    def __init__(self, target, responsible, death_triggers, hidden_methods, callback):
        """
        if not None,
        arg 'responsible' is passed to death_triggers as a keyword argument under the same name
        """
        self.target = target
        self.responsible = responsible
        self.death_triggers = death_triggers
        self.hidden_methods = hidden_methods
        self.callback = callback
        self.reset_called = False

    def __enter__(self):
        return self

    def __exit__(self, *args):
        if self.target is not None:
            self.rollback()

    def __getattr__(self, attr):
        if self.reset_called:
            raise ConfigError("Your modifications and your lock are lost as reset was called")
        if attr in self.hidden_methods:
            raise AttributeError(attr)
        result = getattr(self.target, attr)
        if attr not in self.death_triggers:
            return result

        def new_method(*args, **kwargs):
            if 'responsible' not in kwargs:
                kwargs['responsible'] = self.responsible
            return result(*args, **kwargs)

        self.target = None
        self.callback(trigger=attr)
        return new_method

