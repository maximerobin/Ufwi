
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

from tools import NuCentralTest

class TestServerCore(NuCentralTest):
    def test_component_list(self):
        components = self.client.call("CORE", "getComponentList")
        assert len(components) >= 2
        assert 'CORE' in components

    def test_service_list(self):
        list = self.client.call("CORE", "getServiceList", "CORE")
        assert len(list) >= 4
        assert 'getStatus' in list
        assert 'getComponentList' in list
        assert 'getServiceList' in list
        assert 'getComponentVersion' in list

    def test_component_version(self):
        result = self.client.call("CORE", "getComponentVersion")
        assert result == '1.0'

