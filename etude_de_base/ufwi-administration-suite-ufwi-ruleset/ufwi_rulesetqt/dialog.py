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

from PyQt4.QtCore import QRegExp
from ufwi_ruleset.common.regex import IDENTIFIER_REGEX_STR
from ufwi_rpcc_qt.central_dialog import CentralDialog

IDENTIFIER_REGEX = QRegExp(IDENTIFIER_REGEX_STR)

class RulesetDialog(CentralDialog):
    def __init__(self, window, accept=None):
        self.window = window
        CentralDialog.__init__(self, window, accept)

    def saveObject(self, identifier, library, attr):
        is_new = (self.object_id is None)
        attr['id'] = identifier
        if is_new:
            arguments = ('objectCreate', library, attr)
        else:
            arguments = ('objectModify', library, self.object_id, attr)
        try:
            updates = self.window.ruleset(*arguments, **{'append_fusion': True})
        except Exception, err:
            self.window.exception(err)
            return False
        self.window.refresh(updates)
        return True

