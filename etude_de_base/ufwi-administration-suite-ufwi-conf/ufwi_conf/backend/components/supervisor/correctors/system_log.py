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

import os
from glob import glob
from ufwi_rpcd.common.process import createProcess

corrector_functions = []
def register(function):
    corrector_functions.append(function)
    return function

def _rm_if_exists(filename):
    if os.path.exists(filename):
        os.remove(filename)
        return True
    return False

def _rm_archives_of_log(logger, logfilename):
    """ Remove archives of given log file (e.g. daemon.log.*). """
    # Do not call this function with user data (there is no input check).
    try:
        filenames = glob("/var/log/" + logfilename + ".*")
        for filename in filenames:
            os.remove(filename)
    except Exception:
        logger.error("Error while deleting old log files from /var/log.")
        return False
    return True

def restart_rsyslog(logger):
    process = createProcess(logger, ["/etc/init.d/rsyslog", "restart"],
                            locale=False)
    exit_code = process.wait()
    if exit_code != 0:
        return False  # Failure.
    return True

def purge_logfile(logger, language, filename, need_rsyslog_restart=True):
    messages = {
        "en": "System log purge: deleted /var/log/%s." % filename,
        "fr": u"Purge des logs système : /var/log/%s effacé." % filename,
        }
    succeeded = True
    try:
        _rm_if_exists("/var/log/%s" % filename)
        if need_rsyslog_restart:
            if not restart_rsyslog(logger):
                succeeded = False
    except Exception:
        succeeded = False
    if not succeeded:
        return "Error while deleting %s." % filename
    return messages.get(language, messages["en"])

@register
def purge_ufwi_rpcd_log_archives(logger, language):
    messages = {
        "en": "System log purge: deleted old configuration service logs.",
        "fr": u"Purge des logs système : anciens logs du service " \
            u"de configuration effacés.",
        }
    succeeded = True
    for logfilename in ("ufwi_rpcd.log", "ufwi_rpcd-twistd.log"):
        if not _rm_archives_of_log(logger, logfilename):
            succeeded = False
    if not succeeded:
        return "Error while deleting configuration service logs."
    return messages.get(language, messages["en"])

@register
def purge_daemon_log_archives(logger, language):
    messages = {
        "en": "System log purge: deleted old daemon.log files.",
        "fr": u"Purge des logs système : anciens fichiers daemon.log effacés.",
        }
    if not _rm_archives_of_log(logger, "daemon.log"):
        return "Error while deleting old daemon.log files."
    return messages.get(language, messages["en"])

@register
def purge_syslog_archives(logger, language):
    messages = {
        "en": "System log purge: deleted old syslog files.",
        "fr": u"Purge des logs système : anciens fichiers syslog effacés.",
        }
    if not _rm_archives_of_log(logger, "syslog"):
        return "Error while deleting old syslog files."
    return messages.get(language, messages["en"])

@register
def purge_ufwi_rpcd_log(logger, language):
    messages = {
        "en": "System log purge: deleted configuration service logs.",
        "fr": u"Purge des logs système : logs du service de " \
            u"configuration effacés.",
        }
    no_need_messages = {
        "en": "System log purge: no need to delete configuration service logs.",
        "fr": u"Purge des logs système : pas besoin de supprimer les logs " \
            u"du service de configuration.",
        }
    succeeded = True
    deleted = False
    for filename in ("ufwi_rpcd.log", "ufwi_rpcd-twistd.log"):
        try:
            if os.path.exists(filename) and \
                    os.path.getsize(filename) > 50 * 1024 * 1024:  # 50 MB.
                os.remove("/var/log/" + filename)
                deleted = True
        except Exception:
            succeeded = False
    if not succeeded:
        return "Error while deleting configuration service logs."
    if deleted:
        return messages.get(language, messages["en"])
    else:
        return no_need_messages.get(language, no_need_messages["en"])

@register
def purge_daemon_log(logger, language):
    return purge_logfile(logger, language, "daemon.log")

@register
def purge_syslog(logger, language):
    return purge_logfile(logger, language, "syslog")

@register
def purge_biggest_logfile(logger, language):
    name_of_biggest_file = ""
    size_of_biggest_file = 0
    for path, dirnames, filenames in os.walk("/var/log"):
        for filename in filenames:
            size = os.path.getsize(os.path.join(path, filename))
            if size > size_of_biggest_file:
                name_of_biggest_file = os.path.join(path, filename)
                size_of_biggest_file = size
    if name_of_biggest_file:
        return purge_logfile(logger, language,
                             name_of_biggest_file[len("/var/log/"):])
    return "Error: could not find the biggest log file for deletion."

