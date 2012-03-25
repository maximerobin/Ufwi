# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

import os
from time import mktime, gmtime
from twisted.internet.defer import succeed

from ufwi_rpcd.core.context import Context
from ufwi_rpcd.backend import Component, tr
from ufwi_rpcd.backend.error import RpcdError, CoreError, CONFIG_NO_SUCH_FILE
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore

from .master import Master, TRANSPORT_ID, MULTISITE_CERT_NAME

PKI_NAME = u'__edenwall_multisite'
PKI_ORGUNIT = u'edenwall'
PKI_ORG = u'com'
PKI_LOCATION = u'Paris'
PKI_STATE = u'France'
PKI_COUNTRY = u'FR'
PKI_EMAIL = u'edenwall@edenwall.com'

class MultiSiteSlave(Component):

    NAME = "multisite_slave"
    VERSION = "1.0"
    API_VERSION = 1
    REQUIRES = ('multisite_transport', 'localfw', 'nupki')
    ACLS = {'multisite_transport': set(('setSelf', 'setClientSelf', 'addRemote', 'removeRemote', 'callRemote', 'start', 'getPort')),
            'multisite_master':    set(('hello', 'bye')),
            'nupki':               set(('createPKI', 'listPKI', 'createCertificate', 'getCertRequest')),
            'localfw': set(('open', 'addFilterRule', 'apply', 'close')),
            'nuface': set(('reapplyLastRuleset', )),
            'network': set(('getNetconfig', )),
            'ha': set(('getHAActive', )),
           }

    ROLES = {'multisite_admin':    set(('request_registration', 'unregister', 'setMasterIPAddr', 'checkTime'))}

    def init(self, core):
        self.core = core
        self.master = None
        self.config = None

    def init_done(self):
        d = succeed('done')
        ctx = Context.fromComponent(self)
        try:
            d = self.core.callService(ctx, 'ha', 'getHAActive')
            d.addCallback(self.startWhenActive)
        except CoreError:
            self.startWhenActive(True)
        return d

    def startWhenActive(self, active):
        if not active:
            return succeed(None)

        self.config = VariablesStore()
        d = succeed('done')
        try:
            self.config.load(os.path.join(self.core.config.get('CORE', 'vardir'), Master.CONFIG_PATH))
            attributes = self.config.get('master')
            try:
                self.master = Master(self.config, self.core, Context.fromComponent(self), **attributes)
                d.addCallback(lambda x:self.master.init())
            except Exception:
                self.warning('Unable to read master configuration. It is deleted')
            else:
                scheduleOnce(0, self.master.resume)
        except ConfigError, err:
            if err.error_code != CONFIG_NO_SUCH_FILE:
                self.warning('Unable to load configuration: %s' % err)
        d.addCallback(lambda x: self.loadPki())
        return d

    def createPki(self, pki_list):
        for pki in pki_list:
            if pki[1] == PKI_NAME:
                break
        else:
            return self.core.callService(Context.fromComponent(self), 'nupki', 'createPKI', PKI_NAME, PKI_ORGUNIT, PKI_ORG, PKI_LOCATION, PKI_STATE, PKI_COUNTRY)
        return succeed('done')

    def loadPki(self):
        d = self.core.callService(Context.fromComponent(self), 'nupki', 'listPKI')
        d.addCallback(self.createPki)
        return d

    def destroy(self):
        if self.master:
            return self.master.destroy()

    def service_onHAActive(self, ctx):
        ctx = Context.fromComponent(self)
        return self.service_runtimeFilesModified(ctx)

    def service_onHAPassive(self, ctx):
        ctx = Context.fromComponent(self)
        return self.service_runtimeFilesModified(ctx)

    def service_runtimeFiles(self, context):
        var_dir = self.core.config.get('CORE', 'vardir')
        config_path = os.path.join(var_dir, Master.CONFIG_PATH)
        vpn_path = os.path.join(var_dir, 'multisite', 'vpn')
        return {
            'deleted': (config_path, vpn_path),
            'added': ((config_path,'xml'),(vpn_path, 'dir')),
        }

    def service_runtimeFilesModified(self, ctx):
        """
        Reinitialize the module.
        """
        d = succeed(None)
        d.addCallback(lambda x:self.destroy())
        d.addCallback(lambda x:self.init_done())
        return d

    def service_callRemote(self, ctx, component, service, *args, **kwargs):
        """
        Call a remote service on master.
        @param component  component called on master (str)
        @param service  service called (str)
        @param args  service's arguments (dict)
        @return  service result
        """
        if not self.master or self.master.state != self.master.ONLINE:
            raise RpcdError("MultiSite isn't enabled.")

        return self.core.callService(ctx, 'multisite_transport', 'callRemote', TRANSPORT_ID, MULTISITE_CERT_NAME, component, service, *args, **kwargs)

    def service_request_registration(self, ctx, fw_name, port, protocol, username, password):
        """
        Initialization of a registration with a master.

        It begins the process of registration, when called by a potential master.

        @param username  temporary username used to connect to master (str)
        @param password  password associated to username (str)
        """

        self.info('Received connection from EMS: %s:%s' % (username, password))
        if self.master:
            self.warning("It overrides an existing master")

        self.master = Master(self.config, self.core, Context.fromComponent(self),
                             fw_name,
                             state=Master.INIT,
                             registration={'username': username,
                                           'password': password,
                                           'hostname': ctx.user.host,
                                           'port':     port,
                                           'protocol': protocol,
                                          })

        # Save config before registration (to empty config...)
        self.master.save()

        d = self.master.init()
        d.addCallback(lambda x:self.master.register())
        d.addErrback(self.abortRegister)
        return d

    def service_setMasterIPAddr(self, ctx, ipaddr):
        self.master.setIPAddr(ipaddr)

    def abortRegister(self, err):
        self.master = None
        try:
            self.config.delete('master')
            self.config.save(os.path.join(self.core.config.get('CORE', 'vardir'), Master.CONFIG_PATH))
        except ConfigError:
            pass
        err.raiseException()

    def service_unregister(self, ctx):
        self.info('Unregistering')
        if self.master:
            d = self.master.unregister()
            self.master = None
            if d is not None:
                d.addCallback(lambda x: self.core.callService(ctx, 'multisite_transport', 'removeRemote', TRANSPORT_ID, MULTISITE_CERT_NAME))
        return self.core.notify.emit(self.NAME, 'configModified')

    def service_checkTime(self, ctx, master_time):
        slave_time = mktime(gmtime())

        if abs(slave_time - master_time) > 30:
            raise RpcdError(tr('The time difference between the Edenwall appliance and the EMF appliance is greater than 30 seconds. Please configure a NTP server.'))


