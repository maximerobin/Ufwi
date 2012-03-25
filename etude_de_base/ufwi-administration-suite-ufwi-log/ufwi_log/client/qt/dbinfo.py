# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Pierre Chifflier <chifflier AT inl.fr>

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

from PyQt4.QtGui import QDialog
from ui.dbinfo_ui import Ui_DBInfoDialog

class DBInfoDialog(QDialog):
    def __init__(self, window, fragment=None, parent=None):
        """
            @param window [NulogMainWindow] the window where we edit fragment
            @param fragment [Fragment] the edited fragment
        """

        QDialog.__init__(self, parent)
        self.ui = Ui_DBInfoDialog()
        self.ui.setupUi(self)

        self.window = window
        self.fragment = fragment
        self.is_new = not fragment
        self.args = []
        self.background_color = None
        self.last_firewall = None

        self.connectSignals()

    def connectSignals(self):
        pass
        #self.connect(self.ui.type, SIGNAL('currentIndexChanged(int)'), self.typeChanged)
        #self.connect(self.ui.color_button, SIGNAL('clicked(bool)'), self.colorChanged)

