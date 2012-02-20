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

from PyQt4.QtGui import QScrollArea
from ufwi_rpcd.common.error import writeError
from ufwi_rpcd.client import RpcdError
from ufwi_conf.client.qt.base_widget import BaseWidget

class ScrollArea(QScrollArea, BaseWidget):
    """
    Each frontend pages must inherit of ScrollArea or NuConfForm
    """
    def __init__(self):
        QScrollArea.__init__(self)
        BaseWidget.__init__(self)

    def writeError(self, err, title="ERROR"):
        """
        Write the error 'err' using the logging module (eg. stdout).
        Prefix the error message by title + ": ".

        Write also the backtrace with a lower log level (WARNING).
        """
        writeError(err, title)

    def onApplyFinished(self):
        pass

    def _reset_helper(self, component, service, qcfg, msg_success, msg_error):
        """
        Tries and fetches config info as specified in args.
        Displays messages according to success/failure.
        Returns boolean value for success/failure.
        """
        serialized = self._fetch_serialized(component, service)

        if serialized is not None:
            qcfg.setCfg(serialized)
            self.mainwindow.addNeutralMessage(msg_success)
            return True

        self.mainwindow.addCriticalMessage(msg_error)
        return False

    def _fetch_serialized(self, component, service):
        """
        Returns None in case of failure
        """
        try:
            #can return None in case of problem
            return self.mainwindow.init_call(component, service)
        except RpcdError:
            return None


