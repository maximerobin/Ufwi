
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

from ..common.multisite_component import MultiSiteComponent
from .firewall import UpdateFirewall

class MultiSiteUpdate(MultiSiteComponent):

    NAME = "multisite_update"
    VERSION = "1.0"
    API_VERSION = 1
    REQUIRES = ('multisite_master', )
    ACLS = {
            'CORE' : set(('getMultisiteType', )),
            'multisite_master' : set(('callRemote', 'getFirewallState', 'registerSubComponent',)),
            'multisite_transport' : set(('callRemote', 'hostFile', 'getFile', 'removeFile')),
            'update' : set(('sendUpgradeArchive', 'applyUpgrades', 'deleteArchive', )),
            'ufwi-conf' : set(('takeWriteRole', 'endUsingWriteRole',)),
            }

    FIREWALL_CLASS = UpdateFirewall
    CONFIG_PATH = 'multisite_update.xml'

    ROLES = {
        'multisite_read' : set((
                            "status",
                            "getTasks",
                            )),
        'multisite_write' : set((
                            "@multisite_read",
                            "applyUpdate",
                            "deleteTask",
                            "rescheduleTask",
                            ))
        }

    def init(self, core):
        MultiSiteComponent.init(self, core)

    def service_applyUpdate(self, ctx, sched_options, name, filename, encoded_bin):
        fw = self.getFirewall(name)
        d = self.checkRoleCall(ctx, name, 'nuconf_write', fw.applyUpdate, sched_options, filename, encoded_bin)
        return d
