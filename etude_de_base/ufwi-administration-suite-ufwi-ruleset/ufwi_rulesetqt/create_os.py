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
from ufwi_rulesetqt.create_os_ui import Ui_Dialog
from ufwi_rulesetqt.dialog import RulesetDialog, IDENTIFIER_REGEX
from PyQt4.QtCore import SIGNAL

class CreateOS(RulesetDialog, Ui_Dialog):
    def __init__(self, window):
        RulesetDialog.__init__(self, window)
        self.setupUi(self)
        self.connectButtons(self.buttonBox)
        self.setRegExpValidator(self.id_text, IDENTIFIER_REGEX)
        self.object_id = None
        self.typeother_text.setVisible(False)
        self.connect(self.type_combo, SIGNAL("currentIndexChanged(int)"), self.selectType)
        self.selectType(0)

    def create(self):
        self.object_id = None
        self.id_text.setText(u'')
        self.typeother_text.setText(u'')
        self.version_text.setText(u'')
        self.id_text.setFocus()
        self.execLoop()

    def modify(self, object):
        name = object['name']
        self.object_id = object['id']
        self.id_text.setText(self.object_id)
        self.version_text.setText(u'')

        if name == 'Darwin':
            name = 'Mac OS X'

        if name == 'Windows':
            version = unicode(object.get('version', u''))
            self.version_text.setText(version)
        else:
            release = unicode(object.get('release', u''))
            self.version_text.setText(release)

        index = self.type_combo.findText(name)
        if index != -1 and index != self.type_combo.count() - 1:
            self.type_combo.setCurrentIndex( index )
        else:
            self.type_combo.setCurrentIndex( self.type_combo.count() - 1 )
            self.typeother_text.setText(name)

        self.id_text.setFocus()
        self.execLoop()

    def save(self):
        identifier = unicode(self.id_text.text())

        # if the 'other..' os is selected (the last entry in the combo box), then use the name in the lineedit
        if self.type_combo.currentIndex() != self.type_combo.count() - 1:
            name = unicode(self.type_combo.currentText())
            if name == 'Mac OS X':
                name = 'Darwin'
        else:
            name = unicode(self.typeother_text.text())

        if self.type_combo.currentIndex() != 0:
            release = unicode(self.version_text.text())
            version = u''
        else:
            release = u''
            version = unicode(self.version_text.text())

        attr = {'name':name, 'version':version, 'release':release}
        return self.saveObject(identifier, 'operating_systems', attr)

    def selectType(self, index):
        # Hide/show the text edit widget to enter the OS name
        if index == self.type_combo.count() - 1:
            self.typeother_text.setVisible(True)
        else:
            self.typeother_text.setVisible(False)

        # Set a version number example
        if index == 0:
            # Windows like selected
            self.example_label.setText(tr("Example: 600* (for Vista), 2600 (for XP)"))
        else:
            # Unix like
            self.example_label.setText(tr("Example: 2.4*, 2.6.12"))

