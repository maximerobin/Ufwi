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

from ufwi_ruleset.iptables.arguments import Arguments
from ufwi_ruleset.forward.resource import IPsecNetworkResource

def formatIPsec(source, destination, direction=None):
    arguments = Arguments()
    ipsec_src = bool(source) and isinstance(source, IPsecNetworkResource)
    ipsec_dst = bool(destination) and isinstance(destination, IPsecNetworkResource)
    if not(ipsec_src or ipsec_dst):
        return arguments
    arguments += Arguments('-m', 'policy')
    if direction is None:
        if ipsec_src:
            direction = 'in'
        else:
            direction = 'out'
    arguments += Arguments(
        '--dir', direction,
        '--pol', 'ipsec',
        '--mode', 'tunnel')
    if ipsec_src and source.gateway:
        arguments += Arguments('--tunnel-src', source.gateway)
    if ipsec_dst and destination.gateway:
        arguments += Arguments('--tunnel-dst', destination.gateway)
    return arguments

