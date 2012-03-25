#coding: utf-8
"""
Test case implementing templateDHCP.

Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id:$
"""

#from ldap import initialize, SCOPE_SUBTREE
from __future__ import with_statement
from IPy import IP
from templateDHCP import templateDHCP

class TestDHCP3(templateDHCP):
    """
        Test case :
        - simple eth interface
        - not forcing the dns server
        - not forcing the default route
    """
    test_network = {"name"      : "test",
                    "iface"     : "eth2",
                    "network"   : IP("192.168.2.0/24"),
                    "service"   : set(IP("192.168.2.1"),)}

    test_dhcp = {'dns_server': u'192.168.2.1',
                 'end': u'192.168.2.120',
                 'net_label': u'192.168.2.0/24',
                 'start': u'192.168.2.100',
                 'router': u'192.168.2.1'}

    configure_dns = False
    configure_router = False
