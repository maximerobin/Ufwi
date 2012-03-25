
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

from PyQt4.QtCore import Qt
from PyQt4.QtGui import QSplashScreen, QPixmap, QRegion

class SplashScreen:
    def __init__(self, image_resource=":/images/splash_wait.png", text=None):
        pixmap = QPixmap(image_resource)
        self.splash = QSplashScreen(pixmap)
        self.splash.setMask(QRegion(pixmap.mask()));
        self.splash.setPixmap(pixmap);
        flags = self.splash.windowFlags()
        flags |= Qt.WindowStaysOnTopHint
        self.splash.setWindowFlags(flags)
        self._text = None
        if text is not None:
            self.setText(text)

    def show(self):
        self.splash.show()

    def hide(self):
        self.splash.hide()

    def setText(self, text):
        self._text = text
        self.splash.showMessage(text, Qt.AlignBottom | Qt.AlignHCenter);

    def getText(self):
        return self._text

