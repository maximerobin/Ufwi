
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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QWizard
from PyQt4.QtGui import QPixmap

class NetworkCommonWizard(QWizard):
    def __init__(self, parent=None):
        QWizard.__init__(self, parent)
        self.setOption(QWizard.NoBackButtonOnStartPage, True)
        self.setPixmap(QWizard.WatermarkPixmap, QPixmap(":/images/wizard_watermark"))

    def _setPage(self, index, page):
        self.setPage(index, page)
        self.connect(page, SIGNAL('modified'), self.reemit)

    def reemit(self, *args):
        self.emit(SIGNAL('modified'), *args)
