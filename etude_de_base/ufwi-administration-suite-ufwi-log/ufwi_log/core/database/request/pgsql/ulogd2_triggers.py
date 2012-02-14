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

from ulogd2 import Ulogd2Request

class Ulogd2TriggersRequest(Ulogd2Request):

    def __init__(self, database, tablename):
        Ulogd2Request.__init__(self, database, tablename)
        self.raw_label = None

    def get_count_column(self, filters):
        select = ''
        self.raw_label = None
        if 'raw_label' in filters.filters:
            self.raw_label = filters.args.pop('raw_label')
            filters.build(self)
            if self.raw_label:
                select = 'accepted'
            else:
                select = 'dropped'
        else:
            select = 'accepted + dropped'

        return select

    def reset_raw_label(self, filters):
        if not self.raw_label is None:
            filters.args['raw_label'] = self.raw_label
            filters.build(self)
            self.raw_label = None

    def getcolumn(func):
        def inner(self, filters, *args, **kwargs):
            column = self.get_count_column(filters)
            ret = func(self, filters, column, *args, **kwargs)
            self.reset_raw_label(filters)
            return ret

        return inner

    @getcolumn
    def count_packets(self, filters, column):

        select = 'SUM(%s)' % column
        if filters.have_only(firewall=False, username=True) or \
           filters.have_only(firewall=False, user_id=True):
            return "SELECT %s FROM users_stats %s" % (select, filters.getwhere())
        elif filters.have_only(firewall=False, ip_saddr_str=True):
            return "SELECT %s FROM hosts_stats %s" % (select, filters.getwhere())
        elif filters.have_only(firewall=False, client_app=True):
            return "SELECT %s FROM apps_stats %s" % (select, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return """SELECT COUNT(*) FROM %s %s """ % (self.nufw_view, filters.getwhere())

    @getcolumn
    def select_ip(self, filters, column, direction):
        """ List all ips which matches filters """

        if direction == 's' and filters.have_only(firewall=False, ip_saddr_str=False):
            return "SELECT ip_saddr_str, %s AS packets, first_time AS start_time, last_time AS end_time FROM hosts_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.select_ip(self, filters, direction)

    @getcolumn
    def count_ip(self, filters, column, direction):
        """ Count all dropped packets """

        if direction == 's' and filters.have_only(firewall=False, ip_saddr_str=False):
            return "SELECT SUM(%s) FROM hosts_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.count_ip(self, filters, direction)

    @getcolumn
    def select_apps(self, filters, column):

        if filters.have_only(firewall=False, client_app=False):
            return "SELECT client_app, %s AS packets, first_time AS start_time, last_time AS end_time FROM apps_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.select_apps(self, filters)

    @getcolumn
    def count_apps(self, filters, column):
        """ Count all dropped packets """

        if filters.have_only(firewall=False, client_app=False):
            return "SELECT SUM(%s) FROM apps_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.count_apps(self, filters)

    @getcolumn
    def select_user(self, filters, column):
        """ List all users who have dropped packets """

        if filters.have_only(firewall=False, user_id=False, username=False):
            return "SELECT username, %s AS packets, first_time AS start_time, last_time AS end_time FROM users_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.select_user(self, filters)

    @getcolumn
    def count_user(self, filters, column):
        """ Count all users packets which are dropped """

        if filters.have_only(firewall=False, user_id=False,username=False):
            return "SELECT SUM(%s) FROM users_stats %s" % (column, filters.getwhere())
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.count_user(self, filters)

    @getcolumn
    def select_userid(self, filters, column):

        if filters.have_only(firewall=False, user_id=False, username=False):
            return "SELECT username FROM users_stats %s" % filters.getwhere()
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.select_userid(self, filters)

    @getcolumn
    def select_userid_auth(self, filters, table):

        if filters.have_only(firewall=False, user_id=False, username=False):
            return "SELECT username FROM authfail %s" % filters.getwhere()
        else:
            self.reset_raw_label(filters)
            return Ulogd2Request.select_userid_auth(self, filters)


