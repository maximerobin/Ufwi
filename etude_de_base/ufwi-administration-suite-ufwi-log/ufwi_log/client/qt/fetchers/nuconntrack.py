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

class NuConntrackFetcher(BaseFetcher):

    fields = ('authenticated', 'username', 'orig_ipv4_src', 'orig_port_src', 'orig_ipv4_dst', 'orig_port_dst',
                                           'repl_ipv4_src', 'repl_port_src', 'repl_ipv4_dst', 'repl_port_dst', 'kill')
    can_kill = None

    def getArgs(self):
        # The last column is 'kill' which is an action and not a
        # filter. So we remove it from the returned filters list.
        l = list(self.fields[:-1])
        l.remove('username')
#        l.append('user_id')
        return l

    def kill(self, id):
        self.call('nuconntrack', 'kill', [int(id)])

    def getTime(self, callback):
        pass

    def canKill(self):
        if self.can_kill is None:
            self.can_kill = self.call('acl', 'check', 'nuconntrack', 'kill')
        return self.can_kill

    def fetch(self, callback):
        self.my_args = {'start': 0,
                        'limit': 30,
                        'sortby': 'timeout',
                        'sort': 'ASC'
                       }

        self.my_args.update(self.fragment.args)
        self.my_args.update(self.args)

        # only get from args filters which can be used (fields)
        filters_list = self.getArgs()
        filters = dict([(field, value) for field, value in self.my_args.items() if field in filters_list])

        self.asyncall('nuconntrack', 'view', filters,
                      self.my_args['sortby'], self.my_args['sort'][0],
                      self.my_args['start'], self.my_args['limit'],
                      callback=lambda x: self.fetch_cb(callback, filters, x),
                      errback=self._errorHandler)

    def fetch_cb(self, callback, filters, result):
        # The result is in form [{key: value, key2: value2, …}, {key: value, key2: value2, …}, …]
        # and the view needs table in form [[value, value2, …], [value, value2, …], …] in the order
        # of displayed columns.
        table = []
        for line in result['table']:
            tline = []
            for key in self.fields:
                if key == 'username':
                    tline.append((line[key],line['user_id']))
                    continue
                try:
                    tline += [line[key]]
                except KeyError:
                    # it happends with the 'kill' field
                    if key == 'kill':
                        tline += [line['_id']]
                    else:
                        tline += ['']
            table += [tline]

        # the view needs to have a dict in this form.
        callback({'args': self.my_args,
                  'filters': filters,
                  'columns': self.fields,
                  'rowcount': int(result['total']),
                  'table': table,
                 })
