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


from __future__ import with_statement

import os
import time

from ufwi_rpcd.backend.variables_store import VariablesStore

class Secondary(object):
    (INIT,
     OFFLINE,
     ONLINE) = range(3)

    CONFIG_NAME = 'ha.xml'

    def __init__(self, core):
        self.last_seen = 0
        self.state = self.OFFLINE
        self.core = core
        self.error = ''
        self.vars = VariablesStore()

    def setPort(self, port):
        self.port = port

    def settings(self, interface):
        return {'interface':interface}

    def loadConfig(self):
        vars_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_NAME)
        self.vars.load(vars_path)
        self.last_seen = self.vars.get('last_seen')
        self.state = self.vars.get('state')

    def saveConfig(self):
        self.vars.set('last_seen', self.last_seen)
        self.vars.set('state', self.state)
        vars_path = os.path.join(self.core.config.get('CORE', 'vardir'), self.CONFIG_NAME)
        self.vars.save(vars_path)

    def setState(self, state):
        if self.state != state:
            self.state = state
            self.saveConfig()

    def updateLastSeen(self):
        self.last_seen = int(time.time())
        self.saveConfig()

