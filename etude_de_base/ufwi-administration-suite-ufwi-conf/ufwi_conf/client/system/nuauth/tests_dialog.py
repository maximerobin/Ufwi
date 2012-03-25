# -*- coding: utf-8 -*-
# $Id: $

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

from PyQt4.QtCore import SIGNAL, QObject, QEvent
from PyQt4.QtGui import QDialog, QLineEdit, QMessageBox
from datetime import datetime
from functools import wraps
import re

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcc_qt.colors import COLOR_ERROR, COLOR_SUCCESS
from ufwi_rpcc_qt.html import htmlColor

from .tests_dialog_ui import Ui_UserdirectoryTest

def dotest(function):
    @wraps(function)
    def wrapper(self, *args, **kwargs):
        self.lock(lock=True)
        async = self.client.async()
        return function(self, async, *args, **kwargs)
    return wrapper

_USER_REGEX = re.compile(".*#1308006: ")
_GROUP_REGEX = re.compile(".*#1308007: ")
_AUTH_REGEX = re.compile(".*#1308008: ")
def handleerror(error):
    message = exceptionAsUnicode(error)
    if error.type == "CoreError":
        return tr("This service is not available on your server. "
            "You may want to upgrade the server"
                )
    if error.type == "NoSuchUser":
        return tr("No account named '%(USERNAME)s' was found") % {
            "USERNAME":re.sub(_USER_REGEX, '', message, )
            }
    if error.type == "NoSuchGroup":
        return tr("No group named '%(GROUPNAME)s' was found.") % {
            "GROUPNAME": re.sub(_GROUP_REGEX, '', message)
            }
    if error.type == "AuthError":
        return tr("Could not authenticate '%(USERNAME)s' with the supplied credentials.") % {
            "USERNAME": re.sub(_AUTH_REGEX, '', message)
            }
    return "[%s] %s" % (error.type, message)

def parseresult(result):
    if len(result) != 3:
        return tr("Success. Is your server software too recent for this EAS?") + "\n%s" % unicode(result)
    version, message_type, message = result[0], result[1], result[2]
    if version > 1:
        return tr("Success. Is your server software too recent for this EAS?") + "\n%s" % unicode(result[1:])
    if message_type == "username":
        return tr("Success. A user account for '%(USERNAME)s' was found.") % {"USERNAME": message}
    if message_type == "groupname":
        return tr("Success. A group named '%(GROUPNAME)s' was found.") % {"GROUPNAME": message}
    if message_type == "auth":
        return tr("Success. EdenWall could authenticate '%(USERNAME)s' with the supplied credentials.") % {"USERNAME": message}

TIMESTAMP_COLOR = "grey"

def result(function):
    """
    decorator for feedback functions
    """
    result_nok = function.__name__.endswith("_nok")
    result_ok = function.__name__.endswith("_ok")
    assert result_nok or result_ok, \
        "Only decorating functions with name ending with "\
        "'_ok' or '_nok', not %s" % function.__name__
    @wraps(function)
    def wrapper(self, result, *args, **kwargs):
        self.lock(lock=False)
        if result_nok:
            result = htmlColor(handleerror(result), COLOR_ERROR)
        else:
            result = htmlColor(parseresult(result), COLOR_SUCCESS)

        timestamp = htmlColor("[%s]" % unicode(datetime.now()), TIMESTAMP_COLOR)
        result = "%s %s" % (timestamp, result)
        return function(self, result, *args, **kwargs)
    return wrapper

def _readfield(field):
     return unicode(field.text())



class KeyPressEater(QObject):
    def eventFilter(self, obj, event):
        if event.type() == QEvent.MouseButtonPress:
            if not obj.isModified():
                obj.setModified(True)
                obj.setText("")
            return True
        else:
            return False




class DirectoryTest(QDialog, Ui_UserdirectoryTest):
    def __init__(self, client, parent=None):
        QDialog.__init__(self, parent)
        Ui_UserdirectoryTest.setupUi(self, self)

        self.client = client
        self._testbuttons = (
            self.testuser,
            self.testgroup,
            self.testauth
            )

        self._connect_signals()
        self.lock(lock=False)

        keyfilter = KeyPressEater(self)
        self.login.installEventFilter(keyfilter)
        self.password.installEventFilter(keyfilter)
        self.user.installEventFilter(keyfilter)
        self.group.installEventFilter(keyfilter)

    def lock(self, lock=True):
        for button in self._testbuttons:
            button.setEnabled(not lock)
        self.ongoing.setVisible(lock)

    def _connect_signals(self):
        self.connect(self.testuser, SIGNAL('clicked()'), self.test_user)
        self.connect(self.testgroup, SIGNAL('clicked()'), self.test_group)
        self.connect(self.testauth, SIGNAL('clicked()'), self.test_auth)
        self.connect(self.password_visible, SIGNAL('toggled(bool)'), self._password_echomode)

    def _password_echomode(self, visible):
        if visible:
            self.password.setEchoMode(QLineEdit.Normal)
        else:
            self.password.setEchoMode(QLineEdit.Password)

    @result
    def _test_ok(self, result):
        self.logs.append(result)

    @result
    def _test_nok(self, result):
        self.logs.append(result)

    @dotest
    def test_user(self, async):
        if not self.user.isModified():
            title = tr("User")
            self.warning(title)
            return

        user = _readfield(self.user)
        async.call(
            "nuauth",
            "test_user",
            user,
            callback=self._test_ok,
            errback=self._test_nok
            )

    @dotest
    def test_group(self, async):
        if not self.group.isModified():
            title = tr("Group")
            self.warning(title)
            return

        group = _readfield(self.group)
        async.call(
            "nuauth",
            "test_group",
            group,
            callback=self._test_ok,
            errback=self._test_nok
            )

    @dotest
    def test_auth(self, async):
        if not self.login.isModified() or not self.password.isModified():
            title = tr("Login/password")
            self.warning(title)
            return

        login = _readfield(self.login)
        password = _readfield(self.password)
        async.call(
            "nuauth",
            "test_auth",
            login,
            password,
            callback=self._test_ok,
            errback=self._test_nok
            )

    def warning(self, title):
        title = title
        message = tr("Enter a valid value for %s") % str(title.lower())
        self.lock(lock=False)
        return QMessageBox.warning(self, title, message)

