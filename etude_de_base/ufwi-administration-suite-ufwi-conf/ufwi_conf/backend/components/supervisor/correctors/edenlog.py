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

from ..sql import delete_edenlog_entries
from ..checkers import EDENLOG_FULL_ENTRIES_COUNT
from ..thresholds import Thresholds

purge_messages = {
    "en": "Purge of configuration service logs: deleted %d entries.",
    "fr": u"Purge des logs du service de configuration : effacé %d entrées.",
    }

corrector_functions = []
def register(function):
    corrector_functions.append(function)
    return function

@register
def purge_edenlog_entries(logger, criticity, system_data, language):
    if "sql_edenlog" not in system_data:
        return ""
    target_count = 0.01 * Thresholds.sane * EDENLOG_FULL_ENTRIES_COUNT
    diff_count = system_data["sql_edenlog"] - target_count
    if diff_count > 0:
        deleted_count = delete_edenlog_entries(logger, diff_count)
    return purge_messages.get(language, purge_messages["en"]) % deleted_count

