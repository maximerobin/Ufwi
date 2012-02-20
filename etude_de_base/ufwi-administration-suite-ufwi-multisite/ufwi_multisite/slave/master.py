#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
"""

from IPy import IP
import os

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.python.failure import Failure
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.error import RpcdError
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.logger import Logger

from .registration_client import RegistrationClient
from ..openvpn import OpenVPNClient, OpenVPNError

OPENVPN_IF = 'ew4master0'
OPENVPN_RETRY = 60

TRANSPORT_ID = 'multisite'
PKI_NAME = u'__edenwall_multisite'
PKI_ORGUNIT = u'edenwall'
PKI_ORG = u'com'
PKI_LOCATION = u'Paris'
PKI_STATE = u'France'
PKI_COUNTRY = u'FR'
PKI_EMAIL = u'edenwall@edenwall.com'
PKI_SERIAL = '01'
MULTISITE_CERT_NAME = 'multisite-master'

class Master(Logger):

    HELLO_INTERVAL = 5*60

    (INIT,
     REQUEST_REGISTER,
     STARTING_OPENVPN,
     OFFLINE,
     ONLINE) = range(5)
    CONFIG_PATH = "multisite_slave.xml"

    def __init__(self, config, core, ctx, fw_name='', state=0, registration={},
                       key='', cert='', client_key='', client_cert='', openvpn_port=0, cacert='',
                       openvpn_ip='', openvpn_network='', multisite_port=0):

        Logger.__init__(self, 'master')

        self.config = config
        self.core = core
        self.ctx = ctx
        self.hello_task_id = None
        self.OPENVPN_CA_PATH = os.path.join(self.core.var_dir, 'multisite', 'vpn', 'ca.crt')
        self.OPENVPN_KEY_PATH = os.path.join(self.core.var_dir, 'multisite', 'vpn', 'slave.key')
        self.OPENVPN_CERT_PATH = os.path.join(self.core.var_dir, 'multisite', 'vpn', 'slave.crt')

        # attributes
        try:
            self.fw_name = fw_name
            self.state = int(state)
            self.registration_client = RegistrationClient(**registration)
            self.openvpn_port = int(openvpn_port)
            self.openvpn_ip = openvpn_ip and IP(openvpn_ip)
            self.openvpn_network = openvpn_network and IP(openvpn_network)
            self.multisite_port = int(multisite_port)
            self.key = key
            self.cert = cert
            self.client_key = client_key
            self.client_cert = client_cert
            self.cacert = cacert
        except ValueError, e:
            raise ConfigError("Master configuration isn't valid: %s" % e)

        self.openvpn = OpenVPNClient(os.path.join(self.core.var_dir, 'multisite', 'vpn'),
                                     self.registration_client.hostname, self.openvpn_port,
                                     OPENVPN_IF)

    def init(self):
        # FIXME: use LocalFW wrapper
        ctx = self.ctx
        d = self.core.callService(ctx, 'localfw', 'open', 'multisiterules')
        d.addCallback(lambda x:self.core.callService(ctx, 'localfw', 'addFilterRule',
            {'chain': 'FORWARD', 'decision': 'DROP', 'output': OPENVPN_IF}))
        d.addCallback(lambda x:self.core.callService(ctx, 'localfw', 'addFilterRule',
            {'chain': 'INPUT', 'input': OPENVPN_IF, 'decision': 'ACCEPT',
             'protocol': 'tcp', 'dport': self.multisite_port}))
        d.addCallback(lambda x:self.core.callService(ctx, 'localfw', 'apply'))
        d.addCallback(lambda x:self.core.callService(ctx, 'localfw', 'close'))
        d.addErrback(self.localfwFailed, ctx)
        return d

    def localfwFailed(self, err, ctx):
        self.error("Setting firewall rules failed")
        self.debug("Error: %s" % err)
        self.core.callService(ctx, 'localfw', 'close')

    def save(self):
        self.config.set('master', 'fw_name', self.fw_name)
        self.config.set('master', 'state', self.state)
        self.config.set('master', 'openvpn_port', self.openvpn_port)
        self.config.set('master', 'openvpn_ip', str(self.openvpn_ip))
        self.config.set('master', 'openvpn_network', str(self.openvpn_network))
        self.config.set('master', 'multisite_port', self.multisite_port)
        self.config.set('master', 'key', self.key)
        self.config.set('master', 'cert', self.cert)
        self.config.set('master', 'client_key', self.client_key)
        self.config.set('master', 'client_cert', self.client_cert)
        self.config.set('master', 'cacert', self.cacert)
        for key, val in self.registration_client.save().iteritems():
            self.config.set('master', 'registration', key, val)

        self.config.save(os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_PATH))

    def unregister(self):
        if self.hello_task_id is not None:
            self.hello_task_id.cancel()
        self.hello_task_id = None
        self.config.delete('master')
        self.config.save(os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_PATH))
        d = self.destroy()
        return d

    def destroy(self):
        if self.openvpn.isRunning() and self.state >= self.OFFLINE:
            # useless if there isn't an openvpn to send message.
            d = self.core.callService(self.ctx, 'multisite_transport', 'callRemote', TRANSPORT_ID, MULTISITE_CERT_NAME, 'multisite_master', 'bye')
            d.addErrback(self.writeError)
            d.addCallback(self.stop_openvpn)
            return d

    def __del__(self):
        self.destroy()

    def setIPAddr(self, ipaddr):
        try:
            self.openvpn.setAddress(ipaddr)
        except OpenVPNError:
            self.openvpn.setAddress(self.registration_client.hostname)
            raise
        else:
            self.registration_client.hostname = ipaddr
            self.state = self.OFFLINE
            if self.hello_task_id is not None:
                self.hello_task_id.cancel()
            self.hello_task_id = scheduleOnce(5, self.start_multisite_transport)

    def resume(self):
        """ Restore last state. """
        if self.state == self.INIT or self.state == self.REQUEST_REGISTER:
            return self.register()

        self.start_openvpn()
        if self.state == self.STARTING_OPENVPN:
            return self.retry_start_multisite_transport(None)

        self.state = self.OFFLINE
        self.hello_task_id = scheduleOnce(5, self.retry_start_multisite_transport, None)

    def retry_start_multisite_transport(self, err):
        if isinstance(err, Failure):
            self.writeError(err.getErrorMessage())

        d = self.core.callService(self.ctx, 'multisite_transport', 'start', TRANSPORT_ID)
        d.addCallback(lambda x:self.hello())
        d.addErrback(lambda x:scheduleOnce(OPENVPN_RETRY, self.retry_start_multisite_transport, x))
        return d

    def start_multisite_transport(self):
        if self.hello_task_id is not None:
            self.hello_task_id.cancel()
            self.hello_task_id = None
        return self.core.callService(self.ctx, 'multisite_transport', 'start', TRANSPORT_ID).addCallback(lambda x: self.hello())

    @inlineCallbacks
    def register(self):
        """
        Register myself on master.
        """
        client_cert = {
            'pki': PKI_NAME,
            'type': 'client',
            'cname': self.fw_name,
            'serial': PKI_SERIAL,
            'email': PKI_EMAIL,
            'organization_unit': PKI_ORGUNIT,
            'location': PKI_LOCATION,
            'state': PKI_STATE,
            'country': PKI_COUNTRY,
            'organization': PKI_ORG,
        }

        server_cert = dict(client_cert)
        server_cert['type'] = 'server'
        server_cert['cname'] = self.fw_name + '-server'

        def nupki(*args):
            return self.core.callService(self.ctx, 'nupki', *args)

        # Create client certificate request
        yield nupki('createCertificate', client_cert)
        res = yield nupki('getCertRequest', PKI_NAME, client_cert['cname'], 'client')
        yield self.setClientCert(res)

        # Create server certificate request
        yield nupki('createCertificate', server_cert)
        res = yield nupki('getCertRequest', PKI_NAME, server_cert['cname'], 'server')
        yield self.register_request(res)

    def setClientCert(self, res):
        self.client_cert_req = res[0]
        self.client_key = res[1]

    @inlineCallbacks
    def register_request(self, res):
        cert_req, self.key = res
        self.state = self.REQUEST_REGISTER
        self.save()

        result = yield self.registration_client.call('multisite_master', 'register', cert_req, self.client_cert_req)
        yield self.set_settings(result)

    @inlineCallbacks
    def set_settings(self, result):
        """
        Callback for the master service "register".

        It results a dict with values:
        - 'cert': text of signed certificate
        - 'cacert': text certificate of CA
        - 'vpn_port': openvpn port
        - 'vpn_network': openvpn network
        - 'multisite_host': master's hostname in vpn
        - 'multisite_port': port listened by master for multisite
        """

        # Set received parameter
        self.cert = result['cert']
        self.client_cert = result['client_cert']
        self.openvpn_port = result['vpn_port']
        self.openvpn_network = IP(result['vpn_network'])
        self.cacert = result['cacert']
        self.multisite_port = result['multisite_port']
        self.multisite_host = result['multisite_host']
        self.state = self.STARTING_OPENVPN
        self.save()

        self.openvpn.buildCertificates(self.client_key, self.client_cert, self.cacert)
        self.openvpn.setPort(self.openvpn_port)
        try:
            self.start_openvpn()
        except OpenVPNError:
            yield self.registration_client.call('multisite_master', 'registration_failed', 'Unable to start the securised tunnel.')
            raise

        # Now, to communicate into the new OpenVPN channel with
        # master, it has to provides me a signed certificate...
        yield self.set_multisite_transport()

    @inlineCallbacks
    def set_multisite_transport(self):
        try:
            yield self.core.callService(self.ctx, 'multisite_transport', 'setSelf', TRANSPORT_ID,
                                                                                  '0.0.0.0',
                                                                                  self.multisite_port, # use same port than master
                                                                                  True,
                                                                                  True,
                                                                                  self.cert,
                                                                                  self.key,
                                                                                  self.cacert)
            yield self.core.callService(self.ctx, 'multisite_transport', 'setClientSelf', TRANSPORT_ID,
                                                                                  True,
                                                                                  self.client_cert,
                                                                                  self.client_key,
                                                                                  self.cacert)
            yield self.core.callService(self.ctx, 'multisite_transport', 'addRemote', TRANSPORT_ID, MULTISITE_CERT_NAME, self.multisite_host, self.multisite_port)
            scheduleOnce(5, self.finish_registration)
        except RpcdError, e:
            self.writeError(e)
            scheduleOnce(5, self.set_multisite_transport)
            returnValue('done')

    def start_openvpn(self):
        self.openvpn.stop()

        try:
            self.openvpn.start()
        except OpenVPNError, err:
            self.critical('%s' % err)
            raise

    def stop_openvpn(self, *args):
        self.openvpn.stop()

    @inlineCallbacks
    def finish_registration(self):
        yield self.start_multisite_transport()
        try:
            yield self.registration_client.call('multisite_master', 'end_registration')
        except Exception:
            scheduleOnce(self.HELLO_INTERVAL, self.finish_registration)
        yield self.core.notify.emit('multisite_slave', 'configModified')

    @inlineCallbacks
    def hello(self):
        try:
            yield self.core.callService(self.ctx, 'multisite_transport', 'callRemote', TRANSPORT_ID, MULTISITE_CERT_NAME, 'multisite_master', 'hello')
            self.helloSucceed()
        except Exception, err:
            yield self.helloFailed(err)

    def helloSucceed(self):
        self.state = self.ONLINE
        self.save()
        self.debug('ONLINE\o/')
        self.hello_task_id = scheduleOnce(self.HELLO_INTERVAL, self.hello)

    @inlineCallbacks
    def helloFailed(self, err):
        self.hello_task_id = None
        last_state = self.state
        self.state = self.OFFLINE
        self.debug('Roooh')
        self.writeError(err.value)

        if last_state >= self.OFFLINE:
            # Schedule a retry of HELLO message only if we aren't in a
            # registering process.
            self.hello_task_id = scheduleOnce(self.HELLO_INTERVAL, self.hello)
        else:
            yield self.registration_client.call('multisite_master', 'registration_failed', 'Unable to contact Master in securised tunnel.')
            err.raiseException()
