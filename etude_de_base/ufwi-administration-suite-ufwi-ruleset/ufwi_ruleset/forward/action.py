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

# Import Update and Updates to be able to write:
# "from ufwi_ruleset.forward.action import Action, Update"
from ufwi_ruleset.common.update import Update, Updates

class NoopActionHandler:
    def __init__(self, updates):
        self.updates = updates

    def __call__(self):
        pass

    def __repr__(self):
        return '<NoopActionHandler updates=%s>' % (self.updates,)

class ActionHandler(NoopActionHandler):
    def __init__(self, update, func, *arguments, **kw):
        updates = Updates.create(update)
        NoopActionHandler.__init__(self, updates)
        self.func = func
        self.arguments = arguments
        self.kw = kw

    def __call__(self):
        return self.func(*self.arguments, **self.kw)

    def __repr__(self):
        return '<ActionHandler updates=%s func=%s arguments=%r kw=%r>' % \
            (self.updates, self.func, self.arguments, self.kw)

class Action:
    def __init__(self, apply, unapply):
        self._apply = [apply]
        self._unapply = [unapply]

    def _exec(self, func_list):
        for func in func_list:
            func()

    def apply(self):
        self._exec(self._apply)

    def unapply(self):
        self._exec(reversed(self._unapply))

    def _addUpdate(self, func, update):
        func.updates.addUpdate(update)

    def addApplyUpdate(self, update):
        self._addUpdate(self._apply[0], update)

    def addUnapplyUpdate(self, update):
        self._addUpdate(self._unapply[0], update)

    def addBothUpdate(self, update):
        self.addApplyUpdate(update)
        self.addUnapplyUpdate(update)

    def chain(self, action):
        self._apply.extend(action._apply)
        self._unapply.extend(action._unapply)

    def executeAndChain(self, action):
        action.apply()
        self.chain(action)

    def _createTuple(self, func_list):
        updates = Updates()
        for func in func_list:
            updates.addUpdates(func.updates)
        return updates.createTuple()

    def createApplyTuple(self):
        """create a tuple of updates of all apply actions"""
        return self._createTuple(self._apply)

    def createUnapplyTuple(self):
        """create a tuple of updates of all unapply actions"""
        return self._createTuple(self._unapply)

    @staticmethod
    def createEmpty():
        updates = Updates()
        noop = NoopActionHandler(updates)
        return Action(noop, noop)

