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

from copy import deepcopy
from ufwi_log.client.qt.fetchers.base import BaseFetcher

class NulogTableFetcher(BaseFetcher):

    module = 'ufwi_log'
    available_args = None

    def getArgs(self):
        if self.available_args is None:
            self.available_args = self.call(self.module, 'table_filters', self.fragment.type)
        return self.available_args

    def count(self, callback):

        count_args = {'count': True}
        count_args.update(self.my_args)
        return self.asyncall(self.module, 'table', self.fragment.type, count_args, callback=callback, errback=self._errorHandler, cache=True)

    def getTime(self, callback):
        module = 'ntp'
        self.asyncall(module, 'getServerTime', callback=callback, errback=self._errorHandler)

    def fetch(self, callback):

        # Copy args that the main window wants us to filter on.
        self.my_args = deepcopy(self.fragment.args)
        self.my_args.update(self.args)
        self.asyncall(self.module, 'table', self.fragment.type, self.my_args, callback=callback, errback=self._errorHandler, cache=True)

class OcsFetcher(NulogTableFetcher):

    module = 'ocs'

