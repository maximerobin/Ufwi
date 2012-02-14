#coding: utf-8
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


from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common import tr
from ufwi_rpcd.common.radius_client import RadiusConf
from ufwi_rpcd.common.radius_client import RadiusServer
from ufwi_rpcc_qt.central_dialog import IP_OR_HOSTNAME_OR_FQDN_REGEXP
from ufwi_rpcc_qt.radius_test_ui import Ui_radius_test
from ufwi_rpcc_qt.radius_ui import Ui_Radius
from ufwi_rpcc_qt.validate_widgets import ValidateWidgets
from ufwi_rpcc_qt.validation import INT32_MAX


def __signal_definitions(frame, target):
    return (
        (frame.port, SIGNAL("textEdited(QString)"), target.setPort),
        (frame.shared_secret, SIGNAL("textEdited(QString)"), target.setSecret),
        (frame.timeout, SIGNAL("textEdited(QString)"), target.setTimeout),
        (frame.server, SIGNAL("textEdited(QString)"), target.setServer),
        (frame.test_radius, SIGNAL('clicked(bool)'), frame.test_dialog)
       )

def _connectsignals(frame, target):
    for source, signal, callback in __signal_definitions(frame, target):
        frame.connect(source, signal, callback)

def _disconnectsignals(frame, target):
    for source, signal, callback in __signal_definitions(frame, target):
        frame.disconnect(source, signal, callback)

class RadiusFrame(QFrame, Ui_Radius, ValidateWidgets):
    def __init__(self, client, parent=None, radiusserverconf=None):
        QFrame.__init__(self, parent)

        self.__client = client
        self._target = None
        self._radiusserverconf = None

        ValidateWidgets.__init__(self)
        self.setupUi(self)
        self.lineedits = self.server, self.port, self.shared_secret, self.timeout

        self.__setupvalidators()

        if radiusserverconf is None:
            radiusserverconf = RadiusConf.defaultServer()
        self.setRadiusserverconf(radiusserverconf)

    def setRadiusserverconf(self, radiusserverconf):
        self._radiusserverconf = radiusserverconf

        self.port.setText(
            unicode(self._radiusserverconf.port)
            )

        self.shared_secret.setText(
            self._radiusserverconf.secret
            )

        self.timeout.setText(
            unicode(self._radiusserverconf.timeout)
            )

        self.server.setText(self._radiusserverconf.server)
        self.__setupsignals()

    def getRadiusserverconf(self):
        return self._radiusserverconf

    def __setupvalidators(self):
        self.setRegExpValidator(self.server, IP_OR_HOSTNAME_OR_FQDN_REGEXP)
        self.setIntValidator(self.port, 1, 65535)
        self.setNonEmptyValidator(self.shared_secret)
        self.setIntValidator(self.timeout, 1, INT32_MAX)

    def __setupsignals(self):
        if self._target is self._radiusserverconf:
            return
        if self._target is not None:
            _disconnectsignals(self, self._target)
        self._target = self._radiusserverconf
        _connectsignals(self, self._target)

    def __filldialog(self, dialog):
        dialog.port.setText(self.port.text())
        dialog.shared_secret.setText(self.shared_secret.text())
        dialog.timeout.setText(self.timeout.text())
        dialog.server.setText(self.server.text())

    def cancel_test_report(self):
        self.testui.report_cancelled = True

    def test_dialog(self):
        dialog = QDialog()
        self.testui = Ui_radius_test()
        self.testui.setupUi(dialog)
        self.testui.results_box.hide()
        self.__filldialog(self.testui)
        self.connect(
            self.testui.testbutton,
            SIGNAL('pressed()'),
            self.sendtest
            )

        self.testui.report_cancelled = False

        self.connect(
            self.testui.closebutton,
            SIGNAL('pressed()'),
            self.cancel_test_report
            )

        dialog.exec_()

    def __dialogvalues(self):
        conf = RadiusServer(
            server=unicode(self.testui.server.text()),
            port=unicode(self.testui.port.text()),
            timeout=unicode(self.testui.timeout.text()),
            secret=unicode(self.testui.shared_secret.text())
        )

        ok, msg = conf.isValidWithMsg()
        if not ok:
            QMessageBox.warning(
                self,
                tr("Input error"),
                msg
                )
            return

        username = unicode(self.testui.username.text())
        password = unicode(self.testui.password.text())

        return conf, username, password

    def sendtest(self):
        #can make another call if not in nuconf?
        #Currently, the service is exposed by nuconf/nuauth,
        #but it may be moved
        self.testui.testbutton.setEnabled(False)
        self.testui.testbutton.setText(tr("Ongoing test, please wait"))
        serverconf, user, password = self.__dialogvalues()
        async = self.__client.async()
        async.call('nuauth', 'testRADIUS',
            serverconf.serialize(),
            user,
            password,
            callback=self._test_ok,
            errback=self._test_err
            )

    def _test_ok(self, result):
        if self.testui.report_cancelled:
            return
        self.testui.results_box.show()

        ok, msg = result
        if ok:
            css = 'background-color: #a2ca5d;'
            prefix = 'Success'
        else:
            css = 'background-color: #e6a9ab;'
            prefix = 'Error'

        for line in (self.testui.username, self.testui.password):
            line.setStyleSheet(css)

        self.testui.results_text.append(
            '[%s] %s' % (prefix, msg)
            )
        self.testui.testbutton.setEnabled(True)
        self.testui.testbutton.setText(tr("Test"))

    def _test_err(self, result):
        if self.testui.report_cancelled:
            return
        if isinstance(result, RpcdError):
            err_message = result.unicode_message
        else:
            #unexpected
            err_message = "a diagnostic file analysis may be needed."
        QMessageBox.warning(
            self,
            tr("An error occured"),
            tr("Could not perform radius test:") + err_message
            )
        self.testui.testbutton.setEnabled(True)

    def __resetdisplay(self):
        for line in (self.testui.username, self.testui.password):
            line.setStyleSheet('')

