"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>

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

import weakref
from logging import getLogger

APPLY_ACTIONS = (
    #Restoration
    LOADING_IMPORTED_CONF, #warning, this prunes HA data
    RESTORING_CONFIGURATION, # when saving new config (not apply)
    RESET_CONFIG,
    #There is no config
    FIRST_BOOT,
    #Normal
    BOOTUP_APPLY,
    INITIAL_APPLY,
    USER_APPLY,
    #HA
    HA_FIRST_REPLICATION,
    HA_FULL_SYNCHRONIZATION,
    HA_INCREMENTAL,
    #UPDATE
    UPDATE_WITH_FULL_RELOAD,
    #User tweak
    USER_FORCED_REAPPLICATION,
    ) = (
    #Restoration
    "LOADING IMPORTED CONF",
    "RESTORING CONFIGURATION",
    "RESET CONFIGURATION",
    #There is no config
    "APPLYING -FIRST BOOT",
    #Normal
    "APPLYING -BOOT UP-",
    "APPLYING -INITIAL_APPLY",
    "APPLYING -USER TRIGGERED",
    #HA
    "HA -FIRST REPLICATION",
    "HA -FULL SYNCHRONIZATION",
    "HA -INCREMENTAL SYNC",
    #UPDATE
    "UPDATE REQUIRING FULL RELOAD",
    #User tweak
    "USER FORCED REAPPLICATION OF ALL CONFIG",
    )

COMMIT_ACTIONS = (
    #Saving config
    CONFIG_MODIFICATION,
    CONFIG_AUTOCONFIGURATION,
    CONFIG_ERASURE,
    ) = (
    "CONFIG MODIFICATION",
    "CONFIG AUTOCONFIGURATION",
    "UNCONFIGURING",
    )

ACTIONS = APPLY_ACTIONS + COMMIT_ACTIONS

class Responsible(object):
    """
    Objects of this class contain the context of
    many interactions with the config module, be it IN or OUT.
    """
    def __init__(self, user_context=None, caller_component=None, action=None):
        if user_context and user_context.isUserContext():
            # Context object of an user
            self.user_context = user_context
            logdomain = user_context.user.login
        else:
            self.user_context = None
            if caller_component:
                logdomain = caller_component
            elif action:
                logdomain = action
            else:
                logdomain = ""

        if not action in ACTIONS:
            errmsg = \
                "Unknown action '%s'" % unicode(action) if action \
                else "Action not specified"
            raise ValueError(errmsg)

        # Component name (str)
        self.caller_component = caller_component
        self.action = action   # a value from ACTIONS
        self._journal = None
        self.fallback_logger = getLogger(logdomain)
        self.storage = {}

    def trace_message(self):
        info = []
        if self.caller_component:
            info.append(u"[component %s]" % self.caller_component)
        if self.user_context:
            info.append(u"[user %s]" % unicode(self.user_context))
        if self.action:
            info.append(u"[action %s]" % self.action)
        return u' '.join(info)

    @staticmethod
    def fromContext(context, caller_component=None, action=None):
        if context.isUserContext():
            return Responsible(
                user_context=context,
                caller_component=caller_component,
                action=action)
        return Responsible(
            caller_component=context.component.name,
            action=action
            )

    def setjournal(self, application_journal):
        self._journal = weakref.ref(application_journal)
        application_journal.reset()

    def feedback(self, message, **substitution):
        """
        message is a string, maybe translated: you should enclose its definition
        in a ufwi_rpcd.common.tr() call.
        feedback(tr("hello world"))

        The message may contain keyword substitutions:
        feedback(
            tr("hello %(USER)s."),
            USER=user_name
            )
        """
        journal = self._journal()
        if journal:
            journal.component_info(message, **substitution)
            return

        #fallback
        self.fallback_logger.info(message % substitution)

    def error(self, message, **substitution):
        journal = self._journal()
        if journal:
            journal.log_error(message, **substitution)
            return

        #fallback
        self.fallback_logger.error(message % substitution)

    def warning(self, message, **substitution):
        journal = self._journal()
        if journal:
            journal.log_warning(message, **substitution)
            return

        #fallback
        self.fallback_logger.warning(message % substitution)

    def isRestoring(self):
        return (self.action == RESTORING_CONFIGURATION)

    def implies_full_reload(self):
        """
        Does the current process imply a full reload
        of the slave components of config?
        """
        return self.action in (
            HA_FIRST_REPLICATION,
            HA_FULL_SYNCHRONIZATION,
            LOADING_IMPORTED_CONF,
            RESTORING_CONFIGURATION,
            UPDATE_WITH_FULL_RELOAD,
            USER_FORCED_REAPPLICATION,
            )

    def implies_saved_config_on_hold(self):
        """
        Does the current process imply to put the saved config,
        waiting for application, on hold, before continuing?
        Consistently, the backuped saved conf should be restored afterwards
        """
        return self.action in (
            UPDATE_WITH_FULL_RELOAD,
            USER_FORCED_REAPPLICATION
            )

    def implies_prune_ha(self):
        return self.action == LOADING_IMPORTED_CONF

    def has_no_diff(self):
        #XXX to be continued
        return self.action in (
            BOOTUP_APPLY,
            HA_FIRST_REPLICATION,
            HA_FULL_SYNCHRONIZATION,
            HA_INCREMENTAL,
            USER_FORCED_REAPPLICATION,
            )

