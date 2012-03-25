"""
$Id$


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


import sys
import atexit

from PyQt4.QtCore import Qt, SIGNAL
from PyQt4.QtGui import QMainWindow, QMessageBox

from ufwi_rpcd.common.multisite import NO_MULTISITE
from ufwi_rpcd.common.error import writeError

from ufwi_rpcd.common import tr

from ufwi_rpcc_qt.error import formatException
from ufwi_rpcc_qt.keepalive import KeepAlive
from ufwi_rpcc_qt.html import Html, stripHTMLTags

"""
Three stand-lone mode:
EMBEDDED: The application is not stand-alone, but embedded in an EAS tab
FLOATING: The application is not stand-alone, but started in EAS in a separate window
STANDALONE: The application is stand-alone (started outside of EAS)
"""
EMBEDDED = "EMBEDDED"
STANDALONE = "STANDALONE"
FLOATING = "FLOATING"

class CentralWindow(QMainWindow):
    ROLES = set()
    EAS_MESSAGES = {}
    ICON = None

    def __init__(self, client, parent, eas_window):
        QMainWindow.__init__(self, parent)
        self.setAttribute(Qt.WA_DeleteOnClose)
        self.client = client
        self._server_up = True
        self._at_exit = False
        self._standalone = STANDALONE
        self.old_excepthook = None
        self.keep_alive = None
        self.eas_window = eas_window
        self.debug = False
        self.multisite_type = NO_MULTISITE
        self.status_bar = self.statusBar()
        self._session = None # don't use directly _session instead call
                             # self.getSession() (_session is only used for
                             # standalone application or eas window)
        atexit.register(self.atExit)
        self._at_exit = True

    def load(self):
        # Called by EAS at the first time that the application is opened
        pass

    def isReadOnly(self):
        """
        return False if user is not allowes to do modifications
        """
        raise NotImplementedError()

    def getSession(self):
        """
        return current session
        """
        if self._standalone == STANDALONE:
            if self._session is None:
                raise ValueError('Call setupCentralWindow first')
            return self._session
        else:
            return self.eas_window.getSession()

    def setSession(self, session):
        if self._standalone == STANDALONE:
            self._session = session
        else:
            self.eas_window.setSession(session)
        self.sessionModified()

    def sessionModified(self):
        """
        called when the session have been modified
        """
        pass

    def getRoles(self):
        """
        return a frozenset which contains roles of current session
        """
        session = self.getSession()
        return frozenset(session['user']['roles'])

    def getGroups(self):
        session = self.getSession()
        return session['user']['groups']

    def EAS_MessageHandler(self, from_app, command, *args, **kwargs):
        """
        Handle a message received from an other application.
        """
        try:
            function = self.EAS_MESSAGES[command]
        except KeyError:
            raise NotImplementedError()
        else:
            function(from_app, *args, **kwargs)

    def EAS_SendMessage(self, dest_app, command, *args, **kwargs):
        """
        Send a message to an other application.
        """
        self.emit(SIGNAL('EAS_Message'), dest_app, command, *args, **kwargs)

    def messageBox(self, icon, title, message, escape=True):

        # FIXME : no popup is shown when this exception is raised
        if isinstance(message, Html):
            escape = False

        message = unicode(message)
        if not self.debug and u"underlying C/C++ object has been deleted" in message:
           return

        box = QMessageBox(icon, title, message)
        if escape:
            box.setTextFormat(Qt.PlainText)
        else:
            box.setTextFormat(Qt.RichText)

        return box.exec_()



    def writeError(self, err, title="ERROR", **kw):
        """
        Write the error 'err' using the logging module (eg. stdout).
        Prefix the error message by title + ": ".

        Write also the backtrace with a lower log level (WARNING).
        """
        writeError(err, title, **kw)

    def exceptionHook(self, errtype, value, traceback):
        html = formatException(value, self.debug, traceback, errtype)
        self.error(html, escape=False, dialog=True)

    def exception(self, err, title=None, dialog=None):
        html = formatException(err, self.debug)
        self.error(html, title, escape=False, dialog=dialog)
    # FIXME: Mark ufwi_rpcdError() as deprecated and replace it by exception()
    ufwi_rpcdError = exception

    def stdoutMessage(self, title, message):
        if not self.debug:
            return
        print title
        print "=" * len(title)
        print
        print message
        print

    def information(self, message, title=None):
        if not title:
            title = u"Configuration server information"
        self.stdoutMessage(title, message)
        self.messageBox(QMessageBox.Information, title, message)

    def error(self, message, title=None, dialog=None, escape=True):
        if not title:
            title = u"Configuration server error"
        if escape:
            plaintext = message
        else:
            plaintext = stripHTMLTags(message)
        self.stdoutMessage(title, plaintext)
        if dialog is None:
            dialog = True
        if dialog:
            self.messageBox(QMessageBox.Warning, title, message, escape=escape)

    def setupCentralWindow(self, application, standalone):
        self._standalone = standalone
        options = application.options
        self.debug = options.debug
        if standalone == STANDALONE:
            self.multisite_type = self.client.call('CORE', 'getMultisiteType')
            self.old_excepthook = sys.excepthook
            sys.excepthook = self.exceptionHook
            self.status_bar = self.statusBar()
            self.keep_alive = KeepAlive(self)
            self._session = self.client.call('session', 'get')
        else:
            self.multisite_type = self.eas_window.multisite_type
            self.status_bar = self.eas_window.statusBar()
            self.keep_alive = self.eas_window.keep_alive

    def setCentralWindowTitle(self, app_name, client, title=None):
        text = []

        if title:
            text.append(title)

        if self._standalone == STANDALONE:
            text.append(u"%s@%s" % (client.login, client.host))

        if self.isReadOnly():
            app_name += ' [%s]' % tr('Read-Only')

        text.append(app_name)
        text = u' - '.join(text)
        if self._standalone == STANDALONE:
            window = self
            QMainWindow.setWindowTitle(window, text)
        else:
            eas = self.eas_window
            eas.app_title[self] = text
            eas.setTitle(self)

    def setStatus(self, text, timeout=5):
        self.status_bar.showMessage(text, timeout*1000)

    def atExit(self):
        if not self._at_exit:
            return
        self._at_exit = False
        self.quit()

    def quit(self):
        self._at_exit = False
        if self.keep_alive:
            self.keep_alive.stop()
            self.keep_alive = None
        if self._standalone == STANDALONE:
            self.client.logout()
        if self.old_excepthook:
            sys.excepthook = self.old_excepthook
            self.old_excepthook = None

    def closeEvent(self, event):
        event.accept()
        self.quit()

    def setCentralModified(self, modified=None, message=None):
        if self._standalone != STANDALONE:
            self.eas_window.setCentralModified(modified, message)
        else:
            self.setWindowModified(modified)

