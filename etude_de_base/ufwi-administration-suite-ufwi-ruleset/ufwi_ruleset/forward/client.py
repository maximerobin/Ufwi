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

from ufwi_ruleset.version import VERSION as SERVER_VERSION

from ufwi_ruleset.forward.action import Update, Updates
from ufwi_ruleset.forward.error import RulesetError

# Default values are choosed to keep the compatibility with clients which are
# not supporting setupClient() service (ufwi_ruleset <= 3.0.1)
DEFAULT_CLIENT_VERSION = '3.0.1'
DEFAULT_MODE = 'GUI'

# The mode controls the result of the services:
#  - see Ruleset.formatAction() for the result of operations on the libraries:
#    objectCreate(), objectModify(), ...
#  - see Ruleset.formatRuleset() for the result of operations on the ruleset:
#    rulesetCreate(), rulesetOpen(), rulesetSaveAs()
VALID_MODES = ('CLI', 'GUI', 'GUI2')

class Client:
    def __init__(self, attr):
        """
        Attributes:
         - version (optional): client version (eg. "3.0.2")
         - fusion (optional): enable fusion? (default: False)
         - mode (optional): 'GUI' or 'CLI'
        """
        self.client_version = attr.get('version', DEFAULT_CLIENT_VERSION)

        mode = attr.get('mode', DEFAULT_MODE)
        if mode not in VALID_MODES:
            raise RulesetError(tr("Unknown client mode: %s"), repr(mode))
        self.mode = mode

        self.fusion = bool(attr.get('fusion', False))

    def setFusion(self, fusion, ruleset=None):
        self.fusion = fusion
        if self.mode == 'CLI':
            return self.fusion

        updates = Updates(
            Update('resources', 'update', '*'),
            Update('user_groups', 'update', '*'),
            Update('acls-ipv4', 'update', '*'),
            Update('acls-ipv6', 'update', '*'),
            Update('nats', 'update', '*'),
        )
        result = {'updates': updates.createTuple()}
        if ruleset:
            result['undoState'] = ruleset.undoState()
        return result

    def exportXMLRPC(self):
        return {
            'version': SERVER_VERSION,
            'mode': self.mode,
            'fusion': self.fusion}

def createLocalClient():
    return Client({'version': SERVER_VERSION, 'mode': 'CLI'})

