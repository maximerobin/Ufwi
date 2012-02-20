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
from templateTest import Test
from ufwi_ruleset.config import LOCAL_RULES_IPV4_DIR, LOCAL_RULES_IPV6_DIR
from os.path import join as path_join

FILENAME = 'test'

class TestLocalFW(Test):
    def readRules(self, name, ipv6):
        if ipv6:
            directory = LOCAL_RULES_IPV6_DIR
        else:
            directory = LOCAL_RULES_IPV4_DIR
        filename = path_join(directory, 'filter-localfw_%s.rules' % name)
        rules = []
        with open(filename, 'r') as f:
            for line in f:
                line = line.rstrip('\n')
                if line.startswith('#'):
                    continue
                rules.append(line)
        return rules

    def test_allow(self):
        # Create the rules
        name = self.client.call('localfw', 'open', FILENAME)
        self.client.call('localfw', 'clear')
        count = self.client.call('localfw', 'addFilterRule',
            {'chain': 'INPUT', 'decision': 'ACCEPT',
             'protocol': 'esp', 'sources': ['0.0.0.0/0']})
        assert count == 1
        count = self.client.call('localfw', 'addFilterRule',
            {'chain': 'INPUT', 'decision': 'ACCEPT', 'ipv6': True,
             'protocol': 'esp', 'sources': ['2000::/3']})
        assert count == 1
        count = self.client.call('localfw', 'addFilterRule',
            {'chain': 'INPUT', 'decision': 'ACCEPT',
             'protocol': 'tcp', 'dport': 80, 'sources': ['192.168.0.2']})
        assert count == 1
        count = self.client.call('localfw', 'addFilterRule',
            {'chain': 'INPUT', 'decision': 'ACCEPT', 'ipv6': True,
             'protocol': 'tcp', 'dport': 80, 'sources': ['::1']})
        assert count == 1
        self.client.call('localfw', 'apply')
        self.client.call('localfw', 'close')

        # Check IPv4 iptables rules
        rules = self.readRules(name, False)
        print rules
        assert rules == [
            '-A INPUT -p esp --src 0.0.0.0/0 -j ACCEPT',
            '-A INPUT -p tcp --dport 80 --src 192.168.0.2 -m state --state NEW -j ACCEPT',
        ]

        # Check IPv4 iptables rules
        rules = self.readRules(name, True)
        print rules
        assert rules == [
            '-A INPUT -p esp --src 2000::/3 -j ACCEPT',
            '-A INPUT -p tcp --dport 80 --src ::1 -m state --state NEW -j ACCEPT'
        ]

