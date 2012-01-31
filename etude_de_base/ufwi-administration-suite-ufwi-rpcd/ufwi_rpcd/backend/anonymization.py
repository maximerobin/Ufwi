# -*- coding: utf-8 -*-

"""
Copyright (C) 2007-2011 EdenWall Technologies
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

from IPy import IP
from random import choice

class Anonymizer(object):

    def __init__(self):
        self.networks = []
        self.entities = []

    def _get_relations(self, session, rel_name):
        try:
            return session[rel_name]
        except KeyError:
            rel = {}
            session[rel_name] = rel
            return rel

    def random_word(self, rel, length=5):
        s = ''
        while not s or s in rel.itervalues():
            s = ''
            for i in xrange(length):
                if i % 2:
                    s += choice('bcdfghjklmnpqrstvwxz')
                else:
                    s += choice('aeiouy')

        return s

    ################# decorators ###################
    def check_role(rel_name, entity):
        """
        Do not anonymize data if requester is not a user or
        if user is not in the 'nulog_anonymous' role
        """

        def inner(func):
            def new_f(self, context, data):
                if not context.user or not 'nulog_anonymous' in context.user.roles or not entity in self.entities:
                    return data
                return func(self, self._get_relations(context.getSession(), rel_name), data)
            return new_f
        return inner

    def get_anon(func):
        def inner(self, rel, data):
            try:
                return rel[data]
            except KeyError:
                fake = func(self, rel, data)
                rel[data] = fake
                return fake
        return inner

    def get_real(func):
        def inner(self, rel, data):
            for real, fake in rel.iteritems():
                if str(fake) == str(data):
                    return func(self, rel, real)
            return func(self, rel, None)
        return inner

    ################# methods ##################

    @check_role('nulog_anon_ipaddr', 'ipaddr')
    @get_anon
    def anon_ipaddr(self, rel, ipaddr):
        ip = IP(ipaddr)
        for i, net in enumerate(self.networks):
            if ip in net:
                i += 1
                break
        else:
            i = 0

        return 'net%02d_ip%02d' % (i, len(rel) + 1)

    @check_role('nulog_anon_ipaddr', 'ipaddr')
    @get_real
    def real_ipaddr(self, rel, value):
        return value

    @check_role('nulog_anon_username', 'user')
    @get_anon
    def anon_username(self, rel, username):
        return self.random_word(rel, 5)

    @check_role('nulog_anon_username', 'user')
    @get_real
    def real_username(self, rel, value):
        return value

    @check_role('nulog_anon_userid', 'user')
    @get_anon
    def anon_userid(self, rel, userid):
        n = len(rel) + 1
        while n in rel.itervalues():
            n += 1
        return n

    @check_role('nulog_anon_userid', 'user')
    @get_real
    def real_userid(self, rel, value):
        try:
            return int(value)
        except ValueError:
            return 0

    @check_role('nulog_anon_appname', 'app')
    @get_anon
    def anon_appname(self, rel, appname):
        return self.random_word(rel, 7)

    @check_role('nulog_anon_appname', 'app')
    @get_real
    def real_appname(self, rel, value):
        return value

anonymizer = Anonymizer()
