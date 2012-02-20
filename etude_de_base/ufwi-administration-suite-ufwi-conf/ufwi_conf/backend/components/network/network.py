"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Michael Scherer <m.scherer AT inl.fr>
           Feth AREZKI <farezki AT inl.fr>

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

from os import remove
from os.path import join, exists
from shutil import copy, move
from twisted.internet.defer import inlineCallbacks, succeed
from twisted.internet.threads import deferToThread
import subprocess
from itertools import islice
from time import sleep

from ufwi_rpcd.common import tr
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.core.config.responsible import RESTORING_CONFIGURATION
from ufwi_rpcd.backend.transaction import executeTransactionsDefer
from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.process import createProcess, communicateProcess
from ufwi_rpcd.common.transaction import Transaction
from ufwi_rpcd.common.human import humanFilesize
from ufwi_rpcd.core.config.responsible import CONFIG_AUTOCONFIGURATION, \
    CONFIG_ERASURE, CONFIG_MODIFICATION
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend import NetCfgAutoConf
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.backend.output_parser import CmdError
from ufwi_conf.backend.unix_service import getTempFileName
from ufwi_conf.common.netcfg_rw import deserialize as deserializeNetCfg
from ufwi_conf.common.netcfg_rw import NetCfgRW
from ufwi_conf.common.net_exceptions import NetCfgError
from ufwi_conf.common.net_interfaces import Ethernet
if EDENWALL:
    from ufwi_conf.common import ha_statuses
    from ufwi_conf.backend.ha import readHaType, saveHaType
    ENOHA = ha_statuses.ENOHA
else:
    ENOHA = "ENOHA"

from .ethtool import Ethtool, NoSuchDevice, ERROR_KEY as ethtool_error_key
from .conf_writer import writeConf
from .conf_writer import isInterfaceSpecified
from .conf_writer import iterSpecifiedInterfaces
from .sanity import warn_dangerous_files
from .sanity import check_and_correct_lo

FIRST_APPLY_STAMP = '/var/lib/ufwi_rpcd/network_config_never_applied'
SECOND_APPLY_STAMP = '/var/lib/ufwi_rpcd/network_config_applied_once'
MASTER_KEY = 'network'
TIMEOUT = 5 * 60

MAX_SUPPORTED_ETHERNETS = 24

# TODO write route in the configfile
# check we cannot add twice the same interface

class InterfaceNotFound(Exception):
    pass

class NetworkNotFound(Exception):
    pass

class InvalidOperation(Exception):
    pass

class EthernetSpeedError(Exception):
    pass

def __out2str(out):
    if out is None:
        return ''
    return out.read()

def __stdoutAndStderr(process):
    return __out2str(process.stdout), __out2str(process.stderr)

def _ensureIfDown(ifname, ifconfig_output, logger):
    """
    Check if an interface is down (useful before ifup...)
    If it is not down, perform an ifdown on it
    """

    if "%s " % ifname not in ifconfig_output:
        logger.debug("Ok, %s is down as expected" % ifname)
        return

    logger.debug(
        "Found interface %s to be up. "
        "Setting it down prior to ifup it by safety" % ifname
        )
    command = '/sbin/ifdown %s' % ifname
    process = createProcess(logger,
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={})
    return_code, stdout, stderr = communicateProcess(logger, process, TIMEOUT)

    if return_code != 0:
        logger.error("Error while running '%s'.\n%s" % (command, '\n'.join(stdout)))
    else:
        logger.debug("...ok")

def _ensureIfsDown(interfaces_list, logger):
    command = "/sbin/ifconfig"
    process = createProcess(logger,
            command.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={})
    return_code, stdout, stderr = communicateProcess(logger, process, TIMEOUT)
    stdout, stderr = __stdoutAndStderr(process)
    if return_code != 0:
        output = '\n'.join(stdout)
        logger.critical("Error while running '%s'.\n%s" % (command, output))
        raise NetCfgError("Could not run ifconfig properly ?!\n%s" % output)
    ifconfig_output = stdout
    for ifname in interfaces_list.split():
        _ensureIfDown(ifname, ifconfig_output, logger)

