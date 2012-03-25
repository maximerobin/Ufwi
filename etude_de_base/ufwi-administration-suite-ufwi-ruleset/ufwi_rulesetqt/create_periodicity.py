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

from ufwi_rpcd.common import tr

from ufwi_rulesetqt.create_periodicity_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX

class CreatePeriodicity(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.setRegExpValidator(self.identifier_text, IDENTIFIER_REGEX)
        self.object_id = None
        self.time_from_combo.clear()
        self.time_to_combo.clear()
        for hour in xrange(24):
            self.time_from_combo.addItem(tr("%sh00") % hour)
            self.time_to_combo.addItem(tr("%sh59") % hour)

    def create(self):
        self.object_id = None
        self.identifier_text.setText(u'')
        self.date_from_combo.setCurrentIndex(0)
        self.date_to_combo.setCurrentIndex(0)
        self.time_from_combo.setCurrentIndex(0)
        self.time_to_combo.setCurrentIndex(0)
        self.identifier_text.setFocus()
        self.execLoop()

    def modify(self, object):
        self.object_id = object['id']
        self.identifier_text.setText(self.object_id)
        self.date_from_combo.setCurrentIndex(object['day_from'])
        self.date_to_combo.setCurrentIndex(object['day_to'])
        self.time_from_combo.setCurrentIndex(object['hour_from'])
        self.time_to_combo.setCurrentIndex(object['hour_to'] - 1)
        self.identifier_text.setFocus()
        self.execLoop()

    def save(self):
        identifier = unicode(self.identifier_text.text())
        attr = {
            'day_from': self.date_from_combo.currentIndex(),
            'day_to': self.date_to_combo.currentIndex(),
            'hour_from': self.time_from_combo.currentIndex(),
            'hour_to': 1 + self.time_to_combo.currentIndex(),
        }
        return self.saveObject(identifier, 'periodicities', attr)
