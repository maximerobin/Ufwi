#coding: utf-8
"""

Copyright (C) 2009-2011 EdenWall Technologies

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

# TODO refactor logWithTimestamp, _display_err, display_message, _change_phase
# use one method:
# def display_message(message, color=None, timestamp=None, prefix=None)
# color is used with message and format is timestamp prefix: message
#
# another enhancement: message associated with phases should be sent by server
# in _change_phase method

from datetime import datetime

from PyQt4.QtCore import QTimer
from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.client.error import SessionError, RpcdError
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.journal_messages import (APPLIED_COMPONENT_LIST,
    APPLYING, APPLYING_DONE, COMPONENT_FIRED, COMPONENT_LISTS,
    COMPONENT_MESSAGE, ERRORS, GLOBAL_ERROR, GLOBAL_WARNING, GLOBAL,
    GLOBAL_APPLY_SKIPPED, GLOBAL_DONE, PHASE_CHANGE,
    ROLLED_BACK_COMPONENT_LIST, ROLLING_BACK, ROLLING_BACK_DONE)

from ufwi_rpcd.common.transport import parseDatetime
from ufwi_rpcc_qt.central_window import STANDALONE
from ufwi_rpcc_qt.colors import COLOR_CRITICAL, COLOR_FANCY, COLOR_WARNING
from ufwi_rpcc_qt.error import formatException
from ufwi_rpcc_qt.services_name import ComponentToName
from ufwi_rpcc_qt.splash import SplashScreen
from ufwi_rpcc_qt.html import htmlColor, htmlBold, Html, BR
from ufwi_rpcc_qt.colors import COLOR_ERROR, COLOR_INVALID, COLOR_SUCCESS, COLOR_VERBOSE

_BASE_INTERVAL = 5 #msec
_MAX_INTERVAL = 2000

COLOR_TIMESTAMP = COLOR_VERBOSE
COLOR_EMPHASIZED = "#770077"

RESTORATION_WARNING_TITLE = tr("Restoration procedure")
RESTORATION_WARNING = tr("Applying now (after uploading a backup file) will "
    "erase the current configuration, including the network configuration. "
    "Please make sure that the network and the user directory configurations "
    "are valid in the current context. Otherwise, restoration could fail. "
    "Cancel now or proceed.")

def formatTimestamp(timestamp=None, server_time=False):
    if timestamp is None:
        timestamp = datetime.now()
    # strip microseconds
    timestamp = unicode(timestamp)
    timestamp = timestamp.split(u".", 1)[0]
    if server_time:
        html = tr("server: %s") % timestamp
    else:
        html = timestamp
    html = u"[%s]" % html
    return htmlColor(html, COLOR_TIMESTAMP) + ' '

class Applier(object):
    def __init__(self, mainwindow):
        self.mainwindow = mainwindow
        self._interval = _BASE_INTERVAL
        self.addToInfoArea = mainwindow.addToInfoArea
        self.client = mainwindow.client
        self.splash = SplashScreen()
        self._component_to_name = ComponentToName()
        self.reset()

    def setPhase(self, phase):
        self._last_fired_component = ''
        self._last_fired_component_formatted = ''

    def reset(self):
        self._last_read_index = 0
        self._apply_error = None
        self._applied_component_list = []
        self._rolled_back_component_list = []
        self._rollback_occurred = False
        self._component_counter = 0
        self._final_success_msg = ''
        self._final_error_msg = ''
        self._rollback_error_msg = ''
        self.setPhase('')

    def rollback(self):
        self._component_counter = 0
        self._rollback_occurred = True

    def start(self):
        self.__start_info()
        async = self.client.async()
        async.call('config', 'applyStart',
            callback=self._start_ok,
            errback=self._start_err
            )

    def __force_start(self):
        async = self.client.async()
        async.call('config', 'forceApplyStart',
            callback=self._start_ok,
            errback=self._start_err
            )

    def __start_info(self):
        # Log an empty line
        self.mainwindow.addHTMLToInfoArea(BR)
        self.splash.setText(tr("Applying the new configuration"))
        #TODO: disable hiding on clic.
        self.splash.show()

    def __end_all(self):
        self.splash.hide()
        if self.mainwindow._standalone != STANDALONE:
            self.mainwindow.eas_window.setModified(False)
        # Log an empty line
        self.mainwindow.addHTMLToInfoArea(BR)
        if self._rollback_occurred:
            message = tr("The application of the new configuration failed: the previous configuration has been restored.")
            if self._apply_error:
                message = message + BR + BR + self._apply_error
                message = unicode(message)
            QMessageBox.critical(
                self.mainwindow,
                tr("Application failed"),
                message
                )
        else:
            self.mainwindow.apply_done()

    def component_label(self, comp_name):
        return self._component_to_name.display_name(comp_name)

    def __handle_SessionError(self, err):
        """
        Only acts if action is relevant.
        You safely can pass any error to this function.
        """
        if isinstance(err, SessionError):
            QMessageBox.critical(
                self.mainwindow,
                tr("Disconnected!"),
                tr("You have been disconnected. "
                "Your changes are lost. You may log in again.")
                )
                #FIXME: exit?

    def __handle_errors(self, err):
        debug = self.mainwindow.debug
        if debug:
            html = Html(formatException(err, debug), escape=False) + BR
            self.mainwindow.addHTMLToInfoArea(html, category=COLOR_WARNING)
        else:
            text = exceptionAsUnicode(err)
            self.addToInfoArea(text, category=COLOR_WARNING)
        self.__handle_SessionError(err)

    def logWithTimestamp(self, timestamp, html, prefix=None):
        html = Html(html, escape=False) + BR
        timestamp = formatTimestamp(timestamp, True)
        if prefix is not None:
            timestamp = timestamp + prefix
        self.mainwindow.addHTMLToInfoArea(html, prefix=timestamp)

    def __process_logs(self, logs):
        """
        Does everything that has to be done with logs

        -Write them on the console.
        -take any relevant action

        returns True if there are other messages to process
                False if all messages have been processed
        """
        has_more = True
        if len(logs) == 0:
            if self._interval < _MAX_INTERVAL:
                self._interval *= 2
        for log in logs:
            self._interval = _BASE_INTERVAL
            self._last_read_index += 1
            timestamp, message_type, content = log
            timestamp = parseDatetime(timestamp)
            if message_type == PHASE_CHANGE:
                has_more = self._change_phase(timestamp, content)
            elif message_type in ERRORS:
                self._display_err(timestamp, content)
            elif message_type in (GLOBAL_ERROR, GLOBAL_WARNING):
                colors = {GLOBAL_ERROR:COLOR_ERROR ,GLOBAL_WARNING:COLOR_WARNING}
                format, substitutions = content
                message = tr(format) % substitutions
                self.display_message(timestamp, message, color=colors[message_type])
            elif message_type in COMPONENT_LISTS:
                self._process_component_list(timestamp, message_type, content)
            elif message_type in COMPONENT_FIRED:
                self._set_last_fired_component(content)
                message = tr("%(COMPONENT_NAME)s is being configured") % {
                    "COMPONENT_NAME": self._last_fired_component_formatted}
                splash_message = self._last_fired_component
                self._component_counter += 1
                if self._rollback_occurred:
                    components = self._rolled_back_component_list
                else:
                    components = self._applied_component_list
                if components:
                    progress = " (%s/%s)" % (self._component_counter, len(components))
                    message += progress
                    splash_message += progress
                self.logWithTimestamp(timestamp, message)
                self.splash.setText(splash_message)
            elif COMPONENT_MESSAGE == message_type:
                format, substitutions = content
                message = tr(format) % substitutions
                message = htmlColor(message, COLOR_VERBOSE)
                message = tr("%s: %s") % (
                    self._last_fired_component,
                    unicode(message))
                self.logWithTimestamp(timestamp, message)
            else:
                # unknow message type
                message = tr("%s (unknown message type: '%s')")
                message = message % (content, message_type)
                message = htmlColor(message, COLOR_INVALID)
                self.logWithTimestamp(timestamp, message)

        return has_more

    def _set_last_fired_component(self, component_name):
        translated = self.component_label(component_name)
        self._last_fired_component = translated
        self._last_fired_component_formatted = htmlBold(
            htmlColor(translated, COLOR_EMPHASIZED)
            )

    def _display_err(self, timestamp, err):
        name = self._last_fired_component
        html = tr("%s triggered the following error") % name
        html = htmlColor(html, COLOR_ERROR)
        err = Html(err) # content is an error
        html = tr("%s: %s") % (unicode(html), unicode(err))
        if not self._rollback_occurred:
            self._apply_error = Html(html, escape=False)
        self.logWithTimestamp(timestamp, html)

    def display_message(self, timestamp, message, color=None, prefix=None):
        if color is not None:
            html = htmlColor(message, color)
        else:
            html = Html(message)
        self.logWithTimestamp(timestamp, html)

    def _change_phase(self, timestamp, phase):
        """
        returns True if there are other messages to process
                False if all messages have been processed
        """
        self.setPhase(phase)
        has_more = True
        hexacolor = None

        if phase == GLOBAL_DONE:
            if self._rollback_occurred:
                return False
            hexacolor = COLOR_SUCCESS
            message = tr("The new configuration has been successfully applied")
            if self._final_success_msg:
                message = self._final_success_msg
            message = htmlBold(message)
            has_more = False
        elif phase == GLOBAL_APPLY_SKIPPED:
            hexacolor = COLOR_SUCCESS
            message = tr("Application skipped")
            message = htmlBold(message)
            has_more = False
        elif phase == GLOBAL:
            hexacolor = COLOR_EMPHASIZED
            message = tr("Applying the new configuration")
            message = htmlBold(message)
        elif phase == APPLYING:
            hexacolor = COLOR_EMPHASIZED
            message = tr("Normal application phase started")
        elif phase == APPLYING_DONE:
            hexacolor = COLOR_EMPHASIZED
            message = tr("Normal application phase completed")
        elif phase == ROLLING_BACK:
            self.rollback()
            hexacolor = COLOR_ERROR
            message = tr("The application of the new configuration failed: "
                "restoring the previous configuration")
            if self._rollback_error_msg:
                message = self._rollback_error_msg
            message = htmlBold(message)
        elif phase == ROLLING_BACK_DONE:
            self._rollback_occurred = True
            hexacolor = COLOR_ERROR
            message = tr("The application of the new configuration failed: "
                "the previous configuration has been restored")
            if self._final_error_msg:
                message = self._final_error_msg
            message = htmlBold(message)
        else:
            message = Html(phase)

        if self.mainwindow.debug \
        or phase not in (APPLYING, APPLYING_DONE):
            prefix = formatTimestamp(timestamp, True)
            html = message + BR
            self.mainwindow.addHTMLToInfoArea(html, hexacolor, prefix)
        return has_more

    def _process_component_list(self, timestamp, message_type, component_list):
        displayed_list = map(self.component_label, component_list)
        displayed_list = u', '.join(displayed_list)
        if message_type == APPLIED_COMPONENT_LIST:
            format = tr("Applying the new configuration of components: %s")
            self._applied_component_list = component_list
        elif message_type == ROLLED_BACK_COMPONENT_LIST:
            format = tr("Restoring the previous configuration of components: %s")
            self._rolled_back_component_list = component_list
        else:
            return
        html = Html(format % displayed_list, escape=False)
        self.logWithTimestamp(timestamp, html)

    def _start_err(self, err):
        """
        called when we could not start the poll dance
        """
        if not(isinstance(err, RpcdError) and err.type == "CoreError"):
            self.__handle_errors(err)
            self.__end_all()
            return

        # old ufwi_conf backend version: falling back to old protocol
        async = self.client.async()
        async.call(
            'config', 'apply',
            callback=self._apply_ok,
            errback=self._apply_err
            )

    def __ask_if_force(self, title, message):
        ok = QMessageBox.question(
            self.mainwindow,
            title,
            message,
            QMessageBox.Ok | QMessageBox.Cancel
            )
        if ok == QMessageBox.Ok:
            self.__force_start()
            return

        self.addToInfoArea(tr("Apply operation cancelled."))
        self.__end_all()

    def _start_ok(self, value):
        """
        the poll dance protocol is implemented on the server, go on!
        """

        if value == "trigger reboot? then use force=True":
            self.__ask_if_force(
                tr("Trigger a reboot?"),
                tr(
                    "Applying now (after a restoration) will trigger a reboot of the appliance. "
                    "You can cancel now or proceed."
                  )
                )
            #Anyway, return (also with cancel)
            return
        elif "then use force=True" in value:
            self.__ask_if_force(
                RESTORATION_WARNING_TITLE,
                RESTORATION_WARNING
                )
            #Anyway, return (also with cancel)
            return


        if value == "reboot":
            self.addToInfoArea(
                tr("This will trigger a reboot of the appliance (after restoration)"),
                category=COLOR_CRITICAL
            )

            QMessageBox.information(
                self.mainwindow,
                tr("EdenWall reboot scheduled"),
                tr("First application after restoration: EdenWall will reboot afterwards.")
            )

        #reset the last read index
        self.reset()
        self._poll()

    # FIXME: why is this callback never called?
    def _apply_ok(self, arg):
        """
        End of the apply process.
        """
        self.addToInfoArea(tr("Application successful"), category=COLOR_FANCY)
        self.__end_all()

    def _apply_err(self, err):
        """
        End of the apply process.
        """
        self.addToInfoArea(tr("Application failed"), category=COLOR_WARNING)
        self.__end_all()
        self.__handle_errors(err)

    def _poll(self):
        async = self.client.async()
        async.call(
            'config', 'applyLog', self._last_read_index,
            callback=self._poll_ok,
            errback=self._poll_err
            )

    def _poll_ok(self, logs):
        has_more = self.__process_logs(logs)
        if has_more:
            #loop
            QTimer.singleShot(self._interval, self._poll)
        else:
            self.__end_all()

    def _poll_err(self, err):
        """
        A problem in the apply log dance.

        After that, we'll rely on a future feature: the getState
        dance, to know more about the server
        """
        self.__end_all()
        self.__handle_errors(err)

    def start_polling(
            self,
            final_success_message='',
            final_error_message='',
            rollback_error_message='',
            ):
        self.reset()
        self._final_success_msg = final_success_message
        self._final_error_message = final_error_message
        self._rollback_error_msg = rollback_error_message
        self._poll()

