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

# Number of entries considered as 100% full for edenlog.
EDENLOG_FULL_ENTRIES_COUNT = 500000

# Average size of a table entry in bytes.
sql_ratios = {
    "sql_apps_stats": 1600,  # Table apps_stats in database ulogd.
    "sql_authfail": 160,  # Table authfail in database ulogd.
    "sql_hosts_stats": 4000,  # Table hosts_stats in database ulogd.
    "sql_squid": 372,  # Table squid in database ulogd.
    "sql_ulog2": 520 + 168,  # Tables ulog2 and nufw in database ulogd.
    "sql_users": 320,  # Table users in database ulogd.
    "sql_users_stats": 2500,  # Table users_stats in database ulogd.
    }

error_margin = 1.2

# This dictionary will receive the checker functions defined and registered
# below. The keys are the function names and the values are the functions. See
# decorator "register" below.
checker_functions = {}

def register(function):
    checker_functions[function.__name__] = function
    return function

class CheckResult:
    """This dumb class has two attributes:
    - criticity: a normalized value between 0 and 100 (a high value means
      trouble); above a certain threshold (e.g. 80), we should send an
      alert by e-mail, and above a higher threshold (e.g. 95)
      we must react automatically and report by e-mail.
    - message: localized message.
    """

    def __init__(self, criticity = 0, message = ""):
        self.criticity = criticity
        self.message = message

var_log_alert = {
    "en": "System log partition is %s%% full.",
    "fr": u"La partition de logs système est remplie à %s %%.",
    }

sql_log_alert = {
    "en": "SQL log partition is %s%% full.",
    "fr": u"La partition de logs SQL est remplie à %s %%.",
    }

edenlog_alert = {
    "en": "Configuration service log space is %s%% full.",
    "fr": u"L'espace pour les logs du service de configuration est rempli " \
        u"à %s %%.",
    }

def sql_log_criticity(system_data):
    occupied_bytes = 0
    if "total_bytes_/var/lib/postgresql" not in system_data:
        return None  # Error.  Cannot check.
    for key in sql_ratios:
        if key not in system_data:
            return None  # Error.  Cannot check.
        if system_data[key]:
            occupied_bytes +=  error_margin * sql_ratios[key] * system_data[key]
    return int(100.0 * occupied_bytes / system_data[
            "total_bytes_/var/lib/postgresql"])

def edenlog_criticity(system_data):
    if "sql_edenlog" not in system_data:
        return None  # Error.  Cannot check.
    return int(100.0 * system_data["sql_edenlog"]
               / EDENLOG_FULL_ENTRIES_COUNT)

###################
# Check functions #
###################

@register
def check_var_log(system_data, language):
    if "var_log" not in system_data:
        return None  # Error.  Cannot check.
    criticity = system_data["var_log"]
    message = var_log_alert.get(language, var_log_alert["en"]) % criticity
    return CheckResult(criticity, message)

@register
def check_sql_log(system_data, language):
    criticity = sql_log_criticity(system_data)
    if criticity is None:
        return None  # Error.  Cannot check.
    message = sql_log_alert.get(language, sql_log_alert["en"]) % criticity
    return CheckResult(criticity, message)

@register
def check_edenlog(system_data, language):
    criticity = edenlog_criticity(system_data)
    if criticity is None:
        return None  # Error.  Cannot check.
    message = edenlog_alert.get(language, edenlog_alert["en"]) % criticity
    return CheckResult(criticity, message)

