
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

from PyQt4.QtGui import QGroupBox, QHBoxLayout, QPixmap, QLabel, QSizePolicy
from PyQt4.QtCore import Qt

class MessageArea(QGroupBox):
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"

    def __init__(self, parent=None):
        QGroupBox.__init__(self, parent)
        self.ICONS = {
            self.INFO: QPixmap(":icons-32/info"),
            self.WARNING: QPixmap(":icons-32/warning"),
            self.CRITICAL: QPixmap(":icons-32/off_line"),
        }

        self.box = QHBoxLayout(self)


        self.icon = QLabel()

        self.message = QLabel()
        self.message.setTextFormat(Qt.RichText)
        self.message.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)

        self.display_items = self.message, self.icon

        self.box.addWidget(self.icon)
        self.box.addWidget(self.message)
#        self.box.addStretch()

        self.setNoMessage()

    def setMessage(self, title, message, status=INFO):
        self.icon.setPixmap(self.ICONS[status])
        self.setTitle(title)
        self.message.setText(message)
        for item in self.display_items:
            item.show()
        self.setFlat(False)

    def setWidth(self, chars):
        self.message.setFixedWidth(self.fontMetrics().averageCharWidth() * chars)
        self.setWordWrap()

    def setWordWrap(self):
        self.message.setWordWrap(True)

    def setNoMessage(self):
        self.setTitle("")
        self.setFlat(True)
        for item in self.display_items:
            item.hide()

    def info(self, title, message):
        """
        Convenience method to display an information
        """
        self.setMessage(title, message, status=MessageArea.INFO)

    def warning(self, title, message):
        """
        Convenience method to display a warning
        """
        self.setMessage(title, message, status=MessageArea.WARNING)

    def critical(self, title, message):
        """
        Convenience method to display something critical
        """
        self.setMessage(title, message, status=MessageArea.CRITICAL)

