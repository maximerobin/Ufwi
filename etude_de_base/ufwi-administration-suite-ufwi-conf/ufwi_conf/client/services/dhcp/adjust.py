
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

def adjust_net(old_net, new_net, old_ip):

    delta = new_net.ip - old_net.ip
    new_ip = IP(old_ip.ip + delta)

    return new_ip

def adjust_ip(new_net, old_ip):

    if not isinstance(new_net, IP):
        new_net = IP(new_net)
    if not isinstance(old_ip, IP):
        old_ip = IP(old_ip)

    prefix = new_net.prefixlen()
    old_net = old_ip.make_net(prefix)
    new_ip = adjust_net(old_net, new_net, old_ip)

    return new_ip
