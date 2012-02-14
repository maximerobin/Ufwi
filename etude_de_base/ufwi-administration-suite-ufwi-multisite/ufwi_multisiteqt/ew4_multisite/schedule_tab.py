
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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox
from ufwi_rpcd.common import tr
from .groups_list import GroupsList
from .task_list import TaskList
from .start_task import StartTask
from .task import Task, TASK_TYPES
from .strings import APP_TITLE
from .multisite_tab import MultisiteTab

class ScheduleTab(GroupsList, MultisiteTab):
    HEADERS_ID = [ 'firewall_name', 'task_type', 'schedule_start', 'schedule_rate', 'schedule_stop_on_success', 'task_description', 'task_status', 'task_modify' ]
    FILTER_BY = [ 'firewall_name', 'task_type', 'task_description', 'task_status' ]
    GROUPS_BY_ID = [ 'firewall_name', 'task_type', 'task_description' ]

    def __init__(self, client, scroll_area, main_window, edw_list, categories, categories_order):
        self.task_list = []
        self.ui = main_window
        self.reschedule_tasks = StartTask(':/icons/chrono.png', 'Rechedule selected tasks', self.reschedule, self, 'modify')
        GroupsList.__init__(self, client, scroll_area, main_window, TaskList, self.task_list, categories, categories_order)
        self.connect(self.ui.ui.actionReschedule, SIGNAL("triggered()"), lambda: self.reschedule_tasks.start(True))
        self.connect(self.ui.ui.actionDelete_task, SIGNAL("triggered()"), self.delete)

        if self.ui.read_only:
            self.ui.ui.actionReschedule.setEnabled(False)
            self.ui.ui.actionDelete_task.setEnabled(False)

    def setTab(self):
        self.ui.ui.actionReschedule.setVisible(True)
        self.ui.ui.actionDelete_task.setVisible(True)

    def unsetTab(self):
        self.ui.ui.actionReschedule.setVisible(False)
        self.ui.ui.actionDelete_task.setVisible(False)

    def refreshCells(self):
        tasks = {}
        for service in TASK_TYPES.keys():
            new_tasks = self.client.call(service, "getTasks")
            for fw, task_list in new_tasks.iteritems():
                for task_id, task in task_list.iteritems():
                    task['service'] = service
                    task['host'] = fw
                    tasks[fw + '-' + service + '-' + task_id] = task

        # finished tasks
        for task in self.task_list:
            if task.getID() not in tasks.keys():
                self.task_list.remove(task)
                self.delObj(task)

        for task in tasks.keys():
            for task_obj in self.task_list:
                if task_obj.getID() == task:
                    task_obj.update(tasks[task])
                    break
            else:
                task_obj = Task(self.ui, task, self.client, tasks[task])
                self.task_list.append(task_obj)
                self.newObj(task_obj)

    def reschedule(self, schedule):
        for task in self.task_list:
            task.rescheduleTask(schedule)

    def delete(self):
        count = 0
        for task in self.getAllObjects():
            if task.modify:
                count += 1

        if count == 0:
            QMessageBox.critical(None, APP_TITLE, tr("You must select at least one task"), QMessageBox.Ok)
            return

        if QMessageBox.warning(None, APP_TITLE, tr("You are about to delete the %i task. Are you sure you want to do this?") % count, QMessageBox.Yes | QMessageBox.No) == QMessageBox.No:
            return

        for task in self.task_list:
            task.deleteTask()

