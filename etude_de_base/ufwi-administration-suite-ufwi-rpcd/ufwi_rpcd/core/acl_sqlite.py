"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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
from os import path
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend import tr, AclError
from ufwi_rpcd.core.error import ACL_DB_ERROR

# try importing Python native sqlite support (>= 2.5). If not found, try pysqlite2
try:
    import sqlite3 as sqlite
except ImportError, e:
    from pysqlite2 import dbapi2 as sqlite

from acl_storage import IAclStorage

class SQLiteAclStorage(IAclStorage, Logger):

    VERSION = '2.0'
    FORMAT = '2.0'

    def __init__(self, core, filename = "acl.db"):
        Logger.__init__(self, "acl_sqlite:" + filename)

        vardir = core.config.get("CORE","vardir")
        self._acl_db = path.join(vardir, filename)
        self._version = ''
        self._format = ''

        if not path.exists(self._acl_db):
            raise AclError(ACL_DB_ERROR,
                tr("ACL database file (%s) does not exist!"), self._acl_db)

        # this will create the sqlite database if needed
        try:
            self.db = sqlite.connect(database=self._acl_db, timeout=10.0)
            self._check_version()
        except sqlite.OperationalError, err:
            raise AclError(ACL_DB_ERROR,
                tr("Unable to open the ACL database (%s): %s"),
                self._acl_db, unicode(err))

        if self._version != self.VERSION:
            raise AclError(ACL_DB_ERROR,
                tr("Version of database (%s) is not supported (required: %s)"),
                self._version, self.VERSION)

    def close(self, core):
        self.debug("Total ACL changes: %d" % self.db.total_changes)
        self.db.close()

    def check_acl(self, group, role, host=None):
        result = self._get_acl_user(group, role, host)
        return len(result) > 0

    def get_acl(self, group=None, role=None, host=None):
        sql_result = self._get_acl_user(group, role, host)
        result = [ ]
        for row in sql_result:
            if host:
                (acl_id,acl_group,acl_role,acl_host) = row
                result.append( (acl_id,acl_group,acl_role,acl_host) )
            else:
                (acl_id,acl_group,acl_role) = row
                result.append( (acl_id,acl_group,acl_role) )

        return result

    def set_acl(self, group, role, host=None):
        self._delete_acl(group, role, host)
        if host:
            sql_command = 'INSERT INTO acl (_group, _role, _host) VALUES (?,?,?)'
            args = (group, role, host)
        else:
            sql_command = 'INSERT INTO acl (_group, _role) VALUES (?,?)'
            args = (group, role)
        self.db.execute(sql_command, args)
        self.db.commit()

    def delete_acl(self, group=None, role=None, host=None):
        return self._delete_acl(group, role, host)

    def getStoragePaths(self):
        """
        return iterable which contains all paths used by storage
        """
        return (self._acl_db,)

    def _check_version(self):
        """ Check table version, and create database schema if needed """
        get_version_str = 'SELECT _version,_format FROM version'
        res = self.db.execute(get_version_str)
        row = res.fetchone()
        self._version = row[0]
        self._format = row[1]

    def _get_acl_user(self, group, role, host):
        """ Get all ACL for the given parameters.
        Return a cursor with the selected rows.

        Security note: to avoid SQL injections, Python documentation recommends to use the DB-API's parameter substitution, using "?"
        """
        args = {'group': group, 'role': role, 'host': host}
        where = []
        if group:
            where.append("(acl._group = :group)")
        if role:
            where.append("(acl._role = :role)")
        if host:
            where.append("(acl._host = :host)")

        if where:
            where = "WHERE " + " AND ".join(where)
        else:
            where = ""

        if host:
            sql = "SELECT _id, _group, _role, _host FROM acl %s ORDER BY _group DESC" % where
        else:
            sql = "SELECT _id, _group, _role FROM acl %s ORDER BY _group DESC" % where

        return self.db.execute(sql, args)

    def _delete_acl(self, group, role, host):
        args = { 'group':group, 'role':role, 'host': host}
        where = []
        if group:
            where.append("(acl._group = :group)")
        if role:
            where.append("(acl._role = :role)")
        if host:
            where.append("(acl._host = :host)")

        if where:
            where = "WHERE " + " AND ".join(where)
        else:
            where = ""

        sql_command = "DELETE FROM acl %s" % where
        result = self.db.execute(sql_command, args)
        self.db.commit()
        return result.rowcount

