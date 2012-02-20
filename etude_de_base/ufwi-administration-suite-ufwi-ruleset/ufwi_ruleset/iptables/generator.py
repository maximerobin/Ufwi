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
from os.path import join as path_join
from glob import glob
from datetime import datetime
import itertools
import re
import codecs

from ufwi_rpcd.common.logger import LoggerChild

from ufwi_ruleset import VERSION
from ufwi_ruleset.iptables.chain import (dispatchRules, aclForwardChains,
    IptablesChain, Counters)
from ufwi_ruleset.config import (
    RULESET_DIR, LOCAL_RULES_IPV4_DIR, LOCAL_RULES_IPV6_DIR)
from ufwi_ruleset.iptables.arguments import Arguments
from ufwi_ruleset.iptables.comment import comment, closeComment, longComment
from ufwi_ruleset.iptables.nat import natsRules
from ufwi_ruleset.iptables.acls import aclsRules
from ufwi_ruleset.common.network import IPV4_ADDRESS, IPV6_ADDRESS

REMOVE_COMMENT = re.compile("#.*$")

class IptablesGenerator(LoggerChild):
    def __init__(self, logger, default_decisions, options, config, apply_rules):
        LoggerChild.__init__(self, logger)
        self.options = options
        self.config = config['iptables']
        self.apply_rules = apply_rules

        # DefaultDecisions object, can be None for NAT rules
        self.default_decisions = default_decisions

        self.options.log_type = self.config['log_type']
        self.options.gateway = config.isGateway()
        if self.options.ipv6 and self.options.log_type == "ULOG":
            self.apply_rules.warning("ip6tables doesn't support ULOG: set log type to LOG")
            self.options.log_type = 'LOG'

    def _comment(self, text):
        max_length = 255
        if max_length < len(text):
            full_text = text
            text = text[:max_length]
            self.apply_rules.warning(
                'Truncate iptable comment "%s" (%s) to %s characters: "%s"'
                % (full_text, len(full_text), max_length, text))
        return Arguments("-m", "comment", "--comment", text)

    def ruleComment(self, rule, rule_number):
        return self._comment(u"%s: rule %s" % (unicode(rule), rule_number))

    def logRule(self, decision, text, limit="default"):
        log_type = self.options.log_type
        if log_type == 'NFLOG':
            max_length = 63
        elif log_type == 'ULOG':
            max_length = 31
        else:
            max_length = 28
        if max_length < len(text):
            full_text = text
            text = text[:max_length]
            self.apply_rules.warning(
                'Truncate log prefix "%s" (%s) to %s characters: "%s"'
                % (full_text, len(full_text), max_length, text))
        if log_type == 'LOG':
            text += ' '
        if log_type == 'NFLOG':
            if decision == 'ACCEPT':
                group = self.config['nflog_group_accept']
            elif decision == 'REJECT':
                group = self.config['nflog_group_reject']
            else:
                group = self.config['nflog_group_drop']
            rule = Arguments(
                "-j", "NFLOG",
                "--nflog-prefix", text,
                "--nflog-group", unicode(group))
        elif log_type == 'ULOG':
            rule = Arguments("-j", "ULOG", "--ulog-prefix", text)
        else:
            rule = Arguments("-j", "LOG", "--log-prefix", text)
        if limit == "default":
            limit = self.config['log_limit']
        if limit:
            rule += Arguments('-m', 'limit')
            rule += Arguments('--limit', limit)
        return rule

    def logDrop(self, chain, decision):
        if chain in ('INPUT', 'OUTPUT'):
            chain_letter = chain[0]
        else:
            chain_letter = 'F'
        decision_letter = decision[0].lower()
        message = '%s0%s:Default %s for %s' % (
            chain_letter, decision_letter, decision, chain)
        return Arguments("-A", chain) + self.logRule(decision, message)

    def dropRules(self, table, chains):
        if not chains:
            return
        for line in comment("Default decisions"):
            yield line
        for chain in chains:
            if isinstance(chain, IptablesChain):
                if chain.isGeneric():
                    yield u"# No default drop for chain %s" % chain
                    continue
                chain_key = (chain.input.id, chain.output.id)
            else:
                # chain is a string (eg. 'FORWARD')
                chain_key = chain
            decision, use_log = self.default_decisions.get(chain_key)
            if (table == "mangle") and (decision == 'REJECT'):
                # It's not possible to reject packets in mangle table
                decision = "DROP"
            if use_log:
                yield self.logDrop(chain, decision)
            yield Arguments("-A", chain, "-j", decision) + self._comment("Default decision")

    def filterDrop(self, forward_chains):
        chains = forward_chains
        chains += ('INPUT', 'FORWARD', 'OUTPUT')
        return self.dropRules("filter", chains)

    def mangleRules(self, custom_rules):
        for line in longComment("mangle table"):
            yield line
        yield "*mangle"
        for chain in ("PREROUTING", "INPUT", "FORWARD", "OUTPUT", "POSTROUTING"):
            yield Counters(chain)
        if self.options.deny_all:
            return
        for line in self.userPreRules('mangle'):
            yield line
        for line in self.customRules(custom_rules, 'mangle-pre'):
            yield line
        for line in self.defaultMangleRules():
            yield line
        # -- ufwi_ruleset mangle rules (no rules yet) --
        for line in self.customRules(custom_rules, 'mangle-post'):
            yield line
        for line in self.userPostRules('mangle'):
            yield line

    def userRules(self, table, suffix):
        if self.options.ipv6:
            dirname = LOCAL_RULES_IPV6_DIR
        else:
            dirname = LOCAL_RULES_IPV4_DIR
        pattern = path_join(dirname, '%s*.rules' % table) + suffix
        for filename in glob(pattern):
            text = "User rules: %s" % filename
            for line in comment(text):
                yield line
            with open(filename) as user_file:
                for line in user_file:
                    line = line.strip()
                    if not line:
                        continue
                    if not line.startswith("#"):
                        line = REMOVE_COMMENT.sub('', line)
                    yield line
            for line in closeComment(text):
                yield line

    def userPreRules(self, table):
        return self.userRules(table, '')

    def userPostRules(self, table):
        return self.userRules(table, '.post')

    def headerRules(self):
        yield u"# Generated by Ruleset version %s at %s" % (VERSION, datetime.now())

    def footerRules(self):
        yield u""
        yield u"# Completed at %s" % datetime.now()

    def customRules(self, custom_rules, table):
        if not custom_rules:
            return
        if self.options.ipv6:
            ipv = IPV6_ADDRESS
        else:
            ipv = IPV4_ADDRESS

        for line in custom_rules[ipv][table].split('\r\n'):
            yield line

    def defaultFilterRules(self):
        if self.options.gateway:
            chains = ("FORWARD", "INPUT", "OUTPUT")
        else:
            chains = ("INPUT", "OUTPUT")
        for line in comment("Default filter rules"):
            yield line

        # Accept packets related to established connections
        for chain in chains:
            yield Arguments(
                "-A", chain,
                "-m", "state", "--state", "RELATED,ESTABLISHED",
                "-j", "ACCEPT")

        # Drop invalid packets?
        if self.config['drop_invalid']:
            for chain in chains:
                if chain == 'INPUT':
                    continue
                args = Arguments("-A", chain)
                if self.options.ipv6:
                    args += Arguments("!", "-p", "icmpv6")
                args += Arguments("-m", "state", "--state", "INVALID")
                if self.config['log_invalid']:
                    yield args + self.logRule("DROP", "Drop INVALID %s" % chain)
                yield args + Arguments("-j", "DROP")

        # Accept all packets from loopback interface
        yield Arguments("-A", "INPUT",
            "-i", "lo",
            "-j", "ACCEPT") + self._comment("Trust loopback")
        yield Arguments("-A", "OUTPUT",
            "-o", "lo",
            "-j", "ACCEPT") + self._comment("Trust loopback")

    def defaultMangleRules(self):
        # Copy the mark from the first packet to the next packets
        if self.options.nufw:
            rule = "-A PREROUTING -j CONNMARK --restore-mark".split()
            yield Arguments(*rule)
            rule = "-A POSTROUTING -m mark ! --mark 0 -j CONNMARK --save-mark --mask 0x0000ffff".split()
            yield Arguments(*rule)

    def filterRules(self, acls, forward_chains, custom_rules):
        for line in longComment("filter table"):
            yield line

        yield "*filter"
        for chain in ("INPUT", "FORWARD", "OUTPUT"):
            decision = self.default_decisions.getDecision(chain)
            if decision == 'REJECT':
                decision = 'DROP'
            yield Counters(chain, decision=decision)
        for chain_obj in forward_chains:
            yield chain_obj.create
        if self.options.deny_all:
            return
        for line in self.defaultFilterRules():
            yield line
        for line in self.userPreRules('filter'):
            yield line
        for line in self.customRules(custom_rules, 'filter-pre'):
            yield line

        for line in comment("Dispatch FORWARD to the different chains"):
            yield line
        for line in dispatchRules(forward_chains):
            yield line

        for line in aclsRules(self, acls):
            yield line

        for line in self.customRules(custom_rules, 'filter-post'):
            yield line
        for line in self.userPostRules('filter'):
            yield line
        for line in self.filterDrop(forward_chains):
            yield line

    def natRules(self, nats, custom_rules):
        for line in longComment("nat table"):
            yield line
        yield "*nat"
        for chain in (u"PREROUTING", u"POSTROUTING", u"OUTPUT"):
            yield Counters(chain)
        for line in self.userPreRules('nat'):
            yield line
        for line in self.customRules(custom_rules, 'nat-pre'):
            yield line
        for line in natsRules(self, nats, self.apply_rules):
            yield line
        for line in self.customRules(custom_rules, 'nat-post'):
            yield line
        for line in self.userPostRules('nat'):
            yield line

    def commit(self):
        yield "COMMIT"

    def writeRules(self, acls, nats, custom_rules):
        """
        Write iptables rules for the specified rules.
        custom_rules is a CustomRules object or None (ignore custom rules).
        """
        if self.options.gateway:
            # list of IptablesChain objects
            forward_chains = aclForwardChains(acls)
        else:
            forward_chains = tuple()

        # Create file
        if self.options.ipv6:
            filename = 'new_rules_ipv6'
        else:
            filename = 'new_rules_ipv4'
        filename = path_join(RULESET_DIR, filename)
        self.info("[Ruleset] Write iptables rules to %s" % filename)

        all_rules = [
            self.headerRules(),
            self.mangleRules(custom_rules), self.commit(),
            self.filterRules(acls, forward_chains, custom_rules), self.commit()
        ]
        if not self.options.ipv6:
            all_rules.extend( [self.natRules(nats, custom_rules), self.commit()] )
        all_rules.append( self.footerRules() )

        with codecs.open(filename, 'w', 'UTF-8') as rules:
            for line in itertools.chain(*all_rules):
                print >>rules, unicode(line)

        return filename

