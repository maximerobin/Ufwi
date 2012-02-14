
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

from PyQt4.QtGui import QWidget
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QSpinBox
from PyQt4.QtGui import QSizePolicy

class DurationEditor(QWidget):
    """
    Speaks in seconds to programs, and Hours/Minutes/Seconds to human beings
    """
    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        box = QHBoxLayout(self)

        self.hours = QSpinBox()
        self.minutes = QSpinBox()
        self.seconds = QSpinBox()

        for spinbox in (self.hours, self.minutes, self.seconds):
            spinbox.setMinimum(0)

        box.addWidget(self.hours)
        box.addWidget(QLabel(tr('h')))
        box.addWidget(self.minutes)
        box.addWidget(QLabel(tr('m')))
        box.addWidget(self.seconds)
        box.addWidget(QLabel(tr('s')))
        self.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)

    def _seconds2hms(self, value):
        #integer division
        hours = value[0] / 3600
        remainder = value[0] % 3600
        minutes = remainder / 60
        seconds = remainder % 60
        return hours, minutes, seconds


    def setMaximum(self, maximum):
        hours, minutes, seconds = self._seconds2hms(maximum)
        self.hours.setMaximum(hours)
        self.minutes.setMaximum(minutes)
        self.seconds.setMaximum(seconds)

    def setValue(self, value):
        hours, minutes, seconds = self._seconds2hms(value)
        self.hours.setValue(hours)
        self.minutes.setValue(minutes)
        self.seconds.setValue(seconds)

    def value(self):
        return self.hours.value()*3600 + self.minutes.value()*3600 + self.seconds.value()[0]



