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

from PyQt4.QtGui import QFontMetrics, QRegion, QPainterPath, QPen, QPalette, QColor, QBrush, QLinearGradient
from PyQt4.QtCore import QModelIndex, QPointF, Qt, QRect
from math import floor
from graphxy_view import GraphXYView

TITLE_AREA = 0.2 # Ratio of the area where the title of the column is printed
COLUMN_SPACE_RATIO = 0.66 # Ratio of the size of one column and the size of the space between 2 columns
RESIZE_INCREMENT = 50

class HistogramView(GraphXYView):

    def __init__(self, parent=None):
        GraphXYView.__init__(self, parent)
        self.horizontalScrollBar().setRange(0, 0)
        self.verticalScrollBar().setRange(0, 0)

        self.selectionRect = QRect()
        self.left_margin = 0
        self.top_margin = 0
        self.width = 0

    def updateDimensions(self, widget_size):

        if not self.fm:
            return

        # Value max in the dataset (in packetis count)
        self.value_max = float(self.getValueMax())

        # Size of widget when taking account the step by step resizing (in pixels)
        self.step_width = floor(widget_size.width() / RESIZE_INCREMENT) * RESIZE_INCREMENT
        self.step_height = floor(widget_size.height() / RESIZE_INCREMENT) * RESIZE_INCREMENT
        ## To disable step by step resizing:
        #self.step_width = widget_size.width()
        #self.step_height = widget_size.height()

        # Additional offset to the X axis to let some place to display the Y axis legend (in pixels)
        self.x_axe_off = self.fm.width("0") * 5

        # Size of the blank margin that surround the graph (in pixels)
        self.margin_size = self.fm.width("0")

        # Size of the margin from the border of the widget to the axis (in pixels)
        self.left_margin = (widget_size.width() - self.step_width) / 2.0 + self.margin_size + self.x_axe_off
        self.top_margin = (widget_size.height() - self.step_height) / 2.0 + self.margin_size

        # Size of the "graphable" part of the widget (in pixels)
        self.width_max = self.step_width - (2 * self.margin_size) - self.x_axe_off
        self.height_max = (self.step_height * (1.0 - TITLE_AREA)) - 2 * self.margin_size

        # Width of one bar (in pixels)
        self.width = self.width_max / (self.model().rowCount(self.rootIndex())+1)

    def indexAt(self, point):
        if self.validItems == 0 or not self.model() or not self.data or not self.width or not self.value_max:
            return QModelIndex()

        self.updateDimensions(self.viewport().rect())
        # Check we're between 2 columns
        cx = ((float(point.x()) - self.left_margin) / self.width) - 0.5
        if cx > floor(cx) + COLUMN_SPACE_RATIO:
            return QModelIndex()

        cx = int(floor(cx))
        index = self.model().index(cx, 1, self.rootIndex())
        value = self.model().data(index).toDouble()[0]
        if point.y() < self.height_max - (self.height_max * value/self.value_max) + self.top_margin:
            return QModelIndex()
        if point.y() > self.height_max + self.top_margin:
            return QModelIndex()

        return self.model().index(cx, 1, self.rootIndex())

    def itemRegion(self, index):
        if not index.isValid() or not self.model():
            return QRegion()

        if index.column != 1:
            return self.itemRect(index)

        if self.model().data(index).toDouble()[0] <= 0.0:
            return QRegion()

        startAngle = 0.0
        for row in xrange(self.model().rowCount(self.rootIndex())):

            sliceIndex = self.model().index(row, 1, self.rootIndex())
            value = self.model().data(sliceIndex).toDouble()[0]

            if value > 0.0:
                angle = 360*value/self.totalValue

                if sliceIndex == index:
                    slicePath = QPainterPath()
                    slicePath.moveTo(self.totalSize/2, self.totalSize/2)
                    slicePath.arcTo(self.margin, self.margin,
                                    self.margin+self.histogramSize,
                                    self.margin+self.histogramSize,
                                    startAngle, angle)
                    slicePath.closeSubpath()
                    return QRegion(slicePath.toFillPolygon().toPolygon())

                startAngle += angle

        return QRegion()

    def paint(self, painter, rect, widget_size, draw_highlight):
        GraphXYView.paint(self, painter, rect, widget_size, draw_highlight)
        self.fm = QFontMetrics(painter.font())
        self.updateDimensions(widget_size)
        option = self.viewOptions()

        background = option.palette.base()
        foreground = QPen(option.palette.color(QPalette.Foreground))
        painter.save()

        # Offset to cerrectly center the graph after the resizing due to the step by step increment
        painter.translate(self.left_margin, self.top_margin)

        painter.setPen(foreground)

        if self.validItems > 0:
            # Draw histograms
            if self.model().rowCount(self.rootIndex()) != 0 and self.value_max != 0:
                value_max = self.value_max
            else:
                value_max = 10

            keyNumber = 0
            for row in xrange(self.model().rowCount(self.rootIndex())):

                index = self.model().index(row, 1, self.rootIndex())
                value = self.model().data(index).toDouble()[0]

                if value >= 0.0:
                    height = self.height_max * value / value_max

                    color = QColor("#a2ca60")

                    if draw_highlight and self.highlight and index.row() == self.highlight.row():
                        color = color.dark(120)

                    painter.setBrush(QBrush(color))

                    painter.drawRect((keyNumber+0.5) * self.width, self.height_max - height, COLUMN_SPACE_RATIO * self.width, height)

                    # Legend drawing:
                    painter.translate((keyNumber+0.75) * self.width, self.height_max)
                    painter.rotate(-45.0)
                    text =  self.model().data(self.model().index(index.row(), 0, self.rootIndex()), Qt.EditRole).toString()

                    txt_width = self.fm.width(text)
                    painter.drawText(QRect(-txt_width, 0, txt_width, self.width), Qt.AlignRight, text)
                    painter.rotate(45.0)
                    painter.translate(-((keyNumber+0.75) * self.width), -self.height_max)

                    keyNumber += 1

        painter.translate(-self.left_margin, -self.top_margin)
        painter.restore()

