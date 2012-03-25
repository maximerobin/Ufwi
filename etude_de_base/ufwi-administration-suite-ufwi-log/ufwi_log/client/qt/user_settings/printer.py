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

class PrinterSettings(StoredObject):

    def isDefault(self): return False
    def setDefault(self, b): pass

    def __repr__(self):
        return "<PrinterSettings>"

    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.enterprise = ''
        self.title = ''
        self.logo = ''
        self.content_table = False
        self.header = True
        self.footer = True

    def load(self, items):
        self.enterprise = items.get('enterprise', u'')
        self.title = items.get('title', u'')
        self.logo = items.get('logo', u'')
        self.content_table = items.get('content_table', True)
        self.header = items.get('header', False)
        self.footer = items.get('footer', False)

    def properties(self):
        return {'enterprise':    self.enterprise,
                'title':         self.title,
                'logo':          self.logo,
                'content_table': self.content_table,
                'header':        self.header,
                'footer':        self.footer
               }


