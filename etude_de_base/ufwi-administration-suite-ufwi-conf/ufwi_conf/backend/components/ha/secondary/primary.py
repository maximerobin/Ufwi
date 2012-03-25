# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

import os
from IPy import IP
from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.core.context import Context
from ufwi_rpcd.common.error import reraise
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.error import RpcdError, CONFIG_NO_SUCH_FILE
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_conf.common.ha_base import HA_NET, PRIMARY_ADDR
from ufwi_conf.common.ha_cfg import PRIMARY_PORT, SECONDARY_PORT
from ufwi_conf.common.ha_statuses import SECONDARY

TRANSPORT_ID = 'ha_secondary'

class Primary(LoggerChild):

    HELLO_INTERVAL = 5*60
    TRANSPORT_INTERVAL = 1

    (INIT,
     OFFLINE,
     ONLINE) = range(3)
    CONFIG_NAME = "ha_secondary.xml"

    def __init__(self, secondary):
        self.hello_task_id = None
        self.component = secondary.component
        self.core = secondary.core
        self.ctx = Context.fromComponent(self.component)

        self.state = self.INIT
        self.vars = VariablesStore()

        LoggerChild.__init__(self, self.component)

    @inlineCallbacks
    def loadConfig(self, interface_name):
        yield self.setFirewallRules(interface_name)
        yield self.startTransport()

        try:
            vars_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_NAME)
            self.vars.load(vars_path)
            self.state = self.vars.get('state')
            self.resume()
        except ConfigError, err:
            if err.error_code != CONFIG_NO_SUCH_FILE:
                # The file doesn't exist because it's not yet configured
                self.error("HA configuration isn't valid")
                self.writeError(err)

    def call(self, *args, **kwargs):
        return self.core.callService(self.ctx, *args, **kwargs)

    def saveConfig(self):
        self.vars.set('state', self.state)
        vars_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_NAME)
        self.vars.save(vars_path)

    def scheduleHello(self, sleep_time):
        if self.hello_task_id is not None:
            self.hello_task_id.cancel()
        self.debug('schedule call to hello on primary node (%s)' % sleep_time)
        self.hello_task_id = scheduleOnce(sleep_time, self.hello)

    def setState(self, state):
        if self.state != state:
            self.state = state
            self.saveConfig()

    def resume(self):
        """ Restore last state. """
        if not self.state in [ self.OFFLINE, self.ONLINE ]:
            # we don't know how to resume from other states
            self.warning('Trying to resume from unknown state : %s' % self.state)
            return

        self.setState(self.OFFLINE)
        if self.component.getType() == SECONDARY:
            self.scheduleHello(1)

    @inlineCallbacks
    def startTransport(self):
        yield self.call('multisite_transport', 'setSelf', TRANSPORT_ID,
            '0.0.0.0', SECONDARY_PORT, True, False)
        yield self.call('multisite_transport', 'addRemote', TRANSPORT_ID,
            PRIMARY_ADDR, PRIMARY_ADDR, PRIMARY_PORT)
        status = yield self.call('multisite_transport', 'start', TRANSPORT_ID)
        self.checkTransport(status)

    def checkTransport(self, status):
        if not status:
            scheduleOnce(self.TRANSPORT_INTERVAL, self.startTransport)

    @inlineCallbacks
    def setFirewallRules(self, interface_name):
        """
        configuration of rules for HA, return a deferred

        localfw.close() is always called
        """
        # FIXME: use LocalFW wrapper
        try:
            yield self.call('localfw', 'open', 'harules')
            # transport
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': PRIMARY_PORT})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input':  interface_name, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': SECONDARY_PORT})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 8443})
            # heartbeat
            broadcast = IP(HA_NET).broadcast()
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 694, 'destinations': [broadcast.strNormal()]})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 123})
            # conntrackd
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 3780, 'destinations':['225.0.0.50']})
            # dhcpd omapi
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 519})
            # support
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 22, 'sources': [HA_NET]})
            # ntp
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': interface_name, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 123, 'sources': [HA_NET]})
            yield self.call('localfw', 'apply')
            yield self.call('localfw', 'close')
        except Exception, err:
            yield self.localfwFailed(err)

    @inlineCallbacks
    def localfwFailed(self, err):
        """
        call localfw.close() and pass error to an errback
        """
        self.error("Setting firewall rules failed")
        self.error("Error: %s" % err)
        yield self.call('localfw', 'close')
        reraise(err)

    @inlineCallbacks
    def register(self, configuration):
        """
        Register myself on primary.
        """
        # Set received parameter
        ha_secondary_iface = self.core.config_manager.get('ha', 'interface_id')
        if self.core.config_manager.get('ha', 'interface_id') != configuration['interface']:
            err_msg = 'Different interfaces are configured : %s and %s'
            err_msg %= (ha_secondary_iface, configuration['interface'])
            raise RpcdError(err_msg)

        self.component.setState(SECONDARY)

        try:
            yield self.call('multisite_transport', 'callRemote', TRANSPORT_ID,
                PRIMARY_ADDR, 'ha', 'end_registration')
            # explicit synchronisation have been done at the end of 'end_registration'
            self.scheduleHello(5)
        except Exception, err:
            self.setState(self.OFFLINE)
            reraise(err)
        # here configuration of primary have been pushed on secondary by primary
        # replicated configuration is applied too
        # see ha.service_end_registration()

    @inlineCallbacks
    def unregister(self):
        if self.hello_task_id is not None:
            try:
                self.hello_task_id.cancel()
            except:
                # Ignore errors happening when the task_id is deprecated
                pass

        self.setState(self.OFFLINE)

        try:
            yield self.call('multisite_transport', 'callRemote', TRANSPORT_ID,
                PRIMARY_ADDR, 'ha', 'bye')
        except Exception, err:
            self.writeError(err)

        try:
            yield self.call('multisite_transport', 'stop', TRANSPORT_ID)
        except Exception, err:
            self.writeError(err)

    @inlineCallbacks
    def hello(self, *args):
        self.hello_task_id = None
        try:
            self.component.checkHAType(SECONDARY)
            number = yield self.call('config', 'getConfigSequenceNumber')
            yield self.call('multisite_transport', 'callRemote', TRANSPORT_ID,
                PRIMARY_ADDR, 'ha', 'hello', number)
            self.setState(self.ONLINE)
            self.debug('HA ONLINE\o/')
        except Exception, err:
            self.helloFailed(err)
        else:
            self.scheduleHello(self.HELLO_INTERVAL)

    def helloFailed(self, err):
        last_state = self.state
        self.setState(self.OFFLINE)
        self.hello_task_id = None
        self.debug('HA Roooh')
        self.writeError(err)

        if last_state >= self.OFFLINE:
            # Schedule a retry of HELLO message only if we aren't in a
            # registering process.
            self.scheduleHello(self.HELLO_INTERVAL)

