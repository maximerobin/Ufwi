# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
           Pierre Chifflier <chifflier AT inl.fr>

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

from twisted.enterprise import adbapi # SQL
from ufwi_rpcd.backend import tr, RpcdError
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.common.tools import toUnicode
from ufwi_rpcd.common.error import exceptionAsUnicode, NULOG
from ufwi_log.core.errors import NULOG_DATABASE_ERROR
from twisted.enterprise.adbapi import safe

class DatabaseError(RpcdError):
    def __init__(self, *args, **kwargs):
        RpcdError.__init__(self, NULOG, NULOG_DATABASE_ERROR, *args, **kwargs)

#############################################
#                                           #
#            Database Object                #
#                                           #
#############################################
class GenericDataBase(Logger):

    types = {}

    dbtype = None
    dbapi = None
    kw_max_limit = "" # indicator used to get the max limit in the LIMIT statement
    kw_timestamp = "" # SQL method used to get timestamp from datetime
    kw_datetime =  "" # SQL method used to get datetime from timestamp
    kw_create_table_like = "" # SQL method used to create a table with same schema than other

    dbkw = { 'host' : 'host', 'db': 'db', 'user' : 'user', 'pass': 'passwd' }

    error_type = None

    def __init__(self, conf, logger, log_prefix="database"):
        """
            Build DataBase object.
        """
        Logger.__init__(self, log_prefix, parent=logger)

        self.dbpool = None
        self.conf = conf
        self.ip_type = 4
        adbapi.ConnectionPool.noisy = False
        adbapi.ConnectionPool.reconnect = True

    def start(self):
        """
            Create a connection to database.
        """

        if self.dbpool:
            self.dbpool.close()

        self.dbpool = None

        try:
            self.info('Connecting to database %s' % self.conf['database'])
            kwargs = {}
            kwargs[ self.dbkw['host'] ] = self.conf['hostname']
            kwargs[ self.dbkw['db'] ]   = self.conf['database']
            kwargs[ self.dbkw['user'] ] = self.conf['username']
            kwargs[ self.dbkw['pass'] ] = self.conf['password']

            self.dbpool = adbapi.ConnectionPool(self.dbapi, **kwargs)
            self.dbpool.connect()
            self.info('Connected!')
        except self.error_type, e:
            self.dbpool = None
            try:
                error = e[1]
            except IndexError:
                error = e
            raise DatabaseError(
                tr("Unable to connect to database, check your configuration: %s"),
                exceptionAsUnicode(error))

    def close(self):

        self.dbpool.close()

    def escape(self, s):
        return "'%s'" % safe(s)

    def createRequest(self, table=None):

        if self.types.has_key(self._type):
            obj = self.types[self._type]
        else:
            raise DatabaseError(tr("Unknown database type %s"), self._type)

        if not table:
            table = self.ulog

        return obj(self, table)

    def query_cb(self, value):
        if value is None:
            return None
        else:
            return (value, len(value))

    def query_error(self, error, query=None):
        error.trap(self.error_type, adbapi.ConnectionLost)

        self.writeError(error)
        if self.dbpool is not None and query is not None:
            self.info("Retrying UfwiLog database query...")
            self.start()
            if query.upper().startswith('SELECT'):
                func = self.dbpool.runQuery
            else:
                func = self.dbpool.runOperation
            return func(query).addCallback(self.query_cb).addErrback(self.query_error)
        else:
            self.dbpool = None
            raise DatabaseError('Connection lost to database.')

    def query(self, query):
        #self.debug('Query: %s' % query)
        if query.upper().startswith('SELECT'):
            func = self.dbpool.runQuery
        else:
            func = self.dbpool.runOperation
        return func(query).addCallback(self.query_cb).addErrback(self.query_error, query)

class DataBaseFactory:

    def __init__(self):
        self.objects = {}
        try:
            from .mysql import MySQLDataBase
            self.objects['mysql'] = MySQLDataBase
        except ImportError, e:
            self.objects['mysql'] = exceptionAsUnicode(e)

        try:
            from .pgsql import PostgreSQLDataBase
            self.objects['pgsql'] = PostgreSQLDataBase
        except ImportError, e:
            self.objects['pgsql'] = exceptionAsUnicode(e)

    def create(self, conf, logger):
        dbtype = conf['dbtype']
        try:
            db_object = self.objects[dbtype]
            if isinstance(db_object, (str, unicode)):
                raise DatabaseError(tr('Unable to use %s: %s'), dbtype, toUnicode(db_object))
        except KeyError, e:
            raise DatabaseError(tr('Unsupported database type %s'), dbtype)
        return db_object(conf, logger)

