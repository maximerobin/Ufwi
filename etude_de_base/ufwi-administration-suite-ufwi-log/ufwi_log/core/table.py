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

import struct
import re
import time
from IPy import IP

from ufwi_rpcd.common.defer import gatherResults

from tablebase import TableBase
from ufwi_rpcd.backend.anonymization import anonymizer
from ufwi_rpcd.backend import tr
import filters



class PacketTable(TableBase):

    columns = ['packet_id', 'source', 'ip_daddr_str', 'proto','sport', 'dport','oob_time_sec','oob_prefix']

    default_args = {'sortby': 'oob_time_sec',
                    'sort':   'DESC',
                    'limit':  30,
                    'start':  0,
                    'tiny':   False}

    class FilterUserLike(filters.FilterBase):
        def build(self, request, _filters):
            return filters.FilterLike(self.ctx, 'username', self.value).build(request, _filters)

    class FilterSource(filters.FilterBase):
        def build(self, request, filters_list):
            try:
                filter = filters.FilterUserID(self.ctx, 'username', self.value)
            except ValueError:
                filter = filters.FilterIP(self.ctx, 'ip_saddr_str', self.value)

            return filter.build(request, filters_list)

    filters_list = {'ip_saddr_str':   filters.FilterIP,
                    'ip_daddr_str':   filters.FilterIP,
                    'ip_addr':    filters.FilterIPBoth,
                    'username':   filters.FilterUserID,
                    #'source':     FilterSource,
                    'userlike':   FilterUserLike,
                    'sport':      filters.FilterPort,
                    'dport':      filters.FilterPort,
                    'raw_label':      filters.FilterState,
                    'proto':      filters.FilterProto,
                    'oob_prefix': filters.FilterLike,
                    'client_app': filters.FilterApp,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                    }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [tuple]

            packet_id, username, ip_saddr_str, ip_daddr_str, protocol, sport, dport, oob_time_sec, oob_prefix, raw_label """

        if entry[1]:
            _id = '1'
        else:
            _id = '0'
        result = ((_id, entry[0]),)

        if entry[1] and (not 'source' in self.filters or
                    not isinstance(self.filters['source'], (int,long)) and
                    (not isinstance(self.filters['source'], (str,unicode)) or not self.filters['source'].isdigit())):
            result += ((anonymizer.anon_username(self.ctx, entry[1])),)
        else:
            result += (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[2])),)
        result += (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[3])),)
        result += (self.proto2str(entry[4]),)

        if self.args['tiny']:
            result += entry[5:7]
        else:
            result += entry[5:8]

            # Stock ACL number, if exists, in 'acl' field
            # Parse "F42A:bla bla": acl type=FORWARD, acl id=42, decision=ACCEPT, comment="bla bla"
            match = entry[8] and re.match("([FIO])([0-9]+)([adrADRU]):(.*)", entry[8])
            if match:
                # Add column if doesn't exit
                try:
                    # If doesn't exist it will raise an exception
                    self.columns.index('acl')
                except ValueError:
                    self._add_column('acl')

                target = match.group(1)
                acl_id = match.group(2)
                decision = match.group(3)
                comment = match.group(4)

                #decision = {'a': 'ACCEPT',
                #            'd': 'DROP',
                #            'r': 'REJECT',
                #            'A': 'ACCEPT NUFW',
                #            'D': 'DROP NUFW',
                #            'R': 'REJECT NUFW',
                #            'U': 'UNAUTHENTICATED DROP'
                #           }.get(decision, decision)
                if decision == 'U' and entry[1] == None:
                    comment = comment + tr("(Missing authentication)")
                result += ((comment, entry[8]),)
                ip = IP(self.ip2str(entry[3]))
                result += ('%s:%s:acls-ipv%d' % (target, acl_id, ip.version()),)
            else:
                if entry[8] == "Drop " and entry[1] == None:
                     result += (entry[8] + tr("(Missing authentication)"),)
                else:
                    result += (entry[8],)

        self.states['%s' % entry[0]] = 1 if entry[9] else 0
        return result

    def make_tiny(self):
        self._remove_column('oob_time_sec')
        self._remove_column('oob_prefix')

    def check_args(self, args):
        """
            @param start [integer] first entry
            @param limit [integer] number of results
            @param sortby [string] field to sort by in ('packet_id', 'ip_saddr_str', 'ip_daddr_str', 'protocol',
                                                        'sport', 'dport', 'oob_time_sec', 'oob_prefix')
            @param sort [string] ASC or DESC
            @param ip_saddr_str [string] use a filter on this field
            @param ip_daddr_str [string] use a filter on this field
            @param tcp_sport [string] use a filter on this field
            @param tcp_dport [string] use a filter on this field
        """

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('packet_id', 'username', 'ip_saddr_str', 'ip_daddr_str', 'protocol', 'sport', 'dport', 'oob_time_sec', 'oob_prefix'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool(args, 'tiny')

        if self.args['tiny']:
            self.make_tiny()




    class FilterOptimization(filters.FilterBase):
        def build(self, request, filters):
            for name in filters.args.keys():
                if name in filters.filters_types and \
                   filters.filters_types[name] != self.__class__:
                    return ''

            # This is an optimization to only find on ids >= MAX(_id)-limit-start
            # We can think this is slower to do a second request, but apparently no...
            leave = filters.args['limit'] + filters.args['start']
            return '%s >= (SELECT GREATEST(MAX(%s),%d)-%d FROM %s)' % ('_id',
                                                                       '_id',
                                                                       leave, leave)

    def __call__(self, **args):

        self.check_args(args)

        if self.args['sortby'] == 'oob_time_sec':
            self.args['optimization'] = True
            self.filters_list['optimization'] = self.FilterOptimization

        result = self._sql_query(args, "select_packets")

        result.addCallback(self._print_result)
        return result

class LastPacket(PacketTable):
     default_args = {'sortby': 'oob_time_sec',
                    'sort':   'DESC',
                    'limit':  30,
                    'start':  0,
                    'tiny':   False,
                    'input' : False,
                    }

class InputPacket(PacketTable):
     default_args = {'sortby': 'oob_time_sec',
                    'sort':   'DESC',
                    'limit':  30,
                    'start':  0,
                    'tiny':   False,
                    'input' : True,
                    }

class PacketsCountTable(TableBase):
    class PacketsCountSingleTable(TableBase):
        columns = ['packets']
        default_args = {}
        filters_list = {'ip_saddr_str':   filters.FilterIP,
                        'ip_daddr_str':   filters.FilterIP,
                        'ip_addr':    filters.FilterIPBoth,
                        'username':   filters.FilterUserID,
                        'sport':      filters.FilterPort,
                        'dport':      filters.FilterPort,
                        'raw_label':      filters.FilterState,
                        'proto':      filters.FilterProto,
                        'oob_prefix': filters.FilterLike,
                        'client_app': filters.FilterApp,
                        'start_time': filters.FilterBeginTime,
                        'end_time':   filters.FilterEndTime,
                        'firewall':   filters.FilterFirewall,
                       }

        def _result(self, r, ts):
            return [ts, sum([int(i[0]) for i in r[0]])]

        def __call__(self, ts, **args):
            d = self._sql_query(args, "count_packets")
            d.addCallback(self._result, ts)
            return d

    columns = ['oob_time_sec', 'packets']
    default_args = {'sortby': 'oob_time_sec',
                    'sort':   'DESC',
                    'limit':  30,
                    'start':  0,
                    'interval': 3600*24,
                    'count':  False,
                   }
    filters_list = {'ip_saddr_str':   filters.FilterIP,
                    'ip_daddr_str':   filters.FilterIP,
                    'ip_addr':    filters.FilterIPBoth,
                    'username':   filters.FilterUserID,
                    'sport':      filters.FilterPort,
                    'dport':      filters.FilterPort,
                    'raw_label':      filters.FilterState,
                    'proto':      filters.FilterProto,
                    'oob_prefix': filters.FilterLike,
                    'client_app': filters.FilterApp,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                    'interval':   filters.FilterInterval,
                   }

    def __init__(self, ctx, database):
        # Default interval is last week
        self.default_args['start_time'] = int(time.time()) - 7*24*3600
        self.default_args['end_time'] = int(time.time())

        TableBase.__init__(self, ctx, database)

    def first_cb(self, result):
        return result, len(result)

    def __call__(self, **args):
        self._arg_int(args, 'limit')
        args.pop('limit', None)
        self._arg_int(args, 'start')
        args.pop('start', None)
        self._arg_int(args, 'interval')
        args.pop('interval', None)
        self._arg_int(args, 'start_time')
        args.pop('start_time', None)
        self._arg_int(args, 'end_time')
        args.pop('end_time', None)
        self._arg_in (args, 'sortby', ('oob_time_sec', 'packets'))
        args.pop('sortby', None)
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        args.pop('sort', None)
        self._arg_bool (args, 'count')
        args.pop('count', None)

        if self.args['count']:
            return 0

        defers = []
        ts = self.args['start_time']
        while ts < self.args['end_time']:
            start = ts
            end = ts + self.args['interval']
            if end > self.args['end_time']:
                end = self.args['end_time']

            args['start_time'] = start
            args['end_time'] = end

            table = self.PacketsCountSingleTable(self.ctx, self.database)
            defers.append(table(ts, **args))

            ts = end

        return gatherResults(defers).addCallback(self.first_cb).addCallback(self._print_result)


class AuthFail(TableBase):

    columns = ['username', 'ip_saddr_str', 'reason', 'time']

    default_args = {'sortby':      'username',
                    'limit' :      30,
                    'sort':        'DESC',
                    'start':       0,
                }

    class FilterCurrents(filters.FilterBase):
        def build(self, request, filters):
            if not self.value:
                return
            return '%s IS NULL' % ('session_end_time')

    class Filter_StartTime(filters.FilterBase):
        def build(self, request, filters):
            return '(%s IS NULL OR %s >= %s)' % ('session_end_time',
                                 'session_end_time',
                                 request.database.escape(request.database.kw_datetime % self.value))

    class Filter_EndTime(filters.FilterBase):
        def build(self, request, filters):
            return '(%s <= %s)' % ('session_start_time',
                                   request.database.escape(request.database.kw_datetime % self.value))

    filters_list = {'ip_saddr_str':   filters.FilterIPReverse,
                    'username':   filters.FilterUserID,
                    'reason'  :   '',
                    'time': Filter_StartTime,
                    'start_time': filters.FilterBeginTime_auth,
                    'end_time':   filters.FilterEndTime_auth,
                   }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [tuple]

            username, [ip_saddr_str, os_sysname], start_time[, end_time] """

        return entry

    def __call__(self, **args):
        """
            @param start [integer] first entry
            @param limit [integer] number of results
            @param sortby [string] field to sort by in ('username', 'ip_saddr_str', 'os_sysname', 'start_time', 'end_time')
            @param sort [string] ASC or DESC
            @param ip_saddr_str [string] use a filter on this field
            @param os_sysname [string] filter on os name.
        """
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('username', 'ip_saddr_str', 'reason', 'time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        #self._arg_bool(args, 'currents')
        #self._arg_bool(args, 'extra')

        #if self.args['currents']:
        #    self._remove_column('session_end_time')
        #if not self.args['extra']:
        #    self._remove_column('ip_saddr_str')
        #    self._remove_column('os_sysname')

        result = self._sql_query(args, "select_authfail")
        result.addCallback(self._print_result)

        return result






class UsersHistoryTable(TableBase):

    columns = ['username', 'ip_saddr_str', 'os_sysname', 'session_start_time', 'session_end_time']

    default_args = {'sortby':      'session_start_time',
                    'sort':        'DESC',
                    'limit':       30,
                    'start':       0,
                    'currents':    False,
                    'extra':       True,
                }

    class FilterCurrents(filters.FilterBase):
        def build(self, request, filters):
            if not self.value:
                return
            return '%s IS NULL' % ('session_end_time')

    class Filter_StartTime(filters.FilterBase):
        def build(self, request, filters):
            return '(%s IS NULL OR %s >= %s)' % ('session_end_time',
                                 'session_end_time',
                                 request.database.escape(request.database.kw_datetime % self.value))

    class Filter_EndTime(filters.FilterBase):
        def build(self, request, filters):
            return '(%s <= %s)' % ('session_start_time',
                                   request.database.escape(request.database.kw_datetime % self.value))

    filters_list = {'ip_saddr_str':   filters.FilterIPReverse,
                    'username':   filters.FilterUserID,
                    'os_sysname': filters.FilterRaw,
                    'currents':   FilterCurrents,
                    'firewall':   filters.FilterFirewall,
                    'session_start_time': Filter_StartTime,
                    'session_end_time':   Filter_EndTime,
                   }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [tuple]

            username, [ip_saddr_str, os_sysname], start_time[, end_time] """

        result = ((anonymizer.anon_username(self.ctx, entry[0])),)

        if self.args['extra']:
            # On *usersstats* table, ip endian is not the same than other tables, so we reverse all bits.
            if self.database.ip_type == 4 and (isinstance(entry[1], int) or isinstance(entry[1], long)
                                              or isinstance(entry[1], str) and entry[2].isdigit()):
                ip = struct.unpack("<I", struct.pack(">I", int(entry[1])))[0]
            else:
                ip = entry[1]

            result += (anonymizer.anon_ipaddr(self.ctx, self.ip2str(ip)),)
            result += entry[2:3]

        result += (entry[3],)
        if not self.args['currents']:
            result += (entry[4],)

        return result

    def __call__(self, **args):
        """
            @param start [integer] first entry
            @param limit [integer] number of results
            @param sortby [string] field to sort by in ('username', 'ip_saddr_str', 'os_sysname', 'start_time', 'end_time')
            @param sort [string] ASC or DESC
            @param ip_saddr_str [string] use a filter on this field
            @param os_sysname [string] filter on os name.
        """
        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('username', 'ip_saddr_str', 'os_sysname', 'session_start_time', 'session_end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool(args, 'currents')
        self._arg_bool(args, 'extra')

        if self.args['currents']:
            self._remove_column('session_end_time')
        if not self.args['extra']:
            self._remove_column('ip_saddr_str')
            self._remove_column('os_sysname')

        result = self._sql_query(args, "select_conusers")
        result.addCallback(self._print_result)

        return result

class PortTable(TableBase):

    proto = 'ee'

    default_args = {'start':     0,
                    'limit':     10,
                    'sortby':    'end_time',
                    'sort':      'DESC',
                    'count':     False}

    filters_list = {'ip_saddr_str': filters.FilterIP,
                    'ip_daddr_str': filters.FilterIP,
                    'ip_addr':  filters.FilterIPBoth,
                    'dport':    filters.FilterPort,
                    'sport':    filters.FilterPort,
                    'username':   filters.FilterUserID,
                    'interval': filters.FilterInterval,
                    'client_app': filters.FilterApp,
                    'raw_label':    filters.FilterState,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                     'firewall':   filters.FilterFirewall,
                    }

    def __call__(self, **args):
        """
            @param limit [integer] Number of entry returned
            @param start [integer] First entry number
            @param sortby [string] Sort by this field ('tcp_dport', 'packets', 'start_time', 'end_time')
            @param sort [string] Sort order ('DESC', 'ASC')
            @param ip_saddr_str [string] filter on source ip
            @param ip_daddr_str [string] filter on destination ip
            @param proto [string] filter on protocol.
        """

        self.args['proto'] = self.proto

        self._arg_int  (args, 'limit')
        self._arg_int  (args, 'start')
        self._arg_in   (args, 'sortby', (self.proto + '_dport', 'packets', 'start_time', 'end_time'))
        self._arg_in   (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "count_port", self.proto, display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "select_ports", self.proto)
            result.addCallback(self._print_result)

        return result

class TCPTable(PortTable):

    proto = 'tcp'
    columns = ['tcp_dport', 'packets', 'start_time', 'end_time']

class UDPTable(PortTable):

    proto = 'udp'
    columns = ['udp_dport', 'packets', 'start_time', 'end_time']

class IpTable(TableBase):

    direction = ''

    default_args = {'start':     0,
                    'limit':     10,
                    'sortby':    'end_time',
                    'count':     False,
                    'sort':      'DESC'}

    filters_list =  {'ip_saddr_str': filters.FilterIP,
                     'ip_daddr_str': filters.FilterIP,
                     'ip_addr':  filters.FilterIPBoth,
                     'username':   filters.FilterUserID,
                     'dport':    filters.FilterPort,
                     'sport':    filters.FilterPort,
                     'interval': filters.FilterInterval,
                     'proto':    filters.FilterProto,
                     'raw_label':    filters.FilterState,
                     'start_time': filters.FilterBeginTime,
                     'client_app': filters.FilterApp,
                     'firewall':   filters.FilterFirewall,
                     'end_time':   filters.FilterEndTime,
                    }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [list of tuple]
        """

        # ip, packts, start_time, end_time
        result = (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[0])),)
        result += entry[1:]
        return result

    def __call__(self, **args):
        """
            @param start [integer] First entry number
            @param limit [integer] Number of entry returned
            @param sortby [string] Field used to order table, in ['ip_saddr_str', 'packets', 'start_time', 'end_time']
            @param sort [string] Sort in a ascendant or a descendant order ['ASC', 'DESC']
            @param ip_saddr_str [string] filter on source ip
            @param ip_daddr_str [string] filter on destination ip
            @param dport [integer] filter on destination port
            @param sport [integer] filter on source port
            @param proto [string] filter on protocol.
        """

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('ip_%saddr_str' % self.direction, 'packets', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "count_ip", self.direction, display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "select_ip", self.direction)
            result.addCallback(self._print_result)

        return result

