
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

from ufwi_rpcd.core.context import Context
from ..common.firewall import MultiSiteFirewall
from task import UpdateTask

class UpdateFirewall(MultiSiteFirewall):
    ATTR = []
    RETRY_TIME = 1 # in seconds
    TASK_CLS = UpdateTask

    def __init__(self, component, core, module_name, name, attr):
        MultiSiteFirewall.__init__(self, component, core, module_name, name, attr)

    def applyUpdate(self, sched_options, filename, encoded_bin):
        ctx = Context.fromComponent(self.component)
        task = UpdateTask(self.core, ctx, self, sched_options, filename, encoded_bin)
        self.setTask(task)
