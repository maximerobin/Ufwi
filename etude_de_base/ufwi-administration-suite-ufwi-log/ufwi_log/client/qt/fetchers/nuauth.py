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

from ufwi_log.client.qt.fetchers.base import BaseFetcher

class NuAuthFetcher(BaseFetcher):

    fields =        ('kill', 'username', 'ip_saddr_str', 'os_sysname', 'start_time',        'expire', 'groups', 'client_version')
    nuauth_fields = ('sock', 'name',     'addr',     'sysname',    'connect_timestamp', 'expire', 'groups', 'client_version')
    can_kill = None

    def __init__(self, fragment, args, client):
        BaseFetcher.__init__(self, fragment, args, client)
        self.type = 'real-time'

    def getArgs(self):
        # The first column is 'kill' which is an action and not a
        # filter. So we remove it from the returned filters list.
        return self.fields[1:]

    def getTime(self, callback):
        pass

    def kill(self, id):
        self.call('nuauth_command', 'disconnect', int(id))

    def canKill(self):
        if self.can_kill is None:
            self.can_kill = self.call('acl', 'check', 'nuauth_command', 'disconnect')
        return self.can_kill

    def fetch(self, callback):
        self.my_args = {'start': 0,
                        'limit': 10}
        self.my_args.update(self.fragment.args)
        self.my_args.update(self.args)

        filters = dict([(field, value) for field, value in self.my_args.items() if field in self.fields])

        result = self.asyncall('nuauth_command', 'getUsers', callback=lambda x: self.fetch_cb(callback, filters, x), errback=self._errorHandler)

    def fetch_cb(self, callback, filters, result):
        rowcount = len(result)

        # use only lines we want
        result = result[self.my_args['start'] : (self.my_args['start'] + self.my_args['limit'])]

        # The result is in form [{key: value, key2: value2, …}, {key: value, key2: value2, …}, …]
        # and the view needs table in form [[value, value2, …], [value, value2, …], …] in the order
        # of displayed columns.
        table = []
        for line in result:
            filtered = False
            for field, nuauth_field in zip(self.fields, self.nuauth_fields):
                if self.my_args.has_key(field) and self.my_args[field] != line[nuauth_field]:
                    filtered = True

            if filtered:
                continue

            table += [[line['sock'], (line['name'], line['uid']), line['addr'], line['sysname'],
                      line['connect_timestamp'], line['expire'], line['groups'], line['client_version']]]

        # the view needs to have a dict in this form.
        callback({'args': self.my_args,
                  'filters': filters,
                  'columns': self.fields,
                  'rowcount': rowcount,
                  'table': table,
                 })
