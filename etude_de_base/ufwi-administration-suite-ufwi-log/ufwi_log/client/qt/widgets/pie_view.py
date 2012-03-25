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

from PyQt4.QtGui import QFontMetrics, QRegion, QPainterPath, QPen, QPalette, QColor, QBrush, QRadialGradient
from PyQt4.QtCore import QModelIndex, QRect, Qt
from math import acos, cos, sin, ceil
from graph_view import GraphView

M_PI = 3.1415927
LEGEND_WIDTH = 175
RESIZE_INCREMENT = 50

class PieView(GraphView):

    def __init__(self, parent=None):
        GraphView.__init__(self, parent)
        self.margin = 8
        self.totalSize = 200
        self.pieSize = self.totalSize - 2*self.margin
        self.selectionRect = QRect()

    def indexAt(self, point):
        if self.validItems == 0 or not self.model():
            return QModelIndex()

        if point.x() < self.totalSize:
            cx = point.x() - self.totalSize/2
            cy = self.totalSize/2 - point.y()

            d = pow(pow(cx, 2) + pow(cy, 2), 0.5)

            if d == 0 or d > self.pieSize/2:
                return QModelIndex()

            angle = (180 / M_PI) * acos(cx/d)
            if cy < 0:
                angle = 360 - angle

            startAngle = 0.0

            for row in xrange(self.model().rowCount(self.rootIndex())):

                index = self.model().index(row, 1, self.rootIndex())
                value = self.model().data(index).toDouble()[0]

                if value > 0.0 and self.totalValue > 0.0:
                    sliceAngle = 360*value/self.totalValue

                    if angle >= startAngle and angle < (startAngle + sliceAngle):
                        return self.model().index(row, 1, self.rootIndex())

                    startAngle += sliceAngle

        else:
            itemHeight = QFontMetrics(self.viewOptions().font).height()
            listItem = int((point.y() - self.margin) / itemHeight)
            validRow = 0

            for row in xrange(self.model().rowCount(self.rootIndex())):

                index = self.model().index(row, 1, self.rootIndex())

                if self.model().data(index).toDouble()[0] > 0.0:
                    if listItem == validRow:
                        return self.model().index(row, 1, self.rootIndex())

                    validRow += 1

        return QModelIndex()

