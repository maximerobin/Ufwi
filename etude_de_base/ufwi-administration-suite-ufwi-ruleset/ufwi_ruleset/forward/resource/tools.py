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

from IPy import IP

from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.error import exceptionAsUnicode

from ufwi_ruleset.forward.error import RulesetError
from ufwi_ruleset.forward.flatten import flattenNetwork
from ufwi_ruleset.forward.tools import combinaisons2

def parseIPAddress(text):
    try:
        return IP(text)
    except ValueError, err:
        raise RulesetError(
            tr('Invalid IP address "%s": %s'),
            text, exceptionAsUnicode(err))

def checkNetworkInclusion(parent, networks):
    interface = None
    for group1, group2 in combinaisons2(networks):
        for new_resource in flattenNetwork(group1):
            # Ensure that all networks are part of the same network interface
            if interface is None:
                interface = new_resource.interface
            elif new_resource.interface != interface:
                raise RulesetError(
                    tr('Error in %s: the %s network (%s interface) is not part of the %s interface!'),
                    unicode(parent), group1.formatID(), new_resource.interface.formatID(), interface.formatID())

            # Check network inclusion
            for resource in flattenNetwork(group2):
                if resource.match(new_resource):
                    raise RulesetError(
                        tr('Error in %s: the %s network is already part of the %s network!'),
                        unicode(parent), new_resource.formatID(), group2.formatID())
                if new_resource.match(resource):
                    raise RulesetError(
                        tr('Error in %s: the %s network is already part of the %s network!'),
                        unicode(parent), resource.formatID(), group1.formatID())

