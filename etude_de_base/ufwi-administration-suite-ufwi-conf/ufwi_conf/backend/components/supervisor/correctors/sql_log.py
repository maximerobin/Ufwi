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

from ..sql import delete_slice
from ..checkers import (sql_log_criticity, sql_ratios)
from ..thresholds import Thresholds

purge_messages = {
    "en": "SQL purge: deleted %d entries in firewall logs and %d entries " \
        "in proxy logs.",
    "fr": u"Purge SQL : effacé %d entrées dans les logs du pare-feu et " \
        u"%d entrées dans les logs du proxy.",
    }

corrector_functions = []
def register(function):
    corrector_functions.append(function)
    return function

def update(original_criticity, total_deleted_counts, deleted_counts,
           system_data):
    if deleted_counts is None:
        return None
    new_system_data = system_data.copy()
    for key, value in deleted_counts.items():
        if value:
            total_deleted_counts[key] += value
        new_system_data[key] = system_data[key] - total_deleted_counts[key]
    return sql_log_criticity(new_system_data)

@register
def purge_sql_log_slices(logger, original_criticity, system_data, language):
    total_deleted_counts = {}
    for table in sql_ratios.keys():
        total_deleted_counts[table] = 0

    criticity = original_criticity
    safety_counter = 0  # We absolutely must avoid an infinite loop.
    while criticity > Thresholds.sane:
        deleted_counts = delete_slice(logger)
        criticity = update(original_criticity, total_deleted_counts,
                           deleted_counts, system_data)
        if criticity is None:
            return "SQL purge: error while deleting old log entries."
        safety_counter += 1
        if safety_counter > 100:
            break
    return purge_messages.get(language, purge_messages["en"]) % (
        total_deleted_counts["sql_ulog2"], total_deleted_counts["sql_squid"])
