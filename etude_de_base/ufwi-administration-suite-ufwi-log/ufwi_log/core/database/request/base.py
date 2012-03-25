# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
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

import re

class IRequest:
    """ This class is used to abstract SQL requests.
        Use the same interface on a child class to make other requests..
    """

    def __init__(self, database, tablename):
        """ Create a database request
            @param database [DataBase] database object
            @param tablename [string] ulog table name (can be an archive table)
            @param filters [dict]  dict of filters

            TODO: for now it isn't really useful to give the "tablename"
                  argument because it is database.ulog, but... it can
                  become useful soon.
        """

        self.database = database
        self.ulog = tablename

        # This is usefull to know if we work with an archive table, and
        # which prefix use, for example for usersstats table.
        m = re.match("%s(.*)" % self.database.ulog, self.ulog)
        self.sufix = m and m.groups()[0] or ''

    def is_multisite(self):
        return False

    def raw_label2i(self, raw_label):
        return raw_label

    def rotate_imported(self, period):
        raise NotImplementedError()

    def select_exportable_data(self, proto, begin, end):
        raise NotImplementedError()

    def insert_imported_data(self, proto, firewall, s):
        raise NotImplementedError()

    def select_packets(self, where):
        """ Method used to select all packets which matches "where" clause. """
        raise NotImplementedError()

    def count_packets(self, where):
        raise NotImplementedError()

    def get_packet(self, _id):
        """ Get a specific packet with his _id """
        raise NotImplementedError()

    def select_conusers(self, where):
        """ Get all connected users """
        raise NotImplementedError()

    def select_ports(self, proto, where, filters):
        """ List all ports """
        raise NotImplementedError()

    def count_port(self, proto, where, filters):
        """ Count number of dropped ports on this protocol
            @param proto [string] 'tcp' or 'udp'
        """
        raise NotImplementedError()

    def select_ip(self, direction, where, filters):
        """ List all ips which matches filters """
        raise NotImplementedError()

    def count_ip(self, direction, where, filters):
        """ Count all dropped packets """
        raise NotImplementedError()

    def select_apps(self, where):
        raise NotImplementedError()

    def count_apps(self, where):
        """ Count all dropped packets """
        raise NotImplementedError()

    def select_user(self, where, filters):
        """ List all users who have dropped packets """
        raise NotImplementedError()

    def count_user(self, where, filters):
        """ Count all users packets which are dropped """
        raise NotImplementedError()

    def select_traffic(self, where):
        raise NotImplementedError()

    def select_tuple(self, field1, field2, where):
        raise NotImplementedError()

    def select_badhosts(self):
        raise NotImplementedError()

    def select_badusers(self):
        raise NotImplementedError()

    def count_average(self, minutes, where):
        raise NotImplementedError()

    def select_userid(self, where):
        raise NotImplementedError()

    def squid_select_requests(self, where):
        raise NotImplementedError()
