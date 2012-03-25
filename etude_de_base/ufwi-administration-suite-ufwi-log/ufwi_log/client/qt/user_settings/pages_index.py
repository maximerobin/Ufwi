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

class Section(StoredObject):

    def __repr__(self):
        return "<Section '%s'>" % self.name

    def __init__(self, name, title=u''):
        StoredObject.__init__(self, name)
        self.pages = []
        self.pos = 0
        self.title = title

    def load(self, items):
        self.pos = int(items.get('pos', 0))
        self.title = items.get('title', u'')
        self.icon = items.get('icon', u'')
        self.pages = [(name, None) for name in items['pages'].split()]
        self.setDefault(False)

    def properties(self):
        return {'pos':     self.pos,
                'title':   self.title,
                'icon' :   self.icon,
                'pages':   ' '.join([name for name, value in self.pages])
               }

    def addPage(self, page):
        self.pages.append((page.name, page))
        self.setDefault(False)

    def removePage(self, pagename):
        for name, page in self.pages:
            if name == pagename:
                self.pages.remove((name, page))
                self.setDefault(False)

class PagesIndex(StoredObject):

    def isDefault(self): return False
    def setDefault(self, b):
        for section in self.sections:
            section.setDefault(b)

    def __repr__(self):
        return "<PagesIndex>"

    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.sections = []

    def load(self, items):
        for key, value in items.iteritems():
            section = self.addSection(key)
            section.load(value)

        self.sections.sort(lambda x,y: x.pos - y.pos)

    def properties(self):
        d = dict()
        for section in self.sections:
            if not section.isDefault():
                d[section.name] = section.properties()

        return d

    def addPage(self, page, section_name):
        section = self.addSection(section_name)
        section.pages.append((page.name, page))
        section.setDefault(False)
        return page

    def addSection(self, section_name):
        for section in self.sections:
            if section.name == section_name:
                return section

        section = Section(section_name)
        pos = 0
        if self.sections:
            pos = self.sections[-1].pos + 1
        self.sections.append(section)
        return section

    def removePage(self, pagename):
        for section in self.sections:
            section.removePage(pagename)

