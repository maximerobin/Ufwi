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

from .checkers import checker_functions
from .correctors import (
    edenlog_corrector_functions,
    sql_log_corrector_functions,
    system_log_corrector_functions,
    )
from .refreshers import refresher_functions
from .thresholds import Thresholds

reaction_functions = []

# Decorator to avoid having to manually list functions.
def register(function):
    reaction_functions.append(function)
    return function

def check(checker, system_data, logger, language):
    try:
        check_result = checker(system_data, language)
    except Exception, err:
        logger.writeError(
            err, "Error while checking system data with function %s" %
            checker.__name__)
        check_result = None
    return check_result


######################
# Reaction functions #
######################

@register
def purge_system_log(system_data, logger, language, manual_purge=False):
    check_results = []  # Check results to return.
    checker = checker_functions["check_var_log"]
    refresher = refresher_functions["refresh_var_log"]
    check_result = check(checker, system_data, logger, language)
    if check_result is None:  # Error. Cannot check.
        return []
    if check_result.criticity < Thresholds.insane and not manual_purge:
        return [check_result]
    # Trigger correctors one by one until the criticity falls below the sane
    # threshold.
    for corrector in system_log_corrector_functions:
        if check_result is None:  # Error. Cannot check.
            return check_results
        check_results.append(check_result)
        if check_result.criticity >= Thresholds.sane:
            corrector_message = corrector(logger, language)
            check_result.message += " " + corrector_message
        else:
            break
        # Refresh the system data we need.
        refresh_succeeded = refresher(system_data, logger)
        # Proceed only if we could refresh system_data.
        if not refresh_succeeded:  # Could not refresh system data.
            break
        check_result = check(checker, system_data, logger, language)
    check_results.append(check_result)
    return check_results

@register
def purge_sql_log(system_data, logger, language, manual_purge=False):
    check_results = []  # Check results to return.
    checker = checker_functions["check_sql_log"]
    refresher = refresher_functions["refresh_sql_log"]
    check_result = check(checker, system_data, logger, language)
    if check_result is None:  # Error. Cannot check.
        return []
    if check_result.criticity < Thresholds.insane and not manual_purge:
        return [check_result]
    # Execute the unique corrector until the criticity falls below the sane
    # threshold or there is no more improvement.
    previous_criticity = check_result.criticity + 2
    while check_result.criticity < previous_criticity:
        for corrector in sql_log_corrector_functions:
            if check_result is None:  # Error. Cannot check.
                return check_results
            check_results.append(check_result)
            if check_result.criticity >= Thresholds.sane:
                corrector_message = corrector(logger, check_result.criticity,
                                              system_data, language)
                check_result.message += " " + corrector_message
            else:
                return check_results
            # Refresh the system data we need.
            refresh_succeeded = refresher(system_data, logger)
            # Proceed only if we could refresh system_data.
            if not refresh_succeeded:  # Could not refresh system data.
                logger.warning(
                    "Error: Could not re-estimate the SQL occupation level.")
                return check_results
            previous_criticity = check_result.criticity
            check_result = check(checker, system_data, logger, language)
    return check_results

@register
def purge_edenlog(system_data, logger, language, manual_purge=False):
    check_results = []  # Check results to return.
    checker = checker_functions["check_edenlog"]
    refresher = refresher_functions["refresh_edenlog"]
    check_result = check(checker, system_data, logger, language)
    if check_result is None:  # Error. Cannot check.
        return []
    if check_result.criticity < Thresholds.insane and not manual_purge:
        return [check_result]
    # Execute the unique corrector until the criticity falls below the sane
    # threshold or there is no more improvement.
    previous_criticity = check_result.criticity + 2
    while check_result.criticity < previous_criticity:
        for corrector in edenlog_corrector_functions:
            if check_result is None:  # Error. Cannot check.
                return check_results
            check_results.append(check_result)
            if check_result.criticity > Thresholds.sane:
                corrector_message = corrector(logger, check_result.criticity,
                                              system_data, language)
                check_result.message += " " + corrector_message
            else:
                return check_results
            # Refresh the system data we need.
            refresh_succeeded = refresher(system_data, logger)
            # Proceed only if we could refresh system_data.
            if not refresh_succeeded:  # Could not refresh system data.
                logger.warning(
                    "Error: Could not re-estimate the service configuration "
                    "log occupation level.")
                return check_results
            previous_criticity = check_result.criticity
            check_result = check(checker, system_data, logger, language)
    return check_results

