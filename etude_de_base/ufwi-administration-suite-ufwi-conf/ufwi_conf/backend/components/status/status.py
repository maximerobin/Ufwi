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


from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context

from ufwi_conf.backend.unix_service import UnixServiceComponent
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent

class StatusComponent(AbstractNuConfComponent):
    """
    This component queries other components for their status.
    They should implement a service_status(context) method and return
    the appropriate result among ServiceStatusValues
    """

    NAME = "status"
    VERSION = "1.0"

    ACLS = {
        '*': set(('status', 'getPorts')),
    }
    ROLES = {
        'conf_read': set(("getStatus",)),
        'multisite_read' : set(("getStatus",)),
    }
    CONFIG_DEPENDS = ()

    def apply_config(self, *unused):
        pass

    def read_config(self, *args, **kwargs):
        pass

    def service_getStatus(self, context):
        """
        return 2 lists of components which are - remote services - local services

        [ 'ntp', 'dhcp' ], ['antispam']
        """
        defer = None
        filtered_components = [] # allowed services which can be filtered
        local_components = []    # local services
        # use status component context to be allowed to call
        # the getStatus() service of all components
        context = Context.fromComponent(self)
        for component_name in self.core.getComponentList(context):
            component = self.core.getComponent(context, component_name)
            if issubclass(component.__class__, UnixServiceComponent):
                if defer is None:
                    #first iteration, we create the deferred and add the first callback
                    defer = self.core.callService(context, component_name, 'getPorts')
                    defer.addCallback(self.addComponent, component_name, filtered_components, local_components, context)
                else:
                    #next iterations, we append the callService and the handler to the deffered
                    defer.addCallback(lambda unused: self.core.callService(context, component_name, 'getPorts'))
                    defer.addCallback(self.addComponent, component_name, filtered_components, local_components, context)

        if defer is None:
            return [], []

        defer.addCallback(self.getAllStates)
        defer.addErrback(self.handleError)
        return defer

    def handleError(self, error):
        self.writeError(error)
        return error

    def addComponent(self, ports, component_name, filtered_components, local_components, context):
        if len(ports):
            filtered_components.append(component_name)
        else:
            local_components.append(component_name)

        # pass lists of components to getAllStates
        return context, filtered_components, local_components

    def getAllStates(self, (context, filtered_components, local_components)):
        INDEX_FILTERED = 0
        INDEX_LOCAL = 1
        states = []
        states.insert(INDEX_FILTERED, {})
        states.insert(INDEX_LOCAL, {})
        defer = None

        for components, state_index in ((filtered_components, INDEX_FILTERED),
            (local_components, INDEX_LOCAL)):
            for component_name in components:
                if defer is None:
                    #first iteration, we create the deferred and add the first callback
                    defer = self.core.callService(context, component_name, 'status')
                    defer.addCallbacks(self.getState, errback=self.ignoreAll, callbackArgs=(states, state_index))
                else:
                    #next iterations, we append the callService and the handler to the deffered
                    defer.addCallback(lambda unused: self.core.callService(context, component_name, 'status'))
                    defer.addCallbacks(self.getState, errback=self.ignoreAll, callbackArgs=(states, state_index))
        return defer

    def getState(self, (component_name, state), states, index):
        if state not in (ServiceStatusValues.NOT_A_SERVICE, ServiceStatusValues.STATUS_NOT_IMPLEMENTED):
            states[index][component_name] = state

        return states

    def ignoreAll(self, *args):
        self.writeError(args[0])
        return

