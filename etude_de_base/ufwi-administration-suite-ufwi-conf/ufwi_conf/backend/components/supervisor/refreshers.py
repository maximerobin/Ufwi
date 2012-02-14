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

from ufwi_rpcd.common.process import (createProcess, readProcessOutput)
from .sql import (edenlog_entry_counts, entry_counts)
import re
import subprocess

# This dictionary will receive the refresher functions defined and registered
# below. The keys are the function names and the values are the functions. See
# decorator "register" below.
refresher_functions = {}

def register(function):
    refresher_functions[function.__name__] = function
    return function

var_log_re = re.compile(r"\s(\d+)%")


#######################
# Refresher functions #
#######################

@register
def refresh_var_log(system_data, logger):
    # "df -P /var/log | sed -n '2s/.*\s\([0-9]\+\)%.*/\1/p'"
    process = createProcess(logger, ["df", "-P", "/var/log"],
                            stdout=subprocess.PIPE, locale=False)
    exit_code = process.wait()
    if exit_code != 0:
        return False  # Failure.
    value = readProcessOutput(process.stdout, 2)
    if len(value) < 2:
        return False  # Failure.
    m = var_log_re.search(value[1])
    if not m:
        return False  # Failure.
    system_data["var_log"] = int(m.group(1))
    return True  # Success.

@register
def refresh_sql_log(system_data, logger):
    """ Refresh data and return True if it succeeded. """
    return entry_counts(system_data, logger)

@register
def refresh_edenlog(system_data, logger):
    """ Refresh data and return True if it succeeded. """
    return edenlog_entry_counts(system_data, logger)

