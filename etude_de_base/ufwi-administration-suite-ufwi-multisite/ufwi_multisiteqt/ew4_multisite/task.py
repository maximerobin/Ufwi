
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

from ufwi_rpcd.common import tr
from .edw_data import EdwData
from .cell_data import AttributeCell, AttributeBool, AttributeImg, AttributeDate, AttributeTime
from .cell_edw import AttributeCheckBox

TASK_TYPES =  {
    "multisite_nuface" : tr('Rules application'),
    "multisite_update" : tr('Update'),
    }

TASK_ICONS =  {
    "multisite_nuface" : ":/icons-20/apply_rules.png",
    "multisite_update" : ":/icons-20/upload.png",
    }

TASK_ROLES = {
    "multisite_nuface" : (["ruleset_read"], ["ruleset_write"],),
    "multisite_update" : (["conf_read"], ["conf_write"],)
}

class Task(EdwData):
    def __init__(self, window, name, client, schedule):
        EdwData.__init__(self, window, client, name)
        self.cell_classes = {
            'firewall_name' :                 AttributeCell(self, [], 'host'),
            'schedule_start' :                AttributeDate(self, 'getReadRoles', 'start'),
            'schedule_rate' :                 AttributeTime(self, 'getReadRoles', 'rate'),
            'schedule_stop_on_success' :      AttributeBool(self, 'getReadRoles', 'stop_on_success_foo', 'stop_on_success'),
            'task_type' :                     AttributeImg(self, 'getReadRoles', 'type', 'type_icon'),
            'task_status' :                   AttributeCell(self, 'getReadRoles', 'status'),
            'task_description' :              AttributeCell(self, 'getReadRoles', 'description'),
            'task_modify' :                   AttributeCheckBox(self, 'getWriteRoles', 'modify'),
        }
        self.update(schedule)

    def update(self, schedule):
        self.schedule = schedule
        self.start = schedule['start_date']
        self.rate = schedule['retry_time']
        self.stop_on_success = schedule['stop_on_success']
        self.stop_on_success_foo = ''
        self.service = schedule['service']
        self.type = TASK_TYPES[schedule['service']]
        self.type_icon = TASK_ICONS[schedule['service']]
        self.status = schedule['status']
        self.host = schedule['host']
        self.description = schedule['description']
        self.task_id = schedule['id']
        self.modify = False

    def isHeader(self):
        return False

    def getEdwName(self):
        return self.schedule['host']

    def deleteTask(self):
        if not self.modify:
            return
        self.client.call(self.service, "deleteTask", self.host, self.task_id)

    def rescheduleTask(self, new_schedule):
        if not self.modify:
            return
        self.client.call(self.service, "rescheduleTask", self.host, self.task_id, new_schedule)

    def getReadRoles(self):
        return TASK_ROLES[self.service][0]

    def getWriteRoles(self):
        return TASK_ROLES[self.service][1]

