#coding: utf-8
# $Id$
from datetime import timedelta

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QDialog, QTableWidgetItem, QCheckBox

from ufwi_rpcd.common import tr

from ufwi_rpcd.common.transport import parseDatetime
from ufwi_rpcd.common.human import fuzzyDatetime, fuzzyTimedelta
from ufwi_rpcc_qt.application_name import APPLICATION_NAME

from .session_dialog_ui import Ui_Dialog

class SessionDialog(QDialog):
    def __init__(self, client, rights_locked, label, err_handler, parent):
        """
        rights_locked : iterable, rights which are locked
        err_handler : exeption are passed to err_handler
        """
        QDialog.__init__(self, parent)
        self.window = parent

        self.client = client
        self.directory = u""
        self.error = err_handler
        self.rights_locked = rights_locked

        self.ui = Ui_Dialog()
        self.ui.setupUi(self)
        self.ui.label.setText(label)
        self.setupDialog()

    def setupDialog(self):
        self.checkboxes = None
        self.sessions = None
        self.connect(self.ui.destroy_button, SIGNAL("clicked()"), self.destroySessions)

    def readOnlyMode(self):
        try:
            self.client.call('session', 'dropRoles', self.rights_locked)
        except Exception, err:
            self.error(err)

    def fill(self):
        sessions = self.client.call('session', 'list')
        cookie = self.client.getCookie()
        self.checkboxes = []
        self.sessions = [session for session in sessions
            if ('cookie' not in session) or (session['cookie'] != cookie)]
        if not sessions:
            return False
        self.sessions.sort(key=lambda session: session['idle'])

        table = self.ui.session_table
        table.setRowCount(len(self.sessions))
        for row, session in enumerate(self.sessions):
            user = session['user']
            creation = fuzzyDatetime(parseDatetime(session['creation']))
            idle = timedelta(seconds=session['idle'])
            idle = fuzzyTimedelta(idle)
            if 'login' in user:
                login = user['login']
            else:
                login = u"<%s>" % tr("anonymous")
            application = user['client_name']
            application = APPLICATION_NAME.get(application, application)
            if 'client_release' in user:
                application += ' (%s)' % (user['client_release'],)
            columns = (
                login,
                user['host'],
                application,
                creation,
                idle)
            checkbox = QCheckBox(self)
            if 'cookie' not in session:
                checkbox.setEnabled(False)
            self.connect(checkbox, SIGNAL("toggled(bool)"), self.toggleSession)
            table.setCellWidget(row, 0, checkbox)
            self.checkboxes.append(checkbox)
            for column, text in enumerate(columns):
                table.setItem(row, 1 + column, QTableWidgetItem(text))
        table.resizeColumnsToContents()
        self.ui.destroy_button.setEnabled(False)

    def toggleSession(self, checked):
        enabled = checked or any(checkbox.isChecked() for checkbox in self.checkboxes)
        self.ui.destroy_button.setEnabled(enabled)

    def destroySessions(self):
        for index, checkbox in enumerate(self.checkboxes):
            if not checkbox.isChecked():
                continue
            session = self.sessions[index]
            try:
                self.client.call(
                    'session', 'destroySession', session['cookie'])
            except Exception, err:
                self.error(err)
                return False
        self.accept()
        return True

    def execLoop(self):
        """
        return False: role have been dropped
               True: a session have been killed
        """
        eas_window = self.window.eas_window
        if eas_window:
            text = eas_window.getLoadingSplashScreenText()
            show = eas_window.hideLoadingSplashScreen()
        else:
            show = None
        try:
            self.fill()
            ret = self.exec_()
            if ret == QDialog.Rejected:
                self.readOnlyMode()
                return False
            return True
        finally:
            if show:
                eas_window.showLoadingSplashScreen(text)

