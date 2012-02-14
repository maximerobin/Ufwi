#coding: utf-8
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


from __future__ import with_statement

from subprocess import PIPE
import os
import re
from twisted.internet.defer import inlineCallbacks

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.process import runCommand
from ufwi_rpcd.core.context import Context

from ufwi_ruleset.localfw.wrapper import LocalFW

from ufwi_conf.backend.unix_service import ConfigServiceComponent
from ufwi_conf.common.ids_ips_cfg import IdsIpsCfg

from .error import (
    IdsIpsError,
    IDS_IPS_NO_MINMAX_SCORES_ERROR,
    IDS_IPS_SELECT_RULES_ERROR,
    IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
    IDS_IPS_START_ERROR,
    IDS_IPS_STOP_ERROR,
    IDS_IPS_TOTAL_RULES_COUNTS_ERROR,
    IDS_IPS_INVALID_CONFIG,
)

RULES_SOURCE = '/usr/share/edenwall-snort-inline/sigs/rules-en'
RULES_DEST = '/etc/snort_inline/rules/selected-emerging.rules'
FPSTAT = '/usr/share/edenwall-snort-inline/snort-sig-fpstat.pl'
IDS_IPS_QUEUE_NUM = 1
SNORT_CLAMAV = '/etc/snort_inline/edenwall-clamav.conf'
RULES_COUNTS = '/usr/share/edenwall-snort-inline/rules_counts'

class IdsIpsComponent(ConfigServiceComponent):
    NAME = "ids_ips"
    VERSION = "1.0"

    REQUIRES = ('config', )

