#coding: utf-8

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


from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.client import tr
from ufwi_conf.client.restart_eas import restart_eas

def restoration_restart(parent):
    """
    Parent: a QWidget or None.
    A QApplication must exist
    """
    title = tr("EAS restarts to complete the restoration process")
    message = tr("<h2>Now restarting Edenwall Administration Suite.</h2>\n"
    "After reconnecting to the EdenWall appliance, you may edit its "
    "configuration in the 'System' and 'Services' tabs, then click on the "
    "'Apply' button. You will also have to select a set of firewall rules in "
    "the 'Firewall' tab.")

    icon = QPixmap(":icons/chrono")
    msgbox = QMessageBox(
        QMessageBox.Information,
        title,
        message,
        QMessageBox.Ok,
        parent,
    )
    msgbox.setIconPixmap(icon)

    msgbox.exec_()

    restart_eas()

