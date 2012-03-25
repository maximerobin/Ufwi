#coding: utf-8

"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>
           Victor STINNER <vstinner AT edenwall.com>
           Pierre-Louis BONICOLI <bonicoli AT edenwall.com>

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

class DependsError(Exception):
    pass

class DepObject(object):
    def __init__(self, identifier, deps):
        """
        identifier: unicode
        deps: set of identifiers
        """
        self.identifier = identifier
        self.deps = deps

    def __repr__(self):
        return "<%s: \"%s\">" % (self.__class__.__name__, self.identifier)

class Depends(object):
    """
    No cycle detection, you can loop and fill the stack.
    """
    def __init__(self):
        self.depends = {}

    def addDepObject(self, identifier, deps):
        """
        identifier: unicode
        deps: set of identifiers
        """
        dep_object = DepObject(identifier, deps)
        for dependence in dep_object.deps:
            if dependence not in self.depends:
                self.depends[dependence] = set()
            self.depends[dependence].add(dep_object)

    def getOrderedDependences(self, identifier):
        result = self._getDepends(identifier)
        result.reverse()
        result = Depends.remMultiples(result)
        return result

    def getDependancesForMany(self, identifiers):
        # Retrieve components impacted by a modifications of "identifiers"
        all_deps = set()
        for item in identifiers:
            all_deps |=  set(self.getOrderedDependences(item))

        # Sort impacted components to respect dependencies
        return self.sortDependencies(all_deps)

    def sortDependencies(self, deps, result=None):
        if result is None:
            result = []
        wk_deps = deps.copy()
        for dependence in wk_deps:
            # needed is True if dependence is needed by other
            needed = False
            for dep in deps:
                if dep != dependence and dependence in self._getDepends(dep):
                    needed = True
            if not needed:
                deps.remove(dependence)
                result.append(dependence)
        if deps:
            self.sortDependencies(deps, result)
        return result

    @staticmethod
    def remMultiples(result):
        multiples = []
        for index, name in enumerate(result[:-1]):
            if name in result[index + 1:]:
                multiples.append(name)
        for name in multiples:
            result.remove(name)
        return result

    def _getDepends(self, identifier):
        result = []
        if identifier in self.depends:
            for dep_object in self.depends[identifier]:
                result += self._getDepends(dep_object.identifier)
        result.append(identifier)
        return result

class DependsObjects(Depends):
    """
    Extension of the 'Depends' class to have random objects depending on each other
    """
    def __init__(self, identifier_attr="name"):
        """
        By default, using <your_object>.name, but you can override this
        """
        Depends.__init__(self)
        self.identifier_attr = identifier_attr
        self.association = {}

    def getIdentifier(self, thing):
        return getattr(thing, self.identifier_attr)

    def addDepObject(self, thing, deps):
        identifier = self.getIdentifier(thing)
        if identifier in self.association:
            raise DependsError("identifier %s already known" % identifier)
        self.association[identifier] = thing
        Depends.addDepObject(self, identifier, deps)

    def getOrderedDependences(self, thing):
        identifier = self.getIdentifier(thing)
        deps = Depends.getOrderedDependences(self, identifier)
        result = [self.association[identifier] for identifier in deps]
        return result

