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

import re
from ufwi_ruleset.common.regex import IDENTIFIER_REGEX_STR

DECISIONS = {
    # iptable name => nufw code (written in LDAP)
    u'DROP': 0,
    u'ACCEPT': 1,
    u'REJECT': 3,
}

CHAIN_REGEX = re.compile(IDENTIFIER_REGEX_STR)

def _checkChain(chain):
    if isinstance(chain, (str, unicode)):
        return (chain in (u'INPUT', u'OUTPUT', u'FORWARD'))
    if not isinstance(chain, tuple):
        return False
    if not isinstance(chain[0], (str, unicode)):
        return False
    if not CHAIN_REGEX.match(chain[0]):
        return False
    if not isinstance(chain[1], (str, unicode)):
        return False
    if not CHAIN_REGEX.match(chain[1]):
        return False
    return True

def checkChain(chain):
    if not _checkChain(chain):
        raise ValueError("Invalid chain: %s" % repr(chain))

class DefaultDecisions:
    def __init__(self, config, ipv6):
        self.config = config
        self.ipv6 = ipv6   # boolean

        # chain => (decision, use_log)
        #
        # with:
        #  - chain: 'INPUT, 'OUTPUT', or a tuple of the input and output
        #    interface identifiers, eg. ('DMZ', 'LAN Interface')
        #  - decision: 'ACCEPT', 'DROP' or 'REJECT'
        #  - use_log: boolean
        self.decisions = {}

    def get(self, chain):
        """
        Get the default decision of the specified chain. chain is 'INPUT',
        'OUTPUT', 'FORWARD' or a tuple of interface names.
        Eg. chain = ('eth0','eth2').

        Return (decision, use_log) where decision is 'ACCEPT', 'DROP' or
        'REJECT', and use_log is a boolean.
        """
        # check chain type
        checkChain(chain)

        if self.ipv6 and (not self.config['global']['use_ipv6']):
            return ('DROP', False)

        # User changed the default decision?
        if chain in self.decisions:
            return self.decisions[chain]

        # Hardcoded decisions
        if chain == 'INPUT':
            return ('DROP', True)
        elif chain == 'OUTPUT':
            if self.config.isGateway():
                return ('ACCEPT', False)
            else:
                return ('REJECT', True)
        else:
            # Forward chain
            if self.config.isGateway():
                return (self.config['iptables']['default_drop'], True)
            else:
                # local firewall: no forward
                return ('DROP', False)

    def getDecision(self, chain):
        return self.get(chain)[0]

    def useLog(self, chain):
        return self.get(chain)[1]

    def _checkNew(self, chain, decision, log):
        if chain == 'FORWARD':
            raise ValueError("FORWARD chain default decision is not editable.")
        checkChain(chain)
        if decision not in DECISIONS:
            raise ValueError("Invalid decision: %s" % repr(decision))
        if not isinstance(log, bool):
            raise ValueError("Invalid log: %s" % repr(log))

    def _set(self, decisions, chain, decision, log):
        if isinstance(chain, list):
            chain = tuple(chain)
        log = bool(log)
        self._checkNew(chain, decision, log)
        decisions[chain] = (decision, log)

    def set(self, chain, decision, log):
        self._set(self.decisions, chain, decision, log)

    def exportXMLRPC(self):
        return [
            ((chain,) + decision_log)
            for chain, decision_log in self.decisions.iteritems()]

    def importXMLRPC(self, decisions):
        self.decisions = self._importXMLRPC(decisions)

    def _importXMLRPC(self, xmlrpc):
        decisions = {}
        for chain, decision, log in xmlrpc:
            self._set(decisions, chain, decision, log)
        return decisions

NAT_TRANSLATE = 'translate'
NAT_PREROUTING_ACCEPT = 'prerouting_accept'
NAT_POSTROUTING_ACCEPT = 'postrouting_accept'
NAT_TYPES = set((NAT_TRANSLATE,
    NAT_PREROUTING_ACCEPT, NAT_POSTROUTING_ACCEPT))

