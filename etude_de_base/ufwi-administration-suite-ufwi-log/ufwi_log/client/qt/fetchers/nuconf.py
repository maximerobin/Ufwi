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

from copy import deepcopy
from ufwi_log.client.qt.fetchers.base import BaseFetcher

class IDSIPSFetcher(BaseFetcher):

    def getArgs(self):
        return []

    def getTime(self, callback):
        module = 'ntp'
        self.asyncall(module, 'getServerTime', callback=callback, errback=self._errorHandler)

    def fetch(self, callback):
        # Copy args that the main window wants us to filter on.
        self.my_args = deepcopy(self.fragment.args)
        self.my_args.update(self.args)
        self.asyncall('ids_ips', 'getTableLog', self.my_args, callback=callback, errback=self._errorHandler, cache=True)
