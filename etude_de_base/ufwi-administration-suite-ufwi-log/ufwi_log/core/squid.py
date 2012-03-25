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

import socket
from IPy import IP

from ufwi_rpcd.common import tr
from ufwi_rpcd.backend import RpcdError

import filters
from tablebase import TableBase
from ufwi_rpcd.backend.anonymization import anonymizer

class FilterProxyUser(filters.FilterBase):
    def build(self, request, filters):
        return 'username = %s' % request.database.escape(self.value)

class FilterProxyState(filters.FilterBase):
    STATES = {'accepted' : ['TCP_DENIED', 'UDP_DENIED'],
              'dropped' : ['TCP_DENIED', 'UDP_DENIED']
             }

    ASSOCIATION = {'accepted' : ['!=', 'AND'], 'dropped' : ['=', 'OR']}

    def build(self, request, filters):
        query = ''
        value = request.database.escape(self.value)
        if "'" in value:
            value = value[1:-1]
        try:
            states = self.STATES[value]
        except Exception:
            return ''

        var = self.ASSOCIATION[value]
        for index, raw_label in enumerate(states):
            print "INDEX : ", index
            if index == 0:
                query += "raw_label %s '%s'" % (var[0], raw_label)
            else:
                query += " %s raw_label %s '%s'" % (var[1], var[0], raw_label)

        print "FILTER PROXY STATE : ", query
        return query
        #return 'raw_label = %s' % request.database.escape(self.value)

class FilterBeginTime(filters.FilterBase):
    def build(self, request, filters):
        self.assert_int()
        return '%s >= %s' % ('timestamp', self.value)

class FilterUrl(filters.FilterBase):
    def build(self, request, filters):
        return 'url LIKE %s' % (request.database.escape('%' + self.value + '%'))

class FilterEndTime(filters.FilterBase):
    def build(self, request, filters):
        self.assert_int()
        return '%s <= %s' % ('timestamp', self.value)

class FilterSquidIP(filters.FilterIP):
    def ip_pool(self, request, filters, function):

        try:
            ips = socket.gethostbyname_ex(self.value)[2]
        except socket.gaierror:
            try:
                ip = IP(self.value)
                if ip.version() > request.database.ip_type:
                    raise ValueError('IP address must be an IPv%d' % request.database.ip_type)
            except ValueError, e:
                raise RpcdError(tr('Please enter a correct hostname or IP: %s') % e)
            ips = [self.value]

        s = ''
        for ip in ips:
            if s:
                s += ' OR '

            ip = self.str2ip(request, ip)
            s += '(%s)' % function(self.key, ip)

        return '(%s)' % s

    def entry_form(self, entry):
        # username, packets, start_time, end_time
        result = ((anonymizer.anon_username(self.ctx, entry[0])),)
        result += entry[1:]

        return result


class ProxyRequestTable(TableBase):

    columns = ['ip_saddr_str', 'proxy_state', 'volume', 'url', 'oob_time_sec']

    default_args = {'sortby': 'oob_time_sec',
                    'sort':   'DESC',
                    'limit':  30,
                    'start':  0}

    filters_list = {'ip_saddr_str':       FilterSquidIP,
                    'proxy_username': FilterProxyUser,
                    'proxy_state':    FilterProxyState,
                    'domain':         filters.FilterRaw,
                    'start_time':     FilterBeginTime,
                    'end_time':       FilterEndTime,
                    }

    def entry_form(self, entry):
        result = (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[0])),)
        result += entry[1:]
        return result

    def __call__(self, **args):
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('ip_saddr_str', 'proxy_state', 'volume', 'url', 'oob_time_sec'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))

        result = self._sql_query(args, "squid_select_requests")

        result.addCallback(self._print_result)
        return result

class ProxyDomainsTable(TableBase):

    columns = ['domain', 'requests', 'volume', 'start_time', 'end_time']

    default_args = {'sortby': 'end_time',
                    'sort':   'DESC',
                    'count':  False,
                    'limit':  30,
                    'start':  0}

    filters_list = {'ip_saddr_str':   FilterSquidIP,
                    'proxy_username': FilterProxyUser,
                    'start_time': FilterBeginTime,
                    'end_time':   FilterEndTime,
                    'domain' : filters.FilterRaw,
                    'url' : FilterUrl,
                    'proxy_state' : FilterProxyState,
                    }

    def __call__(self, **args):
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('domain', 'requests', 'volume', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "squid_count_domains", display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "squid_select_domains")
            result.addCallback(self._print_result)

        return result

class ProxyUsersTable(TableBase):

    columns = ['proxy_username', 'requests', 'volume', 'start_time', 'end_time']

    default_args = {'sortby': 'end_time',
                    'sort':   'DESC',
                    'count':  False,
                    'limit':  30,
                    'start':  0}

    filters_list = {'ip_saddr_str':   FilterSquidIP,
                    'domain':     filters.FilterRaw,
                    'start_time': FilterBeginTime,
                    'end_time':   FilterEndTime,
                    }

    def entry_form(self, entry):
        # username, packets, start_time, end_time
        result = ((anonymizer.anon_username(self.ctx, entry[0])),)
        result += entry[1:]
        return result

    def __call__(self, **args):
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('proxy_username', 'requests', 'volume', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "squid_count_users", display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "squid_select_users")
            result.addCallback(self._print_result)

        return result

class ProxyHostsTable(TableBase):

    columns = ['ip_saddr_str', 'requests', 'volume', 'start_time', 'end_time']

    default_args = {'sortby': 'end_time',
                    'sort':   'DESC',
                    'count':  False,
                    'limit':  30,
                    'start':  0}

    filters_list = {'ip_saddr_str':   FilterSquidIP,
                    'domain':     filters.FilterRaw,
                    'start_time': FilterBeginTime,
                    'end_time':   FilterEndTime,
                    'url' : FilterUrl,
                    'proxy_state' : FilterProxyState,
                    }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [list of tuple]
        """

        # ip, requests, start_time, volume, start_time, end_time
        result = (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[0])),)
        result += entry[1:]
        return result

    def __call__(self, **args):
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('ip_saddr_str', 'requests', 'volume', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "squid_count_ipaddress", display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "squid_select_ipaddress")
            result.addCallback(self._print_result)

        return result

