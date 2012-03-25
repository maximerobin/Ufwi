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

from ufwi_rulesetqt.create_application_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX
from PyQt4.QtCore import QRegExp

class CreateApplication(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.setRegExpValidator(self.id_text, IDENTIFIER_REGEX)
        self.setRegExpValidator(self.path_text, QRegExp(ur'^[a-zA-Z0-9*?.:_ \\/-]+$'))
        self.object_id = None

    def create(self):
        self.object_id = None
        self.id_text.setText(u'')
        self.path_text.setText(u'')
        self.id_text.setFocus()
        self.execLoop()

    def modify(self, object):
        self.object_id = object['id']
        self.id_text.setText(self.object_id)
        self.path_text.setText(unicode(object['path']))
        self.id_text.setFocus()
        self.execLoop()

    def save(self):
        identifier = unicode(self.id_text.text())
        path = unicode(self.path_text.text())
        attr = {'path' : path}
        return self.saveObject(identifier, 'applications', attr)
