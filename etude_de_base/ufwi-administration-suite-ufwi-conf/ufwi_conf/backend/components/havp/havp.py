"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>

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

from ufwi_conf.backend.unix_service import ConfigServiceComponent

class HavpComponent(ConfigServiceComponent):
    NAME = "havp"
    VERSION = "1.0"

    REQUIRES = ('config', )
    CONFIG_DEPENDS = ()

    INIT_SCRIPT = "havp"

    PIDFILE="/var/run/havp/havp.pid"
    EXE_NAME="havp"

    def service_start(self, context):
        self.core.callServiceSync(context, "Clamav", "incrementUsageCount")
        return ConfigServiceComponent.service_start(self, context)

    def service_stop(self, context):
        self.core.callServiceSync(context, "Clamav", "decrementUsageCount")
        return ConfigServiceComponent.service_stop(self, context)

    def apply_config(self, *unused):
        pass

