# -*- coding: utf-8 -*-
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

$Id$
"""

import os
from IPy import IP
import time
from copy import deepcopy

from twisted.internet.defer import succeed
from twisted.internet.error import ConnectError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.error import RpcdError, exceptionAsUnicode
from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.core.context import Context

from .common.multisite_component import MultiSiteComponent
from .request import RequestFirewallJob
from .firewall import Firewall
from .common.firewall import MultiSiteFirewall
from .pki import PKI, PKI_NAME, NUPKI_SERVICES
from ..openvpn import OpenVPNServer, OpenVPNError

OPENVPN_PORT = 8844
DEFAULT_OPENVPN_NETWORK = '5.1.0.0/16'
RPCD_PORT = 54321
OPENVPN_IF = 'ew4master0'
TRANSPORT_ID = 'multisite'
MULTISITE_CERT_NAME = 'multisite-master'

from subprocess import PIPE
from ufwi_rpcd.backend.process import runCommand

def get_ip(component):
    interface_name = OPENVPN_IF
    command = "/sbin/ip addr show %s" % interface_name
    process, status = runCommand(component, command.split(), stdout=PIPE)
    for line in process.stdout:
        line = line.split()
        if line[0] in ('inet', 'inet6'):
            return line[1].split('/')[0]
    return None

def dict2list(d):
    return [d[str(i)] for i in xrange(len(d.keys()))]

def list2dict(l):
    d = {}
    for no, val in enumerate(l):
        d[str(no)] = val
    return d

def make_lambda_x(func, *args):
    return lambda x: func(*args)

class MultiSite(MultiSiteComponent):

    NAME = "multisite_master"
    VERSION = "1.0"
    API_VERSION = 1
    REQUIRES = ('multisite_transport', 'nupki')
    ACLS = {'multisite_transport': set(('setSelf', 'setClientSelf', 'addRemote', 'removeRemote', 'callRemote', 'getPort', 'start')),
            'nupki': NUPKI_SERVICES,
            'localfw': set(('open', 'addFilterRule', 'apply', 'close')),
            'nuface': set(('reapplyLastRuleset', )),
            'network': set(('getNetconfig', )),
            'acl': set(('listAllRoles',)),
            '*' : set(('unregister_firewall',)),
            }
    FIREWALL_CLASS = Firewall
    CONFIG_PATH = 'multisite.xml'

    MULTISITE_SERVICES = ['hello', 'bye']

    ROLES = {
        'multisite_read' : set((
                            "listFirewalls",
                            "getFirewallState",
                            "callRemote",
                            "register",
                            "getFirewallCategories",
                            "getCategories",
                            )),
        'multisite_write' : set((
                            "@multisite_read",
                            "delCategories",
                            "setCategories",
                            "setFirewallCategories",
                            )),
        'multisite_admin' : set((
                            "listFirewalls",
                            "listHostsGroups",
                            "setHostsGroup",
                            "setHostsGroupAcl",
                            "getHostsGroupAcl",
                            "deleteHostsGroupAcl",
                            "refreshAcls",

                            "register_firewall",
                            "unregister_firewall",
                            "registration_failed",
                            "end_registration",
                            ))
        }

    def init(self, core):
        self.pki = PKI(self, core)
        self.openvpn = None
        self.request_jobs = {}
        self.openvpn_network = IP(DEFAULT_OPENVPN_NETWORK)
        self.openvpn_ip = None
        self.categories = {}
        self.categories_order = []
        self.acl_hosts_groups = {}
        self.acl_groups_roles = {}
        self.subcomponents = []
        return MultiSiteComponent.init(self, core)

    def init_done(self):
        d = MultiSiteComponent.init_done(self)
        d.addCallback(lambda x:self.core.callService(Context.fromComponent(self), 'acl', 'listAllRoles'))
        d.addCallback(self.setRoles)
        return d

    def setRoles(self, roles):
        self.roles_list = set(roles.keys())

    def destroy(self):
        for name, fw in self.firewalls.iteritems():
            fw.state = Firewall.OFFLINE
            fw.save()

        if self.openvpn:
            self.openvpn.stop()

    def loadConfig(self):
        """
        Load configuration of PKI, OpenVPN and firewalls.
        """

        d = succeed("done")
        d.addCallback(self.pki.loadPki)
        d.addCallback(self.setFirewallRules)
        d.addCallback(self.createOpenVPNCertificate)
        d.addCallback(self.loadCategories)
        d.addCallback(self.loadFirewalls)
        d.addCallback(lambda x: scheduleOnce(3, self.loadTransport))
        d.addErrback(self.loadError)
        return d

    def loadError(self, err):
        self.debug(unicode(err))
        self.error("An error occured while loading : %s" % unicode(err))

    def createOpenVPNCertificate(self, *args):
        server_certs_name = MULTISITE_CERT_NAME + '-server'
        d = self.pki.loadServerCertsPaths(server_certs_name, 'server')
        d.addCallback(self.startOpenVPN, server_certs_name)
        d.addErrback(self.loadError)
        return d

    def setFirewallRules(self, *args):
        # FIXME: use LocalFW wrapper
        comp_ctx = Context.fromComponent(self)
        d = self.core.callService(comp_ctx, 'localfw', 'open', 'multisiterules')
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'localfw', 'addFilterRule',
            {'chain': 'INPUT', 'decision': 'ACCEPT',
             'protocol': 'udp', 'dport': OPENVPN_PORT}))
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'localfw', 'addFilterRule',
            {'chain': 'INPUT', 'input': OPENVPN_IF, 'decision': 'ACCEPT',
             'protocol': 'tcp', 'dport': RPCD_PORT}))
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'localfw', 'addFilterRule',
            {'chain': 'FORWARD', 'output': OPENVPN_IF, 'decision': 'DROP'}))
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'localfw', 'apply'))
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'localfw', 'close'))
        d.addErrback(self.localfwFailed, comp_ctx)
        return d

    def localfwFailed(self, err, ctx):
        self.error("Setting firewall rules failed")
        self.debug("Error: %s" % err)
        self.core.callService(ctx, 'localfw', 'close')

    def startOpenVPN(self, ret, hostname):
        if self.openvpn:
            self.openvpn.stop()

        cert, key, ca = self.pki.getServerCertsPaths(hostname)
        self.openvpn = OpenVPNServer(os.path.join(self.core.var_dir, 'multisite', 'vpn'),
                                     '0.0.0.0', OPENVPN_PORT, OPENVPN_IF,
                                     key, cert, ca, self.openvpn_network)
        try:
            self.openvpn.start()
        except OpenVPNError, err:
            self.critical('%s' % err)
            # TODO What can I do exactly?
            raise

    def loadTransport(self, *args):
        server_certs_name = MULTISITE_CERT_NAME + '-server'
        d = self.pki.loadServerCerts(server_certs_name, 'server')
        d.addCallback(self.startTransport, server_certs_name)
        d.addCallback(lambda x: self.pki.loadServerCerts(MULTISITE_CERT_NAME, 'client'))
        d.addCallback(self.startClientTransport, MULTISITE_CERT_NAME)
        d.addCallback(lambda x: self.core.callService(Context.fromComponent(self), 'multisite_transport', 'start', TRANSPORT_ID))
        return d

    def startTransport(self, ret, cert_name):
        cert, key, ca = self.pki.getServerCerts(cert_name)
        return self.core.callService(Context.fromComponent(self),
                              'multisite_transport', 'setSelf', TRANSPORT_ID,
                              self.getOpenVpnIP(), RPCD_PORT, False, True, cert, key, ca)

    def startClientTransport(self, ret, cert_name):
        cert, key, ca = self.pki.getServerCerts(cert_name)
        return self.core.callService(Context.fromComponent(self),
                              'multisite_transport', 'setClientSelf', TRANSPORT_ID,
                              True, cert, key, ca)

    def getOpenVpnIP(self):
        if self.openvpn_ip:
            return str(self.openvpn_ip)

        ip = get_ip(self)
        if ip is not None:
            return ip

        raise RpcdError('Unable to find my OpenVPN IP (on network %s)' % self.openvpn_network)

    def loadCategories(self, *args):
        try:
            self.categories = self.config.get('categories')
            self.categories_order = []
            order = self.config.get('categories_order')
            for i in range(len(order)):
                self.categories_order.append(order[str(i)])
        except (ConfigError, KeyError):
            pass
        try:
            self.acl_hosts_groups = self.config.get('acl_hosts_groups')
            for group in self.acl_hosts_groups.keys():
                self.acl_hosts_groups[group] = dict2list(self.acl_hosts_groups[group])
            self.acl_groups_roles = self.config.get('acl_groups_roles')
            for group in self.acl_groups_roles.keys():
                for user in self.acl_groups_roles[group]:
                    self.acl_groups_roles[group][user] = dict2list(self.acl_groups_roles[group][user])
        except (ConfigError, KeyError):
            pass
        return True

    def subComponentCall(self, *args):
        ctx = Context.fromComponent(self)

        def lambda_x(func, *args):
            return lambda x: func(*args)

        d = succeed('done')
        for component in self.subcomponents:
            d.addCallback(lambda_x(self.core.callService, ctx, component, *args))
        d.addErrback(self.writeError)
        return d

    def listFirewall_checkFwPermissions(self, permissions, firewall, allowed_firewalls):
        if permissions != set():
            for f in allowed_firewalls:
                if f[0] == firewall.name:
                    break
            else:
                allowed_firewalls.append((firewall.name, firewall.getState(), firewall.error, firewall.last_seen, firewall.hostname))
        return allowed_firewalls

    def service_listFirewalls(self, ctx):
        """
        Get list of firewalls.
        @return  a list of tuple (firewall name, firewall state)
        """

        l = []
        d = succeed([])
        for name, firewall in self.firewalls.iteritems():
            for grp in ctx.user.groups:
                d.addCallback(lambda x:self.core.callService(ctx, 'multisite_transport', 'getAcl', grp, '', name))
                d.addCallback(self.listFirewall_checkFwPermissions, firewall, l)
        return d

    def service_getFirewallState(self, ctx, fw_name):
        """
        Get a firewall state
        @return the status as a string
        """
        return self.firewalls[fw_name].state

    def service_callRemote(self, ctx, firewall, component, service, *args, **kwargs):
        """
        Call a remote service on a firewall.
        @param firewall  the firewall name (str)
        @param component  component called on the remote firewall (str)
        @param service  service called (str)
        @param args  service's arguments (dict)
        @return  service result
        """
        try:
            fw = self.firewalls[firewall]
        except KeyError:
            raise RpcdError("Firewall '%s' does not exist." % firewall)

        if fw.state != MultiSiteFirewall.ONLINE:
            raise RpcdError("Firewall '%s' is offline." % firewall)

        d = self.core.callService(ctx, 'multisite_transport', 'callRemote', TRANSPORT_ID, firewall, component, service, *args, **kwargs)
        d.addCallback(self.remoteCallSucceeded, firewall)
        d.addErrback(self.remoteCallFailed, firewall)
        return d

    def remoteCallFailed(self, err, firewall_name):
        err.trap(ConnectError)

        self.writeError(err.value)
        try:
            fw = self.firewalls[firewall_name]
            fw.state = Firewall.ERROR
            fw.error = str(err.value)
        except KeyError:
            self.warning("An error occured while trying to contact an inexistant firewall")

        err.raiseException()

    def remoteCallSucceeded(self, err, firewall_name):
        try:
            fw = self.firewalls[firewall_name]
            fw.has_been_seen()
        except KeyError:
            self.warning("An error occured while trying to contact an inexistant firewall")
        return err

    ##############
    # REGISTRATION

    def service_register_firewall(self, ctx, name, hostname, port, protocol, login, password):
        """
        Service called by an admin to start a registration process with
        a firewall.

        @param hostname  hostname of firewall (str)
        @param port  port to connect to firewall (int)
        @param protocol  protocol used (http or https) (str)
        @param admin_password  password for the 'admin' account on remote (str)
        @return  True if it works, raises an exception in other case (bool)
        """

        job = RequestFirewallJob(self.core, name, hostname, port, protocol)

        d = job.init_transaction(login, password)
        d.addCallback(lambda x:job.test_slave_state())
        d.addCallback(self.check_slave_component)
        d.addErrback(self.connection_failed, job)
        d.addCallback(self.connection_success, job)
        return d

    def connection_failed(self, err, job):
        job.logout()
        if err.check(RpcdError) and hasattr(err.value, 'type') and err.value.type == 'AuthError':
            raise RpcdError(tr("The Administrator password is invalid."))

        err.raiseException()

    def connection_success(self, success, job):
        """
        Connection with firewall is successfull, so we result True to
        admin client, and schedule the request starting.
        """

        firewall = Firewall(self, self.core, self.NAME, job.name, {'state':Firewall.REGISTERING, 'last_seen':0, 'hostname' : job.hostname})
        self.firewalls[job.name] = firewall
        job.firewall = firewall
        scheduleOnce(0, self.start_request, job)
        return True

    def check_slave_component(self, component_list):
        if 'multisite_slave' not in component_list:
            raise RpcdError(tr('You can only register an Edenwall appliance'))

    def start_request(self, job):
        """
        Callback of the authentication process, it sends the OTP
        """
        name, password = job.create_slave_account()
        self.request_jobs[name] = job
        d = job.send_password(name, password)
        d.addErrback(self.request_failed, job)
        d.addCallback(lambda x:job.test_slave_time())
        d.addErrback(self.request_failed, job)
        d.addBoth(lambda x:job.logout())
        return d

    def request_failed(self, err, job):
        self.critical("An error occured while I tried to establish connection with slave '%s': %s" % (job.hostname, err.value))
        if job.firewall and (not job.firewall.error or job.firewall.state != Firewall.ERROR):
            job.firewall.state = Firewall.ERROR
            job.firewall.error = exceptionAsUnicode(err.value)
            job.firewall.save()

    def ignoreError(self, err):
        self.debug(unicode(err))

    def service_register(self, ctx, cert_req, client_cert_req):
        """
        Called by the *slave*, it registers itself on master.
        """
        try:
            job = self.request_jobs[ctx.user.login]
        except KeyError:
            self.warning('A non requested firewall tries to register itself (id=%s)' % ctx.user.login)
            raise RpcdError(tr("You are not in a registering process"))

        firewall = self.firewalls[job.name]
        firewall.last_seen = int(time.time())

        comp_ctx = Context.fromComponent(self)
        d = succeed('none')
        d.addCallback(lambda x:self.pki.signCertRequest(cert_req, firewall.name + '-server', 'server'))
        d.addCallback(lambda x:self.pki.getSignedCert(firewall.name + '-server'))
        d.addCallback(self.setFirewallCert, firewall.name)
        d.addCallback(lambda x:self.pki.signCertRequest(client_cert_req, firewall.name, 'client'))
        d.addCallback(lambda x:self.pki.getSignedCert(firewall.name))
        d.addCallback(self.setFirewallClientCert, firewall.name)
        d.addCallback(lambda x:self.core.callService(comp_ctx, 'multisite_transport', 'getPort', TRANSPORT_ID))
        d.addCallback(self.cb_register, comp_ctx, firewall)
        return d

    def setFirewallCert(self, ret, fw_name):
        self.firewalls[fw_name].cert = ret[0]
        self.firewalls[fw_name].cacert = ret[1]
        self.firewalls[fw_name].save()

    def setFirewallClientCert(self, ret, fw_name):
        self.firewalls[fw_name].client_cert = ret[0]
        #self.firewalls[fw_name].cacert = ret[1]
        self.firewalls[fw_name].save()

    def cb_register(self, multisite_port, ctx, firewall):
        d = self.core.callService(ctx, 'multisite_transport', 'addRemote', TRANSPORT_ID, firewall.name, firewall.name, multisite_port)
        d.addCallback(self.cb_2_register, multisite_port, firewall)
        return d

    def cb_2_register(self, result, multisite_port, firewall):
        return firewall.settings(self.openvpn_network, self.openvpn.getPort(), self.getOpenVpnIP(), multisite_port)

    def service_hello(self, ctx):
        if not hasattr(ctx, 'firewall'):
            self.warning("A non-firewall tries to HELLO me")
            return

        try:
            firewall = self.firewalls[ctx.firewall]
        except KeyError:
            self.warning('Received a HELLO from an unknown firewall (%s)' % ctx.firewall)
            return

        firewall.state = MultiSiteFirewall.ONLINE
        firewall.has_been_seen()
        firewall.save()
        self.debug("HELLO from %s" % ctx.firewall)

        return True

    def service_bye(self, ctx):
        if not hasattr(ctx, 'firewall'):
            self.warning("A non-firewall tries to BYE me")
            return

        try:
            firewall = self.firewalls[ctx.firewall]
        except KeyError:
            self.warning('Received a BYE from an unknown firewall (%s)' % ctx.firewall)
            return

        firewall.state = firewall.OFFLINE
        firewall.has_been_seen()
        firewall.save()
        self.debug("Good BYE %s!" % ctx.firewall)

        return True

    def service_registration_failed(self, ctx, message):
        """
        An occured has occured on the slave side while registering on me.
        It abort process.
        """
        try:
            job = self.request_jobs.pop(ctx.user.login)
        except KeyError:
            self.warning('A non requested firewall tries report a registration failure (id=%s)' % ctx.user.login)
            return False

        if not job.firewall:
            self.warning('A requested firewall abort registration (id=%s)' % ctx.user.login)
            return False

        job.firewall.error = message
        job.firewall.state = Firewall.ERROR
        job.firewall.save()
        job.remove_account(ctx.user.login)
        return True

    def service_end_registration(self, ctx):
        """
        End of registration, remove the request_job.
        """

        try:
            job = self.request_jobs.pop(ctx.user.login)
        except KeyError:
            self.warning('A non requested firewall tries to end registration (id=%s)' % ctx.user.login)
            return False

        if not job.firewall:
            self.warning('A requested firewall abort registration (id=%s)' % ctx.user.login)
            return False

        job.remove_account(ctx.user.login)
        self.info('Registration of %s succeeded' % job.firewall.name)
        return True

    def service_unregister_firewall(self, ctx, hostname):
        self.info('Unregistering firewall %s' % hostname)

        if hostname not in self.firewalls:
            self.error('Trying to unregister an unknown firewall : %s' % hostname)
            return

        d = succeed('done')
        d.addCallback(lambda x:self.service_callRemote(ctx, hostname, 'multisite_slave', 'unregister'))
        d.addErrback(self.ignoreError)
        d.addCallback(lambda x:self.core.callService(ctx, 'multisite_transport', 'removeRemote', TRANSPORT_ID, hostname))
        d.addErrback(self.ignoreError)
        d.addCallback(lambda x:self.subComponentCall("unregister_firewall", hostname))
        d.addErrback(self.ignoreError)
        d.addCallback(lambda x:self.deleteHostPermissions(ctx, hostname))
        d.addErrback(self.ignoreError)

        # Revoke certificates, fail unregistration in case of failure
        d.addCallback(lambda x:self.core.callService(ctx, 'nupki', 'listServerCerts', PKI_NAME))
        d.addErrback(self.ignoreError)
        d.addCallback(self.deleteHostCerts, ctx, hostname + '-server')
        d.addCallback(lambda x:self.core.callService(ctx, 'nupki', 'listClientCerts', PKI_NAME))
        d.addErrback(self.ignoreError)
        d.addCallback(self.deleteHostCerts, ctx, hostname)
        d.addErrback(self.ignoreError)
        d.addCallback(self.deleteHostConfig, hostname)
        d.addErrback(self.ignoreError)
        return d

    def deleteHostConfig(self, unused, hostname):
        self.firewalls[hostname].erase_config()
        del self.firewalls[hostname]
        self.config.delete("firewalls", hostname)
        self.config.save(self.config_path)
        self.info('Unregistration successfull %s' % hostname)
        return True

    def deleteHostCerts(self, cert_list, ctx, hostname):
        d = succeed('done')

        for cert in cert_list:
            if cert[2] == hostname:
                d.addCallback(lambda x: self.core.callService(ctx, 'nupki', 'revokeCert', PKI_NAME, hostname))
        return d

    def deleteHostPermissions(self, ctx, hostname):
        # Remove the host from all groups:
        new_groups = deepcopy(self.acl_hosts_groups)
        for grp in new_groups:
            if hostname in new_groups[grp]:
                new_groups[grp].remove(hostname)
        self.service_setHostsGroup(ctx, new_groups)

    ###########################
    ### Categories handling

    def service_setFirewallCategories(self, ctx, firewall, categories):
        try:
            fw = self.firewalls[firewall]
        except KeyError:
            raise RpcdError("Firewall '%s' does not exist." % firewall)
        fw.categories = categories
        fw.save()
        return True

    def service_getFirewallCategories(self, ctx, firewall):
        try:
            fw = self.firewalls[firewall]
        except KeyError:
            raise RpcdError("Firewall '%s' does not exist." % firewall)
        return fw.categories

    def service_delCategories(self, ctx, category):
        for fw in self.firewalls.values():
            if category in fw.categories.keys():
                self.config.delete('firewalls', fw.name, 'categories', category)
                fw.categories.pop(category)
        self.categories_order.remove(category)
        self.categories.pop(category)
        self.config.delete('categories', category)
        for x, cat in enumerate(self.categories_order):
            if cat == category:
                self.config.delete('categories_order', str(x))
        return True

    def service_setCategories(self, ctx, categories, categories_order):
        self.categories = categories
        self.categories_order = categories_order
        for key, val in categories.iteritems():
            self.config.set('categories', key, val)

        self.config.delete('categories_order')
        for x, category in enumerate(categories_order):
            self.config.set('categories_order', str(x), category)

        self.config.save(self.config_path)

        return True

    def service_getCategories(self, ctx):
        return self.categories, self.categories_order

    def service_registerSubComponent(self, ctx, component_name):
        self.subcomponents.append(component_name)

    ###########################
    ### ACL handling
    def refreshHostAcls(self, ctx, host, user_group):
        roles = {}
        d = succeed('done')

        # Find the groups in which this host is:
        for grp in self.acl_hosts_groups:
            if host in self.acl_hosts_groups[grp]:
                if user_group:
                    user_list = [ user_group ]
                else:
                    user_list = self.acl_groups_roles[grp].keys()

                for user in user_list:
                    if user in self.acl_groups_roles[grp]:
                        # keep track of registered roles
                        if user not in roles:
                            roles[user] = []

                        for role in self.acl_groups_roles[grp][user]:
                            if not role in roles[user]:
                                d.addCallback(make_lambda_x(self.core.callService, ctx, 'multisite_transport', 'setAcl', user, role, host))
                                roles[user].append(role)

        for user in roles.keys():
            for role in list(self.roles_list - set(roles[user])):
                d.addCallback(make_lambda_x(self.core.callService, ctx, 'multisite_transport', 'deleteAcl', user, role, host))
        return d

    def service_refreshAcls(self, ctx, user_group, host_group):
        d = succeed('done')
        for host in self.acl_hosts_groups[host_group]:
            d.addCallback(make_lambda_x(self.refreshHostAcls, ctx, host, user_group))
        return d

    def service_listHostsGroups(self, ctx):
        """
        Returns the list of all hosts groups defined
        """
        return self.acl_hosts_groups

    def service_setHostsGroup(self, ctx, groups):
        """
        Set the list of hosts for a group
        group_name : name of the group
        hosts : list of hosts
        """
        modified_hosts = set()
        d = succeed('done')

        for group in groups.keys():
            # create new roles list
            if group not in self.acl_groups_roles.keys():
                self.acl_groups_roles[group] = {}
            else:
                # Check if a host has been deleted or added
                previous_set = set(self.acl_hosts_groups[group])
                new_set = set(groups[group])

                modified_hosts |= previous_set ^ new_set

                # erase acls of deleted hosts
                for host in (previous_set - new_set):
                    for user in self.acl_groups_roles[group]:
                        for role in self.roles_list:
                            d.addCallback(make_lambda_x(self.core.callService, ctx, 'multisite_transport', 'deleteAcl', user, role, host))

        # delete deprecated roles list
        for group in self.acl_groups_roles.keys():
            if group not in groups:
                modified_hosts |= set(self.acl_hosts_groups[group])

                # erase acls of deleted groups
                for host in self.acl_hosts_groups[group]:
                    for user in self.acl_groups_roles[group]:
                        for role in self.roles_list:
                            d.addCallback(make_lambda_x(self.core.callService, ctx, 'multisite_transport', 'deleteAcl', user, role, host))
                del self.acl_groups_roles[group]

        self.acl_hosts_groups = groups

        for host in modified_hosts:
            d.addCallback(make_lambda_x(self.refreshHostAcls, ctx, host, None))
        d.addCallback(lambda x:self.saveAcl())
        return d

    def service_getHostsGroupAcl(self, ctx, filter_group, filter_role, group_name):
        """
        Returns the list of hosts in the group
        group_name : name of the group
        """
        lst = []

        for user in self.acl_groups_roles[group_name]:
            if filter_group and filter_group != user:
                continue

            for role in self.acl_groups_roles[group_name][user]:
                if filter_role and filter_role != role:
                    continue

                lst.append([0, user, role])

        return lst

    def service_setHostsGroupAcl(self, ctx, group_name, user_group, role):
        """
        Returns the roles for a particular user group/host group
        group_name : name of the group
        user_group : name of the user group
        role : role to set
        """
        if user_group not in self.acl_groups_roles[group_name]:
            self.acl_groups_roles[group_name][user_group] = []
        if role not in self.acl_groups_roles[group_name][user_group]:
            self.acl_groups_roles[group_name][user_group].append(role)

        #for host in self.acl_hosts_groups[group_name]:
        #    d.addCallback(make_lambda_x(self.core.callService, ctx, 'multisite_transport', 'setAcl', user_group, role, host))

        return self.saveAcl()

    def service_deleteHostsGroupAcl(self, ctx, group_name, user_group, role):
        """
        Set roles for a particular user group/host group
        group_name : name of the group
        user_group : name of the user group
        role : role to delete
        """
        if user_group in self.acl_groups_roles[group_name] and role in self.acl_groups_roles[group_name][user_group]:
            self.acl_groups_roles[group_name][user_group].remove(role)

        return self.saveAcl()

    def saveAcl(self, *args):
        self.config.delete('acl_hosts_groups')
        self.config.delete('acl_groups_roles')

        cfg_group = {}
        cfg_roles = {}
        for group in self.acl_hosts_groups.keys():
            cfg_group[group] = list2dict(self.acl_hosts_groups[group])

        # delete deprecated roles list
        for group in self.acl_groups_roles.keys():
            cfg_roles[group] = {}
            for user in self.acl_groups_roles[group]:
                cfg_roles[group][user] = list2dict(self.acl_groups_roles[group][user])

        self.config.set('acl_hosts_groups', cfg_group)
        self.config.set('acl_groups_roles', cfg_roles)
        self.config.save(self.config_path)

