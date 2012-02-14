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

from .refreshers import refresher_functions
from ufwi_rpcd.common.process import (createProcess, readProcessOutput)
import subprocess

def total_space_partition(logger, partition):
    process = createProcess(logger, ["df", "-P", partition],
                            stdout=subprocess.PIPE, locale=False)
    exit_code = process.wait()
    if exit_code != 0:
        return False  # Failure.
    value = readProcessOutput(process.stdout, 2)
    if len(value) < 2:
        return False  # Failure.
    try:
        return int(value[1].split()[1]) * 1024
    except Exception:
        return False  # Failure.

def data_gatherer(logger):
    """This function gathers all system data, return in a dictionary.  It may
    call specialized refreshers but is supposed to retrieve more data at once
    (using less processes).
    """

    system_data = {}

    total_bytes_sql = total_space_partition(logger, "/var/lib/postgresql")
    if total_bytes_sql:
        system_data["total_bytes_/var/lib/postgresql"] = total_bytes_sql

    [refresher_function(system_data, logger)
     for refresher_function in refresher_functions.values()]
    return system_data
