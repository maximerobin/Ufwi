
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
from .firewall import NuFaceFirewall

class MultiSiteNuFace(MultiSiteComponent):

    NAME = "multisite_nuface"
    VERSION = "1.0"
    API_VERSION = 1
    REQUIRES = ('multisite_master', 'network', 'config')
    ACLS = {
            'CORE' : set(('getMultisiteType', )),
            'multisite_master' : set(('callRemote', 'getFirewallState', 'registerSubComponent', )),
            'multisite_transport' : set(('callRemote', 'hostFile', 'getFile', 'removeFile')),
            'ufwi_ruleset' : set(('applyMultisite', 'downloadTemplate', 'offlineSetGenericLinks', 'getMissingLinks')),
            'network' : set(('getNetconfig',)),
            }

    FIREWALL_CLASS = NuFaceFirewall
    CONFIG_PATH = 'multisite_nuface.xml'

    ROLES = {
        'multisite_read' : set((
                            "status",
                            "getGenericLinks",
                            "getCurrentConfig",
                            "getTasks",
                            )),
        'multisite_write' : set((
                            "setGenericLinks",
                            "applyRules",
                            "deleteTask",
                            "rescheduleTask",
                            ))
        }

    def getFirewallConfig(self, fw):
        return fw.last_sent, fw.status, fw.template, fw.template_version

    def service_getGenericLinks(self, ctx, name):
        return self.checkRoleCall(ctx, name, 'ruleset_read', lambda: self.getFirewall(name).getGenericLinks())

    def service_setGenericLinks(self, ctx, name, links):
        self.checkRoleCall(ctx, name, 'ruleset_write', lambda: self.getFirewall(name).setGenericLinks(links))

    def service_getCurrentConfig(self, ctx, name):
        d = self.checkRoleCall(ctx, name, 'ruleset_read', lambda: self.getFirewall(name))
        d.addCallback(self.getFirewallConfig)
        return d

    def service_applyRules(self, ctx, sched_options, name, template, template_version, ruleset, association):
        fw = self.getFirewall(name)
        return self.checkRoleCall(ctx, name, 'ruleset_write', fw.applyRules, sched_options, template, template_version, ruleset, association)

