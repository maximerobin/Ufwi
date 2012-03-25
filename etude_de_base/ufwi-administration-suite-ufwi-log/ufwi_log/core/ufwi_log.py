# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2010 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

License: All rights reserved.

$Id$
"""

from __future__ import with_statement

from os.path import join as path_join, exists
from os import umask
from datetime import datetime

from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread

from ufwi_rpcd.common.streaming import UDPacket
from ufwi_rpcd.core import context
from ufwi_rpcd.backend.cron import scheduleRepeat
from ufwi_rpcd.backend.error import CoreError
from ufwi_rpcd.backend import tr, Component, RpcdError
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.anonymization import anonymizer
from ufwi_rpcd.backend.variables_store import VariablesStore

from ufwi_conf.common.netcfg import deserializeNetCfg

import table
import streams
import info
from .database import DataBaseFactory, DatabaseError
from .dns_resolver import DNSResolver

from ufwi_rpcd.common import EDENWALL
if EDENWALL:
    import squid
    from .exporter import Exporter
    from .importer import Importer
else:
    from .free_stub import Exporter, Importer, squid

class NulogCore(Component):

    NAME = "ufwi_log"
    VERSION = "3.0-3"
    API_VERSION = 1
    REQUIRES = set(('network',))
    ACLS = {'multisite_transport': set(('callRemote', 'hostFile', 'getFile', 'removeFile')),
            'multisite_slave':     set(('callRemote',)),
            'ufwi_log':               set(('export',)), # remote called by myself.
            'network':             set(('getNetconfig',)),
           }
    ROLES = {'log_read':         set(('table', 'stream', 'table_list', 'table_filters', 'get_db_size', 'get_row_size_estimation', 'get_row_count_week', 'setupClient', 'resolveReverseDNS')),
             'log_anonymous':    set(('@log_read',)),
             'log_write':        set(('@log_read', 'setConfig', 'getConfig')),
             'multisite_read':     set(('table',)),
             'multisite_write':    set(('@multisite_read',)),
             'nudpi_read':         set(('@log_read',)),
            }

    MULTISITE_SERVICES = ['export']

    update_archives_period = 3600*24 # 1j

    tables = {'TCPTable':             table.TCPTable,
              'UDPTable':             table.UDPTable,
              'IPsrcTable':           table.IPsrcTable,
              'IPdstTable':           table.IPdstTable,
              'UserTable':            table.UserTable,

              'PacketTable':          table.PacketTable,
              'LastPacket':           table.LastPacket,
              'InputPacket':          table.InputPacket,

              'UsersHistoryTable':    table.UsersHistoryTable,
              'AuthFail':             table.AuthFail,

              'AppTable':             table.AppTable,
              'PacketInfo':           info.PacketInfo,
              'BadHosts':             table.BadHosts,
              'BadUsers':             table.BadUsers,

              'UserIDTable':          table.UserIDTable,
              'UserIDTableAuth':      table.UserIDTableAuth,

              'UserAppTable':         table.UserAppTable,
              'HostPortTable':        table.HostPortTable,
              'PacketsCountTable':    table.PacketsCountTable,
              'TrafficStream':        streams.TrafficStream,
              'Stats':                streams.StatsStream,
              'LastPacketsStream':    streams.LastPacketsStream,
              'LoadStream' :          streams.LoadStream,
              'MemoryStream':         streams.MemoryStream,
              'StorageStream':        streams.StorageStream,
             }

    if EDENWALL:
        tables.update({
              'ProxyRequestTable':    squid.ProxyRequestTable,
              'ProxyDomainsTable':    squid.ProxyDomainsTable,
              'ProxyUsersTable':      squid.ProxyUsersTable,
              'ProxyHostsTable':      squid.ProxyHostsTable,
        })

    DEFAULT_CONF = {
         'hostname': 'localhost',
         'database': 'ulog',
         'username': 'ufwi_log',
         'password': 'ufwi_log',
         'dbtype': 'mysql',
         'type': 'triggers',
         'ip': '4',
         'table': 'ulog',
         'maxrotate': '52',
         'export_period': 0,
         'import_rotation': 0,
         'anonymization': 'user ipaddr app',
         'squid_path': '',
    }

    def init(self, ufwi_rpcd_core):
        self.ufwi_rpcd_core = ufwi_rpcd_core

        self.database = None
        self.archives_cron = None
        self.exporter = Exporter(context.Context.fromComponent(self), self.ufwi_rpcd_core)
        self.importer = Importer(self.ufwi_rpcd_core)
        self.dns_resolver = DNSResolver()

        self.conf_filename = path_join(ufwi_rpcd_core.var_dir, 'ufwi_log.xml')
        self.conf = VariablesStore()
        for key, value in self.DEFAULT_CONF.iteritems():
            self.conf.set(key, value)
        if exists(self.conf_filename):
            self.conf.load(self.conf_filename)

        try:
            self.start_dbpool()
        except DatabaseError, err:
            # We don't stop ufwi_rpcd launch because this isn't a problem,
            # user will correct it with ufwi_log-qt and the setConfig() service.
            self.writeError(err, "start_dbpool() error")

        try:
            return self.ufwi_rpcd_core.callService(context.Context.fromComponent(self),
                                                   "network", "getNetconfig") \
                        .addCallback(self.cb_networks)
        except CoreError:
            # The 'network' component is not loaded, it is not a matter.
            pass

    def cb_networks(self, result):
        netcfg = deserializeNetCfg(result)
        for network in netcfg.iterNetworks():
            anonymizer.networks.append(network.net)

    def start_dbpool(self):
        anonymizer.entities = self.conf['anonymization'].split()
        if not self.database or self.database.dbtype != self.conf['dbtype']:
            try:
                self.database = DataBaseFactory().create(self.conf, self)
                self.exporter.database = self.database
                self.importer.database = self.database
            except DatabaseError, err:
                self.database = None
                self.exporter.database = None
                self.importer.database = None
                self.writeError(err, "Unable to connect to the database")
                raise
        else:
            self.database.conf = self.conf

        self.database.start()

        self.database._type = self.conf['type']
        self.database.ip_type = int(self.conf['ip'])
        self.database.ulog = self.conf['table']
        self.database.archives = {}

        if self.archives_cron:
            self.archives_cron.stop()
        self.archives_cron = scheduleRepeat(self.update_archives_period, self.update_archives)

        self.exporter.rehash(self.conf)
        self.importer.rehash(self.conf)

    def update_archives(self, result=None, nb_table=0):
        """
            This function is used to update cache of archives list.
            We store the first and last packet timestamp, to know
            in which time interval this archive table is used.

            Call it without any param to launch the process, and it
            will call itself as callback to iterate all archive table.

            It begins with ulog_1 and increment to the latest existant table.
        """

        # There is not any database connection.
        if not self.database or not self.database.dbpool:
            return

        def eb(result):
            # We doesn't care about an error..
            pass

        if result:
            # If result != None it is because this is a callback,
            # so we can store it.

            try:
                assert result[0][0][0]
                assert result[0][0][1]

                start = datetime.fromtimestamp(result[0][0][0])
                end = datetime.fromtimestamp(result[0][0][1])

                self.database.archives['%s_%d' % (self.database.ulog, nb_table)] = (start, end)
                if self.database.archives[self.database.ulog][0] == datetime.min:
                    self.database.archives[self.database.ulog] = (end, datetime.max)
            except Exception, e:
                self.writeError(e)

        else:
            self.database.archives[self.database.ulog] = (datetime.min, datetime.max)

        table = '%s_%d' % (self.database.ulog, nb_table+1)

        return self.database.query("""SELECT MIN(oob_time_sec), MAX(oob_time_sec) FROM %s"""
                                    % table).addCallback(self.update_archives, nb_table+1).addErrback(eb)

    def check_dbpool_running(self):
        if not self.database or not self.database.dbpool:
            raise DatabaseError(tr('There is no database connection'))

    ##########
    # SERVICES

    def service_setConfig(self, ctx, new_config):
        """
            Set ufwi_log configuration

            @param config [dict] must contains configuration values.
        """

        last_config = self.conf.copy()
        for key, value in new_config.iteritems():
            if not self.conf.has_key(key):
                raise RpcdError(tr('This key does not exist'))
            try:
                self.conf.set(key, value)
            except ConfigError, err:
                raise RpcdError(
                    tr('Unable to set value for key %s: %s'), repr(key), unicode(err))

        try:
            # After set configuration, (re)start dbpool
            self.start_dbpool()
        except Exception:
            # There is an error when trying to reconnect to database.
            # It reset last config.
            self.conf.update(last_config)
            raise

        umask(0077)
        self.conf.save(self.conf_filename)
        return True

    def service_getConfig(self, ctx):
        """
            Get configuration dictionary
        """
        return self.conf.toDict()

    def service_export(self, ctx, path, dist_meta):
        if EDENWALL:
            deferred = self.ufwi_rpcd_core.callService(ctx, 'multisite_transport', 'getFile', ctx.firewall, path)
            deferred.addCallback(self.importer.receivedExport, ctx.firewall, dist_meta)
            deferred.addErrback(self.importer.exportError)
            return deferred
        raise NotImplemented()

    def service_table_list(self, ctx):
        return self.tables.keys()

    def service_table_filters(self, ctx, name):
        p = self.tables.get(name)

        if p is None:
            raise RpcdError(tr('Table not found: %s'), name)

        try:
            p = p(ctx, self.database) # We instance class

            return p.getFiltersList()

        except Exception, err:
            self.writeError(err, "table_filters() error")
            raise

    def service_table(self, ctx, name, args):
        """ This is the 'table' distant access function.
            @param name [string] function name;
            @param args [dictionnary]
        """

        self.check_dbpool_running()

        p = self.tables.get(name) # We get class type

        if p is None:
            raise RpcdError(tr('Table not found: %s'), name)

        try:
            p = p(ctx, self.database) # We instance class

            defer = p(**args) # <=> p.__call__(..)

            return defer

        except Exception, err:
            self.writeError(err, "table() error")
            raise

    def format_stream(self, result):
        packet = UDPacket(0, result['table'][0])
        packet.columns = ['oob_time_sec'] + result['columns']
        return packet

    def service_stream(self, ctx, *args, **kwargs):
        d = self.service_table(ctx, *args, **kwargs)
        d.addCallback(self.format_stream)
        return d

    def service_get_db_size(self, ctx, *args, **kwargs):
        defer =  self.database.query("""SELECT pg_database_size('ulogd'), pg_size_pretty(pg_database_size('ulogd'))""")
        defer.addCallback(self.add_partition_size)
        return defer

    def add_partition_size(self, result):
        # get total space
        import os, statvfs
        f = os.statvfs('/var/lib/postgresql')
        result = list(result)
        val = list(result[0][0])
        val.append(f[statvfs.F_BSIZE])
        val.append(f[statvfs.F_BLOCKS])
        result[0] = [[str(item) for item in val]]
        return result

    def service_get_row_size_estimation(self, ctx, *args, **kwargs):
        defer =  self.database.query("""SELECT SUM(reltuples::integer), COALESCE(pg_database_size('ulogd')::float/NULLIF(SUM(reltuples::integer),0),0) as row_size from pg_class inner join pg_tables on tablename=relname where tablename !~* 'pg_*' and tablename !~* 'sql_*'""")
        defer.addCallback(self.return_data)
        return defer

    def service_get_row_count_week(self, ctx, *args, **kwargs):
        defer =  self.database.query("""SELECT count(1) FROM ulog2 WHERE oob_time_sec > extract(epoch from now() - interval '7 days')::integer""")
        defer.addCallback(self.return_data)
        return defer

    def service_setupClient(self, ctx, attr):
        """
        Setup the client: attr = {
            'version': client_version,
        }.

        Return {'version': server_version}.
        """
        self.client_version = attr.get('version')
        session = ctx.getSession()
        session['ufwi_log_client_version'] = self.client_version
        return {'version' : self.VERSION}

    @inlineCallbacks
    def service_resolveReverseDNS(self, ctx, ip):
        dns = yield deferToThread(self.dns_resolver.resolveReverseDNS, ip)
        returnValue(dns)

    def return_data(self, data):
        return data

    def logService(self, context, logger, service, text):
        if service == 'stream':
            # don't log calls to ufwi_log.stream()
            return
        Component.logService(self, context, logger, service, text)

