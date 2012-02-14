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

$Id$
"""

from ufwi_rpcd.common import tr

from ufwi_log.client.qt.fetchers import NulogTableFetcher, \
                                     NuConntrackFetcher, \
                                     NuAuthFetcher, \
                                     OcsFetcher, \
                                     NulogStreamFetcher, \
                                     RealTimeStreamFetcher, \
                                     IDSIPSFetcher

class FragType:
    """ Class to give information of a fragment type """

    def __init__(self, title, fetcher, views):
        """
            @param title [string] the default title of this kind of fragment
            @param views [list] list of available views for this fragment type
        """

        assert isinstance(views, tuple)

        self.title = title
        self.views = views
        self.fetcher = fetcher

frag_types = {'TCPTable':          FragType(tr('TCP ports'),                NulogTableFetcher,      ('table', 'pie', 'histo')),
              'UDPTable':          FragType(tr('UDP ports'),                NulogTableFetcher,      ('table', 'pie', 'histo')),
              'IPsrcTable':        FragType(tr('Source IP'),                NulogTableFetcher,      ('table', 'pie', 'histo')),
              'IPdstTable':        FragType(tr('Destination IP'),           NulogTableFetcher,      ('table', 'pie', 'histo')),
              'UserTable':         FragType(tr('Users'),                    NulogTableFetcher,      ('table', 'pie', 'histo')),
              # Server version 3.0-1
              'PacketTable':       FragType(tr('Connections'),              NulogTableFetcher,      ('table',)),

              # Server version 3.0-2
              'LastPacket':       FragType(tr('Connections'),              NulogTableFetcher,      ('table',)),
              'InputPacket':       FragType(tr('Connections'),              NulogTableFetcher,      ('table',)),

              'AppTable':          FragType(tr('Applications'),             NulogTableFetcher,      ('table', 'pie', 'histo')),
              'UserAppTable':      FragType(tr('User applications'),        NulogTableFetcher,      ('table',)),
              'HostPortTable':     FragType(tr('Host port connections'),   NulogTableFetcher,      ('table',)),
              'UsersHistoryTable': FragType(tr('User session history'), NulogTableFetcher,      ('table',)),
              'AuthFail':          FragType(tr('User session history'), NulogTableFetcher,      ('table',)),
              'PacketInfo':        FragType(tr('Packet information'),              NulogTableFetcher,      ('packetinfo',)),
              'Stats':             FragType(tr('Statistics'),                    RealTimeStreamFetcher,  ('stats',)),
              'TrafficStream':     FragType(tr('Traffic (stream)'),           NulogStreamFetcher,     ('line',)),
              'LastPacketsStream': FragType(tr('Last connections (stream)'),      NulogStreamFetcher,     ('line',)),
              'LoadStream':        FragType(tr('Load (stream)'),              NulogStreamFetcher,     ('line',)),
              'MemoryStream':      FragType(tr('Memory usage'),             NulogStreamFetcher,     ('line',)),
              'ConntrackTable':    FragType(tr('Conntrack'),                NuConntrackFetcher,     ('table',)),
              'ConUserTable':      FragType(tr('Connected users'),          NuAuthFetcher,          ('table',)),
              'HostInformation':   FragType(tr('Host information'),                OcsFetcher,             ('table',)),
              'IDSIPSTable':       FragType(tr('IDS-IPS logs'),             IDSIPSFetcher,          ('table',)),
              'PacketsCountTable': FragType(tr('Number of connections'),            NulogTableFetcher,      ('histo',)),
              'ProxyRequestTable': FragType(tr('Proxy requests'),      NulogTableFetcher,      ('table',)),
              'ProxyDomainsTable': FragType(tr('Proxy top domains'),   NulogTableFetcher,      ('table', 'pie', 'histo')),
              'ProxyUsersTable':   FragType(tr('Proxy top users'),     NulogTableFetcher,      ('table', 'pie', 'histo')),
              'ProxyHostsTable':   FragType(tr('Proxy top hosts'),     NulogTableFetcher,      ('table', 'pie', 'histo')),
             }
