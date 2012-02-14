#coding: utf-8
"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
Written by Pierre Chifflier <chifflier AT inl.fr>

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

$Id$
"""

from __future__ import with_statement

from grp import getgrnam
from os import chmod, chown, close
from os.path import isabs, join as path_join
from pwd import getpwnam
from stat import (
    S_IRGRP, # readable by group
    S_IRUSR, # readable by owner
    S_IWUSR) # writable by owner
from subprocess import PIPE, STDOUT
from tempfile import mkstemp
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
import errno
import IPy
import os

from ufwi_rpcd.common.human import typeName
from ufwi_rpcd.common.process import (getPidByName, formatCommand,
    createProcess, communicateProcess)
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcd.common.validators import check_hostname, check_ip, check_port, check_domain
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import RpcdError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.process import (runCommand, DEFAULT_TIMEOUT,
    set_enabled_in_runit)
from ufwi_rpcd.core.config.responsible import CONFIG_MODIFICATION
from ufwi_rpcd.core.context import Context

from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent

class StartStopError(RpcdError):
    pass

class OwnerSettingError(RpcdError):
    pass

class RunCommandError(RpcdError):
    """
    args : command, status, output
    """
    def __init__(self, command, status, output):
        RpcdError.__init__(self,
            tr('Command "%s" failed (exit code %s):\n%s'),
            command, status, output)
        self.command = command
        self.status = status
        self.output = output

def getInitRank(name, value):
    if not isinstance(value, int) or not (0 <= value <= 99):
        raise ValueError("Expected an integer between 0 and 99 for parameter '%s'" % name)
    return value

def _getEnabled(value):
    if not isinstance(value, bool):
        raise ValueError("Expected a boolean value for ON/OFF state, got %s" % typeName(value))
    return value

def runCommandAndCheck(logger, command, timeout=DEFAULT_TIMEOUT, **popen_args):
    # Return (process, stdout) where stdout is a list of unicode strings
    popen_args.update({'stdout': PIPE, 'stderr': STDOUT})
    cmdstr = formatCommand(command)

    process = createProcess(logger, command, **popen_args)
    status, stdout, stderr = communicateProcess(logger, process, timeout)

    if status:
        output = u'\n'.join(stdout)
        raise RunCommandError(cmdstr, unicode(status), output)
    else:
        command_str = popen_args.get('cmdstr', command)
        logger.debug("Success : '%s'" % unicode(command_str))

    return process, stdout

class UnixServiceComponent(AbstractNuConfComponent):
    """Class to derive to implement a component managing
    a unix service.

    Note on service_status protocol implemented by UnixServiceComponent:
    PIDFILE is preferred; then EXE_NAME.

    If not overriding apply_config, you need to implement
    * a should_run method, taking responsible, returning a boolean
    * a genConfigFiles method, taking no arg, possibly returning a defer

    HARD_STOP_REQUIRED: set to True if you want a "kill -9 EXE_NAME" command
    issued when init script is not stopping the process correctly
    """
    NAME = "Unix Service"
    INIT_SCRIPT = '/bin/false'
    _DEFAULT_RUNLEVEL = 2
    PIDFILE = None
    EXE_NAME = None
    HARD_STOP_REQUIRED = False
    EXE_CAN_RELOAD = False

    INITRANK_S = 20
    INITRANK_K = None

    ROLES = {
        'conf_read': set(('getEnabledOnBoot', 'getPorts', 'status',)),
        'conf_write': set(('reload', 'restart', 'start', 'stop',
            'setEnabledOnBoot',
        )),
        'multisite_read': set(),
        'multisite_write': set(("@multisite_read",)),
    }

    REQUIRES = ('access',)

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        # do not place this as a static declaration, this will be overidden by others
        if not os.path.exists(self.get_initscript()):
            raise RpcdError(tr("The %s initialization script is not present"), self.get_initscript())

    def checkServiceCall(self, context, service_name):
        """Allow each component to call their reload, restart, start and stop services"""
        if (context.isComponentContext() and context.ownerString() == self.NAME
          and service_name in ['reload', 'restart', 'start', 'status', 'stop']):
            return

        AbstractNuConfComponent.checkServiceCall(self, context, service_name)

    def get_initscript(self):
        if isabs(self.INIT_SCRIPT):
            return self.INIT_SCRIPT
        else:
            return path_join("/etc/init.d", self.INIT_SCRIPT)

    def gen_actionCommand(self, action):
        """
        returns a tuple like ("/etc/init.d/ntp", "start"),
        if component is ntp and action start.
        """
        return (self.get_initscript(), action)

    def get_ports(self):
        # list of dict with keys:
        #  - proto: protocol number
        #  - port: destination port number (proto='tcp' or proto='udp')
        #  - icmp_type: ICMP type (proto='icmp')
        #
        # eg. [{'proto':'tcp', 'port': 8443}, {'proto':'icmp', 'icmp_type': 8}]
        return []

    def startstopManager(self, action):
        """
        factorisation for init scripts management, action should be one of start, stop, restart, reload

        Closes/Opens ports, starts/stop/etc the service.
        Behaviour :
           If it is a service by itself (no attribute MASTER_SERVICE):
             action the daemon (avoiding unnecessary start/stop)
           Else if the master daemon is not in the expected state already:
               action the master daemon

        see class docstring about cls.HARD_STOP_REQUIRED
        """
        START_ACTIONS = ("start", "restart", "reload")

        expected = "undefined"

        if action not in START_ACTIONS:
            expected = ServiceStatusValues.STOPPED

        if action == "start":
            expected = ServiceStatusValues.RUNNING

        daemon_status = self._status()
        if daemon_status == expected:
            self.debug("'%s' already in state '%s'" % (self.NAME, expected))
            return

        init_script = self.get_initscript()
        assert init_script is not None, "init_script not specified"
        command = "%s %s" % (init_script, action)
        try:
            runCommandAndCheck(self, command.split())
        except RunCommandError:
            if action == 'stop' and self.HARD_STOP_REQUIRED and self.EXE_NAME:
                self.error(
                    "Could not stop %s normally, killing it." % self.EXE_NAME
                    )
                command = 'killall -9 %s' % self.EXE_NAME
                runCommand(self, command.split())
            else:
                raise

    def set_enabled_in_runit(self, enabled, service):
        return set_enabled_in_runit(self, enabled, service)

    def service_reload(self, context):
        """ Reload the service, return None if ok else raise RunCommandError"""
        self.startstopManager("reload")

    def service_restart(self, context):
        """ Restart the service, return None if ok else raise RunCommandError"""
        self.startstopManager("restart")

    def service_start(self, context):
        """ starts the service, return None if ok else raise RunCommandError"""
        self.startstopManager("start")

    def service_stop(self, context):
        """ stops the service, return None if ok else raise RunCommandError"""
        self.startstopManager("stop")

    def service_setEnabledOnBoot(self, context, enabled, S=20, K=None):
        """
        Enable/disable the service on boot

        enabled: True/False
        S=20 - expects integer
        K=S
        """

        return self.setEnabledOnBoot(enabled, S=S, K=K)

    def setEnabledOnBoot(self, enabled, S=None, K=None):
        """
        See doc of service_setEnabledOnBoot
        """
        S = self.get_initrank_s(S)
        K = self.get_initrank_k(K, S)

        enabled = _getEnabled(enabled)

        values = {
            'S': S,
            'K': K,
            'initscript': self.INIT_SCRIPT,
        }

        #first always disabling
        command = "/usr/sbin/update-rc.d -f %(initscript)s remove" % values
        runCommandAndCheck(self, command.split())
        if not enabled:
            return

        command = "/usr/sbin/update-rc.d -f %(initscript)s defaults %(S)d %(K)d" % values
        runCommandAndCheck(self, command.split())

    def get_initrank_s(self, S):
        if S is not None:
            return getInitRank('S', S)

        return self.INITRANK_S

    def get_initrank_k(self, K, S):
        if K is not None:
            return getInitRank('K', K)

        if self.INITRANK_K is not None:
            return self.INITRANK_K

        if S is not None:
            return S

        return 20


    @abstractmethod
    def should_run(self, responsible):
        """
        Subclasses not overriding apply_config must implement
        this method and return a boolean
        """
        pass

    @inlineCallbacks
    @abstractmethod
    def genConfigFiles(self, responsible):
        """
        Subclasses not overriding apply_config must implement
        this method and may return a defer
        """
        pass

    @inlineCallbacks
    def apply_config(self, responsible, arg, modified_paths):
        """
        If not overriding this, see class docstring
        """
        # deferToThread because of multiple commands being ran
        # This checks the daemon is down
        yield deferToThread(self.startstopManager, 'stop')

        should_run = yield self.configure(responsible)

        if should_run:
            yield deferToThread(self.startstopManager, 'start')

    @inlineCallbacks
    def configure(self, responsible):
        """
        All configuration stuff done here.
        return value of should_run method
        """
        yield self.genConfigFiles(responsible)
        should_run = self.should_run(responsible)
        yield deferToThread(self.setEnabledOnBoot, should_run)
        returnValue(should_run)

    def service_getEnabledOnBoot(self, context):
        """ Return true if the service is enabled on boot """
        for i in os.listdir("/etc/rc%s.d" % self._DEFAULT_RUNLEVEL):
            # 3: to remove the Sxx or Kxx from script name
            if i[3:] == self.INIT_SCRIPT and i[0] == 'S':
                return True
        return False

    def service_getPorts(self, context):
        return self.get_ports()

    def logService(self, context, logger, service, text):
        if service in ('status', 'getPorts'):
            logger.debug(context, text)
        else:
            logger.info(context, text)

    def _checkPid(self, text):
        text = text.rstrip()
        try:
            pid = int(text)
        except ValueError:
            # Invalid number (eg. empty text)
            return ServiceStatusValues.STOPPED
        try:
            #This kill -0 does nothing to the target.
            #Success means the component is running. (else clause)
            #OSError mean either:
            # -process not running (stopped)
            # -not allowed to kill (running)
            # - ??
            #
            os.kill(pid, 0)
        except OSError, err:
            if err.errno == errno.ESRCH:
                return ServiceStatusValues.STOPPED
            elif err.errno == errno.EPERM:
                return ServiceStatusValues.RUNNING
            else:
                #TODO: unexpected (can we get another errno here ?)
                raise
        else:
            return ServiceStatusValues.RUNNING

    def service_status(self, context):
        """
        If PIDFILE is set as a class attribute, we try and locate the process.
        kill with signal 0 does nothing if successful
        if unsuccessfull, errno must be checked.
        """
        return (self.NAME, self._status())

    def _status(self):
        status = ServiceStatusValues.STATUS_NOT_IMPLEMENTED

        if self.PIDFILE is None:
            #Fallback: EXE_NAME
            if self.EXE_NAME:
                pidsGenerator = getPidByName(self.EXE_NAME)
                try:
                    pidsGenerator.next()
                except StopIteration:
                    status = ServiceStatusValues.STOPPED
                except Exception, err:
                    self.warning(err)
                else:
                    status = ServiceStatusValues.RUNNING
        else:
            try:
                with open(self.PIDFILE) as pidfile:
                    text = pidfile.readline()
            except IOError:
                status = ServiceStatusValues.STOPPED
            else:
                status = self._checkPid(text)
        return status

class ConfigServiceComponent(UnixServiceComponent):

    # (misc) yes, using two times the configuration is bad, but this was done before
    # a config module existed. This should be removed later
    CONFIG = {}

    ROLES = {
        'ufwi_conf_read': set(('readConfiguration',)),
        'ufwi_conf_write': set((
            'checkConfiguration', 'saveConfiguration',
        )),
    }

    def check_mail(self, value):
        # the real regexp take 4 kb , will see later how we handle this
        return True

    def check_port(self, value):
        return check_port(value)

    def check_ip(self, value):
        return check_ip(value)

    def check_domain(self, value):
        return check_domain(value)

    def check_ip_or_domain(self, value):
        return self.check_ip(value) or self.check_domain(value)

    def check_ip_in_network(self, address, network):
        return IPy.IP(address) in IPy.IP(network)

    def check_hostname(self, value):
        return check_hostname(value)

    def check_boolean(self, value):
        return type(value) == type(True)

    def read_config(self, *args, **kwargs):
        try:
           self.CONFIG = self.core.config_manager.get(self.NAME)
        except ConfigError:
            self.debug("config not loaded, use default configuration")

    def save_config(self, message, context=None, action=CONFIG_MODIFICATION):
        with self.core.config_manager.begin(self, context, action=action) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                # Means the value does not exist in the first place
                pass
            cm.set(self.NAME, self.CONFIG)
            cm.commit(message)

    def get_template_variables(self):
        """ this can be override to provides more variable to the template """
        return self.CONFIG


    def service_checkConfiguration(self, context):
        self.verify_config()

    def verify_config(self):
        """ check the config. raise a Exception in case of problem """
        pass

    def service_saveConfiguration(self, context, message):
        self.save_config(message, context)

    def service_readConfiguration(self, context):
        self.read_config()

    def runCommandAsRootAndCheck(self, command):
        #FIXME: rename this function, because of course we are root but we don't
        #care of running sudo or ufwi_rpcd_sudo anymore.
        return runCommandAndCheck(self, command)

    @inlineCallbacks
    def ha_time_sync(self):
            context = Context.fromComponent(self)
            if not self.core.hasComponent(context, 'ha'):
                return
            try:
                yield self.core.callService(context, 'ha', 'syncTime')
            except Exception, err:
                self.writeError(err, "syncTime error")


def fix_strict_perms(user, group, filename):
    """
    Sets perms:
    owner: rw-
    group: r--
    other: ---
    """
    uid = getpwnam(user)[2]
    gid = getgrnam(group)[2]

    chown(filename, uid, gid)
    chmod(filename, S_IRUSR | S_IWUSR |S_IRGRP)

def getTempFileName():
    x = mkstemp()
    close(x[0])
    return x[1]

