# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
           Laurent Defert <lds AT inl.fr>

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

$Id$
"""
from math import floor

from PyQt4.QtGui import QFontMetrics, QPen, QPalette, QColor
from PyQt4.QtCore import Qt, QRect

from ufwi_rpcd.common.human import humanFilesize

from graph_view import GraphView

TITLE_AREA = 0.2 # Ratio of the area where the title of the column is printed
COLUMN_SPACE_RATIO = 0.66 # Ratio of the size of one column and the size of the space between 2 columns
RESIZE_INCREMENT = 50

class GraphXYView(GraphView):

    def __init__(self, parent=None):
        GraphView.__init__(self, parent)
        self.horizontalScrollBar().setRange(0, 0)
        self.verticalScrollBar().setRange(0, 0)

        self.margin = 8
        self.totalSize = 200
        self.histogramSize = self.totalSize - 2*self.margin
        self.selectionRect = QRect()
        self.is_value = False

#    def itemRect(self, index):
#        return QRect()

    def paint(self, painter, rect, widget_size, draw_highlight):
        if not self.model():
            return

        option = self.viewOptions()

        background = option.palette.base()
        foreground = QPen(option.palette.color(QPalette.Foreground))
        painter.save()
        painter.fillRect(rect, background)

        # Handle step by step size increment
        step_width = floor(widget_size.width() / RESIZE_INCREMENT) * RESIZE_INCREMENT
        step_height = floor(widget_size.height() / RESIZE_INCREMENT) * RESIZE_INCREMENT

        # Offset to correctly center the graph after the resizing due to the step by step increment
        painter.translate((widget_size.width() - step_width) / 2.0, (widget_size.height() - step_height) / 2.0)

        painter.setPen(foreground)
        fm = QFontMetrics(painter.font())
        margin_size = fm.width("0")

        # Find the highest column
        if self.model().rowCount(self.rootIndex()) > 1:
            value_max = self.getValueMax()
        else:
            value_max = 0

        # If there is no data yet, or the max is at 0, use a max of 10 to display an axe
        if value_max == 0:
            value_max = 10
        else:
            if not self.is_value:
                self.is_value = True
        if self.fetcher.fragment.type == 'TrafficStream':
            x_axe_off = fm.width(unicode(value_max * 2000))
        else:
            x_axe_off = fm.width(unicode(value_max * 200))

        # If there is no data yet, or the max is at 0, use a max of 10 to display an axe
        if self.fetcher.fragment.type == 'LoadStream':
            if value_max < 100:
                value_max = 100

        else:
            if value_max == 0:
                value_max = 10

        width_max =  step_width - (2 * margin_size) - x_axe_off
        height_max = (step_height * (1.0 - TITLE_AREA)) - 2 * margin_size
        width = width_max / (self.model().rowCount(self.rootIndex())+1)

        if height_max < 0 or width_max < 0:
            painter.restore()
            return

        # Draw the horizontal axe
        painter.drawLine(margin_size + x_axe_off, height_max + margin_size, step_width - margin_size, height_max + margin_size)

        # Draw the vertical axe
        painter.drawLine(margin_size  + x_axe_off, margin_size, margin_size + x_axe_off, height_max + margin_size)

        # Graduations
        nbr_grad = value_max
        dgrad = 1
        dy = float(dgrad) * height_max / value_max # pixel count between 2 graduations

        while fm.height() > dy:
            nbr_grad = floor(nbr_grad / 10)
            dgrad = dgrad * 10
            dy = float(dgrad) * height_max / value_max

        # Try to fit graduations 5 by 5
        if fm.height() < dy / 2:
            nbr_grad = nbr_grad * 2
            dgrad = dgrad / 2
            dy = float(dgrad) * height_max / value_max

        # Prevent for infinite loops.
        if dgrad < 1:
            dgrad = 1

        dy = float(dgrad) * height_max / value_max
        text_dy = fm.height()
        i = 1
        while (i * dgrad) <= value_max:
            y = height_max - (dy * i) + margin_size
            grad_width = fm.width("0")
            painter.drawLine(margin_size + x_axe_off - grad_width, y, margin_size + x_axe_off, y)
            text = unicode(int(dgrad * i))

            if self.fetcher.fragment.type == 'LoadStream':
                text = unicode(float(dgrad * i) / 100)

            if self.fetcher.fragment.type == 'TrafficStream':
                if int(float(text)) > 0:
                    text = humanFilesize(float(text))
            elif self.fetcher.fragment.type == 'MemoryStream':
                if float(text) > 0:
                    text = humanFilesize(float(text) * 1024)

            if self.is_value:
                painter.drawText(QRect(0, y - text_dy / 2.0, margin_size + x_axe_off - 2 * grad_width, text_dy), Qt.AlignRight|Qt.AlignVCenter, text)
            else:
                painter.drawText(0, y + text_dy / 4.0, text)

            if i % 2:
                painter.setBrush(QColor(135, 135, 135, 64)) # Gray
                painter.setPen(QPen(QColor(0, 0, 0, 0)))
                painter.drawRect(margin_size + x_axe_off, y, width_max, dy)
                painter.setPen(QPen(option.palette.color(QPalette.Foreground)))
            i = i + 1

        if i == 1: # no graduation was drawn, draw the max
            y = margin_size
            grad_width = fm.width("0")
            painter.drawLine(margin_size + x_axe_off - grad_width, y, margin_size + x_axe_off, y)
            text = unicode(int(value_max))
            painter.drawText(QRect(0, y - text_dy / 2.0, margin_size + x_axe_off - 2 * grad_width, text_dy), Qt.AlignRight|Qt.AlignVCenter, text)

        painter.translate((step_width - widget_size.width()) / 2.0, (step_height - widget_size.height()) / 2.0)
        painter.restore()
