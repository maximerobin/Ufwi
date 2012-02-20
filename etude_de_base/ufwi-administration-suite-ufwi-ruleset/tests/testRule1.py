#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Julien Miotte <jmiotte AT edenwall.com>
$Id$
"""

from templateRules import templateRules

class TestRule1(templateRules):
    """
        Test_case :
        * SSH, avec auth, avec label, single/single
    """
    ruleV4 = {
                'name' : "acl_test1",

                'description':"  * SSH, avec auth, avec label, single/single",

                'rule' : {'applications': [],
                          'auth_quality': 3,
                          'comment': '',
                          'decision': 'ACCEPT',
                          'destinations': ['Test2'],
                          'durations': [],
                          'enabled': True,
                          'id': 10,
                          'log': False,
                          'log_prefix': '',
                          'mandatory': True,
                          'operating_systems': [],
                          'periodicities': [],
                          'protocols': ['SSH'],
                          'sources': ['Test1'],
                          'user_groups': ['tests']},

                'xml_file' : '<acls_ipv4 next_id=\"2\">\n      ' \
                             '<acl decision=\"ACCEPT\" id=\"1\" log=\"0\">' \
                             '\n         ' \
                             '<source>Test1</source>\n         ' \
                             '<protocol>SSH</protocol>\n         ' \
                             '<destination>Test2</destination>\n         ' \
                             '<user_group>tests</user_group>\n      </acl>',

                'iptables' : 'NFQUEUE    tcp  --  \*      \*       ' \
                             '192.168.16.0/24      192.168.17.0/24     tcp ' \
                             'spts:1024:65535 dpt:22 flags:0x17/0x02 state NEW',

                'dump_ldap':[{'AclFlags': ['2'],
                              'AclWeight': ['1'],
                              'AuthQuality': ['3'],
                              'Decision': ['1'],
                              'DstIPEnd': ['3232240127'],
                              'DstIPStart': ['3232239872'],
                              'DstPort': ['22'],
                              'DstPortEnd': ['22'],
                              'DstPortStart': ['22'],
                              'Group': ['9000'],
                              'InDev': ['eth1'],
                              'OutDev': ['eth2'],
                              'Proto': ['6'],
                              'SrcIPEnd': ['3232239871'],
                              'SrcIPStart': ['3232239616'],
                              'SrcPortEnd': ['65535'],
                              'SrcPortStart': ['1024'],
                              'cn': ['ipv4_acl10_rule1'],
                              'description': ['F10?:'],
                              'objectClass': ['top', 'NuAccessControlList']}]

           }
