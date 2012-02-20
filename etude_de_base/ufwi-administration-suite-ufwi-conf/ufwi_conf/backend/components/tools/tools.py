#coding: utf-8
"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           François Toussenel <ftoussenel AT edenwall.com>

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

from __future__ import with_statement

import subprocess
from shutil import rmtree
from twisted.internet.threads import deferToThread
from twisted.internet.defer import inlineCallbacks, returnValue

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.common.process import createProcess, communicateProcess
from ufwi_rpcd.common.validators import check_ip_or_domain
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.backend.process import runCommand, DEFAULT_TIMEOUT

from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.backend.unix_service import runCommandAndCheck
from .error import CreateDiagFailed

if EDENWALL:
    from ufwi_ruleset.localfw.wrapper import LocalFW

    from .vpn import (isVpnSupportRunningOrPending, vpnrules, vpn_support_last,
        getVpnSupportStatusAndIP)
    from .factory_defaults import (askFactoryDefault, is_factory_default_asked,
        cancel_factory_default)

RESTARTABLE_SERVICES = frozenset(('ntp', 'nuauth', 'ufwi_rpcd-server',
                                  'winbind'))

class ToolsComponent(AbstractNuConfComponent):
    """
    Component that provides various utilities services
    - restart ufwi_rpcd
    - reboot system
    - halt system
    - create the diagnostic file

    - ping
    - traceroute
    - halt system
    - reboot system
    - search in the logs (TODO)
    - start/stop/query the VPN support
    """
    NAME = "tools"
    VERSION = "1.0"
    ACLS = {
        'localfw': set(('addFilterIptable', 'apply', 'clear', 'close',
                        'open')),
        'network': set(('getNetconfig',)),
        'ufwi_ruleset': set(('open', 'reapplyLastRuleset',)),
    }
    ROLES = {
        'conf_read': set((
                'runPing',
                'runTraceroute',
                'getDiagnosticFile',
                'getArpTable',
                'getRoutingTable',
                'getVpnSupportStatusAndIP',
                'getVpnSupportLastConnections',
                'isFactoryDefaultAsked')),
        'conf_write': set((
                'askFactoryDefault',
                'cancelFactoryDefault',
                'rebootSystem',
                'haltSystem',
                'restartNucentral',
                'restartService',
                'vpnSupport'))
    }

    CONFIG_DEPENDS = ()

    def read_config(self, *unused):
        pass

    def apply_config(self, *unused):
        pass

    def checkServiceCall(self, context, service_name):
        if 'rebootSystem' == service_name \
        and context.isComponentContext() \
        and 'config' == context.component.name:
            # config component doesn't need a lock to reboot the system
            return
        AbstractNuConfComponent.checkServiceCall(self, context, service_name)

    # Services:

    if EDENWALL:
        def service_isFactoryDefaultAsked(self, context):
            return is_factory_default_asked()

        def service_askFactoryDefault(self, context):
            return askFactoryDefault()

        def service_cancelFactoryDefault(self, context):
            return cancel_factory_default()

    def service_rebootSystem(self, context):
        """
        Reboot the system
        """
        if context.isComponentContext:
            runCommandAndCheck(self, '/sbin/reboot')
            return

        defer = self.core.callService(context, 'session', 'destroy')
        defer.addCallback(lambda unused: runCommandAndCheck(self, '/sbin/reboot'))
        # don't return defer

    def service_haltSystem(self, context):
        """
        destroy current session and halt the system
        """
        defer = self.core.callService(context, 'session', 'destroy')
        defer.addCallback(lambda unused: runCommandAndCheck(self, '/sbin/halt'))
        # don't return defer

    if EDENWALL:
        def service_getDiagnosticFile(self, context):
            """
            Return a diagnostic file, containing the result of various command
            """
            process = createProcess(self,
                '/usr/share/ufwi_rpcd/scripts/diagnostic',
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, locale=False)

            return_code, out, err = communicateProcess(self, process, DEFAULT_TIMEOUT)
            if return_code != 0:
                raise CreateDiagFailed(err)

            tmp_dir = out[0].strip()
            with open(tmp_dir + "/diagnostic.tar.gz") as fd:
                result = encodeFileContent(fd.read())
            try:
                rmtree(tmp_dir)
            except Exception, err:
                self.error(
                    'Could not delete temporary diagnostic directory (%s).',
                    err)
            return result

    def service_restartNucentral(self, context):
        """
        Restart ufwi_rpcd
        """
        runCommand(self, ['/etc/init.d/ufwi_rpcd-server', 'restart'])

    def service_restartService(self, context, service):
        """
        Restart a "restartable" service.
        """
        if service in RESTARTABLE_SERVICES:
            runCommand(self, ['/etc/init.d/%s' % service, 'restart'])
            return True
        else:
            return False

    if EDENWALL:
        def service_vpnSupport(self, context, action):
            """
            Start or stop the VPN support.

            We do not use the term 'enabled' because the VPN will not be started
            on boot.
            """
            if not action in ['start', 'stop']:
                return False
            if action == 'start':
                return self._startvpn()
            elif action == 'stop':
                return self._stopvpn()

        @inlineCallbacks
        def _stopvpn(self):
            yield deferToThread(vpnrules, self, False)

            localfw = LocalFW('vpn_support')
            # don't create any rule: just clear existing rules
            context = Context.fromComponent(self)
            try:
                yield localfw.execute(self.core, context)
            except Exception, err:
                self.writeError(err,
                    'Error while disabling firewall rules for the VPN support')
                raise

        @inlineCallbacks
        def _startvpn(self):
            if isVpnSupportRunningOrPending(self):
                returnValue(False)
            yield deferToThread(vpnrules, self, True)

            localfw = LocalFW('vpn_support')
            localfw.call('addFilterIptable', False, '-I FORWARD -i support -j DROP')
            localfw.call('addFilterIptable', False, '-I INPUT -i support -p udp --dport 8080 -j ACCEPT')
            for dport in ["8443", "22"]:
                localfw.call('addFilterIptable', False,
                             '-I INPUT -i support -p tcp --dport %s -j ACCEPT' % dport)

            context = Context.fromComponent(self)
            try:
                yield localfw.execute(self.core, context)
            except Exception, err:
                self.writeError(err,
                    'Error while enabling firewall rules for the VPN support')
                raise

        def service_getVpnSupportStatusAndIP(self, context):
            return getVpnSupportStatusAndIP(self)

        def service_getVpnSupportLastConnections(self, context):
            """
            Limited log: return the last few connections.
            """
            return vpn_support_last(self)

    # OLD CODE BELOW
    def runPipe(self, *arguments):
        return deferToThread(self._runPipe, arguments)

    def _runPipe(self, arguments):
        process = subprocess.Popen(arguments,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT)
        return process.communicate()[0]

    def service_runPing(self, context, target):
        """
        Ping the specified address
         - target : a ip or a hostname that should be probed

        return the output of the command
        """
        if not check_ip_or_domain(target):
            raise ValueError()
        return self.runPipe("/bin/ping", "-c", "4", target)

    def service_runTraceroute(self, context, target):
        """
        Trace the network route to the specified address
         - target : a ip or a hostname that should be probed

        return the output of the command
        """
        if not check_ip_or_domain(target):
            raise ValueError()
        return self.runPipe("/usr/bin/traceroute", target)

    # TODO parser et renvoyer un truc plus moins brut de fonderie ?
    def service_getArpTable(self, context):
        """
        Return the arp table
        """
        return self.runPipe("/usr/sbin/arp", "-n")

    def service_getRoutingTable(self, context):
        """
        Return the routing table
        """
        return self.runPipe("/sbin/route", "-n")