def _speed_dict(netcfg):
    return dict(
        (
            ethernet.system_name,
            (
                ethernet.eth_auto,
                ethernet.eth_speed,
                ethernet.eth_duplex
            )
        )
        for ethernet in netcfg.iterEthernets()
        )

class ConfigFileTransaction(Transaction):
    """
    if current_netcfg is None : bring all interfaces down and next bring all
    known interfaces up
    """
    def __init__(self, responsible, netcfg, current_netcfg, config_file, component, ha_status):
        self.responsible = responsible
        self.current_netcfg = current_netcfg
        self.netcfg = netcfg
        self.component = component
        self.core = component.core
        self.ha_status = ha_status
        self.config_file = config_file
        self.temp_file = None
        self.backup_file = None
        for function_name in ('critical error warning info debug'.split()):
            setattr(self, function_name, getattr(component, function_name))

        if EDENWALL:
            self.prev_ha_status = readHaType(component.ufwi_conf_var_dir)
            self.debug("current HA state : %s (previous : %s)" % (self.ha_status, self.prev_ha_status))
        else:
            self.prev_ha_status = ENOHA

        self.down_interfaces, self.up_interfaces = self.changed_interfaces_names()
        self.speed_changed = self.changed_ethernets_speeds()

        self.critical("down_interfaces: %s " % self.down_interfaces)
        self.critical("up_interfaces: %s " % self.up_interfaces)

    def prepare(self):
        self.debug("Preparing network conf change: Writing network configuration (ha_status=%s)" % self.ha_status)
        self.temp_file = getTempFileName()
        self.backup_file = getTempFileName()
        writeConf(self.netcfg, self.temp_file, self.ha_status)
        if self.core.config.getboolean('CORE', 'use_edenwall'):
            warn_dangerous_files(self)

    def save(self):
        copy(self.config_file, self.backup_file)

    @inlineCallbacks
    def apply(self):
        if exists(FIRST_APPLY_STAMP):
            #the first apply comes after a discovery of linux net parameters
            #there is a dhclient running
            move(FIRST_APPLY_STAMP, SECOND_APPLY_STAMP)
        elif exists(SECOND_APPLY_STAMP):
            #The second application is made by a human being, maybe a confirmation
            #of what dhclient gave us, or not
            yield(self.killdhclients())
            remove(SECOND_APPLY_STAMP)
        yield self.stopNetwork()
        move(self.temp_file, self.config_file)
        yield self.startNetwork()
        self.setEthernetSpeeds()
        if EDENWALL:
            saveHaType(self.component.ufwi_conf_var_dir, self.ha_status)

    def _setethernetspeed(self, ethernet):
        if ethernet.eth_auto:
            cmd = "/usr/sbin/ethtool -s %s autoneg on" % ethernet.system_name
            self.responsible.feedback(
                tr("Setting up speed for interface %(DESCRIPTION)s: auto"),
                DESCRIPTION=ethernet.fullName()
                )
        else:
            args = {
            'name': ethernet.system_name,
            'duplex': "full" if ethernet.eth_duplex == Ethernet.FULL else "half",
            'speed': ethernet.eth_speed
            }
            cmd = "/usr/sbin/ethtool -s %(name)s autoneg off speed "\
                "%(speed)s duplex %(duplex)s" % args
            self.responsible.feedback(
                tr(
                    "Setting up speed for interface %(DESCRIPTION)s: "
                    "speed: %(SPEED)s, duplex: %(DUPLEX)s."),
                DESCRIPTION=ethernet.fullName(),
                SPEED=args['speed'],
                DUPLEX=args['duplex']
                )
        process = createProcess(self, cmd.split(),
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={})
        retcode, stdout, stderr = communicateProcess(self, process, 30)
        if retcode == 0:
            return
        else:
            self.responsible.feedback("Could not set speed.")
            #Explicitely catched
            raise EthernetSpeedError("Error while running [%s]." % cmd)

    def setEthernetSpeeds(self):
        for ethernet in self.speed_changed:
            self._setethernetspeed(ethernet)

    @inlineCallbacks
    def rollback(self):
        try:
            yield self.stopNetwork()
        except Exception:
            pass

        #Most important command: this allows us to reboot safely
        try:
            move(self.backup_file, self.config_file)
        finally:
            yield self.startNetwork()

        if EDENWALL:
            saveHaType(self.component.ufwi_conf_var_dir, self.prev_ha_status)

    def cleanup(self):
        try:
            if exists(self.temp_file):
                remove(self.temp_file)
            if exists(self.backup_file):
                remove(self.backup_file)
        except Exception:
            #exceptions forbidden here
            pass

    def _start_or_stopNetwork(self, unused, log_prefix, command):
        """
        Specify None for the unused arg when chaining as a deferred
        """
        return deferToThread(self._start_or_stopNetworkDefer, log_prefix, command)

    def _start_or_stopNetworkDefer(self, log_prefix, command):
        process = createProcess(self, command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            env={})
        retcode, stdout, stderr = communicateProcess(self, process, TIMEOUT)
        if not check_and_correct_lo(self):
            self.critical("Networking configuration problem. :-(")
        if retcode == 0:
            return
        for line in stdout:
            self.info("%s: %s" % (log_prefix, line))
            line_lower = line.lower()
            if (u'failed' in line_lower) or (u'error' in line_lower):
                raise ConfigError(line)

    def startNetwork(self):
        if not self.up_interfaces:
            return succeed(None)

        defer = deferToThread(_ensureIfsDown, self.up_interfaces, self)
        #ifup eth0, eth1, bond0, bond0.3
        command ='/sbin/ifup %s --verbose' % self.up_interfaces

        #When used as a callback, we don't need to supply the magical unused 'None'
        defer.addCallback(
            self._start_or_stopNetwork,
            'Start network (ifup)',
            command.split()
            )
        return defer

    def stopNetwork(self, *unused):
        if not self.down_interfaces:
            return succeed(None)
        command = '/sbin/ifdown %s --verbose' % self.down_interfaces
        return self._start_or_stopNetwork(None, 'Stop network (ifdown)', command.split())

    def killdhclients(self):
        for name in ('dhclient', 'dhclient3'):
            command = 'killall %s' % name
            process = createProcess(self,
                command.split(),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env={})
            return_code, stdout, stderr = communicateProcess(self, process, 20)
            if stdout:
                self.debug("stdout: %s" % '\n'.join(stdout))

    def changed_interfaces_names(self):
        down = ''
        up = ''

        if self.current_netcfg is None:
            #Down all interfaces, up all known interfaces
            for interface in self.netcfg.iterInterfaces():
                up += '%s ' % interface.system_name
            return '--exclude lo -a', up

        unchanged_interfaces = tuple(self.unchanged_interfaces_names())
        self.debug('unchanged interfaces : %s' % str(unchanged_interfaces))

        old_interfaces = tuple(
            iterSpecifiedInterfaces(self.current_netcfg, down=True)
            )

        new_interfaces = tuple(
            iterSpecifiedInterfaces(self.netcfg)
            )

        yielded = set()
        for interface in old_interfaces:
            name = interface.system_name
            if name not in unchanged_interfaces:
                children = list(self.current_netcfg.iterInterfaceChildrenNames(interface))
                children.reverse()
                for child in children:
                    if child not in yielded:
                        down += '%s ' % child
                        yielded.add(child)

        yielded = set()
        for interface in new_interfaces:
            name = interface.system_name
            if name not in unchanged_interfaces:
                for child in self.netcfg.iterInterfaceChildrenNames(interface):
                    if child not in yielded:
                        up += '%s ' % child
                        yielded.add(child)

        return down, up

    def changed_ethernets_speeds(self):
        if self.current_netcfg is None:
            #Reconfigure all known interfaces
            return tuple(self.netcfg.iterEthernets())

        old_values = _speed_dict(self.current_netcfg)
        new_values = _speed_dict(self.netcfg)

        result = []
        #iterate over new values, try and find old
        for ethernet in self.netcfg.iterEthernets():
            old_speed = old_values.get(ethernet.system_name, None)
            new_speed = new_values.get(ethernet.system_name, None)
            if old_speed != new_speed:
                result.append(ethernet)

        return result

    def unchanged_interfaces_names(self):
        yield 'lo'
        if self.current_netcfg is None:
            return

        #{'eth0': <Ethernet Interface...>, ...}
        current_interfaces, new_interfaces = (
            dict(
                (interface.system_name, interface)
                for interface in netcfg.iterInterfaces()
            )
            for netcfg in (
                self.current_netcfg,
                self.netcfg
            )
        )
        #sets of names of interfaces
        current_names = set(current_interfaces)
        new_names = set(new_interfaces)

        #intersection of system names pre selects cadidates
        pre_result = current_names & new_names
        for name in pre_result:
            current, new = current_interfaces[name], new_interfaces[name]
            if current.equalsSystemWise(new, ha_state=(self.ha_status, self.prev_ha_status)) and isInterfaceSpecified(current):
                yield name
            elif (not isInterfaceSpecified(current)) and (not isInterfaceSpecified(new)):
                yield name