#    PIDFILE = "/var/run/..."
#    EXE_NAME = "..."

    #INIT_SCRIPT = "..."

    MASTER_KEY = NAME
    CONFIG_DEPENDS = ()

    ACLS = {
        'localfw': set(('addFilterIptable', 'addMangleIptable', 'apply',
                        'clear', 'close', 'open')),
        'ufwi_ruleset': set(('reapplyLastRuleset',)),
        'network': set(('getNetconfig',)),
        }

    ROLES = {
        'conf_read': set(('getIdsIpsConfig', 'getSelectedRulesCounts',
                            'minmaxScores')),
        'conf_write': set(('@conf_read', 'setIdsIpsConfig')),
        'multisite_read': set(('@conf_read', "status")),
        'multisite_write': set(('@conf_write',)),
        'log_read': set(('getTableLog',)),
    }

    def __init__(self):
        ConfigServiceComponent.__init__(self)

        self.ids_ips_cfg = None


    def init(self, core):
        ConfigServiceComponent.init(self, core)
        self.addConfFile("/etc/snort_inline/edenwall-home-net.conf",
                         "root:root", "0644")
        try:
            self.handle_transition()
        except Exception, err:
            self.critical(
                "Could not handle configuration transition to new IDS-IPS backend (%s)."
                % exceptionAsUnicode(err))

    def handle_transition(self):
        # Make sure the old configuration (incompatible with snort_inline 2.8)
        # is not still in place.
        old_conf = False
        with open("/etc/snort_inline/edenwall-home-net.conf") as fd:
            for line in fd.xreadlines():
                if line.find("any") != -1:
                    old_conf = True
                    break
        if old_conf:
            self.read_config()
            self.generate_configfile({
                    "home_net": ",".join(map(str,
                                             self.ids_ips_cfg.networks))})
            self.info(
                "Handled configuration transition for new IDS-IPS backend.")

    @inlineCallbacks
    def apply_config(self, responsible, paths, arg=None):
        self.read_config()
        self._select_rules()

        self.generate_configfile({
                "home_net": ",".join(map(str, self.ids_ips_cfg.networks))})

        if self.ids_ips_cfg.antivirus_enabled:
            if self.ids_ips_cfg.block:
                clamav = 'preprocessor clamav: action-drop\n'
            else:
                clamav = 'preprocessor clamav\n'
        else:
            clamav = ''
        with open(SNORT_CLAMAV, 'w') as fp:
            fp.write(clamav)

        started = self._is_started()
        if self.ids_ips_cfg.enabled:
            if not started:
                try:
                    os.symlink('/etc/sv/snort_inline', '/etc/service/snort_inline')
                except OSError:
                    raise IdsIpsError(IDS_IPS_START_ERROR,
                                      tr('Could not start the IDS-IPS service.'))
                yield self._open_firewall()
            else:
                # Update firewall rules, in case networks selection changed:
                yield self._open_firewall()

                # Reload the configuration (or restart the service):
                # FIXME: check exitcode?
                runCommand(self, ('sv', 'restart', 'snort_inline'))
        elif started:
            yield self._close_and_stop()

    def read_config(self, *args, **kwargs):
        self.ids_ips_cfg = self._read_config()

    def _read_config(self):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
            return IdsIpsCfg.deserialize(serialized)
        except (ConfigError, KeyError):
            self.warning("IDS-IPS not configured, default values loaded")
            return IdsIpsCfg()

    def save_config(self, message, context=None):
        self.debug("Saving IDS-IPS module configuration")
        serialized = self.ids_ips_cfg.serialize()
        with self.core.config_manager.begin(self, context) as cm:
            cm.set(self.MASTER_KEY, serialized)
            cm.commit(message)

    def _select_rules(self):
        command = [FPSTAT, '-a' '%f' % self.ids_ips_cfg.alert_threshold]
        if self.ids_ips_cfg.block:
            command.extend(('-d', '%f' % self.ids_ips_cfg.drop_threshold))
        command.append("%s/*.rules" % RULES_SOURCE)

        with open(RULES_DEST, "w") as stdout:
            process, retcode = runCommand(self, command, stdout=stdout)
        if retcode != 0:
            raise IdsIpsError(IDS_IPS_SELECT_RULES_ERROR,
                              tr('Error while selecting rules.'))

    def _total_rules_count(self):
        try:
            with open(RULES_COUNTS) as fd:
                total = int(fd.readline().split()[1])
            return total
        except:
            raise IdsIpsError(IDS_IPS_TOTAL_RULES_COUNTS_ERROR,
                              tr("Error while reading total rules count."))

    def _is_started(self):
        return os.path.exists('/etc/service/snort_inline')

    def _firewall_error(self, fail):
        self.writeError(fail, u'Error while handling firewall rules for the IDS-IPS service: ')

    @inlineCallbacks
    def _open_firewall(self):
        localfw = LocalFW('ids_ips')

        localfw.call('addMangleIptable', False,
                '-A POSTROUTING -m mark --mark 0x20000/0x20000 -j MARK --and-mark 0xfffdffff')
        localfw.call('addFilterIptable', False, '-N IPS_NETS')
        for network in self.ids_ips_cfg.networks:
            localfw.call('addFilterIptable', False,
                    '-A IPS_NETS -d %s -j NFQUEUE --queue-num %d' %
                    (network.strNormal(1), IDS_IPS_QUEUE_NUM))
            # Snort_inline inspects the trafic both ways:
            localfw.call('addFilterIptable', False,
                    '-A IPS_NETS -s %s -j NFQUEUE --queue-num %d' %
                    (network.strNormal(1), IDS_IPS_QUEUE_NUM))
        localfw.call('addFilterIptable', False,
                '-I FORWARD -m mark ! --mark 0x20000/0x20000 -j IPS_NETS')

        context = Context.fromComponent(self)
        try:
            yield localfw.execute(self.core, context)
        except Exception, err:
            self.writeError(err,
                'Error while handling firewall rules for the ids-ips')
            raise

    @inlineCallbacks
    def _close_and_stop(self):
        context = Context.fromComponent(self)
        localfw = LocalFW('ids_ips')
        try:
            yield localfw.execute(self.core, context)
        except Exception, err:
            self.writeError(err,
                'Error while handling firewall rules for the ids-ips')
            raise
        try:
            os.unlink('/etc/service/snort_inline')
        except OSError:
            raise IdsIpsError(IDS_IPS_STOP_ERROR,
                              tr('Could not stop the IDS-IPS service.'))

    def service_minmaxScores(self, context):
        """Read the lowest and highest scores for current rules"""
        try:
            with open(RULES_COUNTS) as fd:
                lines = fd.readlines()
            return [float(lines[0].split()[0]), float(lines[-1].split()[0])]
        except:
            raise IdsIpsError(
                IDS_IPS_NO_MINMAX_SCORES_ERROR,
                tr('Could not read the min/max scores.'))

    def service_getSelectedRulesCounts(self, context, thresholds=None):
        """Return 3 counts: selected rules for alert and drop, and available
        rules.

        If thresholds is None, then this method reads the actual rules file;
        if thresholds is a list of two floats, then this method uses these
        values to compute the count of rules, not touching or reading the
        actual file."""
        results = []
        if thresholds is None:
            file_to_read = RULES_DEST
            try:
                command = [FPSTAT, '-a', '%f' % thresholds[0]]
                if self.ids_ips_cfg.block:
                    command.append('-d %f' % thresholds[1])
                command.append('%s/*.rules' % RULES_SOURCE)
                file_to_read = '/dev/shm/selected_rules'
                with open(file_to_read, "w") as stdout:
                    process, retcode = runCommand(self, command, stdout=stdout)
            except TypeError:
                raise IdsIpsError(IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
                    tr('Could not count the selected rules (type error).'))
            except IndexError:
                raise IdsIpsError(IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
                    tr('Could not count the selected rules (index error).'))
            if retcode != 0:
                raise IdsIpsError(IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
                    tr('Error while selecting rules for counting.'))
            # FIXME: use "grep -c" or just use Python code
            commands = ("grep '^alert ' %s |wc -l" % file_to_read,
                        "grep '^drop ' %s |wc -l" % file_to_read)
            for command in commands:
                # FIXME: don't use shell=True
                p = createProcess(self, command, shell=True, stdout=PIPE)
                stdout, stderr = p.communicate()
                retcode = p.wait()
                if retcode != 0:
                    raise IdsIpsError(
                        IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
                        tr('Could not count the selected rules.'))

                first_line = stdout.splitlines()[0]
                results.append(int(first_line))
        else:
            alert_count = None
            drop_count = None
            try:
                with open(RULES_COUNTS) as fd:
                    # First threshold (alert):
                    for line in fd:
                        cols = line.split()
                        if float(cols[0]) >= thresholds[0]:
                            alert_count = int(cols[1])
                            if float(cols[0]) >= thresholds[1]:
                                drop_count = int(cols[2])
                            break
                    # Second threshold (drop):
                    if drop_count is None:
                        for line in fd:
                            cols = line.split()
                            if float(cols[0]) >= thresholds[1]:
                                drop_count = int(cols[2])
                                break
            except:
                pass  # We will test the counts anyway.
            if alert_count is None or drop_count is None:
                raise IdsIpsError(IDS_IPS_SELECTED_RULES_COUNTS_ERROR,
                                  tr('Could not count the selected rules.'))
            results.extend([alert_count, drop_count])
        results.append(self._total_rules_count())
        return results

    def service_saveConfiguration(self, context, message):
        self.save_config(message, context)

    def service_getIdsIpsConfig(self, context):
        return self.ids_ips_cfg.serialize()

    def service_setIdsIpsConfig(self, context, serialized, message):
        self.ids_ips_cfg = IdsIpsCfg.deserialize(serialized)
        ok, msg = self.ids_ips_cfg.isValidWithMsg()
        if not ok:
            raise IdsIpsError(IDS_IPS_INVALID_CONFIG, msg)
        self.save_config(message, context)

    # Samples:
    # 10/27-10:13:02.598955  [**] [133:1:1] (spp_clamav) Virus Found: Eicar-Test-Signature [**] {TCP} 172.21.0.10:80 -> 172.40.6.10:33531
    # 10/29-16:10:33.536412  [**] [122:26:0] (portscan) ICMP Filtered Sweep [**] [Priority: 3] {PROTO:255} 172.21.0.10 -> 172.40.11.21

    LOG_REGEXP = re.compile("([0-9/\-\:]+)[\.0-9]*  \[*([A-Za-z0-9]*)\]*\s*\[\*\*\] \[[0-9A-Za-z:]+\] (.*) {[\w:0-9]*} ([0-9\.:]+) -> ([0-9\.:]+)")
    LOG_FILE = '/var/log/snort/snort_inline-fast'
    LOG_COLUMNS = ['id', 'ip_saddr', 'ip_daddr', 'state', 'oob_time_sec', 'oob_prefix']

    def service_getTableLog(self, context, args):
        table = []
        states = {}
        start = int(args.get('start', 0))
        limit = int(args.get('limit', 30))
        sortby = args.get('sortby', 'oob_time_sec')
        sort = args.get('sort', 'DESC')

        try:
            with open(self.LOG_FILE) as fp:
                for i, line in enumerate(fp):
                    m = self.LOG_REGEXP.match(line)
                    if m:
                        ts = m.group(1)
                        state = m.group(2)
                        log = m.group(3).replace('[**]', '')
                        src = m.group(4)
                        dst = m.group(5)

                        if state == 'Drop':
                            state = 0
                        else:
                            state = 1
                        states[str(i)] = state
                        table.append([i, src, dst, state, ts, log])
                    else:
                        table.append([i, '',  '',  -2,    '', line])
        except IOError:
            return {'args': args,
                    'filters': {},
                    'columns': self.LOG_COLUMNS,
                    'rowcount': len(table),
                    'table': [],
                    'states': states,
                   }
        try:
            col = self.LOG_COLUMNS.index(sortby)
        except ValueError:
            table.reverse() # sort by ts reversed
        else:
            table = sorted(table, key=lambda row: row[col], reverse=(sort == 'DESC'))

        return {'args': args,
                'filters': {},
                'columns': self.LOG_COLUMNS,
                'rowcount': len(table),
                'table': table[start:start+limit],
                'states': states,
               }
