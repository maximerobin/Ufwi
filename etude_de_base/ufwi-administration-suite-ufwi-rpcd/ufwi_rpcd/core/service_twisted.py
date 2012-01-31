"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

from twisted.application.service import Service
from twisted.web.resource import Resource
from twisted.web.server import Site

class RpcdService(Service):
    def __init__(self, **childs):
        self.resource = Resource()

        for name, child in childs.iteritems():
            self.resource.putChild(name, child)

    def getResource(self):
        return self.resource

class RpcdSite(Site):
    def __init__(self, service):
        Site.__init__(self, service.getResource())
        self.service = service

