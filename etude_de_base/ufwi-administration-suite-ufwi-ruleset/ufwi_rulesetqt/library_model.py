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

from ufwi_rulesetqt.objects import Objects
from ufwi_rulesetqt.model import Model

class LibraryModel(Model):
    def __init__(self, controler):
        Model.__init__(self, controler.window, controler.REFRESH_DOMAIN)
        self.controler = controler
        self.compatibility = self.window.compatibility
        self.objects = Objects(controler, {})

    def clear(self):
        self.objects.clear()

    def refresh(self, all_updates, updates):
        # updateObjects() fills all_update to ask to redisplay the references
        # of updated objects
        data = self.ruleset('getObjects', self.name, append_fusion=True)
        self.objects.updateObjects(self.controler, data, all_updates, updates)

    def __getitem__(self, identifier):
        return self.objects[identifier]

    def __iter__(self):
        return self.objects.itervalues()

    def delete(self, object):
        identifier = object['id']
        return self.ruleset("objectDelete", self.name, identifier)

    def templatize(self, identifier):
        return self.ruleset('objectTemplatize', self.name, identifier, self.window.useFusion())

class NetworksModel(LibraryModel):
    def __init__(self, controler):
        LibraryModel.__init__(self, controler)
        # identifier => Network object
        self.network_index = {}

    def _flatten(self, objects):
        for network in objects.itervalues():
            self.network_index[network['id']] = network
            if 'children' in network:
                self._flatten(network['children'])

    def refresh(self, all_updates, updates):
        LibraryModel.refresh(self, all_updates, updates)
        self.network_index.clear()
        self._flatten(self.objects)

    # FIXME: Remove error argument?
    def _getResource(self, resources, identifier, error=False):
        if identifier in resources:
            return resources[identifier]
        for resource in resources.itervalues():
            if 'children' not in resource:
                continue
            result = self._getResource(resource['children'], identifier)
            if result:
                return result
        if error:
            raise KeyError('Unable to find the resource "%s"!' % identifier)
        return None

    def getResource(self, identifier):
        return self._getResource(self.objects, identifier, error=True)

    def resourcesIterator(self, node=None):
        if node is None:
            for res in self.objects.itervalues():
                for n in self.resourcesIterator(res):
                    yield n
        else:
            yield node
            if 'children' in node:
                for res in node['children']:
                    for n in self.resourcesIterator(self.getResource(res)):
                        yield n

    def __getitem__(self, identifier):
        return self.network_index[identifier]

