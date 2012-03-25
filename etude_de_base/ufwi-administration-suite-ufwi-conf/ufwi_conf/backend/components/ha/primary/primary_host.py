#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
"""

from time import asctime

from twisted.internet.error import ConnectError
from twisted.python.failure import Failure
from twisted.internet.defer import inlineCallbacks, returnValue

from IPy import IP

from ufwi_rpcd.backend.error import RpcdError, exceptionAsUnicode
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.common.error import reraise
from ufwi_rpcd.core.context import Context
from ufwi_conf.common.ha_base import HA_NET, PRIMARY_ADDR, SECONDARY_ADDR
from ufwi_conf.common.ha_cfg import (PRIMARY_PORT, SECONDARY_PORT, NOT_CONNECTED,
    CONNECTED)

from .secondary import Secondary
from .mail import FR, MAIL_SUBJECT, MAIL_BODY, MAIL_NOROUTE_BODY
from ..error import IncoherentState

TRANSPORT_ID = 'ha'
SECONDARY_TRANSPORT_ID = 'ha_secondary'

class PrimaryHost(LoggerChild):
    def __init__(self, component, core, config):
        self.core = core
        self.config = config
        self.hostname = None
        self.interface = None
        self.secondary = None
        self.context = Context.fromComponent(component)
        LoggerChild.__init__(self, component)

    def call(self, *args, **kwargs):
        return self.core.callService(self.context, *args, **kwargs)

    @inlineCallbacks
    def loadConfig(self):
        try:
            yield self.createSecondary()
        except Exception:
            create_secondary_failed = True
        else:
            create_secondary_failed = False

        try:
            self.interface = self.core.config_manager.get('ha', 'interface_name')
        except ConfigError, err:
            if not create_secondary_failed:
                self.critical("incoherent state: empty config but config file found")
                raise IncoherentState(unicode(err))
        else:
            self.debug("Primary host: initial configuration")

        yield self.setFirewallRules()
        yield self.startTransport()
        yield self.call('multisite_transport', 'setSelf', TRANSPORT_ID,
            '0.0.0.0', PRIMARY_PORT, True, False)
        yield self.call('multisite_transport', 'setSelf', SECONDARY_TRANSPORT_ID,
            '0.0.0.0', SECONDARY_PORT, True, False)

    def stop(self):
        self.debug('Stopping primary instance')
        return self.call('multisite_transport', 'stop', TRANSPORT_ID)

    @inlineCallbacks
    def remotePostUpdate(self):
        errors = yield self.call(
            'multisite_transport',
            'callRemote',
            TRANSPORT_ID,
            SECONDARY_ADDR,
            'config',
            'apply_post_update'
            )

        if errors:
            self.critical(
                "%s errors while reapplying after update on secondary:" %
                len(errors)
                )
            for error in errors:
                self.critical(" - %s" % unicode(error))
            returnValue(False)
        returnValue(True)

    def createSecondary(self):
        # Raises a ConfigError in case of failure
        self.secondary = Secondary(self.core)
        self.secondary.loadConfig()

    @inlineCallbacks
    def setFirewallRules(self):
        # FIXME: use LocalFW wrapper
        try:
            yield self.call('localfw', 'open', 'harules')
            # transport
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': PRIMARY_PORT})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': SECONDARY_PORT})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 8443})
            # heartbeat
            broadcast = IP(HA_NET).broadcast()
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 694, 'destinations': [broadcast.strNormal()]})
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 123})
            # conntrackd
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 3780, 'destinations':['225.0.0.50']})
            # dhcpd omapi
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 519})
            # support
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'tcp', 'dport': 22, 'sources':[HA_NET]})
            # ntp
            yield self.call('localfw', 'addFilterRule',
                {'chain': 'INPUT', 'input': self.interface, 'decision': 'ACCEPT',
                 'protocol': 'udp', 'dport': 123, 'sources': [HA_NET]})
            yield self.call('localfw', 'apply')
            yield self.call('localfw', 'close')
        except Exception, err:
            yield self.localfwFailed(err)

    @inlineCallbacks
    def localfwFailed(self, err):
        self.error("Setting firewall rules failed")
        self.error("Error: %s" % err)
        yield self.call('localfw', 'close')
        reraise(err)

    @inlineCallbacks
    def startTransport(self):
        success = yield self.call('multisite_transport', 'start', TRANSPORT_ID)
        if success:
            returnValue("done")
        scheduleOnce(0, self.startTransport)
        returnValue("done")

    ##############
    # REGISTRATION
    @inlineCallbacks
    def register(self, configuration):
        """
        Callback of the authentication process, it sends the OTP
        """
        yield self.call('multisite_transport', 'addRemote', TRANSPORT_ID, SECONDARY_ADDR, SECONDARY_ADDR, SECONDARY_PORT)
        yield self.call('multisite_transport', 'addRemote', SECONDARY_TRANSPORT_ID, PRIMARY_ADDR, PRIMARY_ADDR, PRIMARY_PORT)
        yield self.call('multisite_transport', 'callRemote', TRANSPORT_ID, SECONDARY_ADDR, 'ha', 'register', configuration)

    def checkConfigVersions(self, primary_seq_no, secondary_seq_no):
        if primary_seq_no != secondary_seq_no:
            msg = "Configuration synchronization (primary version %i / secondary version %i)"
            self.info( msg % (primary_seq_no, secondary_seq_no))
        return primary_seq_no != secondary_seq_no

    def service_hello(self, ctx, config_seq_no):
        if not hasattr(ctx, 'firewall'):
            self.warning("A non-firewall tries to HELLO me")
            return False

        if self.secondary is None:
            self.warning('Received a HELLO from an unregistered secondary')
            return False

        self.secondary.setState(Secondary.ONLINE)
        self.secondary.updateLastSeen()
        self.debug("HELLO from secondary firewall")

        # Check the config sequence number to eventually trigger a config synchronisation
        d = self.core.callService(ctx, 'config', 'getConfigSequenceNumber')
        d.addCallback(self.checkConfigVersions, config_seq_no)
        return d

    def service_bye(self, ctx):
        if not hasattr(ctx, 'firewall'):
            self.warning("A non-firewall tries to BYE me")
            return

        if self.secondary is None:
            self.warning('Received a BYE from an unknown firewall (%s)' % ctx.firewall)
            return

        self.secondary.setState(Secondary.OFFLINE)
        self.debug("Good BYE %s!" % ctx.firewall)

        return True

    def service_callRemote(self, ctx, component, service, *args):
        """
        Call a remote service on a firewall.
        Errors encountered are ONLY logged, you MUST add an errback
        @param firewall  the firewall name (str)
        @param component  component called on the remote firewall (str)
        @param service  service called (str)
        @param args  service's arguments (dict)
        @return  service result
        """
        if self.secondary is None:
            raise RpcdError('Not associated to a secondary firewall')

        d = self.call('multisite_transport', 'callRemote', TRANSPORT_ID, SECONDARY_ADDR, component, service, *args)
        d.addCallback(self.remoteCallSucceeded)
        d.addErrback(self.remoteCallFailed)
        d.addBoth(self.saveError)
        return d

    def saveError(self, err):
        if isinstance(err, Failure):
            strerror = exceptionAsUnicode(err.value)
        elif isinstance(err, Exception):
            strerror = exceptionAsUnicode(err)
        if isinstance(err, (Failure, Exception)):
            self.secondary.error = "%s %s" % (asctime(), strerror)
        return err

    @inlineCallbacks
    def sendLastSecondaryError(self):
        lang = FR
        if "An error occurred while connecting: 113: No route to host" in self.secondary.error:
            template = MAIL_NOROUTE_BODY
        else:
            template = MAIL_BODY
        yield self.call(
            'contact',
            'sendMailToAdmin',
            MAIL_SUBJECT[lang],
            template[lang] % {'ERROR': self.secondary.error}
            )

    def remoteCallFailed(self, err):
        err.trap(ConnectError) # FIXME other errors are unhandled
        self.secondary.setState(Secondary.OFFLINE)
        return err

    def remoteCallSucceeded(self, err):
        self.secondary.updateLastSeen()
        return err

    def getState(self, ctx):
        """
        return list containing:
            - status of other node
            - date of last response of other node
            - last error
        """
        # Make a distant call to refresh the state
        self.service_callRemote(ctx, 'ha', 'getState')

        if not self.secondary is None:
            ha_state = {
                Secondary.ONLINE :      CONNECTED,
                Secondary.OFFLINE :     NOT_CONNECTED,
            }
            if not self.secondary.state in ha_state.keys():
                msg = 'Secondary is in an unknown state : %i'
                raise RpcdError(msg % self.secondary.state)
            else:
                return [ha_state[self.secondary.state],
                             self.secondary.last_seen,
                             self.getLastError()]
        else:
            return [NOT_CONNECTED, 0, '']

    def getLastError(self):
        if self.secondary is None:
            return u''
        return self.secondary.error
