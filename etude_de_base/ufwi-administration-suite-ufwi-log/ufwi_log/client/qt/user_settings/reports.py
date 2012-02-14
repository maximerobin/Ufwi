# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
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

from ufwi_rpcd.common.config import serializeElement, deserializeElement

from ufwi_log.client.qt.user_settings.stored import StoredObject

class ReportType(StoredObject):
    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.title = ''
        self.filters = ()
        self.scenario = []

    def __repr__(self):
        return "<Report '%s'>" % self.name

    def load(self, items):
        items = deserializeElement(items)
        self.title =    items.get('title', '')
        self.filters =  items.get('filters', ())
        self.scenario = items.get('scenario', [])

    def properties(self):
        items = {'title':    self.title,
                 'filters':  self.filters,
                 'scenario': self.scenario
                }
        return serializeElement(items)

class ReportsList(StoredObject):
    def __init__(self, name):
        StoredObject.__init__(self, name)
        self.reports = {}

    def __repr__(self):
        return '<ReportsList>'

    def isDefault(self): return False
    def setDefault(self, b):
        for reports in self.reports.itervalues():
            reports.setDefault(b)

    def load(self, items):
        for key, value in items.iteritems():
            self.reports[key] = ReportType(key)
            self.reports[key].load(value)

    def properties(self):
        d = dict()
        for key, report in self.reports.iteritems():
            if not report.isDefault():
                d[key] = report.properties()

        return d

    def __contains__(self, key):
        return (key in self.reports)

    def __getitem__(self, key):
        return self.reports[key]

    def __setitem__(self, key, value):
        self.reports[key] = value

    def __delitem__(self, key):
        if key not in self.reports:
            return
        del self.reports[key]