class IPsrcTable(IpTable):

    columns = ['ip_saddr_str', 'packets', 'start_time', 'end_time' ]
    direction = 's'

class IPdstTable(IpTable):

    columns = ['ip_daddr_str', 'packets', 'start_time', 'end_time' ]
    direction = 'd'

class UserTable(TableBase):

    columns = ['username', 'packets', 'start_time', 'end_time']

    default_args = {'start':     0,
                    'limit':     10,
                    'count':     False,
                    'sortby':    'end_time',
                    'sort':      'DESC'}

    filters_list = {'ip_saddr_str': filters.FilterIP,
                    'ip_daddr_str': filters.FilterIP,
                    'ip_addr':  filters.FilterIPBoth,
                    'dport':    filters.FilterPort,
                    'sport':    filters.FilterPort,
                    'proto':    filters.FilterProto,
                    'username':   filters.FilterUserID,
                    'interval': filters.FilterInterval,
                    'client_app': filters.FilterApp,
                    'raw_label':    filters.FilterState,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                   }

    def entry_form(self, entry):

        # username, packets, start_time, end_time

        result = ((anonymizer.anon_username(self.ctx, entry[0])),)
        result += entry[1:]

        return result

    def __call__(self, **args):
        """
            @param start [integer] First entry number
            @param limit [integer] Number of entry returned
            @param sortby [string] Field used to order table, in ['ip_saddr_str', 'packets', 'start_time', 'end_time']
            @param sort [string] Sort in a ascendant or a descendant order ['ASC', 'DESC']
        """

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('username', 'packets', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "count_user", display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "select_user")
            result.addCallback(self._print_result)

        return result

