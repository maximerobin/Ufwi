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

from __future__ import with_statement

from tablebase import TableBase
import filters
from ufwi_rpcd.common.defer import gatherResults, succeed

from twistedsnmp import snmpprotocol, agentproxy
import time

from logging import getLogger, CRITICAL

# Hide all twisted snmp logs
logger = getLogger('twsnmp')
logger.setLevel(CRITICAL+1)

class StreamBase(TableBase):

    # send data in the stream every `delay` seconds
    default_args = {}
    columns = []

    def __init__(self, ctx, database):
        TableBase.__init__(self, ctx, database)

    def _sendSQLToStream(self, result):
        try:
            return [ int(result[0][0][0]) ]
        except Exception:
            return []

    def _returnPacket(self, result):
        return self._print_result([[result], 1])

class SNMPBase(StreamBase):

    default_args = {'interval': 1}
    OIDS = []
    SNMP_METHOD = agentproxy.AgentProxy.get
    PROXY = None

    def __init__(self, ctx, database):
        StreamBase.__init__(self, ctx, database)
        if SNMPBase.PROXY is None:
            port = snmpprotocol.port()
            SNMPBase.PROXY = agentproxy.AgentProxy(
                                '127.0.0.1', 161,
                                community = 'public',
                                snmpVersion = 'v2',
                                protocol = port.protocol,
                            )

        self.proxy = SNMPBase.PROXY

    def snmp_result(self, r):
        return [r[agentproxy.OID(k)] for k in self.OIDS]

    def __call__(self, **args):
        df = self.SNMP_METHOD(self.proxy, self.OIDS, timeout=.25, retryCount=5)

        return df.addCallback(self.snmp_result).addCallback(self._returnPacket)


class LoadStream(SNMPBase):

    columns = ['load1', 'load5', 'load15']
    OIDS = ['.1.3.6.1.4.1.2021.10.1.5.1', #load1
            '.1.3.6.1.4.1.2021.10.1.5.2', #load5
            '.1.3.6.1.4.1.2021.10.1.5.3'] #load15

class MemoryStream(SNMPBase):

    columns = ['memory_total', 'memory_used']
    MEM_TOTAL = '.1.3.6.1.4.1.2021.4.5.0'
    MEM_FREE = '.1.3.6.1.4.1.2021.4.6.0'
    MEM_CACHED = '.1.3.6.1.4.1.2021.4.15.0'
    OIDS = [MEM_TOTAL, MEM_FREE, MEM_CACHED]

    def snmp_result(self, r):
        return [r[agentproxy.OID(self.MEM_TOTAL)], r[agentproxy.OID(self.MEM_TOTAL)] - r[agentproxy.OID(self.MEM_FREE)] - r[agentproxy.OID(self.MEM_CACHED)]]

class TrafficStream(SNMPBase):

    columns = ['bytes_in', 'bytes_out']
    DESC_OID = '.1.3.6.1.2.1.2.2.1.2'
    INOCTETS_OID = '.1.3.6.1.2.1.2.2.1.10'
    OUTOCTETS_OID = '.1.3.6.1.2.1.2.2.1.16'
    OIDS = [DESC_OID, INOCTETS_OID, OUTOCTETS_OID]
    SNMP_METHOD = agentproxy.AgentProxy.getTable

    def snmp_result(self, r):
        tab = [0, 0]
        avg = [0, 0]
        for oid, iface in r[agentproxy.OID(self.DESC_OID)].iteritems():
            if iface == 'lo':
                continue

            sufix = unicode(oid).split(self.DESC_OID)[1]
            tab[0] += r[agentproxy.OID(self.INOCTETS_OID)][agentproxy.OID('%s%s' % (self.INOCTETS_OID, sufix))]
            tab[1] += r[agentproxy.OID(self.OUTOCTETS_OID)][agentproxy.OID('%s%s' % (self.OUTOCTETS_OID, sufix))]

        try:
            id = self.ctx.stream_id
        except AttributeError:
            id = 0

        session = self.ctx.getSession()
        try:
            last_in, last_out, last_update_ts = session['ufwi_log:TrafficStream:%d' % id]
        except KeyError:
            last_in = last_out = last_update_ts = 0.0

        if last_update_ts:
            avg[0] = int((tab[0] - last_in)  * 1 / (time.time() - last_update_ts))
            avg[1] = int((tab[1] - last_out) * 1 / (time.time() - last_update_ts))

        session['ufwi_log:TrafficStream:%d' % id] = (tab[0], tab[1], time.time())

        return avg

class LoadStream(SNMPBase):

    columns = ['load1', 'load5', 'load15']
    OIDS = ['.1.3.6.1.4.1.2021.10.1.5.1', #load1
            '.1.3.6.1.4.1.2021.10.1.5.2', #load5
            '.1.3.6.1.4.1.2021.10.1.5.3'] #load15

