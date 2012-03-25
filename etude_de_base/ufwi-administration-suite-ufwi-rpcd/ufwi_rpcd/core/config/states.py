"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>

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

ConfigManager states

     +-----------------+                          +-----------------------------+
     |  IDLE           |                          |  MODIFIED                   |
     |                 |                          |                             |
O--->| *enter:         |---------+                |  *enter: .getValue reads    |
     |                 |         |                |           modified_config.  |
     |                 |         |                |          .make running_conf.|
     |  .getValue()    |         |                |                             |
     |   reads running_|         |                |        +--------------+     |
     |   configuration |         |   setValue()   |        |              |     |
     |                 |         +----------------|------->| DRAFT        |     |
     |                 |                          |        |              |     |
     |                 |                          |        | *......      |     |
     |                 |                          |        +--------------+     |
     | *provides:      |                          |             ^     |         |
     |     save()      |                          |             |     | commit()|
     +-----------------+                          |  setValue() |     | revert()|
              ^                                   |             |    \./        |
              |                                   |       +--------------+      |
              |                                   |       |              |      |
              |                                   |       | APPLICABLE   |      |
              |                                   |       |              |      |
              |                                   |       |              |      |
              |                                   |       +--------------+      |
              |                                   |               |             |
              |                                   |               |             |
              |                                   |       apply() |             |
              |                                   |               |             |
              |                                   |              \./            |
              |                                   |        +--------------+     |
              |                                   |        |              |     |
              |                                   |        | APPLYING     |     |
              |                                   |        |              |     |
              +---------------------------------------------runCallbacks()|     |
                                                  |        +--------------+     |
                                                  |                             |
                                                  +----------------------------+
"""

from .configuration import Configuration

class StateError(Exception):
    pass

class State(object):
    """
    Base class for states
    """
    NAME = "Base state"
    def __init__(self):
        raise StateError("States should not be instantiated")


    @staticmethod
    def enter(config_manager, silent=False):
        pass

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        pass

class NotInitializedState(State):
    NAME = "Not initialized"
    pass

class IdleState(State):
    """
    The base state, when nothing is modified
    """
    NAME = "Idle"
    @staticmethod
    def enter(config_manager, silent=False):
        config_manager.state = IdleState
        if not hasattr(config_manager, '_running_configuration'):
            config_manager._running_configuration = Configuration()
        if not silent:
            config_manager.info("Running configuration is the saved configuration.")

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        pass

    @staticmethod
    def _apply(config_manager, filename):
        config_manager.info("Nothing to apply")

class ModifiedState(State):
    NAME = "Modified"
    @staticmethod
    def enter(config_manager, silent=False):
        if not silent:
            config_manager.info("Configuration opened for modification")
        config_manager.state = ModifiedState
        config_manager._modified_configuration = Configuration()

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        if hasattr(config_manager, '_modified_configuration'):
            del config_manager._modified_configuration
        if not silent:
            config_manager.debug(
                "No modification registered (anymore?) - applied "
                "configuration sequence number: %s" %
                config_manager.running_sequence_number
                )

class DraftState(ModifiedState):
    NAME = "Draft"
    @staticmethod
    def enter(config_manager, silent=False):
        if not issubclass(config_manager.state, ModifiedState):
            ModifiedState.enter(config_manager, silent=silent)
        if not silent:
            config_manager.info("Configuration draft opened")
        config_manager.state = DraftState
        config_manager._draft_configuration = Configuration()

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        del config_manager._draft_configuration
        if not silent:
            config_manager.info("Configuration draft closed")
        if not issubclass(new_state, ModifiedState):
            #Why this 'if':
            #If we exit a sub state and its parent, because the state
            #being entered has another parent, then we call parent.exit()
            #too. Otherwise, nothing to do.
            ModifiedState.exit(config_manager, new_state)

    @staticmethod
    def _claimBlock(config_manager, claimer, path):
        for configuration in (
            config_manager._draft_configuration,
            config_manager._modified_configuration,
            config_manager._running_configuration):

            block = configuration
            try:
                for path_item in path:
                    block = block[path_item]
            except KeyError:
                pass
            block.claim(claimer)

    @staticmethod
    def _revert(config_manager):
        config_manager.enterState(ApplicableState)

    @staticmethod
    def _delete(config_manager, *path):
        path, key = path[:-1], path[-1]

        result_block = config_manager._draft_configuration
        for item in path:
            result_block = result_block.alwaysGet(item)
        result_block.delete(key)

class AbstractApplyState(ModifiedState):
    pass

class ApplicableState(AbstractApplyState):
    NAME = "Applicable"
    @staticmethod
    def enter(config_manager, silent=False):
        if not issubclass(config_manager.state, ModifiedState):
            ModifiedState.enter(config_manager, silent=silent)
        config_manager.state = ApplicableState

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        if not issubclass(new_state, ModifiedState):
            ModifiedState.exit(config_manager, new_state)

class ApplyingState(ApplicableState):
    NAME = "Applying"
    @staticmethod
    def enter(config_manager, silent=False):
        if not issubclass(config_manager.state, ApplicableState):
            ApplicableState.enter(config_manager, silent=silent)

        # TODO raise ConfigError
        assert not issubclass(config_manager.state, ApplyingState), "Trying to enter in state ApplyingState, while already in it"
        assert issubclass(config_manager.state, ApplicableState), "Was in '%s', expected : ApplicableState" % unicode(config_manager.state)
        config_manager.state = ApplyingState

    @staticmethod
    def exit(config_manager, new_state, silent=False):
        if new_state != IdleState:
            raise StateError("You cannot change state from %s to %s" % (ApplyingState.__name__, new_state.__name__))
        if not issubclass(new_state, ApplicableState):
            ApplicableState.exit(config_manager, new_state)

