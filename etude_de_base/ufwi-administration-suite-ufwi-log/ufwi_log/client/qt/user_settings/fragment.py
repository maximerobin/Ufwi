# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

from ufwi_log.client.qt.user_settings.stored import StoredObject
from ufwi_rpcd.common import tr

class Fragment(StoredObject):
    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.type = ''
        self.title = ''
        self.args = {}
        self.view = ''
        self.firewall = ''
        self.background_color = 0xffffff # the white color

    def __repr__(self):
        return "<Fragment '%s'>" % self.name

    def load(self, items):
        self.type =  items.get('type', '')
        self.title = items.get('title', '')
        self.view =  items.get('view', '')
        self.background_color = int(items.get('background_color', 0xffffff))
        self.firewall = items.get('firewall', '')
        self.args = items.get('args', {})

    def properties(self):
        return {'title':            self.title,
                'type':             self.type,
                'view':             self.view,
                'background_color': self.background_color & 0x00ffffff,
                'firewall':         self.firewall,
                'args':             self.args,
               }

class FragmentsList(StoredObject):
    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.frags = {}

    def __repr__(self):
        return '<FragmentsList>'

    def isDefault(self): return False
    def setDefault(self, b):
        for frag in self.frags.itervalues():
            frag.setDefault(b)

    def load(self, items):
        for key, value in items.iteritems():
            self.frags[key] = Fragment(key)
            self.frags[key].load(value)

    def properties(self):
        d = dict()
        for key, frag in self.frags.iteritems():
            if not frag.isDefault():
                d[key] = frag.properties()

        return d

    def __contains__(self, key):
        return (key in self.frags)

    def __getitem__(self, key):
        return self.frags[key]

    def __setitem__(self, key, value):
        self.frags[key] = value

    def __delitem__(self, key):
        if key not in self.frags:
            return
        del self.frags[key]
