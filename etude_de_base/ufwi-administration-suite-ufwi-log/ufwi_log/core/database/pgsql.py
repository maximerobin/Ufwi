# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <chifflier AT inl.fr>
           Romain Bignon <romain AT inl.fr>

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

import psycopg2
from psycopg2.extensions import adapt as psycoadapt

from database import GenericDataBase
from request.pgsql import UlogRequest, TriggerRequest, Ulogd2TriggersRequest

#############################################
#                                           #
#            Database Object                #
#                                           #
#############################################
class PostgreSQLDataBase(GenericDataBase):

    types = {'ulog': UlogRequest,
             'triggers': TriggerRequest,
             'ulogd2': Ulogd2TriggersRequest
            }

    dbtype = "pgsql"
    dbapi = "psycopg2"
    kw_max_limit = "ALL"
    kw_timestamp = "EXTRACT(epoch FROM %s)::integer"
    kw_datetime =  "%s" #TODO
    kw_create_table_like = "CREATE TABLE %s (LIKE %s)"

    dbkw = { 'host' : 'host', 'db': 'database', 'user' : 'user', 'pass': 'password' }

    error_type = psycopg2.OperationalError

    def __init__(self, conf, logger):
        """
            Build DataBase object.
        """

        GenericDataBase.__init__(self, conf, logger, log_prefix="pgsql")

    def escape(self, s):
        if isinstance(s, unicode):
            s = s.encode('utf-8')
        return '%s' % psycoadapt(str(s))

    def whereIP(self, key, ip):

        prefix_lens = {4: 32, 6: 128}
        if ip.prefixlen() < prefix_lens[ip.version()]:
            return "inet %s >> %s" % (self.escape(ip), key)
        else:
            return "%s = inet %s" % (key, self.escape(ip))

    def whereIP_REVERSE(self, key, ip):
        return self.whereIP(key, ip)
