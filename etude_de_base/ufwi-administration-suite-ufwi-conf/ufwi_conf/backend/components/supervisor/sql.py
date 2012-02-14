# -*- coding: utf-8 -*-
"""
Copyright (C) 2010-2011 EdenWall Technologies
Written by François Toussenel <ftoussenel AT edenwall.com>

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

"""

import psycopg2
from .checkers import sql_ratios

step_max_count = 50000  # Do not delete more rows than this at once.
slice_interval = 3600 * 24 * 7  # One week.
_sql_ratios_tables = tuple(key[4:] for key in sql_ratios.keys())
id_columns = {
    "ulog2": "_id",
    "squid": "_id",
    }

def get_ulogd_credentials(logger):
    nulog_conf = logger.core.config_manager.get("nulog")
    return (nulog_conf["config"]["username"],
            nulog_conf["config"]["password"])

def connect(dbname, user, password):
    connection = psycopg2.connect(
        "host=localhost dbname=%(dbname)s user=%(user)s password=%(password)s"
        % {"dbname": dbname, "user": user, "password": password})
    return connection

def entry_counts(system_data, logger):
    result = True
    ulogd_user, ulogd_password = get_ulogd_credentials(logger)
    for database, tables in ((("ulogd", ulogd_user, ulogd_password),
                              _sql_ratios_tables),):
        connection = connect(*database)
        cursor = connection.cursor()
        for table in tables:
            try:
                id_column = id_columns.get(table, "")
                if id_column == "":
                    cursor.execute("SELECT count(*) FROM %s" % table)
                else:
                    cursor.execute("SELECT max(%s) - min(%s) FROM %s" %
                                   (id_column, id_column, table))
                value = cursor.fetchone()
            except Exception:
                connection.rollback()
                if table not in ("dpi", "dropped_users"):
                    logger.error("Error while counting entries in table %s" %
                                 table)
                    raise
            if value:
                system_data["sql_%s" % table] = value[0]
            else:
                result = False
        connection.close()
    return result

def get_min_times(logger):
    min_times = {}

    # ulogd database.
    ulogd_user, ulogd_password = get_ulogd_credentials(logger)
    connection = connect("ulogd", ulogd_user, ulogd_password)

    for table, min_column in (
        ("squid", "min(timestamp)"),
        ("ulog2", "min(oob_time_sec)"),
        ):
        cursor = connection.cursor()
        cursor.execute("SELECT %s from %s" % (min_column, table))
        result = cursor.fetchone()
        if result:
            min_times["sql_%s" % table] = result[0]
        else:
            min_times["sql_%s" % table] = None

    connection.close()

    return min_times

def delete_slice_table(logger, connection, min_time, table, id_column,
                       time_column, log_name, join=""):

    if not connection:
        return None
    cursor = connection.cursor()

    end_time = min_time + slice_interval

    deleted_count = 0
    while True:  # While there are more entries before end_time.
        try:
            cursor.execute(
                "DELETE FROM %s WHERE %s IN (SELECT %s FROM %s %s WHERE "
                "%s <= %d LIMIT %d)" %
                (table, id_column, id_column, table, join, time_column,
                 end_time, step_max_count))

            deleted_count += cursor.rowcount
            rowcount = cursor.rowcount
            connection.commit()
            logger.info(
                "SQL purge: deleted %d entries in %s logs until %d." %
                (rowcount, log_name, end_time))
            if rowcount < step_max_count:
                break
        except Exception, err:
            logger.writeError(
                err, "Error while deleting entries in %s logs until %d." %
                (log_name, end_time))
            return None
    return deleted_count

def delete_slice(logger):
    deleted_counts = {}
    min_times = get_min_times(logger)
    min_times_values = filter(None, min_times.values())  # None-proof.
    if min_times_values:
        min_time = min(min_times_values)
    else:
        return deleted_counts

    # Database ulogd.
    ulogd_user, ulogd_password = get_ulogd_credentials(logger)
    connection = connect("ulogd", ulogd_user, ulogd_password)
    # First, delete entries in nufw table (linked to ulog2). Next, delete
    # entries in the rest of the tables. Do not mention deletion in nufw table
    # in the alert (do not add it in correctors/sql_log.py).
    delete_slice_table(
        logger, connection, min_time, "nufw", "_nufw_id",
        "ulog2.oob_time_sec", "users",
        "LEFT JOIN ulog2 ON (ulog2._id = nufw._nufw_id)")
    for table, log_name, id_column, time_column in (
        ("ulog2", "firewall", "_id", "oob_time_sec"),
        ("squid", "proxy", "_id", "timestamp"),
        ):
        if min_times.get("sql_%s" % table, None) is not None:
            deleted_counts["sql_%s" % table] = delete_slice_table(
                logger, connection, min_time, table, id_column, time_column,
                log_name)
    connection.close()

    return deleted_counts

def edenlog_entry_counts(system_data, logger):
    result = True
    connection = connect(*["edenlog"]*3)
    cursor = connection.cursor()
    cursor.execute("SELECT max(id) - min(id) FROM edenlog")
    value = cursor.fetchone()
    if value:
        system_data["sql_edenlog"] = value[0]
    else:
        result = False
    connection.close()
    return result

def delete_edenlog_entries(logger, count):
    connection = connect(*["edenlog"]*3)
    cursor = connection.cursor()
    cursor.execute("DELETE FROM edenlog WHERE id IN (SELECT id FROM edenlog "
                   "ORDER BY date LIMIT %d)" % count)
    deleted_count = cursor.rowcount
    connection.commit()
    connection.close()
    return deleted_count

