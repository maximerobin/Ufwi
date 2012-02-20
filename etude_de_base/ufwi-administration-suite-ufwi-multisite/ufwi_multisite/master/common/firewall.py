
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

from sys import maxint

class MultiSiteFirewall:
    ATTR = []

    ONLINE = 'online'
    REGISTERING = 'registering'
    ERROR = 'error'
    OFFLINE = 'offline'

    TASK_CLS = None

    def __init__(self, component, core, module_name, name, attributes):
        self.name = name
        self.core = core
        self.module_name = module_name
        self.component = component
        self.status = u''
        self.tasks = {}
        self.last_id = 0

        for attr in self.ATTR:
            if attr in attributes:
                setattr(self, attr, attributes[attr])

    def save(self):
        d = dict()
        for attr in self.ATTR:
            val = getattr(self, attr)
            if isinstance(val, dict):
                for attr2, val2 in val.iteritems():
                    if isinstance(val2, dict):
                        for attr3, val3 in val2.iteritems():
                            self.component.config.set('firewalls', self.name, attr, attr2, attr3, val3) # Beurk
                    else:
                        self.component.config.set('firewalls', self.name, attr, attr2, val2) # Beurk
            else:
                self.component.config.set('firewalls', self.name, attr, val)

        self.component.config.save(self.component.config_path)

    def debug(self, *args, **kw):
        self.component.debug(*args, **kw)

    def info(self, *args, **kw):
        self.component.info(*args, **kw)

    def warning(self, *args, **kw):
        self.component.warning(*args, **kw)

    def error(self, *args, **kw):
        self.component.error(*args, **kw)

    def erase_config(self):
        try:
            self.component.config.delete('firewalls', self.name)
        except:
            pass
        self.component.config.save(self.component.config_path)

    def newID(self):
        id = self.last_id

        while str(id) in self.tasks.keys():
            id += 1

            if id == maxint:
                id = 0

        self.last_id = id
        return str(id)

    def getTasks(self):
        return self.tasks

    def setTask(self, task, id = -1):
        if id == -1:
            id = self.newID()
        #if self.task:
        #    self.task.cancelTask()
        self.tasks[id] = task
        task.setID(id)

    def cancelTask(self, id):
        self.tasks[id].cancelTask()
        self.tasks.pop(id)

    def unregister(self):
        self.erase_config()
        while len(self.tasks) != 0:
            task_id = self.tasks.keys()[0]
            self.cancelTask(task_id)

