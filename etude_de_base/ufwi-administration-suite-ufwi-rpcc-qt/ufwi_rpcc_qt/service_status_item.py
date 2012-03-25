#encoding: utf-8 -*-

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


from PyQt4.QtGui import QFrame, QLabel, QHBoxLayout, QPixmap, QColor, QPalette
from PyQt4.QtCore import QSize
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.common.i18n import tr
from time import ctime

_TOOLTIP = tr(
    'Service "%(SERVICE)s" is %(STATUS)s<br/>(checked at %(TIMESTAMP)s)'
    )

class ServiceStatusItem(QFrame):
    """
    A small frame with borders, displaying a service name and an icon
    supported statuses: StatusValues.monitor_status
    """

    #'Static' class data is stored here
    pix_n_colors = None
    __PIXMAP, __PALETTE, __MSG = range(3)

    def __init__(self, name, on_off, parent):

        QFrame.__init__(self, parent)

        if ServiceStatusItem.pix_n_colors is None:
            self._staticDataInit()

        self.name = name
        self.value = "initial value"

        self._cfg()

        self.labels = QLabel(), QLabel()
        self.labels[1].setContentsMargins(0,0,0,0)
        self.update(on_off)

        layout = QHBoxLayout(self)
        for label in self.labels:
            layout.addWidget(label)

    def _cfg(self):
        self.setFrameStyle(QFrame.StyledPanel | QFrame.Sunken)
        self.setAutoFillBackground( True )

    def __repr__(self):
        return "%s(%s: %s)" % (self.__class__.__name__, self.name, self.value)

    def update(self, value):
        if value != self.value:
            display_data = ServiceStatusItem.pix_n_colors[value]
            self.labels[1].setPixmap(display_data[ServiceStatusItem.__PIXMAP])
            if value == ServiceStatusValues.NOT_LOADED:
                self.labels[0].setText('<i>%s</i>' % self.name)
            elif value == ServiceStatusValues.STOPPED:
                self.labels[0].setText('<h4>%s</h4>' % self.name)
            else:
                self.labels[0].setText(self.name)

            self.setPalette(display_data[ServiceStatusItem.__PALETTE])
            values = {
                'SERVICE': self.name,
                'STATUS': display_data[ServiceStatusItem.__MSG],
                'TIMESTAMP': ctime()
                }
            self.setToolTip(_TOOLTIP % values)

    def _staticDataInit(self):
        u"""
        Class initialization: building pixmaps, palettes… only once.
        """

        normalpalette = QPalette(self.palette())

        redpalette = QPalette( normalpalette )
        redpalette.setColor( QPalette.Base, QColor("#FF9D9F") )

        greenpalette = QPalette(normalpalette)
        greenpalette.setColor(QPalette.Base, QColor("#B0FF86") )
        size = QSize(16, 16)

        ServiceStatusItem.pix_n_colors = {
            ServiceStatusValues.RUNNING: (
                QPixmap(":/icons/status_on").scaled(size),
                greenpalette,
                '<b><font color="green">%s</font></b>.' % 'running'),
            ServiceStatusValues.STOPPED: (
                QPixmap(":/icons/status_off").scaled(size),
                redpalette,
                '<b><font color="red">%s</font></b>.' % 'stopped'),
            ServiceStatusValues.NOT_LOADED: (
                QPixmap(":/icons/status_na").scaled(size),
                normalpalette,
                '<b>%s</b>.' % 'not loaded'),
            ServiceStatusValues.POLLING: (
                QPixmap(":/icons/status_refresh"),
                normalpalette,
                '%s.' % 'polling')
        }

