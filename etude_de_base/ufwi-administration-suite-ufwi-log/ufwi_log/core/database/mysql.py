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

import MySQLdb
import _mysql_exceptions
import struct

from database import GenericDataBase
from request.mysql import UlogRequest, TriggerRequest, Ulogd2Request

#############################################
#                                           #
#            Database Object                #
#                                           #
#############################################
class MySQLDataBase(GenericDataBase):

    types = {'ulog': UlogRequest,
             'triggers': TriggerRequest,
             'ulogd2': Ulogd2Request
            }

    dbtype = "mysql"
    dbapi = "MySQLdb"
    kw_max_limit = "18446744073709551615"
    kw_timestamp = "UNIX_TIMESTAMP(%s)"
    kw_datetime =  "FROM_UNIXTIME(%s)"
    kw_create_table_like = "CREATE TABLE IF NOT EXISTS %s LIKE %s"

    dbkw = { 'host' : 'host', 'db': 'db', 'user' : 'user', 'pass': 'passwd' }

    error_type = _mysql_exceptions.OperationalError

    def __init__(self, conf, logger):
        """
            Build DataBase object.
        """

        GenericDataBase.__init__(self, conf, logger, log_prefix="mysql")

    def escape(self, s):
        return "'%s'" % MySQLdb.escape_string(s)

    def whereIP(self, key, ip):
        if self.ip_type == 6:
            if ip.prefixlen() < 128:
                if (ip.prefixlen() % 8) == 0:
                    if 0 < ip.prefixlen():
                        mask = '%032X' % ip.int()
                        mask = mask[:ip.prefixlen()/4]
                        return "%s LIKE CONCAT(0x%s, '%%')" % (key, mask)
                    else:
                        return '1'
                else:
                    first = ip.int()
                    last = ip.broadcast().int()
                    return '%s >= 0x%032X AND %s <= 0x%032X' % (key, first, key, last)
            else:
                return '%s = LPAD(0x%X, 16, 0x00)' % (key, ip.int())
        else:
            if ip.prefixlen() < 32:
                first = ip.int()
                last = ip.broadcast().int()
                return '(%s >= %s AND %s <= %s)' % (key, first, key, last)
            else:
                return '%s = %s' % (key, ip.int())

    def whereIP_REVERSE(self, key, ip):
        if self.ip_type == 6:
            return self._arg_where_ip(key, ip)
        else:
            value = struct.unpack("<I", struct.pack(">I", long(ip.int())))[0]
            return '%s = %s' % (key, value)
