
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

import os
from twisted.internet.defer import succeed
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.backend import Component
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_rpcd.backend import tr, AclError
from ufwi_rpcd.core.error import ACL_PERMISSION_DENIED
from ufwi_rpcd.backend.error import RpcdError

TRANSPORT_ID = 'multisite'

def make_lambda(func, *args):
    return lambda x: func(*args)

class MultiSiteComponent(Component):
    FIREWALL_CLASS = None

    def init(self, core):
        self.core = core
        self.firewalls = {}
        self.config = VariablesStore()
        self.config_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_PATH)
        try:
            self.config.load(self.config_path)
        except ConfigError, e:
            self.debug(str(e))
            pass

    def init_done(self):
        d = self.loadConfig()

        if self.NAME != "multisite_master": # arf..
            ctx = Context.fromComponent(self)
            d.addCallback(lambda x: self.core.callService(ctx, "multisite_master", "registerSubComponent", self.NAME))
        return d

    def loadConfig(self):
        """
        Load configuration of PKI, OpenVPN and firewalls.
        """

        d = succeed(None)
        d.addCallback(self.loadFirewalls)
        d.addErrback(self.loadError)
        return d

    def loadError(self, err):
        self.writeError(err)

    def loadFirewalls(self, *args):
        try:
            firewalls = self.config.get('firewalls')

            for name, attributes in firewalls.iteritems():
                try:
                    self.firewalls[name] = self.FIREWALL_CLASS(self, self.core, self.NAME, name, attributes)
                except TypeError:
                    self.error('Unable to read %s firewall settings: %s' % (name, attributes))
        except ConfigError, e:
            self.debug(str(e))
            pass

    def getFirewall(self, name):
        if name in self.firewalls:
            return self.firewalls[name]
        fw = self.FIREWALL_CLASS(self, self.core, self.NAME, name, {})
        self.firewalls[name] = fw
        return fw

    def checkRole(self, ctx, host, role):
        if 'multisite_admin' in ctx.user.roles:
            return succeed(True)

        d = self.core.callService(ctx, 'multisite_transport', 'getRoles', TRANSPORT_ID, host)
        d.addCallback(self.checkHostRoles, ctx, host, role)
        return d

    def checkRoleCall(self, ctx, host, role, func, *args, **kwargs):
        d = succeed("done")
        if 'multisite_admin' in ctx.user.roles:
            d.addCallback(lambda x:func(*args, **kwargs))
            return d

        d = self.checkRole(ctx, host, role)
        d.addCallback(self.checkRoleDoCall, func, *args, **kwargs)
        return d

    def checkHostRoles(self, roles, ctx, host, role):
        if role in roles:
            return True
        return False

    def checkRoleDoCall(self, role_validity, func, *args, **kwargs):
        if role_validity:
            return func(*args, **kwargs)
        raise AclError(ACL_PERMISSION_DENIED, tr('Call to %s is denied') % func)

    def getTask_addTask(self, role_ok, tasks, fw, task_list):
        if role_ok:
            task_list[fw] = {}
            for id, task in tasks.iteritems():
                task_list[fw][id] = task.getSchedule()
        return task_list

    def service_getTasks(self, ctx):
        task_list = {}
        d = succeed(task_list)
        role = self.FIREWALL_CLASS.TASK_CLS.getRWRole('read')

        for fw in self.firewalls.keys():
            tasks = self.firewalls[fw].getTasks()
            if tasks != {}:
                d.addCallback(make_lambda(self.checkRole, ctx, fw, role))
                d.addCallback(self.getTask_addTask, tasks, fw, task_list)
        return d

    def service_rescheduleTask(self, ctx, fw, id, sched_options):
        if id not in self.firewalls[fw].tasks:
            raise RpcdError(tr('No such task'))
        role = self.firewalls[fw].TASK_CLS.getRWRole('read')
        self.checkRoleCall(ctx, fw, role, self.firewalls[fw].tasks[id].reschedule, sched_options)

    def service_deleteTask(self, ctx, fw, id):
        if id not in self.firewalls[fw].tasks:
            raise RpcdError(tr('No such task on firewall %s') % fw)
        role = self.firewalls[fw].TASK_CLS.getRWRole('write')
        self.checkRoleCall(ctx, fw, role, self.firewalls[fw].cancelTask, id)

    def service_unregister_firewall(self, ctx, firewall):
        try:
            self.firewalls[firewall].unregister()
            self.firewalls.pop(firewall)
        except KeyError, e:
            pass

    def status_add(self, role_validity, state, states):
        if role_validity:
            states [ state ] += 1
        return states

    def service_status(self, ctx, fw):
        states = [ 0, 0, 0 ]

        if fw not in self.firewalls.keys():
            return states

        d = succeed(states)
        role = self.firewalls[fw].TASK_CLS.getRWRole('read')

        for task in self.firewalls[fw].tasks.itervalues():
            d.addCallback(make_lambda(self.checkRole, ctx, fw, role))
            d.addCallback(self.status_add, task.state, states)
        return d
