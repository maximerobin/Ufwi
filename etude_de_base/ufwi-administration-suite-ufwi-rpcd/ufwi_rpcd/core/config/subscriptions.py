
"""
Copyright (C) 2009-2011 EdenWall Technologies

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
"""

from ufwi_rpcd.core.config.configuration import Configuration
from ufwi_rpcd.backend import Depends

VIRTUAL_NODE = 'virtual'
VIRTUAL_PATH = '/%s/' % VIRTUAL_NODE

class SubscriptionError(Exception):
    pass

class Subscription(object):
    def __init__(self, name, callback, callback_arg):
        self.name = name
        self.callback = callback
        self.callback_arg = callback_arg
        self.paths = []

    def data(self):
        return self.name, self.callback, self.callback_arg, self.paths

    def __repr__(self):
        return u'<%s name=%s callback=%s paths=%s>' % (
            self.__class__.__name__,
            self.name,
            self.callback.__name__,
            self.paths
            )

class Subscriptions:
    def __init__(self, name):
        self.name = name
        self.depends = Depends()
        self.subscriptions = {}
        self.name2subscription = {}

    @staticmethod
    def _pathToStr(path):
        if isinstance(path, (tuple, list)) and len(path) == 1:
            path = path[0]
        if bool(path) is False:
            return '/'
        if isinstance(path, (str, unicode)):
            return '/%s' % path
        if path is None:
            return '/'
        return '/%s' % ('/'.join(path))# if path else "/"

    @staticmethod
    def pathIterator(data):
        if isinstance(data, Configuration):
            for path in data.iterpaths():
                yield Subscriptions._pathToStr(path)
        else:
            for path in data:
                yield path

    def addSubscriber(self, callback, component_name, depends_on, *path, **kwargs):
        """
        depends_on: a set of component names
        """
        if component_name in self.name2subscription:
            raise SubscriptionError("[%s] Component already registered" % self.name)
        callback_arg = kwargs.get("callback_arg")
        path = self._pathToStr(path)
        subscription = Subscription(component_name, callback, callback_arg)
        self.name2subscription[component_name] = subscription

        if depends_on:
            self.depends.addDepObject(component_name, depends_on)

        if path not in self.subscriptions:
            self.subscriptions[path] = set()
        self.subscriptions[path].add(subscription)

    def match(self, data, match_all=False):
        """
        @arg data: a Configuration OR paths
        """
        self.cleanup_paths()
        if not self.subscriptions:
            return tuple()

        if match_all:
            names = [item.name for item in self.name2subscription.values()]
        else:
            names = [item.name for item in self._match(data)]
        alldeps = self.depends.getDependancesForMany(names)
        subscribers = [self.name2subscription[item] for item in alldeps]
        return [item.data() for item in subscribers]

    def _match(self, data):
        """
        @arg data: a Configuration OR paths
        """
        subscribers = set()

        for path in Subscriptions.pathIterator(data):
            if path.startswith(VIRTUAL_PATH):
                path = path.replace(VIRTUAL_PATH, '/', 1)
            for subscribed_path in self.subscriptions:
                if not subscribed_path.startswith(path):
                    continue
                for subscription in self.subscriptions[subscribed_path]:
                    subscribers.add(subscription)
                    subscription.paths.append(path)
        return subscribers

    def iterSubscriptions(self):
        for subscriptions in self.subscriptions.itervalues():
            for subscription in subscriptions:
                yield subscription

    def cleanup_paths(self):
        for subscription in self.iterSubscriptions():
            subscription.paths = []

