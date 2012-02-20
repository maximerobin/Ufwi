#!/usr/bin/python
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


from sys import exit
from ufwi_rpcc_qt.application import create_application
from ufwi_rpcd.client import tr

from PyQt4.QtGui import QSplashScreen, QPixmap, QRegion
from PyQt4.QtCore import Qt
from ufwi_rpcc_qt.multisite_client import MultisiteClient

def start_eas(host, client, app):
    multisite_client = MultisiteClient(host, client)

    # Add splash screen
    pixmap = QPixmap(":/images/splash_start.png")
    splash = QSplashScreen(pixmap)
    splash.setMask(QRegion(pixmap.mask()));
    splash.setPixmap(pixmap);
    splash.show()
    app.splash = splash
    splash.showMessage(tr("Loading application"), Qt.AlignBottom | Qt.AlignRight);
    app.processEvents()

    # Load the main window
    from console_edenwall import MainWindow
    window = MainWindow(app, multisite_client)
    window.show()
    splash.finish(window)

