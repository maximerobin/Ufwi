
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

from ufwi_rpcd.common.abstract_cfg import AbstractConf

class UpdateCfg(AbstractConf):
    ATTRS = """
            auto_check
            update_mirror
            use_custom_mirror
           """.split()

    DATASTRUCTURE_VERSION = 1

    def __init__(self, auto_check=False, update_mirror='',
                 use_custom_mirror=False):
        AbstractConf.__init__(self)
        self._setLocals(locals())

    def isValid(self, raise_error=False):
        return True

    def setAutoCheck(self, state):
        self.auto_check = bool(state)

    def setUpdateServer(self, update_server):
        self.update_server = unicode(update_server)

