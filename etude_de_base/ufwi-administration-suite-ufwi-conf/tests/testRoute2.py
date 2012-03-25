#coding: utf-8
"""
Test case implementing templateRoutedNetworks

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from templateRoutedNetworks import templateRoutedNetworks

class TestRoute2(templateRoutedNetworks):
    """
        Test case : default route
    """
    network_test = {
        "local_ip":'192.168.72.1',
        "local_net":'192.168.72.0/24',
        "routed_net":'0.0.0.0/0',
        "gateway":'192.168.72.60',
        "should_have_interfaces":'auto eth1\n' \
             'iface eth1 inet static\n' \
             '    pre-up ip addr flush dev eth1 ||:\n' \
             '    pre-down ip addr flush dev eth1 ||:\n' \
             '    address 192.168.72.1\n' \
             '    netmask 255.255.255.0\n' \
             '    broadcast 192.168.72.255\n' \
             '    pre-down ip route flush dev eth1 ||:\n' \
             '    post-up ip route add default via 192.168.72.60 dev eth1',
        "should_have_ip_route":'default via 192.168.72.60 dev eth1'
   }
