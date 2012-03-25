# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id: default.py 18615 2010-03-15 21:37:17Z farezki $
"""

from ufwi_rpcd.common import tr

default_settings = \
    {'frags': {'AppTable_most_drop': {'args': {'sort': 'DESC',
                                     'sortby': 'packets',
                                     'raw_label': 0
                                    },
                            'background_color': '16777215',
                            'title': tr('Dropped Applications'),
                            'type': 'AppTable',
                            'view': 'pie'},
               'AppTable_accept': {'args': {'sort': 'DESC',
                                            'sortby': 'packets',
                                            'raw_label': 1
                                           },
                                   'background_color': '16777215',
                                   'title': tr('Most Accepted Applications'),
                                   'type': 'AppTable',
                                   'view': 'histo'},
               'AppTable': {'args': {},
                                   'background_color': '16777215',
                                   'title': tr('Applications in Use'),
                                   'type': 'AppTable',
                                   'view': 'histo'},
               'AppTable_currently': {'args': {'raw_label': 1, 'sortby' : 'packets'},
                                   'background_color': '16777215',
                                   'title': tr('Applications Currently Used'),
                                   'type': 'AppTable',
                                   'view': 'table'},
               'AppTable_drop': {'args': { 'sort': 'DESC',
                                            'sortby': 'packets',
                                            'raw_label': 0},
                                   'background_color': '16777215',
                                   'title': tr('Dropped Applications'),
                                   'type': 'AppTable',
                                   'view': 'histo'},
               'AppTable_last_drop': {'args': {'raw_label': 0},
                                  'background_color': '16777215',
                                  'title': tr('Last Dropped Applications'),
                                  'type': 'AppTable',
                                  'view': 'pie'},
               'ConUserTable': {'args': {},
                                'background_color': '16777215',
                                'title': tr('Connected Users'),
                                'type': 'ConUserTable',
                                'view': 'table'},
               #'ConntrackTable': {'args': {},
               #                   'background_color': '16777215',
               #                   'title': tr('Conntrack'),
               #                   'type': 'ConntrackTable',
               #                   'view': 'table'},
               'IDSIPSTable': {'args': {},
                               'title': tr('IDS-IPS Logs'),
                               'type': 'IDSIPSTable',
                               'view': 'table'},
               'ProxyRequestTable': {'args': {},
                                      'title': tr('Proxy Logs'),
                                      'type': 'ProxyRequestTable',
                                      'view': 'table'},
               'ProxyDomainsTable': {'args': {},
                                     'title': tr('Top Domains'),
                                     'type': 'ProxyDomainsTable',
                                     'view': 'table'},
               'ProxyUsersTable': {'args': {},
                                   'title': tr('Top Users'),
                                   'type': 'ProxyUsersTable',
                                   'view': 'table'},
               'ProxyHostsTable': {'args': {},
                                   'title': tr('Top Hosts'),
                                   'type': 'ProxyHostsTable',
                                   'view': 'table'},
               'HostPortTable_drop': {'args': {'raw_label': 0},
                                 'background_color': '16777215',
                                 'title': tr('Dropped Host Port Connections'),
                                 'type': 'HostPortTable',
                                 'view': 'table'},
               'HostPortTable_accept': {'args': {'proto': 'tcp', 'raw_label': 1},
                                       'background_color': '16777215',
                                       'title': tr('Host Port Connections'),
                                       'type': 'HostPortTable',
                                       'view': 'table'},
               'IPdstTable': {'args': {'sortby': 'packets'},
                              'background_color': '16777215',
                              'title': tr('Destination IP'),
                              'type': 'IPdstTable',
                              'view': 'pie'},
               'IPsrcTable': {'args': {},
                              'background_color': '16777215',
                              'title': tr('Last Active Hosts'),
                              'type': 'IPsrcTable',
                              'view': 'table'},
               'IPsrcTable_drop': {'args': {'raw_label': 0},
                              'background_color': '16777215',
                              'title': tr('Dropped Hosts'),
                              'type': 'IPsrcTable',
                              'view': 'table'},
               'IPsrcTable_most_drop': {'args': {'raw_label': 0, 'sortby': 'packets'},
                              'title': tr('Most Dropped Hosts'),
                              'type': 'IPsrcTable',
                              'view': 'table'},
               'IPsrcTable_accept': {'args': {'sort': 'DESC',
                                              'sortby': 'packets',
                                              'raw_label': 1},
                                     'background_color': '16777215',
                                     'title': tr('Most Accepted Hosts'),
                                     'type': 'IPsrcTable',
                                     'view': 'histo'},
               'IPsrcTable_active': {'args': {'raw_label': 1},
                                     'background_color': '16777215',
                                     'title': tr('Accepted Hosts'),
                                     'type': 'IPsrcTable',
                                     'view': 'table'},
               'IPsrcTable_drop': {'args': { 'sort': 'DESC',
                                              'sortby': 'packets',
                                              'raw_label': 0},
                                     'background_color': '16777215',
                                     'title': tr('Most Dropped Hosts'),
                                     'type': 'IPsrcTable',
                                     'view': 'histo'},
               'LastPacketsStream': {'args': {'interval': 5},
                                     'background_color': '16777215',
                                     'title': tr('Packets Traffic'),
                                     'type': 'LastPacketsStream',
                                     'view': 'line'},
               'LastPacketsStream_drop': {'args': {'interval': 5, 'raw_label': 0},
                                            'background_color': '16777215',
                                            'title': tr('Dropped Packets'),
                                            'type': 'LastPacketsStream',
                                            'view': 'line'},
               'PacketsCountTable': {'args': {},
                                     'title': tr('Packets per Day'),
                                     'type': 'PacketsCountTable',
                                     'view': 'histo'},
               'PacketsCountTable_drop': {'args': {'raw_label': 0},
                                          'title': tr('Dropped Packets per Day'),
                                          'type': 'PacketsCountTable',
                                          'view': 'histo'},
               'PacketInfo': {'args': {},
                              'background_color': '16777215',
                              'title': tr('Packet Info'),
                              'type': 'PacketInfo',
                              'view': 'packetinfo'},
               'PacketTable': {'args': {},
                               'background_color': '16777215',
                               'title': tr('Packets List'),
                               'type': 'PacketTable',
                               'view': 'table'},
               'TCPTable': {'args': {},
                            'background_color': '16777215',
                            'title': tr('TCP Ports'),
                            'type': 'TCPTable',
                            'view': 'pie'},
               'TrafficStream': {'args': {'interval': 15},
                                 'background_color': '16777215',
                                 'title': tr('Traffic'),
                                 'type': 'TrafficStream',
                                 'view': 'line'},
               'UserAppTable_drop': {'args': {'raw_label': 0, 'sortby': 'packets'},
                                'background_color': '16777215',
                                'title': tr('Dropped User Applications'),
                                'type': 'UserAppTable',
                                'view': 'table'},
               'UserAppTable_accept': {'args': {'raw_label': 1, 'sortby': 'packets'},
                                       'background_color': '16777215',
                                       'title': tr('Most Accepted User Applications'),
                                       'type': 'UserAppTable',
                                       'view': 'table'},
               'UserTable_most_drop': {'args': {'sort': 'DESC',
                                      'sortby': 'packets',
                                      'raw_label': 0},
                             'background_color': '16777215',
                             'title': tr('Most Dropped Users'),
                             'type': 'UserTable',
                             'view': 'histo'},
               'UserTable': {'args': {},
                                    'background_color': '16777215',
                                    'title': tr('Disconnected Users'),
                                    'type': 'UserTable',
                                    'view': 'table'},
               'UsersHistoryTable': {'args': { 'sort': 'DESC',
                                             'sortby': 'username' },
                                    'background_color': '16777215',
                                    'title': tr('User session history'),
                                    'type': 'UsersHistoryTable',
                                    'view': 'table'},
               'UserTable_accept': {'args': {'raw_label': 1},
                                    'background_color': '16777215',
                                    'title': tr('Most Accepted Users'),
                                    'type': 'UserTable',
                                    'view': 'histo'},
               'UserTable_drop': {'args': {'sort': 'DESC',
                                             'sortby': 'end_time',
                                             'raw_label': 0},
                                    'background_color': '16777215',
                                    'title': tr('Last Dropped Users'),
                                    'type': 'UserTable',
                                    'view': 'histo'},
               'UserTable_most': {'args': {'sort': 'DESC',
                                             'sortby': 'packets'},
                                    'background_color': '16777215',
                                    'title': tr('Most Active Users'),
                                    'type': 'UserTable',
                                    'view': 'histo'},
               'UserTable_drop': {'args': {'sort': 'DESC',
                                             'sortby': 'packets',
                                             'raw_label': 0},
                                    'background_color': '16777215',
                                    'title': tr('Most Dropped Users'),
                                    'type': 'UserTable',
                                    'view': 'histo'},
    },
     'links': {'client_app': 'client_app',
               'dport': 'dport',
               'ip_daddr_str': 'ip_daddr_str',
               'ip_saddr_str': 'ip_saddr_str',
               'orig_ipv6_src': 'ip_saddr_str',
               'orig_ipv6_dst': 'ip_daddr_str',
               'orig_ipv4_src': 'ip_saddr_str',
               'orig_ipv4_dst': 'ip_daddr_str',
               'orig_port_src': 'sport',
               'orig_port_dst': 'dport',
               'packet_id': 'packet_id',
               'sport': 'sport',
               'username': 'username',
               'domain': 'proxy_domain',
               'proxy_username': 'proxy_user'},
     'pages': {'app_accept': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                              'frames': {'0': {'frags': 'AppTable_currently',
                                               'pos': 0},
                                         '1': {'frags': 'AppTable_accept',
                                               'pos': 1},
                                         '2': {'frags': 'UserAppTable_accept',
                                               'pos': 2}},
                              'title': tr('Accepted Applications')},
               'app_drop': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                            'frames': {'0': {'frags': 'AppTable_currently',
                                             'pos': 0},
                                       '1': {'frags': 'AppTable_drop',
                                             'pos': 1},
                                       '2': {'frags': 'UserAppTable_drop',
                                             'pos': 2}},
                            'title': tr('Dropped Applications')},
               'app_misc': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                            'frames': {'0': {'frags': 'AppTable_currently',
                                             'pos': 0},
                                       '1': {'frags': 'AppTable',
                                             'pos': 1},
                                       '3': {'frags': 'AppTable_most_drop',
                                             'pos': 3}},
                            'title': tr('General Applications')},
               'client_app': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                              'frames': {'0': {'frags': 'PacketTable',
                                               'pos': 0},
                                         '1': {'frags': 'UserTable',
                                               'pos': 1},
                                         '2': {'frags': 'TCPTable',
                                               'pos': 2},
                                         '3': {'frags': 'LastPacketsStream_drop',
                                               'pos': 3}},
                              'title': tr('Application')},
               'dport': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                         'frames': {'0': {'frags': 'UserTable',
                                          'pos': 0
                                         },
                                    '1': {'frags': 'AppTable',
                                          'pos': 1
                                         },
                                    '2': {'frags': 'PacketTable',
                                          'pos': 2
                                         },
                                   },
                         'title': tr('Port Information')},
               'host_accept': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                               'frames': {'0': {'frags': 'IPsrcTable_active',
                                                'pos': 0},
                                          '1': {'frags': 'IPsrcTable_accept',
                                                'pos': 1},
                                          '2': {'frags': 'HostPortTable_accept',
                                                'pos': 2}},
                               'title': tr('Accepted Hosts')},
               'host_drop': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                             'frames': {'0': {'frags': 'IPsrcTable_drop',
                                              'pos': 0},
                                        '1': {'frags': 'HostPortTable_drop',
                                              'pos': 1}},
                             'title': tr('Dropped Hosts')},
               'host_misc': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                             'frames': {'0': {'frags': 'IPsrcTable_active',
                                              'pos': 0},
                                        '1': {'frags': 'IPsrcTable',
                                              'pos': 1},
                                        '3': {'frags': 'IPsrcTable_drop',
                                              'pos': 3}},
                             'title': tr('General Hosts')},
               'ip_daddr_str': {'args': {},
                              'filters': 'ip_saddr_ste ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                            'frames': {'0': {'frags': 'PacketTable',
                                             'pos': 0},
                                       '1': {'frags': 'TCPTable',
                                             'pos': 1},
                                       '3': {'frags': 'LastPacketsStream_drop',
                                             'pos': 3}},
                            'title': tr('Host')},
               'ip_saddr_str': {'args': {},
                            'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                            'frames': {'0': {'frags': 'PacketTable',
                                             'pos': 0},
                                       '1': {'frags': 'TCPTable',
                                             'pos': 1},
                                       '2': {'frags': 'UserTable',
                                             'pos': 2},
                                       '3': {'frags': 'LastPacketsStream',
                                             'pos': 3}},
                            'title': tr('Host')},
               'last_packets': {'args': {},
                              'force_cumulative': True,
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                                'frames': {'0': {'frags': 'PacketTable',
                                                 'pos': 0}},
                                'title': tr('Last Packets')},
               'main': {'args': {},
                        'frames': {'0': {'frags': 'AppTable_last_drop', 'pos': 0},
                                   '1': {'frags': 'UserTable_drop', 'pos': 1},
                                   '2': {'frags': 'TrafficStream LastPacketsStream LastPacketsStream_drop',
                                         'pos': 2},
                                   '3': {'frags': 'IPsrcTable_drop', 'pos': 3}},
                        'title': tr('Main View')},
               #'nutrack': {'args': {},
               #            'force_cumulative': True,
               #            'filters': 'authenticated user_id status orig_ipv4_src orig_port_src orig_ipv4_dst orig_port_dst' \
               #                       'repl_ipv4_src repl_port_src repl_ipv4_dst repl_port_dst',
               #            'frames': {'0': {'frags': 'ConntrackTable',
               #                             'pos': 0}},
               #            'title': tr('Active Connections')},
#               'idsips': {'args': {},
#                          'frames': {'0': {'frags': 'IDSIPSTable',
#                                           'pos': 0}},
#                          'title': tr('IDS-IPS Logs')},
#               'proxy':  {'args': {},
#                          'frames': {'0': {'frags': 'ProxyDomainsTable',
#                                           'pos': 0},
#                                     '2': {'frags': 'ProxyHostsTable',
#                                           'pos': 2}},
#                          'title': tr('Proxy Logs')},
               'proxy_user': {'args': {},
                              'filters': 'ip_saddr_str proxy_username proxy_state domain start_time end_time url',
                              'frames': {'0': {'frags': 'ProxyDomainsTable',
                                               'pos': 0}},
                              'title': tr('Proxy User'),
                              'links': {'domain': 'proxy_list'}},
               'proxy_domain': {'args': {},
                              'filters': 'ip_saddr_str proxy_state domain start_time end_time url',
                              'frames': {'0': {'frags': 'ProxyHostsTable',
                                               'pos': 0}},
                              'title': tr('Proxy Domain'),
                              'links': {'ip_saddr_str': 'proxy_list'}},
               'proxy_list': {'args': {},
                              'filters': 'ip_saddr_str proxy_username proxy_state domain start_time end_time url',
                              'frames': {'0': {'frags': 'ProxyRequestTable',
                                               'pos': 0}},
                              'title': tr('Proxy Requests')},
               'packet_id': {'args': {},
                             'frames': {'0': {'frags': 'PacketInfo', 'pos': 0}},
                             'title': tr('Packet Information')},
               'report1': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                           'frames': {'0': {'frags': 'UserTable_most_drop',
                                            'pos': 0},
                                      '1': {'frags': 'UserTable_most',
                                            'pos': 1},
                                      '2': {'frags': 'UserAppTable_drop UserAppTable_accept',
                                            'pos': 2},
                                      '3': {'frags': 'AppTable_most_drop',
                                            'pos': 3}},
                           'title': tr('User Report')},
               'report2': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                           'frames': {'0': {'frags': 'PacketsCountTable_drop PacketsCountTable',
                                            'pos': 0},
                                      '1': {'frags': 'UserTable_most_drop UserTable_most',
                                            'pos': 1},
                                      '2': {'frags': 'UserAppTable_drop',
                                            'pos': 2},
                                      '3': {'frags': 'IPsrcTable_most_drop IPdstTable',
                                            'pos': 3},
                                      },
                           'title': tr('Top')},
               'report3': {'args': {},
                           'frames': {},
                           'title': tr('')},
               'report4': {'args': {},
                           'frames': {},
                           'title': tr('')},
               'report5': {'args': {},
                           'frames': {},
                           'title': tr('')},
               'sport': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                         'frames': {'0': {'frags': 'UserTable',
                                          'pos': 0
                                         },
                                    '1': {'frags': 'AppTable_last_drop',
                                          'pos': 1
                                         },
                                    '2': {'frags': 'PacketTable',
                                          'pos': 2
                                         },
                                   },
                         'title': tr('Port Information')},
               'user_accept': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                               'frames': {'0': {'frags': 'ConUserTable',
                                                'pos': 0},
                                          '1': {'frags': 'UserTable_accept',
                                                'pos': 1},
                                          '2': {'frags': 'UserAppTable_accept',
                                                'pos': 2}},
                               'title': tr('Accepted Users')},
               'user_drop': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                             'frames': {'0': {'frags': 'ConUserTable',
                                              'pos': 0},
                                        '1': {'frags': 'UserTable_drop',
                                              'pos': 1},
                                        '2': {'frags': 'UserAppTable_drop',
                                              'pos': 2}},
                             'title': tr('Dropped Users')},
               'user_history': {'args': {},
                              'filters': 'ip_saddr_str username ',
                                'frames': {'0': {'frags': 'UsersHistoryTable',
                                                 'pos': 0}},
                             'title': tr('User session history')},
               'user_misc': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                             'frames': {'0': {'frags': 'ConUserTable',
                                              'pos': 0},
                                        '1': {'frags': 'UserTable',
                                              'pos': 1},
                                        '3': {'frags': 'UserTable_drop',
                                              'pos': 3}},
                             'title': tr('All Users')},
               'username': {'args': {},
                              'filters': 'ip_saddr_str ip_daddr_str ip_addr username sport '\
                                         'dport raw_label proto oob_prefix client_app start_time end_time firewall',
                            'frames': {'0': {'frags': 'PacketTable',
                                             'pos': 0},
                                       '1': {'frags': 'AppTable',
                                             'pos': 1},
                                       '2': {'frags': 'IPdstTable', 'pos': 2},
                                       '3': {'frags': 'LastPacketsStream_drop',
                                             'pos': 3}},
                            'title': tr('User')}},
     'pagesindex': {
                    'general': {'pages': 'main last_packets nutrack',
                                'pos': 0,
                                'title': tr('General')},
                    'user': {'pages': 'user_misc user_drop user_accept user_history',
                             'pos': 1,
                             'title': tr('User')},
                    'application': {'pages': 'app_misc app_drop app_accept',
                                    'pos': 2,
                                    'title': tr('Application')},
                    'hosts': {'pages': 'host_misc host_drop host_accept',
                              'pos': 3,
                              'title': tr('Hosts')},
                    'reports': {'pages': 'report1 report2',
                                'pos': 4,
                                'title': tr('Reports')},
                    'bookmarks': {'pages': '', 'pos': 5, 'title': tr('Bookmarks')},
                    'history': {'pages': '', 'pos': 6, 'title': tr('History')},
                },
    'reports': {'top': {'title':    tr('Top Report'),
                        'filters':  (),
                        'scenario': [('newPage', tr('Activity'), [1,1]),
                                     ('append', tr('Dropped packets per day'), 'histo', 'PacketsCountTable', {'raw_label': 0, 'sortby': 'packets'}),
                                     ('append', tr('All packets per day'), 'histo', 'PacketsCountTable', {'sortby': 'packets'}),
                                     #('newPage', tr('Users sessions'), [1]),
                                     #('append', '', 'gantt', 'UsersHistoryTable', {'extra': False, 'limit': 200}),
                                     ('newPage', tr('Users'), [1,1]),
                                     ('append', tr('Dropped user applications'), 'table', 'UserAppTable', {'raw_label': 0, 'sortby': 'packets'}),
                                     ('append', tr('Accepted user applications'), 'table', 'UserAppTable', {'raw_label': 1, 'sortby': 'packets'}),
                                     ('newPage', tr('Users'), [1,1]),
                                     ('append', tr('Most dropped users'), 'histo', 'UserTable', {'raw_label': 0, 'sortby': 'packets'}),
                                     ('append', tr('Most accepted users'), 'histo', 'UserTable', {'raw_label': 1, 'sortby': 'packets'}),
                                     ('newPage', tr('Hosts'), [1]),
                                     ('append', tr('Most destination'), 'pie', 'IPdstTable', {'sortby': 'packets'}),
                                     ('newPage', tr('Hosts'), [1,1]),
                                     ('append', tr('Most dropped hosts'), 'table', 'IPsrcTable', {'raw_label': 0, 'sortby': 'packets'}),
                                     ('append', tr('Most accepted hosts'), 'table', 'IPsrcTable', {'raw_label': 1, 'sortby': 'packets'}),
                                     ('newPage', tr(''), [1]),
                                     ('appendTopOfThePop', 'Top 10 dropped users with their Top 10 ports',
                                                               'UserTable', {'sortby': 'packets', 'limit': 10, 'raw_label': 0}, 'username',
                                                               'TCPTable',  {'sortby': 'packets', 'limit': 10, 'raw_label': 0}),
                                    ]
                        },
                'user': {'title':    tr('User Report'),
                         'filters':  ('username',),
                         'scenario': [('newPage', tr('Activity'), [1,1]),
                                      ('append', tr('Dropped packets per day'), 'histo', 'PacketsCountTable', {'raw_label': 0, 'sortby': 'packets'}),
                                      ('append', tr('All packets per day'), 'histo', 'PacketsCountTable', {'sortby': 'packets'}),
                                      ('newPage', tr('Applications'), [1,1]),
                                      ('append', tr('Dropped applications'), 'table', 'AppTable', {'raw_label': 0, 'sortby': 'packets'}),
                                      ('append', tr('Accepted applications'), 'table', 'AppTable', {'raw_label': 1, 'sortby': 'packets'}),
                                     ]
                        },
               },
    'printer': {}
    }


