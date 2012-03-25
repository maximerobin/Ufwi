
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

from PyQt4.QtGui import QDialog, QMessageBox
from PyQt4.QtCore import SIGNAL, QDate, QTime
from ufwi_rpcd.common import tr
from .ui.start_task_ui import Ui_Dialog
from .strings import APP_TITLE

class StartTask(QDialog):
    def __init__(self, icon, text, callback, obj_list, enabled_attr):
        QDialog.__init__(self)
        self.callback = callback
        self.window = Ui_Dialog()
        self.window.setupUi(self)
        self.window.task_label.setText(tr('<img src="%s" width=64 height=64 />%s' % (icon, text)))
        self.window.start_schedule_date.setCalendarPopup(True)
        self.connect(self.window.start_now_radio, SIGNAL("clicked()"), self.switchSchedule)
        self.connect(self.window.start_schedule, SIGNAL("clicked()"), self.switchSchedule)
        self.obj_list = obj_list
        self.enabled_attr = enabled_attr
        self.setWindowTitle(APP_TITLE)

    def start(self, allow_repeat):
        # Check at least one obj is selected:
        count = 0
        for obj in self.obj_list.getAllObjects():
            enabled = getattr(obj, self.enabled_attr)
            if enabled:
                count += 1

        if count == 0:
            QMessageBox.critical(None, APP_TITLE, tr("You must select at least one %s") % self.obj_list.obj_class.getObjectTypeName(), QMessageBox.Ok)
            return

        self.init(allow_repeat)
        if self.exec_():
            self.callback(self.getScheduleOptions())

    def init(self, allow_repeat):
        self.window.start_now_radio.setChecked(True)
        self.window.start_schedule.setChecked(False)
        self.window.retry_until_success.setChecked(True)
        self.window.retry_forever.setChecked(False)
        self.window.start_schedule_date.setDate(QDate.currentDate())
        self.window.retry_time.setTime(QTime(1, 0))
        self.window.retry_forever.setEnabled(allow_repeat)
        self.switchSchedule()

    def switchSchedule(self):
        enable_sched = not (self.window.start_now_radio.isChecked())
        self.window.start_schedule_date.setEnabled(enable_sched)

    def getScheduleOptions(self):
        sched = {
            'start_date' : 0,
            'retry_time' : 60,
            'stop_on_success' : True
        }

        if self.window.start_schedule.isChecked():
            sched['start_date'] = self.window.start_schedule_date.dateTime().toTime_t()
        sched['retry_time'] = - self.window.retry_time.time().secsTo(QTime(0,0))
        sched['stop_on_success'] = self.window.retry_until_success.isChecked()
        return sched
