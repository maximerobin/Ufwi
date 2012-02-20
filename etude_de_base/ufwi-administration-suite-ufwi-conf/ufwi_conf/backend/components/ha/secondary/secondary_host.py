#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
"""

from __future__ import with_statement

from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.error import reraise
from ufwi_rpcd.core.context import Context
from ufwi_conf.common.ha_cfg import NOT_REGISTERED, NOT_CONNECTED, CONNECTED
from .primary import Primary

TRANSPORT_ID = 'ha_secondary'

class SecondaryHost(LoggerChild):
    def __init__(self, component, core, config):
        LoggerChild.__init__(self, component)
        self.core = core
        self.component = component
        self.config = config
        self.primary = None

    def loadConfig(self):
        self.primary = Primary(self)
        return self.primary.loadConfig(self.config.interface_name)

    @inlineCallbacks
    def stop(self):
        self.debug('Stopping secondary instance')
        if not self.primary is None:
            yield self.primary.unregister()
            self.primary = None

    def service_callRemote(self, ctx, component, service, *args):
        """
        Call a remote service on primary.
        @param component  component called on primary (str)
        @param service  service called (str)
        @param args  service's arguments (dict)
        @return  service result
        """
        if not self.primary or self.primary.state != self.primary.ONLINE:
            raise RpcdError("HA isn't enabled. calling %s.%s() : %s" %
                unicode(component, service, self.primary.state))

        ctx_component = Context.fromComponent(self.component)
        return self.core.callService(ctx_component, 'multisite_transport',
            'callRemote', TRANSPORT_ID, 'primary', component, service, *args)

    @inlineCallbacks
    def register(self, configuration):
        self.info('Received connection from primary')
        if self.primary:
            # FIXME this message is always displayed !
            self.warning("Overriding previous primary configuration")

        self.primary = Primary(self)
        try:
            yield self.primary.loadConfig(self.config.interface_name)
            # Save config before registration (to empty config...)
            yield self.primary.saveConfig()
            yield self.primary.register(configuration)
        except Exception, err:
            self.primary = None
            reraise(err)

    @inlineCallbacks
    def unregister(self):
        self.info('Unregistering secondary')
        if self.primary:
            ret = yield self.primary.unregister()
            self.primary = None
            if ret is not None:
                ctx = Context.fromComponent(self.component)
                yield self.core.callService(ctx, 'multisite_transport',
                    'removeRemote', TRANSPORT_ID, '5.0.0.1')

    def getState(self, ctx):
        """
        return list containing:
            - status of other node
            - date of last response of other node TODO
            - last error                          TODO
        """
        if not self.primary is None:
            ha_state = {
                Primary.INIT : NOT_REGISTERED,
                Primary.OFFLINE : NOT_CONNECTED,
                Primary.ONLINE : CONNECTED
            }
            if not self.primary.state in ha_state.keys():
                raise RpcdError('Primary is in an unknown state : %i' % self.primary.state)
            else:
                return [ ha_state[self.primary.state] , 0, '']
        else:
            return [NOT_REGISTERED, 0, '']

    def getLastError(self):
        return ''


