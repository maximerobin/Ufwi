# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
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
import socket
from ufwi_rpcd.backend import tr, RpcdError
from datetime import datetime
from IPy import IP
from ufwi_rpcd.backend.anonymization import anonymizer
from copy import copy

class FiltersList:

    def __init__(self, ctx, filters_types, args):
        self.filters_types = filters_types
        self.args = args
        self.filters = {}
        self.where = ''
        self.ctx = ctx

    def build(self, request):

        where = StringIO()
        self.filters = {}
        for name, filterClass in self.filters_types.iteritems():
            if not name in self.args:
                continue

            filter = filterClass(self.ctx, name, self.args[name])
            s = filter.getwhere(request, self)
            if not s:
                continue

            if not where.getvalue():
                where.write('WHERE ')
            else:
                where.write(' AND ')

            where.write(s)
            self.filters[name] = self.args[name]

        self.where = where.getvalue()

    def getwhere(self):
        return self.where

    def have_only(self, **kwargs):
        """
        Check contained filters.

        All arguments are filters names concerned, with True value if
        needed, or False if optional.
        """

        filters = copy(self.filters)
        for key, needed in kwargs.iteritems():
            try:
                filters.pop(key)
            except KeyError:
                if needed:
                    return False

        return not filters

class FilterBase:

    def __init__(self, ctx, key, value):
        self.ctx = ctx
        self.key = key
        self.value = value
        self.where = None

    def getwhere(self, request, filters):
        if self.where:
            return self.where

        return self.build(request, filters)

    def build(self, request, filters):
        raise NotImplementedError()

    def assert_int(self):
        try:
            self.value = int(self.value)
        except ValueError:
            raise RpcdError(tr("Please specify an integer value"))

class FilterRaw(FilterBase):
    def build(self, request, filters):
        return '%s = %s' % (self.key,
                            request.database.escape(self.value))

class FilterLike(FilterBase):
    def build(self, request, filters):
        return '%s LIKE %s' % (self.key, request.database.escape('%%%s%%' % self.value))

class FilterApp(FilterLike):
    def __init__(self, ctx, key, value):
        if '\\' in value:
            values = value.split("\\")
            value = '\\\\'.join(values)

        value = anonymizer.real_appname(ctx, value)
        FilterLike.__init__(self, ctx, key, value)

class FilterFirewall(FilterBase):

    def build(self, request, filters):
        if not request.is_multisite():
            raise RpcdError(tr("The SQL scheme doesn't support the '%s' field"), self.key)

        return '%s = %s' % (self.key,
                            request.database.escape(self.value))

class FilterIP(FilterBase):

    def __init__(self, ctx, key, value):
        value = anonymizer.real_ipaddr(ctx, value)
        FilterBase.__init__(self, ctx, key, value)

    def build(self, request, filters):
        return self.ip_pool(request, filters, request.database.whereIP)

    def str2ip(self, request, string):
        """ Get a string to return an IP integer
            @param string [string]  IP string
            @return [IP]  an IP object
        """
        if request.database.ip_type == 6:
            if IP(string).iptype() == 'IPV4COMP':
                string = '::ffff:' + string.lstrip(':')
        return IP(string)

    def ip_pool(self, request, filters, function):

        try:
            if not self.value:
                raise RpcdError('Service does not exist, or you need permissions to use it')
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

class FilterIPReverse(FilterIP):

    def build(self, request, filters):
        return self.ip_pool(request, filters, request.database.whereIP_REVERSE)

class FilterIPBoth(FilterIP):

    def build(self, request, filters):
        if not filters.args.has_key('ip_from') or not filters.args['ip_from'] in ('s', 'd'):
            return '(%s OR %s)' % (self.source(request, filters),
                                   self.dest(request, filters))
        else:
            self.key = 'ip_%saddr' % filters.args['ip_from']
            return self.ip_pool(request, filters, request.database.whereIP)

    def source(self, request, filters):
        self.key = 'ip_saddr_str'
        return self.ip_pool(request, filters, request.database.whereIP)

    def dest(self, request, filters):
        self.key = 'ip_daddr_str'
        return self.ip_pool(request, filters, request.database.whereIP)

class FilterPort(FilterBase):

    def build(self, request, filters):
        self.assert_int()

        proto = ('tcp', 'udp')
        if not filters.args.has_key('proto') or not filters.args['proto'] in proto:
            return '(COALESCE(%s,%s) = %s)' % ('tcp_%s' % self.key,
                                             'udp_%s' % self.key, self.value)
        else:
            return '%s = %s' % ('%s_%s' % (filters.args['proto'], self.key),
                                self.value)

class FilterInt(FilterBase):

    def build(self, request, filters):
        #self.assert_int()

        return "%s = '%s'" % (self.key, self.value)

class FilterUserID(FilterInt):
    def __init__(self, ctx, key, value):
        value = anonymizer.real_username(ctx, value)
        FilterInt.__init__(self, ctx, 'username', value)

class FilterProto(FilterBase):

    def build(self, request, filters):
        protos = {'tcp':   6,
                  'udp':   17,
                  'icmp':  1,
                  'igmp':  2}

        try:
            proto = protos[self.value]
            return '%s = %s' % ('ip_protocol', proto)
        except KeyError:
            raise RpcdError(tr('Protocol must be tcp or udp (is %s)'), self.value)
            raise RpcdError(tr('Unknown protocol: %s'), self.value)

class FilterState(FilterBase):
    def build(self, request, filters):
        self.assert_int()

        if self.value == -1:
            # -1 = ALL
            return ''

        if self.value != 0 and self.value != 1:
            raise RpcdError(tr('State must be 0 (dropped) or 1 (accepted).'))

        return '%s = %s' % (self.key, request.raw_label2i(self.value))

class FilterBeginTime(FilterBase):

    def build(self, request, filters):
        self.assert_int()

        return '%s >= %s' % ('oob_time_sec', self.value)

class FilterBeginTime_auth(FilterBase):

    def build(self, request, filters):
        self.assert_int()
        s_time = datetime.fromtimestamp(self.value)

        return "%s >= '%s'" % ('time', s_time)

class FilterEndTime(FilterBase):

    def build(self, request, filters):
        self.assert_int()

        return '%s <= %s' % ('oob_time_sec', self.value)

class FilterEndTime_auth(FilterBase):

    def build(self, request, filters):
        self.assert_int()
        e_time = datetime.fromtimestamp(self.value)

        return "%s <= '%s'" % ('time', e_time)

class FilterInterval(FilterBase):

    def build(self, request, filters):
        self.assert_int()

        return '%s >= %s' % ('timestamp',
                             request.database.kw_datetime % ('%s - %d' % (request.database.kw_timestamp % 'Now()', int(self.value))))
