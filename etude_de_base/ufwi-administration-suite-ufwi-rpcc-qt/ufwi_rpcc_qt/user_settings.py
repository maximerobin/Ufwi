
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

from PyQt4.QtCore import QSettings, QVariant, QStringList

class UserSettings(QSettings):
    def __init__(self, app_name, parent = None):
        QSettings.__init__(self, QSettings.IniFormat, QSettings.UserScope, "INL", app_name, parent)

    def _get(self, key, default):
        if default is not None:
            default = QVariant(default)
            return self.value(key, default)
        else:
            return self.value(key)

    def getUnicode(self, key, default=None):
        value = self._get(key, default)
        if value.type() == QVariant.String:
            return unicode(value.toString())
        else:
            return default

    def getInt(self, key, default=None):
        value = self._get(key, default)
        if value.toInt()[1]:
            return value.toInt()[0]
        return default

    def getSize(self, key, default=None):
        # Probably broken: QSettings seems to be always returning QVariant of type QString
        value = self._get(key, default)
        if value.type() == QVariant.Size:
            return value.toSize()
        else:
            return default

    def getPoint(self, key, default=None):
        # Probably broken: QSettings seems to be always returning QVariant of type QString
        value = self._get(key, default)
        if value.type() == QVariant.Point:
            return value.toPoint()
        else:
            return default

    def getStringList(self, key, default=None):
        value = self._get(key, default)
        if value.type() == QVariant.StringList:
            strlist = value.toStringList()
            return map(unicode, strlist)
        else:
            return default

    def _set(self, key, value):
        self.setValue(key, QVariant(value))

    def setUnicode(self, key, value):
        self._set(key, value)

    def setInt(self, key, value):
        self._set(key, unicode(int(value)))

    def setSize(self, key, value):
        self._set(key, value)

    def setPoint(self, key, value):
        self._set(key, value)

    def setStringList(self, key, value):
        value = QStringList(value)
        self._set(key, value)

