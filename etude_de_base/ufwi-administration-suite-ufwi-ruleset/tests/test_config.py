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

from copy import deepcopy
from .client import Client
from templateTest import Test
from ufwi_ruleset.common.parameters import LOCAL_FIREWALL, NUFW_GATEWAY

FILENAME = 'test'

class TestConfig(Test):
    def test_getset(self):
        # get config
        old_config = self.client.call('ufwi_ruleset', 'getConfig')

        # set new config #1
        new_config = deepcopy(old_config)
        new_config['global']['firewall_type'] = LOCAL_FIREWALL
        new_config['iptables']['log_type'] = u'LOG'
        result = self.client.call('ufwi_ruleset', 'setConfig', new_config)
        assert new_config['global'] == result['global']
        assert new_config['iptables'] == result['iptables']
        assert new_config == result

        # set new config #2
        new_config2 = deepcopy(new_config)
        new_config2['global']['firewall_type'] = NUFW_GATEWAY
        new_config2['iptables']['log_type'] = u'ULOG'
        result = self.client.call('ufwi_ruleset', 'setConfig', new_config2)
        assert result['global'] == new_config2['global']
        assert result['iptables'] == new_config2['iptables']
        assert result == new_config2

        # restore old config
        result = self.client.call('ufwi_ruleset', 'setConfig', old_config)
        assert result == old_config

