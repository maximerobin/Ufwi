
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

from PyQt4.QtGui import QGraphicsEllipseItem

class PieItem(QGraphicsEllipseItem):

    PIE = 0
    C_PIE = 1

    def __init__(self, rect, type):
        QGraphicsEllipseItem.__init__(self, rect)
        self._color = None
        self._darkColor = None
        self._pos = None
        self._startAngle = None
        self._spanAngle = None
        self._value = None
        self._type = type

    def setColor(self, color):
        self._color = color
        self.setBrush(self._color)
        self.setDarkColor(color.darker(120))

    def getColor(self):
        return self._color

    def setDarkColor(self, color):
        self._darkColor = color

    def getDarkColor(self):
        return self._darkColor

    def setPos(self, pos):
        self._pos = pos

    def getPos(self):
        return self._pos

    def setValue(self, value):
        self._value = value

    def getValue(self):
        return self._value

    def setStartAngle(self, angle):
        self._startAngle = angle
        QGraphicsEllipseItem.setStartAngle(self, angle * 16)

    def getStartAngle(self):
        return self._startAngle

    def setSpanAngle(self, angle):
        self._spanAngle = angle
        QGraphicsEllipseItem.setSpanAngle(self, angle * 16)

    def getSpanAngle(self):
        return self._spanAngle

    def setLabel(self, label):
        self._label = label

    def getLabel(self):
        return self._label

    def getType(self):
        return self._type

    type = property(getType)
    startAngle = property(getStartAngle, setStartAngle)
    spanAngle = property(getSpanAngle, setSpanAngle)
    value = property(getValue, setValue)
    pos = property(getPos, setPos)
    color = property(getColor, setColor)
    darkColor = property(getDarkColor, setDarkColor)
    label = property(getLabel, setLabel)
