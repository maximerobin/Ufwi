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

from ufwi_rpcd.backend.cron import scheduleOnce
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.contact_cfg import ContactConf
from .checkers import CheckResult
from .data_gatherer import data_gatherer
from .mail import SupervisorMail
from .reactions import reaction_functions
from .thresholds import Thresholds
from twisted.internet.defer import inlineCallbacks
from twisted.internet.threads import deferToThread

delay_seconds = 3600

purge_next_messages = {
    "en": "The next alert will be accompanied with an automatic purge " \
        "of old entries.",
    "fr": u"La prochaine alerte sera accompagnée d'une purge automatique " \
        u"d'anciennes entrées.",
}

failure_messages = {
    "en": "Could not correct the situation using function %s.",
    "fr": u"Échec du rétablissement de la situation en utilisant " \
        u"la fonction %s.",
}

warning_messages = {
    "en": "Warning: ",
    "fr": u"Avertissement : ",
}

subjects = {
    "en": "New alerts",
    "fr": u"Nouvelles alertes",
}

class SupervisorComponent(AbstractNuConfComponent):
    """
    This component periodically checks system data like space available in the
    log partition, compares them to thresholds and take appropriate action
    (alert e-mail and/or selective purges).
    """

    NAME = "supervisor"
    VERSION = "1.0"
    ACLS = {
        "contact": set(("sendMailToAdmin",)),
        }
    ROLES = {"conf_write": set(("purge",)),
             "conf_read": set(("getStates",))}
    CONFIG_DEPENDS = ("contact",)

    def __init__(self):
        AbstractNuConfComponent.__init__(self)
        self.states = VariablesStore()
        self.registered_for_mail = SupervisorMail()
        self.purging = False

    def init_done(self):
        self.states_path = os.path.join(
            self.core.config.get("CORE", "vardir"), "supervisor.xml")
        try:
            self.states.load(self.states_path)
        except ConfigError:
            for reaction_function in reaction_functions:
                self.states.set(reaction_function.__name__, 0)
        # Launch the first check in 10 seconds. The callback function will
        # schedule itself with a delay of delay_seconds seconds at the end of
        # its body.
        scheduleOnce(10, self.check_and_react)

    # (Method copied from contact.py and extended.)
    def read_config(self, *args, **kwargs):
        self.config = ContactConf.defaultConf()
        try:
            serialized = self.core.config_manager.get("contact")
            valid, message = self._setconfig(serialized)
            if not valid:
                self.error(
                    "This means that the configuration is incorrect or that there is a bug"
                    )
        except ConfigError:
            self.debug("Not configured, defaults loaded.")

        self.registered_for_mail.set_config(self.config)

    # (Method copied from contact.py.)
    def _setconfig(self, serialized):
        # TODO: factorize with exim component _setconfig (and maybe other modules)
        config = ContactConf.deserialize(serialized)

        valid, error = config.isValidWithMsg()
        if valid:
            self.config = config
        else:
            self.error(
                "Component %s read incorrect values. Message was: %s" % (self.NAME, error)
                )
        return valid, error

    def apply_config(self, *unused):
        pass

    def enhance_message(self, name, check_result):
        """ Add information to base message and return whether the alert is
        new. """
        threshold = Thresholds.in_threshold(check_result.criticity)
        previous_threshold = Thresholds.in_threshold(
            self.states.get(name))
        if threshold == Thresholds.last_alert:
            check_result.message += " " + purge_next_messages.get(
                self.config.language, purge_next_messages["en"])
        if threshold >= Thresholds.alert1:
            check_result.message = warning_messages.get(
                self.config.language, warning_messages["en"]) + \
                check_result.message
        return Thresholds.threshold_higher(previous_threshold, threshold)

    def mail_and_log(self, logger_function, name, *args):
        """ Log if new and register for mail (as new or old). """
        new = False
        if isinstance(args[0], CheckResult):
            new = self.enhance_message(name, args[0])
            logger_args = (args[0].message,) + args[1:]
        else:
            logger_args = args
        if logger_function == self.critical:
            new = True
        if new:
            logger_function(*logger_args)
        if logger_args:
            self.register_for_mail(name, new, logger_args[0])

    def mail_critical(self, name, *args):
        """ A critical message is always new. """
        self.mail_and_log(self.critical, name, *args)

    def mail_warning(self, name, *args):
        self.mail_and_log(self.warning, name, *args)

    def register_for_mail(self, name, new, message):
        self.registered_for_mail.add_alert(name, new, message)

    def handle_last_result(self, name, check_result, reached_insane):
        """ Register messages to include in an e-mail. If the first and/or
        intermediate results reached insane threshold, an e-mail was already
        sent. """

        if check_result.criticity >= Thresholds.insane:
            failure_message = failure_messages.get(
                self.config.language,
                failure_messages["en"]) % name
            self.mail_critical(name, failure_message)
            return
        if check_result.criticity >= Thresholds.alert1:
            # mail_warning will decide whether this is a new alert.
            self.mail_warning(name, check_result)
        else:
            if reached_insane:
                # Add it to new alerts and to critical logs, to show that
                # after being insane the situation is back to normal.
                self.mail_critical(name, check_result.message)
            self.registered_for_mail.add_other(name, check_result.message)

    def _execute_reactions(self, system_data, manual_purge):
        # Each reaction function addresses a problem and executes corrections
        # if necessary, until the problem is solved.  For instance,
        # purge_system_log checks /var/log partition remaining space and
        # deletes logs if there is not enough space left.
        for reaction_function in reaction_functions:
            try:
                check_results = reaction_function(
                    system_data, self, self.config.language, manual_purge)
                if not check_results:  # Should not happen in production.
                    self.critical("Error: could not check criticity for "
                                  "function %s." % reaction_function.__name__)
                    break
                reached_insane = False
                for check_result in check_results:
                    if check_result.criticity >= Thresholds.insane:
                        self.mail_critical(reaction_function.__name__,
                                           check_result.message)
                        reached_insane = True
                # Warn if the problem is still present (testing last
                # check_result).
                if check_results and check_results[-1]:
                    self.handle_last_result(reaction_function.__name__,
                                            check_results[-1], reached_insane)
                    self.states.set(reaction_function.__name__,
                                    check_results[-1].criticity)
                    self.states.save(self.states_path)
            except Exception, err:
                self.writeError(
                    err, "Error while checking system with function %s" %
                    reaction_function.__name__)

    @inlineCallbacks
    def check_and_react(self, manual_purge=False):
        yield deferToThread(self._check_and_react, manual_purge)
        try:
            if self.registered_for_mail.new_alerts:
                body = self.registered_for_mail.make_body()
                context = Context.fromComponent(self)
                yield self.core.callService(context, 'contact', 'sendMailToAdmin',
                                      subjects.get(self.config.language,
                                                   subjects["en"]),
                                      body)
        except Exception, err:
            self.writeError(err, "Error while sending alert e-mail")

        if not manual_purge:
            scheduleOnce(delay_seconds, self.check_and_react)

    def _check_and_react(self, manual_purge=False):
        self.purging = True
        system_data = data_gatherer(self)
        self.registered_for_mail.clear()
        self._execute_reactions(system_data, manual_purge)
        self.purging = False

    ############
    # Services #
    ############

    def service_purge(self, context):
        if self.purging:
            return False
        self.purging = True
        self.info("Manual purge.")
        # check_and_react will set self.purging to False when done.
        self.check_and_react(manual_purge=True)
        return True

    def service_getStates(self, context):
        table = []
        for name in sorted(self.states.keys()):
            table.append({"name": name,
                          "criticity": self.states[name],
                          "level": Thresholds.level(self.states[name])})
        return table
