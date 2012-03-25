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

from ufwi_rpcd.backend import tr
from ufwi_ruleset.forward.error import RulesetError

class ActionError(RulesetError):
    pass

class ActionStack:
    def __init__(self, ruleset, max_size):
        self.ruleset = ruleset
        self.max_size = max_size
        self.stack = []
        self.pointer = -1
        self.init_pointer = -1

    def setSavedState(self):
        self.init_pointer = self.pointer

    def isSavedState(self):
        return (self.pointer == self.init_pointer)

    def add(self, action):
        # Update the pointer and truncate the stack
        # if there are old undo actions
        self.pointer += 1
        if self.pointer != len(self.stack):
            del self.stack[self.pointer:]

        # Store the action
        self.stack.append(action)

        # Truncate action stack if needed
        if self.max_size \
        and self.max_size < len(self.stack):
            self.pointer -= (len(self.stack) - self.max_size)
            del self.stack[:-self.max_size]
            # Broken init pointer: we can never restore the initial state
            self.init_pointer = None

    def undoLast(self):
        if not self.canUndo():
            raise ActionError(tr("Unable to undo the last action!"))
        action = self.stack[self.pointer]
        action.unapply()
        self.pointer -= 1
        return action

    def redoLast(self):
        if not self.canRedo():
            raise ActionError(tr("Unable to redo the last action!"))
        action = self.stack[self.pointer+1]
        action.apply()
        self.pointer += 1
        return action

    def canUndo(self):
        return 0 <= self.pointer

    def canRedo(self):
        return 0 <= (self.pointer+1) < len(self.stack)


