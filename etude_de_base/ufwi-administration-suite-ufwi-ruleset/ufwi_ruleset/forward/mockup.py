# Dummy classes used in unit tests

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


class Ruleset:
    def __init__(self, client):
        self.acls = tuple()
        self.client = client

    def addAction(self, action, apply=True):
        if apply:
            action.apply()
        updates = action.createApplyTuple()
        if self.client.mode == 'GUI':
            return updates
        else:
            return None

    def updateFusion(self, action=None, add_updates=False):
        pass

class Interface:
    def __init__(self, parent, attr):
        self.id = attr['id']
        self.name = attr['name']

