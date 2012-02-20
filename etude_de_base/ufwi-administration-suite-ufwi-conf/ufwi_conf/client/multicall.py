#coding: utf-8
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

from copy import deepcopy
from inspect import getmro

from ufwi_rpcd.client.multicall import Multicall
from ufwi_rpcd.client import RpcdError
from ufwi_conf.client.qt.ufwi_conf_form import NuConfForm
from ufwi_conf.client.qt.scrollarea import ScrollArea

class InitMultiCall(object):
    """
    when started, join all calls needed by frontend in one multicall
    calls, additionnal id of service (can be empty):
        [(component_name1, service_name1, [count]), (component_name2, service_name2, [count])]
    """
    COMP_SERV_FORMAT = '%s-%s'
    def __init__(self, client, mainwindow):
        self._init_multicall = Multicall(client)
        self.mainwindow = mainwindow
        self._calls_id = {}

    def run(self):
        self._init_responses = self._init_multicall()
        assert len(self._calls_id) == len(self._init_responses),\
            "number of responses != number of calls (%s %s)" % (len(self._calls_id), len(self._init_responses))

    def listConfigCalls(self, pages, calls):
        """
        build list of init calls

        Search static method get_calls in frontend and frontend's base classes
        'get_calls' must return one iterable which contains tuple like that:
            (component_name1, service_name1, count)

        Third argument in tuples is not mandatory (it's 1 by default) :
            ('component', 'service') <=> ('component', 'service', 1)
        """

        if calls is not None:
            assert callable(calls), "InitMultiCall.__init__(...) : 'calls' parameter must be callable"
            for component_name, service_name in calls():
                self._addCall(component_name, service_name)

        #for frontend in tuple(pages.itervalues()):
        if isinstance(pages, dict):
            iterable = pages.itervalues()
        else:
            iterable = tuple(pages)
        for frontend in iterable:
            self.addCallsForFrontend(frontend)

    def addCallsForFrontend(self, frontend):
        if not isinstance(frontend, type):
            frontend = type(frontend)
        parents = getmro(frontend)
        for parent_class in parents:
            if not issubclass(parent_class, (ScrollArea, NuConfForm)):
                continue
            for call in parent_class.get_calls():
                if 2 == len(call):
                    call = call + (1,)
                component_name, service_name, count = call
                assert count >= 1, "count must be >= 1"
                for i in xrange(count):
                    self._addCall(component_name, service_name)


    def _addCall(self, component_name, service_name):
        """
        add service to dict call_id
        """
        service_id = self.COMP_SERV_FORMAT % (component_name, service_name)
        if service_id not in self._calls_id:
            # store index inside future response (append to self._calls_id)
            CallParam(service_id,self._calls_id)
            self._init_multicall.addCall(component_name, service_name)
        else:
            self._calls_id[service_id].increment()

    def isCached(self, component, service):
        service_id = self.COMP_SERV_FORMAT % (component, service)
        return self._calls_id.has_key(service_id)

    def getResponse(self, component, service):
        """
        service could not have parameters (static parameters could be implemented)
        """
        service_id = self.COMP_SERV_FORMAT % (component, service)
        assert not self._calls_id[service_id].done(), "getResponse for '%s' '%s' no more in cache" % (component, service)
        self._calls_id[service_id].decrement()
        result = self._init_responses[self._calls_id[service_id].getIndex()]
        if isinstance(result, RpcdError):
            self.mainwindow.writeError(result, "Error calling service '%s.%s'" % (component, service))
            return None

        return deepcopy(result)

    def clean(self):
        """
        response is not needed anymore
        """
        self._calls_id.clear()
        del self._init_responses[:]

class CallParam(object):
    """
    map service to index inside the list used by getResponse

    count : number of allowed calls
    """
    def __init__(self, service_id, saved_calls):
        """
        store a new call inside saved_calls
        """
        self.id = len(saved_calls)
        saved_calls[service_id] = self
        self.count = 1

    def increment(self):
        self.count += 1

    def decrement(self):
        assert self.count > 0, "count must be greater than 0"
        self.count -= 1

    def getIndex(self):
        """
        index inside the response of multicalls
        """
        return self.id

    def done(self):
        """
        response for this call should not be used if self.count is null
        """
        return 0 == self.count
