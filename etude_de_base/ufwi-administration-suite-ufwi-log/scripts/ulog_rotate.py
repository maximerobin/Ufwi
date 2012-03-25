#!/usr/bin/env python
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

#################################################
# Usage:
##
# You can use this script two times to rotate logs:
# - One daily to copy old logs from main ulog table
#   to latest archive table.
# - One weekly (or --interval number of days) to rename
#   all tables (ulog_1 to ulog_2, etc.., and remove
#   ulog_maxrotate (42? it is in configuration).
#
# The daily script must run with this command:
#   $ ./ulog_rotate.py -c /path/to/core.conf --daily --interval=7
#
# The weekly script must run with this command:
#   $ ./ulog_rotate.py -c /path/to/core.conf --weekly
#
#
# Use it in a cron.
#
# WARNING: user MUST have the ALTER privilege to
#          be able to use the RENAME command.
##

import MySQLdb
import _mysql_exceptions
from optparse import OptionParser
from ConfigParser import SafeConfigParser
from sys import exit, stderr

def parseOptions():
    parser = OptionParser(usage="%prog -c config_file [-i rotate_interval] [-vhd] [--weekly] [--daily]")
    parser.add_option("--config", "-c", help="Nulog-core configuration", action="store", type="str", default=None)
    parser.add_option("--interval", "-i", help="Rotate interval in days (default=7)", action="store", type="int", default=7)
    parser.add_option("--debug", "-v", help="Activate debug mode (default=false)", action="store_true", default=False)
    parser.add_option("--daily", "-d", help="Use this script to make day rotate", action="store_true", default=False)
    parser.add_option("--weekly", "-w", help="Use this script to rotate tables", action="store_true", default=False)
    parser.add_option("--optimize", "-o", help="Use optimization of table", action="store_true", default=False)

    options, args = parser.parse_args()

    if (not options.config or not options.interval or
        (not options.daily and not options.weekly)):
        parser.print_help()
        exit(1)

    return options

class Database:

    def __init__(self, options, parser):

        self.options = options
        self.parser = parser
        self.db = MySQLdb.connect(parser.get("DB", "host"),
                                  parser.get("DB", "user"),
                                  parser.get("DB", "password"),
                                  parser.get("DB", "db"))

        self.db.autocommit(True)

        self.cursor = self.db.cursor()
        self.ulog = parser.get("DB", "table")
        self.maxrotate = parser.get("DB", "maxrotate")
        self.errors = []

    def __del__(self):

        self.db.close()

    def debug(self, msg):
        if self.options.debug:
            print msg
        else:
            # if there isn't the --debug flag, we store
            # errors in memory and we show them only
            # if there is a real error, to help admin.
            self.errors += msg

    def error(self, err):
        # flush stocked errors
        if not self.options.debug:
            for msg in self.errors:
                print msg
            self.errors = []
        print >>stderr, '*** ERROR *** ', err

    def __table_exists(self, table):

        try:
            self.cursor.execute('select _id from %s_1 limit 1' % self.ulog)
            return True
        except _mysql_exceptions.ProgrammingError, e:
            self.debug(e)
            return False

    def daily_rotate(self, table, timestamp):

        if not self.__table_exists(table):
            return
        self.cursor.execute("""INSERT INTO %s_1
                                SELECT * FROM %s
                                WHERE %s IS NOT NULL
                                      AND %s < CURDATE() - INTERVAL %d DAY"""
                            % (table, table, timestamp, timestamp, self.options.interval))
        self.cursor.execute("""DELETE FROM %s
                                WHERE %s IS NOT NULL
                                      AND %s < CURDATE() - INTERVAL %s DAY"""
                            % (table, timestamp, timestamp, self.options.interval))
        if self.options.optimize:
            self.cursor.execute("OPTIMIZE TABLE %s" % table)

    def rotate_table(self, table):

        try:
            self.cursor.execute("""DROP TABLE IF EXISTS %s_%s""" % (table, self.maxrotate))
        except Exception, e:
            self.error(e)

        for t in xrange(int(self.maxrotate)-1, 0, -1):
            try:
                self.cursor.execute("""RENAME TABLE %s_%d TO %s_%d"""
                                     % (table, t, table, t+1))
            except Exception, e:
                self.debug(e)
                continue

        try:
            self.cursor.execute("""CREATE TABLE %s_1 LIKE %s""" % (table, table))
        except Exception, e:
            self.error(e)

def main():

    # Options parsing
    options = parseOptions()

    # We parse ufwi_log config file.
    parser = SafeConfigParser()

    try:
        # Check if this file exists...
        file(options.config)
    except IOError, e:
        print >>stderr, e
        exit(1)

    parser.read(options.config)

    database = Database(options, parser)

    tables = {database.ulog: 'timestamp',
              'users':       'end_time'}

    for table, timestamp in tables.items():
        if options.daily:
            database.daily_rotate(table, timestamp)
        elif options.weekly:
            database.rotate_table(table)

if __name__ == '__main__':
    main()