class AppTable(TableBase):

    columns = ['client_app',  'packets', 'start_time', 'end_time']

    default_args = {'start':       0,
                    'limit':       10,
                    'count':       False,
                    'sortby':      'end_time',
                    'sort':        'DESC'}

    filters_list = {'ip_saddr_str': filters.FilterIP,
                    'ip_daddr_str': filters.FilterIP,
                    'username':   filters.FilterUserID,
                    'dport':    filters.FilterPort,
                    'sport':    filters.FilterPort,
                    'proto':    filters.FilterProto,
                    'interval': filters.FilterInterval,
                    'raw_label':    filters.FilterState,
                    'client_app': filters.FilterApp,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                   }

    def entry_form(self, entry):
        return (anonymizer.anon_appname(self.ctx, entry[0]),) + entry[1:]

    def __call__(self, **args):
        """
            @param start [integer] First entry number
            @param limit [integer] Number of entry returned
            @param sortby [string] Field used to order table, in ['ip_saddr_str', 'packets', 'start_time', 'end_time']
            @param sort [string] Sort in a ascendant or a descendant order ['ASC', 'DESC']
            @param ip_saddr_str [string] filter on source ip
            @param ip_daddr_str [string] filter on destination ip
            @param dport [integer] filter on destination port
            @param sport [integer] filter on source port
            @param proto [string] filter on protocol.
        """

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('client_app', 'packets', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))
        self._arg_bool (args, 'count')

        if self.args['count']:
            result = self._sql_query(args, "count_apps", display=False)
            result.addCallback(self._print_count)
        else:
            result = self._sql_query(args, "select_apps")
            result.addCallback(self._print_result)

        return result