class NetworkComponent(AbstractNuConfComponent):
    """
    Component to manage the network, the routing table
    """
    NAME = "network"
    VERSION = "1.0"

    REQUIRES = ('config', 'ufwi_conf')
    ACLS = {
        'ha': frozenset(('getHAMode',)),
        'nuauth': frozenset(('restartWinbind',)),
    }
    ROLES = {
        'ruleset_write': frozenset(('getNetconfig',)),
        'multisite_read': frozenset(('getNetconfig',)),
        'multisite_write': frozenset(('@multisite_read',)),
        'conf_read': frozenset((
            'getNetconfig',
            'ethtool_show_ring', 'ethtool_show_ring_all', 'ethtool_statistics',
            'ethtool_statistics_all', 'ethtool_nooptions',
            'ethtool_nooptions_all', 'ethtool_digest_all',
        )),
        'conf_write': frozenset((
            'autoconf', 'clearConf', 'setNetconfig',
        )),
        'dpi_write': frozenset(('getNetconfig',))
    }

    CONFIG_DEPENDS = ()

    NETWORK_FILE = '/etc/network/interfaces'

    def __init__(self):
        AbstractNuConfComponent.__init__(self)
        self.config_loaded = False
        self.var_dir = None
        self.ufwi_conf_var_dir = None
        self.context = None
        self.__during_ha_import = False
        self.__config_before_ha_import = None

    def setCfgValue(self, path, key, value, config_manager):
        path = path + (key, value)
        config_manager.set(*path)

    def getCfgValue(self, name, section, key):
        return self.core.config_manager.getValue(*(name + (section, key)))

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        self.context = Context.fromComponent(self)
        self.var_dir = self.core.config.get('CORE', 'vardir')
        self.ufwi_conf_var_dir = join(self.var_dir, 'ufwi_conf')
        if self.core.config.getboolean('CORE', 'use_edenwall'):
            warn_dangerous_files(self)
        if not check_and_correct_lo(self):
            self.critical("Networking configuration problem. :-(")

        self.core = core
        self.ethtool = Ethtool('/usr/sbin/ethtool', self)

        if not self.config_loaded:
            self.autoconf()
            self.save_config(
                    CONFIG_AUTOCONFIGURATION,
                    "network : auto configuration",
                    self.context
                    )
        else:
            self.info("not autoconfiguring")

        self.core.notify.connect('ha', 'ImportStart', self.__haImportStart)
        self.core.notify.connect('ha', 'ImportEnd', self.__haImportEnd)

    def __haImportStart(self, cb_context):
        self.__during_ha_import = True
        #save the config before we overwrite it!
        #This config will only be used to calculate if we should or not
        #attempt an AD join
        self.__config_before_ha_import = self.netcfg.serialize()

    def __haImportEnd(self, cb_context):
        self.__during_ha_import = False
        self.__config_before_ha_import = None

    def apply_config(self, responsible, trigger_module, trigger_keys):
        self.debug("Network module asked to reload, with args %s" % ", ".join(unicode(item) for item in (responsible.trace_message(), trigger_module, trigger_keys)))
