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

from ufwi_rulesetqt.create_duration_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX
#from PyQt4.QtCore import QRegExp

class CreateDuration(RulesetDialog, Ui_Dialog):
    DURATION_UNIT = [1, 60, 60 * 60, 60 * 60 * 24]

    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.setRegExpValidator(self.identifier_text, IDENTIFIER_REGEX)
        self.setIntValidator(self.duration_text, 0, 2**32 - 1)
        self.object_id = None

    def create(self):
        self.object_id = None
        self.identifier_text.setText(u'')
        self.duration_text.setText(u'')
        self.duration_combo.setCurrentIndex(0)
        self.identifier_text.setFocus()
        self.execLoop()

    def modify(self, object):
        self.object_id = object['id']
        self.identifier_text.setText(self.object_id)

        seconds = object['seconds']
        # Select the correct unit
        self.duration_combo.setCurrentIndex(0)
        for no, unit in enumerate(self.DURATION_UNIT):
            if (seconds % unit) == 0:
                self.duration_combo.setCurrentIndex(no)
        unit = self.duration_combo.currentIndex()
        self.duration_text.setText(unicode(seconds / self.DURATION_UNIT[unit]))
        self.identifier_text.setFocus()
        self.execLoop()

    def save(self):
        identifier = unicode(self.identifier_text.text())
        unit = self.duration_combo.currentIndex()
        seconds  = int(self.duration_text.text())
        seconds *= self.DURATION_UNIT[unit]
        attr = {'seconds' : seconds}
        return self.saveObject(identifier, 'durations', attr)
