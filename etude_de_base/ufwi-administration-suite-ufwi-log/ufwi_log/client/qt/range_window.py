# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Eric Leblond <eleblond@edenwall.com>

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

$Id: addfrag_window.py 11659 2009-09-04 15:00:31Z carrere $
"""

from PyQt4.QtGui import QDialog
from PyQt4.QtGui import QMessageBox
from PyQt4.QtCore import QDateTime
from ui.range_ui import Ui_ChooseRange

from ufwi_log.client.qt.args import CheckError, Interval

class ChooseRangeDialog(QDialog):
    def __init__(self, window, parent=None):
        """
            @param window [NulogMainWindow] the window where we edit fragment
            @param fragment [Fragment] the edited fragment
        """

        QDialog.__init__(self, parent)
        self.ui = Ui_ChooseRange()
        self.ui.setupUi(self)

        self.window = window
        self.parent = parent

        self.ui.starttime.setDateTime(parent.interval.getStartClient())
        self.ui.endtime.setDateTime(parent.interval.getEndClient())

    def run(self):
        while 1:
            if not self.exec_():
                return False

            try:
                if self.ui.starttime.dateTime() >= self.ui.endtime.dateTime():
                        QMessageBox.critical(self, self.tr('Range error'),
                                            self.tr('Start time is superior to end time'),
                                            QMessageBox.Ok)
                if self.parent != None:
                    start = QDateTime.fromTime_t( \
                                        self.ui.starttime.dateTime().toTime_t() - self.parent.interval.delta() \
                                                )
                    end = QDateTime.fromTime_t( \
                                        self.ui.endtime.dateTime().toTime_t() - self.parent.interval.delta() \
                                                )
                    self.parent.interval = Interval('custom', start, end)

                    self.parent.interval.setLastStartTime(self.ui.starttime.dateTime().toTime_t())
                    self.parent.interval.setLastEndClient(self.ui.endtime.dateTime().toTime_t())
                return True

            except CheckError, e:
                QMessageBox.critical(self, self.tr("Invalid argument"),
                                           unicode(e), QMessageBox.Ok)