class BadHosts(TableBase):

    columns = ['ip_saddr_str', 'rate']

    default_args = {'start':    0,
                    'limit':    5,
                    'sortby':   'rate',
                    'sort':     'DESC',
               }

    filters_list = {
                    'firewall':   filters.FilterFirewall,
                    }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [list of tuple]
        """

        # ip, packts
        result = (anonymizer.anon_ipaddr(self.ctx, self.ip2str(entry[0])),)
        result += entry[1:]
        return result

    def __call__(self, **args):

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('ip_saddr_str', 'rate'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))

        return self._sql_query(args, "select_badhosts").addCallback(self._print_result)

class BadUsers(TableBase):

    columns = ['username', 'rate']

    default_args = {'start':    0,
                    'limit':    5,
                    'sortby':   'rate',
                    'sort':     'DESC',
               }

    filters_list = {
                    'firewall':   filters.FilterFirewall,
                   }

    def entry_form(self, entry):
        """ We transform IP form to a string
            @param entry [tuple]
            @return [list of tuple]
        """

        # username, packets
        result = ((anonymizer.anon_username(self.ctx, entry[1])),)
        result += entry[1:]
        return result

    def __call__(self, **args):

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('username', 'rate'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))

        return self._sql_query(args, "select_badusers").addCallback(self._print_result)

class UserIDTable(TableBase):

    columns = ['username']
    default_args = {'start':  0,
                    'limit':  20,
                    'sortby': 'username',
                    'sort':   'DESC'}

    filters_list = {'username': filters.FilterLike}

    def entry_form(self, entry):
        return (anonymizer.anon_username(self.ctx, entry[0]))

    def _only_table(self, result):
        return result['table']

    def __call__(self, **args):
        return self._sql_query(args, "select_userid").addCallback(self._print_result).addCallback(self._only_table)

class UserIDTableAuth(TableBase):

    columns = ['username']
    default_args = {'start':  0,
                    'limit':  20,
                    'sortby': 'username',
                    'sort':   'DESC'}

    filters_list = {'username': filters.FilterLike}

    def entry_form(self, entry):
        return (anonymizer.anon_username(self.ctx, entry[0]))

    def _only_table(self, result):
        return result['table']

    def __call__(self, **args):
        return self._sql_query(args, "select_userid_auth").addCallback(self._print_result).addCallback(self._only_table)


class UserAppTable(TableBase):

    columns = ['client_app', 'username', 'packets', 'start_time', 'end_time']
    default_args = {'start':  0,
                    'limit':  10,
                    'sortby': 'packets',
                    'sort':   'DESC'}

    filters_list = {'ip_saddr_str':   filters.FilterIP,
                    'ip_daddr_str':   filters.FilterIP,
                    'ip_addr':    filters.FilterIPBoth,
                     'username':   filters.FilterUserID,
                    'sport':      filters.FilterPort,
                    'dport':      filters.FilterPort,
                    'raw_label':      filters.FilterState,
                    'proto':      filters.FilterProto,
                    'oob_prefix': filters.FilterLike,
                    'interval':   filters.FilterInterval,
                    'client_app': filters.FilterApp,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                   }

    def entry_form(self, result):
        return (anonymizer.anon_appname(self.ctx, result[0]),
                (anonymizer.anon_username(self.ctx, result[1])),
                result[2], result[3], result[4])

    class FilterOnlyUsers(filters.FilterBase):
        def build(self, request, filters):
            return '%s IS NOT NULL' % 'username'

    def __call__(self, **args):

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('client_app', 'username', 'packets', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))

        self.filters_list['only_users'] = self.FilterOnlyUsers
        args['only_users'] = True

        return self._sql_query(args, "select_tuple", 'client_app', 'username').addCallback(self._print_result)

class HostPortTable(TableBase):

    columns = ['ip_saddr_str', 'tcp_dport', 'packets', 'start_time', 'end_time']
    default_args = {'start':  0,
                    'limit':  10,
                    'sortby': 'packets',
                    'sort':   'DESC'}

    filters_list = {'ip_saddr_str':   filters.FilterIP,
                    'ip_daddr_str':   filters.FilterIP,
                    'ip_addr':    filters.FilterIPBoth,
                    'username':   filters.FilterUserID,
                    'sport':      filters.FilterPort,
                    'dport':      filters.FilterPort,
                    'raw_label':      filters.FilterState,
                    'oob_prefix': filters.FilterLike,
                    'interval':   filters.FilterInterval,
                    'client_app': filters.FilterApp,
                    'start_time': filters.FilterBeginTime,
                    'end_time':   filters.FilterEndTime,
                    'firewall':   filters.FilterFirewall,
                   }

    def entry_form(self, result):
        return (anonymizer.anon_ipaddr(self.ctx, self.ip2str(result[0])),) + result[1:]

    class FilterOnlyPorts(filters.FilterBase):
        def build(self, request, filters):
            return '%s IS NOT NULL' % 'tcp_sport'

    def __call__(self, **args):

        self._arg_int(args, 'limit')
        self._arg_int(args, 'start')
        self._arg_in (args, 'sortby', ('ip_saddr_str', 'tcp_dport', 'packets', 'start_time', 'end_time'))
        self._arg_in (args, 'sort',   ('DESC', 'ASC'))

        self.filters_list['only_ports'] = self.FilterOnlyPorts
        args['only_ports'] = True

        return self._sql_query(args, "select_tuple", 'ip_saddr_str', 'tcp_dport').addCallback(self._print_result)