#        optim = not responsible.implies_full_reload()
        if responsible.action is RESTORING_CONFIGURATION:
            optim = False
        else:
            optim = True
        return self.apply(responsible, optim=optim)

    def rollback_config(self, responsible, trigger_module, trigger_keys):
        self.debug("Network module asked to rollback, with args %s" % ", ".join(unicode(item) for item in (responsible.trace_message(), trigger_module, trigger_keys)))
        return self.apply(responsible, optim=False)

    def autoconf(self):
        self.error(u"Discovering network config")
        self.netcfg = NetCfgAutoConf(parent=self)
        self.netcfg.discover()
        self.config_loaded = True

    def service_autoconf(self, context):
        self.autoconf()
        message = "Network auto config requested by %s" % context.ownerString()
        self.save_config(
            CONFIG_AUTOCONFIGURATION,
            message,
            context
            )

    def service_clearConf(self, context, message):
        with self.core.config_manager.begin(
                self,
                context,
                action=CONFIG_ERASURE
                ) as cm:
            try:
                cm.delete(MASTER_KEY)
            except ConfigError, err:
                self.debug(u"While clearing config: %s" % err)
                cm.revert()
            else:
                cm.commit(message)

    def read_config(self, responsible, *args, **kwargs):
        #responsible can be none
        need_autoconf = False

        try:
            config = self.core.config_manager.get(self.NAME)
        except ConfigError, err:
            self.important("Unable to load network configuration (%s)" % err)
            return

        ok = True
        try:
            netcfg = deserializeNetCfg(config, NetCfgAutoConf, parent=self)
        except NetCfgError, err:
            #FIXME: Try and fix structure when applicable instead of autoconfiguring
            need_autoconf = True
            self.writeError(err, title="Unable to load network configuration (%s): "
                "error while loading %s from configuration" % self.NAME)
            ok = False
        except DatastructureIncompatible, err:
            #FIXME: Upgrade structure when applicable instead of autoconfiguring
            need_autoconf = True
            self.important("Unable to load network configuration (%s): "
            "cannot deal with this unknown datastructure version" % err)
            ok = False

        if ok:
            ok, msg = netcfg.isValidWithMsg()

        if ok:
            self.netcfg = netcfg
        else:
            self.critical("Read invalid configuration!")
            #TODO: could we make a netcfg.autofix() ?
            need_autoconf = True

        if need_autoconf:
            self.autoconf()

        self.info("Config loaded")
        if len(self.netcfg):
            #some interface(s) found
            self.config_loaded = True

    def save_config(self, action, message=None, context=None):
        self.debug("Saving network config")

        if message is None:
            message = "Default network message"

        if context is None:
            context = self.context
        with self.core.config_manager.begin(self, context, action=action) as cm:
            try:
                cm.delete(MASTER_KEY)
            except ConfigError:
                pass

            serialized = self.netcfg.serialize()
            cm.set(MASTER_KEY, serialized)
            cm.commit(message)

        self.info("Network config saved")

    def __previous_config(self):
        """
        Finds the running config or returns None
        """
        if self.__during_ha_import:
            return self.__config_before_ha_import
        try:
            return self.core.config_manager.get(
                self.NAME,
                which_configuration='applied'
                )
        except (KeyError, ConfigError):
            return None

    @inlineCallbacks
    def apply(self, responsible, optim=True):
        ha_status = ENOHA
        if EDENWALL:
            try:
                ha_status = yield self.core.callService(self.context, 'ha', 'getHAMode')
            except Exception, err:
                self.error(exceptionAsUnicode(err))

        current_config = None
        if optim:
            #When 'not optim' (ie. in a rollback), we have lost the config
            #whose application was tried.
            current_config = self.__previous_config()
        if current_config is None:
            current_netcfg = NetCfgRW()
        else:
            current_netcfg = deserializeNetCfg(current_config, NetCfgAutoConf, parent=self)

        transaction = ConfigFileTransaction(
            responsible,
            self.netcfg,
            current_netcfg,
            self.NETWORK_FILE,
            self,
            ha_status
            )
        transactions = (transaction,)
        yield executeTransactionsDefer(self, transactions)
        yield deferToThread(sleep, 2)
        yield self.core.callService(self.context, 'nuauth', 'restartWinbind')

    def service_getNetconfig(self, context):
        """
        Returns a serialized NetCfg object.
        See netcfg.py, especially deserializeNetCfg()
        """
        return self.netcfg.serialize()

    def service_setNetconfig(self, context, netcfg, message):
        """
        Overrides the network configuration.
        Argument: a serialized NetCfg.
        Deserialization takes care of integrity testing, or should.
        """
        netcfg = deserializeNetCfg(netcfg)
        ok, errmsg = netcfg.isValidWithMsg()
        if not ok:
            raise NetCfgError(errmsg)
        #if netcfg == self.netcfg:
        #    return
        self.netcfg = netcfg
        self.save_config(CONFIG_MODIFICATION, message, context)

    def service_ethtool_show_ring(self, context, interfaces_names):
        result = {}
        for interface_name in islice(interfaces_names, 0, MAX_SUPPORTED_ETHERNETS):
            try:
                result[interface_name] = self.ethtool.ethtool_show_ring(interface_name)
            except NoSuchDevice:
                pass
            except CmdError, err:
                result[interface_name] = self.ethtool.formatError(err)
        return result

    def service_ethtool_show_ring_all(self, context):
        interfaces_names = [iface.name for iface in self.netcfg.iterIfaces()]
        return self.service_ethtool_show_ring(context, interfaces_names)

    def service_ethtool_statistics(self, context, interfaces_names):
        result = {}
        for interface_name in islice(interfaces_names, 0, MAX_SUPPORTED_ETHERNETS):
            try:
                result[interface_name] = self.ethtool.ethtool_statistics(interface_name)
            except NoSuchDevice:
                pass
            except CmdError, err:
                result[interface_name] = self.ethtool.formatError(err)
        return result

    def service_ethtool_statistics_all(self, context):
        interfaces_names = [iface.system_name for iface in self.netcfg.iterEthernets()][0:MAX_SUPPORTED_ETHERNETS]
        return self.service_ethtool_statistics(context, interfaces_names)

    def service_ethtool_nooptions(self, context, interfaces_names):
        result = {}
        for interface_name in islice(interfaces_names, 0, MAX_SUPPORTED_ETHERNETS):
            try:
                result[interface_name] = self.ethtool.ethtool_nooptions(interface_name)
            except NoSuchDevice:
                pass
            except CmdError, err:
                result[interface_name] = self.ethtool.formatError(err)
        return result

    def service_ethtool_nooptions_all(self, context):
        interfaces_names = [iface.system_name for iface in self.netcfg.iterEthernets()][0:MAX_SUPPORTED_ETHERNETS]
        return self.service_ethtool_nooptions(context, interfaces_names)

    def service_ethtool_digest_all(self, context):
        result = {}
        nooptions = self.service_ethtool_nooptions_all(context)
        statistics = self.service_ethtool_statistics_all(context)

        for iface in nooptions:

            nooptions_data = nooptions[iface]
            statistics_data = statistics[iface]

            nooptions_error = ethtool_error_key in nooptions_data
            statistics_error = ethtool_error_key in statistics_data
            if nooptions_error:
                #silently ignore here: likely not an ethernet iface
                continue

            speed = u"%s %s Duplex" % (
                nooptions_data[u'Speed'],
                nooptions_data[u'Duplex']
            )

            result[iface] = {}

            if statistics_error:
                stats = ()
            else:
                rx = statistics_data.get('rx_bytes')
                if rx is None:
                    stats = ()
                    continue
                rx = humanFilesize(statistics_data['rx_bytes'])
                tx = humanFilesize(statistics_data['tx_bytes'])
                if 'rx_errors' in statistics_data:
                    rx_errors = statistics_data['rx_errors']
                else:
                    rx_errors = statistics_data['rx_errors_total']
                if 'tx_errors' in statistics_data:
                    tx_errors = statistics_data['tx_errors']
                else:
                    tx_errors = statistics_data['tx_errors_total']
                stats = (
                    ('Received:', rx),
                    ('Transfered:', tx),
                    ('Reception Errors:', rx_errors),
                    ('Transmission Errors:', tx_errors)
                )

            result[iface] = (
                ('Speed:', speed),
                ('Link detected:', nooptions_data['Link detected']),
            ) + stats

        return result