#    def itemRect(self, index):
#        if not index.isValid():
#            return QRect()
#
#        if index.column() != 1:
#            valueIndex = self.model().index(index.row(), 1, self.rootIndex())
#        else:
#            valueIndex = index
#
#        if self.model().data(valueIndex).toDouble()[0] > 0.0:
#
#            listItem = 0
#            row = index.row() - 1
#            while row >= 0:
#                if self.model().data(self.model().index(row, 1, self.rootIndex())).toDouble()[0] > 0.0:
#                    listItem += 1
#                row -= 1
#
#            itemHeight = 0.0
#
#            if index.column() == 0:
#                itemHeight = QFontMetrics(self.viewOptions().font).height()
#
#                return QRect(self.totalSize,
#                             int(self.margin + listItem * itemHeight),
#                             self.margin + LEGEND_WIDTH,
#                             int(itemHeight))
#            elif index.column() == 1:
#                return self.viewport().rect()
#
#        return QRect()

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
                                    self.margin+self.pieSize,
                                    self.margin+self.pieSize,
                                    startAngle, angle)
                    slicePath.closeSubpath()
                    return QRegion(slicePath.toFillPolygon().toPolygon())

                startAngle += angle

        return QRegion()

    def paint(self, painter, rect, widget_size, draw_highlight):
        if not self.model() or not self.totalValue:
            return
        selections = self.selectionModel()
        option = self.viewOptions()

        background = option.palette.base()
        foreground = QPen(option.palette.color(QPalette.Foreground))

        painter.fillRect(rect, background)
        painter.setPen(foreground)

        if widget_size == self.viewport().rect():
            # We are drawing on screen
            legend_width = LEGEND_WIDTH
            totalSize = self.totalSize
        else:
            # TODO: factorize with resizeEvent
            # We are drawing on printer
            fm = QFontMetrics(painter.font())
            legend_width = fm.width("0000:0000:0000:0000:0000:0000:0000:0000") # Let's use an ipv6 as the legend size reference
            if widget_size.width() - legend_width < widget_size.height():
                totalSize = widget_size.width()
            else:
                totalSize = widget_size.height() + legend_width

            if totalSize < legend_width * 2:
                totalSize = legend_width * 2
            totalSize -= legend_width

        pieSize = totalSize - 2*self.margin

        if self.validItems > 0:
            painter.save()
            painter.drawEllipse(self.margin, self.margin, pieSize, pieSize)

            startAngle = 0.0
            class MyPoint:
                def __init__(self, x = 0, y = 0):
                    self.x = x
                    self.y = y
            def to_rad(x):
                return x / 180.0 * M_PI

            pies_pos = {}

            keyNumber = 0
            # Draw all parts of pie
            for row in xrange(self.model().rowCount(self.rootIndex())):

                index = self.model().index(row, 1, self.rootIndex())
                value = self.model().data(index).toDouble()[0]

                if value > 0.0:
                    angle = 360*value/self.totalValue

                    colorIndex = self.model().index(row, 0, self.rootIndex())
                    color = QColor(self.model().data(colorIndex, Qt.DecorationRole).toString())

                    if self.highlight and index.row() == self.highlight.row():
                        color = color.light(120)

                    # Create the gradient effect
                    grad = QRadialGradient(0.0, 0.0, pieSize / 2.0 + 10.0)
                    grad.setColorAt(1.0, Qt.black)
                    grad.setColorAt(0.85, color)
                    grad.setColorAt(0.0, color)

                    painter.setBrush(QBrush(grad))
                    painter.setBrushOrigin(totalSize / 2, totalSize / 2)

                    painter.drawPie(self.margin, self.margin, pieSize, pieSize, int(startAngle*16), int(angle*16))
                    point_angle = (startAngle + (angle / 2.0))
                    pies_pos[keyNumber] = MyPoint(self.margin + (pieSize / 2.0) * (1.0 + 0.66 * cos(to_rad(point_angle))),
                                                  self.margin + (pieSize / 2.0) * (1.0 - 0.66 * sin(to_rad(point_angle))))

                    startAngle += angle
                    keyNumber += 1

            # Todo: factorize-me
            if draw_highlight:
                keyNumber = 0
                for row in xrange(self.model().rowCount(self.rootIndex())):
                    index = self.model().index(row, 1, self.rootIndex())
                    value = self.model().data(index).toDouble()[0]

                    if keyNumber >= len(pies_pos):
                        break

                    if value > 0.0:
                        if self.highlight and index.row() == self.highlight.row():
                            itemHeight = QFontMetrics(painter.font()).height()

                            x0 = pies_pos[keyNumber].x
                            y0 = pies_pos[keyNumber].y

                            x2 = totalSize + itemHeight
                            y2 = self.margin + (keyNumber +0.5) * itemHeight

                            y1 = y2
                            if y0 > y1:
                                x1 = x0 + (y0 - y1) / 2
                            else:
                                x1 = x0 + (y1 - y0) / 2

                            painter.drawLine(x0, y0, x1, y1)
                            painter.drawLine(x1, y1, x2, y2)
                        keyNumber += 1

            # Draw the legend
            keyNumber = 0
            for row in xrange(self.model().rowCount(self.rootIndex())):

                index = self.model().index(row, 1, self.rootIndex())
                value = self.model().data(index).toDouble()[0]

                if value > 0.0:

                    labelIndex = self.model().index(row, 0, self.rootIndex())
                    color = QColor(labelIndex.data(Qt.DecorationRole).toString())
                    txt = unicode(labelIndex.data().toString())

                    painter.setBrush(color)
                    itemHeight = QFontMetrics(painter.font()).height()
                    x = totalSize + itemHeight
                    y = self.margin + keyNumber * itemHeight
                    painter.drawRect(x, y, itemHeight, itemHeight)
                    painter.drawText(QRect(x + 1.5 * itemHeight, y, legend_width - 2 * itemHeight, itemHeight), Qt.AlignLeft|Qt.AlignVCenter, txt)

                    keyNumber += 1

            painter.restore()

    def resizeEvent(self, event):
        if self.viewport().width()  - LEGEND_WIDTH < self.viewport().height():
            self.totalSize = ceil(self.viewport().width() / RESIZE_INCREMENT) * RESIZE_INCREMENT
        else:
            self.totalSize = ceil(self.viewport().height() /RESIZE_INCREMENT) * RESIZE_INCREMENT + LEGEND_WIDTH

        if self.totalSize < LEGEND_WIDTH * 2:
            self.totalSize = LEGEND_WIDTH * 2
        self.totalSize -= LEGEND_WIDTH
        self.pieSize = self.totalSize - 2*self.margin

