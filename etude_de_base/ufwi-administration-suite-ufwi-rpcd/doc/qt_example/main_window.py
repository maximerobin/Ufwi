
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

from PyQt4.QtGui import QMainWindow, QMessageBox
from main_window_ui import Ui_MainWindow
from services import Services

class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self, client, parent=None):
        QMainWindow.__init__(self, parent)
        self.setupUi(self)
        self.client = client
        self.services = Services(self)

    def information(self, message, title=None):
        if not title:
            title = self.tr("NuCentral example information")
        QMessageBox.information(self, title, message)

    def error(self, message, title=None):
        if not title:
            title = self.tr("NuCentral example error")
        QMessageBox.warning(self, title, message)

