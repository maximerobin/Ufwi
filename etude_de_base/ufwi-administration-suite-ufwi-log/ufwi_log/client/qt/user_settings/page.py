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
from ufwi_log.client.qt.args import arg_types

class FragmentFrame(StoredObject):

    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.frags = []
        self.pos = 0

    def __repr__(self):
        return "<Frame n='%s'>" % self.pos

    def load(self, items):
        self.pos = int(items.get('pos', 0))
        self.frags = [(name, None) for name in items['frags'].split()]

    def properties(self):
        return {'pos':   self.pos,
                'frags': ' '.join([name for name, value in self.frags])
               }

class Page(StoredObject):
    """
        The Page class represents a window with some fragments in.
        This object is stored in the user settings
    """

    def __init__(self, name):
        StoredObject.__init__(self, name)

        self.title = name
        self.args = {}
        self.frames = []
        self.pagelinks = {}
        self.filters = []
        self.force_cumulative = False
        self.search_page = False

    def __repr__(self):
        return "<Page '%s'>" % self.name

    def load(self, items):
        for key, value in items.get('frames', {}).iteritems():
            frame = FragmentFrame(key)
            frame.load(value)
            self.frames.append(frame)

        self.frames.sort(lambda x,y: x.pos - y.pos)
        self.title = items.get('title', self.name)
        self.args = items.get('args', {})
        self.pagelinks = items.get('links', {})
        self.filters = items.get('filters', '').split()
        self.force_cumulative = items.get('force_cumulative', False)

    def properties(self):
        d = dict()
        for frame in self.frames:
            if not frame.isDefault():
                d[frame.name] = frame.properties()

        return {'frames':  d,
                'title':   self.title,
                'args':    self.args,
                'links':   self.pagelinks,
                'filters': ' '.join(self.filters),
                'force_cumulative': self.force_cumulative
               }

    def addFragment(self, fragment, pos=-1):
        if pos >= 0 and len(self.frames) > pos:
            frame = self.frames[pos]
        else:
            pos = 0
            if self.frames:
                pos = self.frames[-1].pos + 1
            frame = FragmentFrame(unicode(pos))
            frame.pos = pos
            self.frames.insert(frame.pos, frame)

        self.setDefault(False)
        frame.frags.append((fragment.name, fragment))

    def removeFragment(self, fragname):
        for frame in self.frames:
            for name, frag in frame.frags:
                if name == fragname:
                    self.setDefault(False)
                    frame.frags.remove((name, frag))
                    if len(frame.frags) == 0:
                        self.frames.remove(frame)

    def get_pagelink_args(self, arg, data, page_args):
        args = {}
        if arg in self.pagelinks:
            # If this is a specific page link, cumulate args.
            args.update(page_args)
        args.update(arg_types[arg].get_pagelink_args(arg, data))
        return args

    def get_pagelink_default(self, field, arg_data):
        try:
            return self.pagelinks[field]
        except KeyError:
            return arg_types[field].get_pagelink_default(field, arg_data)

    def get_pagelinks(self, field, arg_data):
        try:
            return [self.pagelinks[field]]
        except KeyError:
            return arg_types[field].get_pagelinks(field, arg_data)

class PagesList(StoredObject):

    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.pages = {}

    def __repr__(self):
        return '<PagesList>'

    def isDefault(self): return False
    def setDefault(self, b):
        for page in self.pages.itervalues():
            page.setDefault(b)

    def load(self, items):
        for key, value in items.iteritems():
            self.pages[key] = Page(key)
            self.pages[key].load(value)

    def properties(self):
        d = dict()
        for key, page in self.pages.iteritems():
            if not page.isDefault():
                d[key] = page.properties()

        return d

    def __contains__(self, key):
        return (key in self.pages)

    def __getitem__(self, key):
        return self.pages[key]

    def __setitem__(self, key, value):
        self.pages[key] = value

    def __delitem__(self, key):
        if key not in self.pages:
            return
        del self.pages[key]