class LastPacketsStream(StreamBase):

    default_args = {'interval': 1}

    columns = ['packets']
    filters_list = {'ip_saddr_str': filters.FilterIP,
                    'ip_daddr_str': filters.FilterIP,
                    'dport':    filters.FilterPort,
                    'sport':    filters.FilterPort,
                    'proto':    filters.FilterProto,
                    'interval': filters.FilterInterval,
                    'raw_label':    filters.FilterState,
                    'client_app': filters.FilterRaw,
                    'firewall':   filters.FilterFirewall,
                   }

    ACCEPTED_PATH = '/proc/sys/net/netfilter/nf_stat/nf_accepted_pckts'
    DROPPED_PATH = '/proc/sys/net/netfilter/nf_stat/nf_dropped_pckts'

    def get_file_value(self, *paths):
        value = 0
        for path in paths:
            with open(path, 'r') as f:
                value += int(f.read())

        session = self.ctx.getSession()
        try:
            id = self.ctx.stream_id
        except AttributeError:
            id = 0

        try:
            return value - session['ufwi_log:LastPacketsStream:%d' % id]
        except KeyError:
            return 0
        finally:
            session['ufwi_log:LastPacketsStream:%d' % id] = value

    def __call__(self, **args):
        s = set(args.keys()).difference(set(self.default_args.keys()))
        try:
            if not s:
                d = succeed([self.get_file_value(self.ACCEPTED_PATH, self.DROPPED_PATH)])
            elif len(s) == 1 and 'raw_label' in args:
                if int(args['raw_label']) == 0:
                    d = succeed([self.get_file_value(self.DROPPED_PATH)])
                else:
                    d = succeed([self.get_file_value(self.ACCEPTED_PATH)])
            else:
                raise IOError()
        except IOError:
            d = self._sql_query(args, 'count_packets').addCallback(self._sendSQLToStream)

        d.addCallback(self._returnPacket)
        return d

#class TrafficStream(StreamBase):
#
#    columns = ['bytes_in', 'bytes_out']
#    filters_list = {'ip_saddr_str': filters.FilterIP,
#                    'ip_daddr_str': filters.FilterIP,
#                    'user_id':  filters.FilterUserID,
#                    'dport':    filters.FilterPort,
#                    'sport':    filters.FilterPort,
#                    'proto':    filters.FilterProto,
#                    'client_app': filters.FilterRaw,
#                    'interval': filters.FilterInterval,
#                    'firewall':   filters.FilterFirewall,
#                   }
#
#    def cb(self, result):
#
#        return [int(result[0][0][0] or 0), int(result[0][0][1] or 0)]
#
#    def __call__(self, **args):
#        """
#            @param ip_saddr_str [string] filter on source ip
#            @param ip_daddr_str [string] filter on destination ip
#            @param user_id [integer] filter on user_id
#            @param dport [integer] filter on destination port
#            @param sport [integer] filter on source port
#            @param proto [string] filter on protocol.
#            @param client_app [string] filter on application
#        """
#
#        result = self._sql_query(args, "select_traffic")
#        result.addCallback(self.cb)
#        result.addCallback(self._returnPacket)
#
#        return result

class StatsStream(StreamBase):

    default_args = {'raw_label': 0}
    filters_list = {'ip_saddr_str': filters.FilterIP,
                    'ip_daddr_str': filters.FilterIP,
                    'dport':    filters.FilterPort,
                    'sport':    filters.FilterPort,
                    'proto':    filters.FilterProto,
                    'raw_label':    filters.FilterState,
                    'client_app': filters.FilterRaw,
                    'firewall':   filters.FilterFirewall,
                   }

    def decimal2str(self, d):
        return '%1.2f' % d[0][0][0]

    def decimal2int(self, d):
        return int(d[0][0][0])

    def __call__(self, **args):

        sql = []
        sql.append(self._sql_query(args, 'count_average', 1).addCallback(self.decimal2str))
        sql.append(self._sql_query(args, 'count_average', 5).addCallback(self.decimal2str))
        sql.append(self._sql_query(args, 'count_average', 15).addCallback(self.decimal2str))
        sql.append(self._sql_query(args, 'count_packets').addCallback(self.decimal2int))

        return gatherResults(sql).addCallback(self._returnPacket)

class StorageStream(SNMPBase):
    columns = []
    OIDS = []
    USED_OID = '.1.3.6.1.2.1.25.2.3.1.6.'
    SIZE_OID = '.1.3.6.1.2.1.25.2.3.1.5.'
    BLOCK_SIZE_OID = '.1.3.6.1.2.1.25.2.3.1.4.'

    def __init__(self, ctx, database):
        SNMPBase.__init__(self, ctx, database)

    def setPartitions(self, r):
        r = r[agentproxy.OID('.1.3.6.1.2.1.25.2.3.1.2')]
        self.columns = []
        self.partitions = {}
        oids = []
        for key, val in r.iteritems():
            # Keep paritions of type hrStorageFixedDisk only
            if val == [1, 3, 6, 1, 2, 1, 25, 2, 1, 4]:
                # Retrieve the partition name
                part_no = str(key).split('.')[-1]
                oids.append('.1.3.6.1.2.1.25.2.3.1.3.' + str(part_no))
        return self.SNMP_METHOD(self.proxy, oids, timeout=.25, retryCount=5)

    def createPartition(self, r):
        for key, val in r.iteritems():
            part_no = str(key).split('.')[-1]
            self.columns.append(val)
            self.columns.append('total ' + val)
            self.part_no.append(str(part_no))
            self.OIDS.append(self.USED_OID + str(part_no))
            self.OIDS.append(self.SIZE_OID + str(part_no))
            self.OIDS.append(self.BLOCK_SIZE_OID + str(part_no))

    def snmp_result(self, r):
        no = self.part_no[0]
        lst = []
        for no in self.part_no:
            block_size = r[agentproxy.OID(self.BLOCK_SIZE_OID + no)]
            lst.append(r[agentproxy.OID(self.USED_OID + no)] * block_size)
            lst.append(r[agentproxy.OID(self.SIZE_OID + no)] * block_size)
        return lst

    def __call__(self, **args):
        self.part_no = []
        # Retrieve the list of partitions and their types
        d = agentproxy.AgentProxy.getTable(self.proxy, ['.1.3.6.1.2.1.25.2.3.1.2'], timeout=.25, retryCount=5)
        d.addCallback(self.setPartitions)
        d.addCallback(self.createPartition)
        d.addCallback(lambda x:self.SNMP_METHOD(self.proxy, self.OIDS, timeout=.25, retryCount=5))
        return d.addCallback(self.snmp_result).addCallback(self._returnPacket)
