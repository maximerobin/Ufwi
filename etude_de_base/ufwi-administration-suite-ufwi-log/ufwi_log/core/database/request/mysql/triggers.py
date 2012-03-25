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

from .ulog import UlogRequest

class TriggerRequest(UlogRequest):
    """ This class, child of DataBase, is used to make SQL requests on help tables 'offenders',
        'tcp_ports, 'udp_ports' and 'usersstats'.
    """

    def select_ports(self, filters, proto):

        if filters.filters != {'raw_label': 0} or self.sufix:
            # We can only show all dropped packets, without any filter.
            return UlogRequest.select_ports(self, filters, proto)

        return """SELECT %s_dport, count AS packets, first_time AS start_time, last_time AS end_time
                    FROM %s_ports """ % (proto, proto)

    def count_port(self, filters, proto):

        if filters.filters != {'raw_label': 0} or self.sufix:
            return UlogRequest.count_port(self, filters, proto)

        return """SELECT SUM(count) FROM %s_ports""" % proto

    def select_ip(self, filters, direction):

        if filters.filters != {'raw_label': 0} or direction != 's' or self.sufix:
            return UlogRequest.select_ip(self, filters, direction)

        return """SELECT ip_addr_str, count AS packets, first_time AS start_time, last_time AS end_time
                    FROM offenders
               """

    def count_ip(self, filters, direction):

        if filters.filters != {'raw_label': 0} or direction != 's' or self.sufix:
            return UlogRequest.count_ip(self, filters, direction)

        return """SELECT SUM(count) FROM offenders"""

    def select_user(self, filters):

        if filters.filters != {'raw_label': 0} or self.sufix:
            return UlogRequest.select_user(self, filters)

        return """SELECT username, user_id, bad_conns AS packets, first_time AS start_time, last_time AS end_time
                    FROM usersstats
                    WHERE bad_conns > 0
                """

    def count_user(self, filters):

        if filters.filters != {'raw_label': 0} or self.sufix:
            return UlogRequest.count_user(self, filters)

        return """SELECT SUM(bad_conns) FROM usersstats"""


