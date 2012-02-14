
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

from PyQt4.QtCore import QSize, SIGNAL
from PyQt4.QtGui import QTableWidget, QPushButton, QSizePolicy, QLabel, QIcon, QPixmap, QFrame, QGridLayout

class FoldableTable(QFrame):

    def __init__(self, parent = None):
        QFrame.__init__(self, parent)
        self.setFrameStyle(QFrame.Box | QFrame.Raised);
        self.setupWidget()
        self.folded = False
        self.connect(self.folding_button, SIGNAL("clicked()"), self.toggleVisible)
        self.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Maximum)

    def setupWidget(self):
        self.plus_icon = QIcon()
        self.plus_icon.addPixmap(QPixmap(":/icons/add.png"))
        self.minus_icon = QIcon()
        self.minus_icon.addPixmap(QPixmap(":/icons/moins.png"))
        self.layout = QGridLayout(self)
        self.folding_button = QPushButton(self.minus_icon, "", self)
        self.folding_button.setMaximumSize(QSize(30,30))
        self.layout.addWidget(self.folding_button, 0, 0)
        self.label = QLabel("")
        self.layout.addWidget(self.label, 0, 1)
        self.table = QTableWidget(self)
        self.layout.addWidget(self.table, 1, 1)
        self.table.horizontalHeader().setStretchLastSection(1)
        self.font = self.label.font()
        self.font.setBold(True)
        self.font.setPointSize(self.font.pointSize() * 1.5)
        self.label.setFont(self.font)
        ## resize table to contents
        ## set column stretch to ensure first column won't expand when table
        ## is hidden
        self.layout.setColumnStretch(1, 10)

    def toggleVisible(self):
        self.folded = not self.folded
        if self.folded:
            self.folding_button.setIcon(self.plus_icon)
            self.table.hide()
        else:
            self.folding_button.setIcon(self.minus_icon)
            self.table.show()

    def setLabel(self, text):
        self.label.setText(text)
