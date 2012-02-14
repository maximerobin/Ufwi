"""
$Id$


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
from PyQt4.QtGui import QWidget

from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.colors import COLOR_INVALID

class Validable(object):
    OK_STYLE = ''
    NOK_STYLE = '{ background-color: %s; }' % COLOR_INVALID

    def __init__(self, accept_empty=False):
        self.accept_empty = accept_empty

        #Ensure we're not setting stylesheet for our children (a menu for instance):
        #specify class name in the css
        qt_base = self._discover_base_qt_class()
        self._nok_stylesheet = qt_base.__name__ + Validable.NOK_STYLE

    def _discover_base_qt_class(self):
        for base in self.__class__.__bases__:
            if issubclass(base, QWidget):
                return base
        assert False, "Please call Validable.__init__ AFTER a Qt __init__"

    def validColor(self, force=None):
        if self.accept_empty and self.isEmpty():
            valid = True
        elif force is not None:
            valid = force
        else:
            valid = self.isValid()

        if valid:
            self.setStyleSheet(Validable.OK_STYLE)
        else:
            self.setStyleSheet(self._nok_stylesheet)

    def focusInEvent(self, event):
        self.validColor(True)
        self.setReadOnly(False)

    def focusOutEvent(self, event):
        self.validColor()
        self.setReadOnly(True)
        self.emit(SIGNAL('editing done'))

    def isEmpty(self):
        """
        default implementation: False
        """
        return False

    @abstractmethod
    def isValid(self):
        pass

    @abstractmethod
    def getFieldInfo(self):
        pass

    def setValidatorEnabled(self, enabled):
        try:
            if enabled:
                self.validColor()
            else:
                self.validColor(force=True)
        except AttributeError:
            pass

