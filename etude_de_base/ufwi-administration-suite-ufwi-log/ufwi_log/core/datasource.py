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

from cStringIO import StringIO
from ufwi_rpcd.backend import tr, RpcdError
import datetime
from copy import deepcopy
from twisted.internet import defer
from IPy import IP

from filters import FiltersList

def formatIPv6(ipv6):
    """
    >>> formatIPv6(IP('::ffff:192.168.0.1'))
    '::ffff:192.168.0.1'
    >>> formatIPv6(IP('2001:200:0:8002:203:47ff:fea5:3085'))
    '2001:200:0:8002:203:47ff:fea5:3085'
    """
    if ipv6.ip >> 32 == 0xffff:
        # Fix for IPy < 0.60
        return "::ffff:%s" % IP(ipv6.ip & 0xffffffff, 4)
    else:
        return ipv6.strCompressed()

class DataSource:

    default_args = {}
    filters_list = {}

    def __init__(self, ctx, database):
        self.database = database
        self.args = deepcopy(self.default_args)
        self.filters = {}
        self.ctx = ctx

    def getFiltersList(self):
        return [key for key in self.filters_list.keys() if not key.startswith('_')]

    def ip2str(self, ip):
        """ Get an IP integer and return a formated IP string
            @param ip [integer]
            @return [string]
        """

        if self.database.dbtype == 'pgsql':
            return ip

        if self.database.ip_type == 6:
            i = 0
            for j in xrange(len(ip)):
                i |= ord(ip[j]) << (8 * (len(ip) - j - 1))

            ipret = IP(i, 6)
            return formatIPv6(ipret)
        else:
            try:
                return IP(int(ip), 4).strCompressed()
            except ValueError:
                raise RpcdError(tr('Invalid IP format. Please change IP type value (4 -> 6) in UfwiLog configuration'))

    def proto2str(self, proto):
        """
        Get an integer which describes an IP protocol and return the name.
        @param proto [integer]
        @return [str]
        """

        # TODO: find a method to get proto name from a list like /etc/protocols.
        protos = {6:  'tcp',
                  17: 'udp',
                  1:  'icmp',
                  2:  'igmp',
                  47: 'gre',
                  58: 'ipv6-icmp',
                  50: 'esp',
                  51: 'ah',
                 }

        if protos.has_key(proto):
            return protos[proto]
        else:
            return str(proto)

    def _sql_query(self, userargs, functioname, *args, **kwargs):
        """ Send a query to SGDB and receive answer in _print_result() method.
            @param query [string] SQL formated query

            @return [Deferred] This is a deferred object. If this method is called by a
                               SOAP client, return this Deferred objet to tell SOAP to
                               wait callback result to send it to client.
        """

        start_time = None
        end_time = None
        query = StringIO()

        filters = FiltersList(self.ctx, self.filters_list, userargs)

        # Actual 'ulog' table is from the first packet (0) and now.
        self.database.archives[self.database.ulog] = (self.database.archives[self.database.ulog][0], datetime.datetime.today())

        if userargs.has_key('no_limit'):
            if self.args.has_key('limit'):
                self.args.pop('limit')
            if userargs.has_key('limit'):
                userargs.pop('limit')

        if userargs.has_key('start_time'):
            start_time = datetime.datetime.fromtimestamp(int(userargs['start_time']))
        else:
            start_time = self.database.archives[self.database.ulog][0]

        if userargs.has_key('end_time'):
            end_time = datetime.datetime.fromtimestamp(int(userargs['end_time']))
        else:
            end_time = self.database.archives[self.database.ulog][1]

        assert start_time
        assert end_time

        display = True
        if kwargs.has_key('display') and not kwargs['display']:
            display = False
            kwargs.pop('display')

        for table, date in self.database.archives.iteritems():
            if date[1] and date[0] and start_time < date[1] and end_time > date[0]:
                request = self.database.createRequest(table)
                if query.getvalue():
                    query.write(' UNION ')

                filters.build(request)
                query.write(getattr(request, functioname)(filters, *args, **kwargs))

        self.filters.update(filters.filters)

        if not query.getvalue():
            # There isn't any query, so we exit
            return defer.succeed(([], 0))

        # Server Version : 3.0-2
        if functioname == "select_packets":
            session = self.ctx.getSession()

            if 'ufwi_log_client_version' in session and session['ufwi_log_client_version'] >= "3.0-2":
                if self.args.has_key('input'):
                    if not self.args['input']:
                        query.write(" AND COALESCE(oob_hook, 2) != 1 ")
                    elif self.args['input']:
                        query.write(" AND oob_hook = 1 ")

        if display:
            if self.args.has_key('sortby') and self.args.has_key('sort'):
                query.write(' ORDER BY %s %s' % (self.args['sortby'], self.args['sort']))

            limit = None
            if self.args.has_key('limit') or userargs.has_key('limit'):
                limit = self.args['limit'] if self.args.has_key('limit') else userargs['limit']
                print "LIMIT ", limit
            start = None
            if self.args.has_key('start'):
                start = self.args['start']
            if limit is not None and start is not None:
                query.write(' LIMIT %s OFFSET %d' % (limit, start))

        return self.database.query(query.getvalue())

    def _arg_int(self, args, argname):
        """ Check if argname is in args, and if it is an integer
            @param args [dict] Args where we look for argname
            @param argname [string] Argument we want to check
            @return NOTHING. Value is changed in self.args
        """

        if not args.has_key(argname):
            if not self.args.has_key(argname):
                raise RpcdError(tr("Missing argument '%s'"), argname)
            else:
                return

        value = args[argname]
        try:
            self.args[argname] = int(value)
        except:
            raise RpcdError(tr('%s must be an integer'), argname)

    def _arg_bool(self, args, argname):

        if not args.has_key(argname):
            if not self.args.has_key(argname):
                raise RpcdError(tr("Missing argument '%s'"), argname)
            else:
                return

        value = args[argname]
        if value == 1 or value is True or value == '1' or value == 'true' or value == 'True' or value == 'yes' or value == 'y':
            self.args[argname] = True
        else:
            self.args[argname] = False

    def _arg_in(self, args, argname, lst):
        """ Look for argname in args, and check if it is in lst.
            @param args [dict] Args
            @param argname [string] Argument name
            @param lst [list] Value may be in this list.
            @return NOTHING. Value is changed in self.args
        """

        if not args.has_key(argname):
            return

        if args[argname] in lst:
            self.args[argname] = args[argname]
