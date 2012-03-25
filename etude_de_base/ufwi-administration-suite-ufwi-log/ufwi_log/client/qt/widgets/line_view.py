# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
           Laurent Defert <lds AT inl.fr>
           Eric Leblond <eric@inl.fr>

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

from PyQt4.QtGui import QFontMetrics, QRegion, QPainterPath, QPen, QPalette, QColor, QBrush, QLinearGradient, QPolygon
from PyQt4.QtCore import QString, QModelIndex, QPointF, Qt, QRect, QRectF
from math import floor, sin

from ufwi_rpcd.common.odict import odict

from graphxy_view import GraphXYView

margin_size = 16
TITLE_AREA = 0.2 # Ratio of the area where the title of the column is printed
COLUMN_SPACE_RATIO = 0.66 # Ratio of the size of one column and the size of the space between 2 columns
RESIZE_INCREMENT = 50

class LineView(GraphXYView):

    def __init__(self, parent=None):
        GraphXYView.__init__(self, parent)
        self.horizontalScrollBar().setRange(0, 0)
        self.verticalScrollBar().setRange(0, 0)

        self.selectionRect = QRect()

    def indexAt(self, point):
        if self.validItems == 0 or not self.model():
            return QModelIndex()

        return QModelIndex()

    def itemRegion(self, index):

        if not index.isValid() or not self.model():
            return QRegion()
        return QRegion()

        # TODO: what to do with this code?

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
        smooth = 2.5 # this is invert smoothing, increase it to sharpen graph

        if not self.model():
            return

        option = self.viewOptions()

        background = option.palette.base()
        foreground = QPen(option.palette.color(QPalette.Foreground))

        # Handle step by step size increment
        step_width = floor(widget_size.width() / RESIZE_INCREMENT) * RESIZE_INCREMENT
        step_height = floor(widget_size.height() / RESIZE_INCREMENT) * RESIZE_INCREMENT

        if self.model().rowCount(self.rootIndex()) != 0:
            value_max = self.getValueMaxAll()
        else:
            value_max = 0

        # If there is no data yet, or the max is at 0, use a max of 10 to dispaly an axe
        if self.fetcher.fragment.type == 'LoadStream':
            if value_max < 100:
                value_max = 100
        else:
            if value_max == 0:
                value_max = 10

        if len(self.data) != 0:
            xmin = self.getValueMin(0)
            xmax = self.getValueMax(0)
        else:
            return

        if xmin == xmax:
            return # avoid division by 0

        painter.save()

        # Offset to cerrectly center the graph after the resizing due to the step by step increment
        painter.translate((widget_size.width() - step_width) / 2.0, (widget_size.height() - step_height) / 2.0)

        painter.setPen(foreground)

        # Draw lines
        fm = QFontMetrics(painter.font())
        margin_size = fm.width("0")

        if self.fetcher.fragment.type == 'TrafficStream':
            x_axe_off = fm.width(unicode(value_max * 2000))
        else:
            x_axe_off = fm.width(unicode(value_max * 200))

        # Order them by max mean value
        means = {}
        for col in xrange(1, len(self.data[0])):
            means[col] = self.getMeanValue(col)

        def mean_sorter(x, y):
            return cmp(y[1], x[1])

        means_sorted = means.items()
        means_sorted.sort(mean_sorter)

        def slope_by_index(points, index, sens):
            if index >= len(points):
                return 0
            if index == 0:
                return points[index].y() + (points[index+1].y()-points[index].y())/smooth
            if index == (len(points) - 1):
                return points[index].y() - (points[index].y()-points[index-1].y())/smooth
            vpoints = [ points[index-1].y(), points[index].y(), points[index+1].y()]
            if points[index].y() == max(vpoints):
                return points[index].y()
            if points[index].y() == min(vpoints):
                return points[index].y()
            if sens == 0:
                return points[index].y() + (points[index+1].y()-points[index].y())/smooth
                #return points[index].y() + (points[index+1].y() - points[index-1].y()) / (points[index+1].x()-points[index-1].x()) * (points[index+1].x() - points[index].x()) / smooth
            else:
                return points[index].y() - (points[index].y()-points[index-1].y())/smooth
                #return points[index].y() + (points[index+1].y() - points[index-1].y()) / (points[index+1].x()-points[index-1].x()) * (points[index-1].x() - points[index].x()) / smooth

        colors = odict()

        for _col in means_sorted:
            col = _col[0]
            path = QPainterPath()
            path.setFillRule(Qt.WindingFill)
            last_point = None
            height_max = 0.0
            width_max =  step_width - 2 * margin_size - x_axe_off
            height_max = (step_height * (1.0 - TITLE_AREA)) - 2 * margin_size

            points = []

            for row in xrange(len(self.data)):
                index = self.model().index(row, col, self.rootIndex())
                value = index.data().toInt()[0]
                x_value = int(self.data[row][0])
                #print "x=", x_value, "y=", value

                if value >= 0.0:
                    height = height_max * value/value_max

                    x = (float(x_value - xmin) / float(xmax - xmin)) * width_max
                    point = QPointF(x + margin_size + x_axe_off, height_max - height + margin_size)

                    points.append(point)

            for index, point in enumerate(points):
                # draw simple point
                painter.setBrush(QBrush(QColor(self.colours[col]).dark(200)))
                painter.drawEllipse(QRectF(point.x() - 2, point.y() - 2, 4, 4))
            # init drawing
                if index == 0:
                    path.moveTo(point)
                    continue

                px = points[index-1].x() + (points[index].x() - points[index-1].x()) / smooth
                py = slope_by_index(points, index-1, 0)
                c1 = QPointF(px, py)
                px = points[index].x() - ( points[index].x() - points[index-1].x() ) / smooth
                py = slope_by_index(points, index, 1)
                c2 = QPointF(px, py)

                path.cubicTo(c1, c2, point)

            last_point = points[len(points)-1]
            if last_point:
                txt = self.model().headerData(col, Qt.Horizontal).toString()
                txt_width = fm.width(txt)
                txt_height = fm.height()

                colors[txt] = QColor(self.colours[col])
                path.lineTo(QPointF(x + margin_size + x_axe_off, height_max + margin_size))
                path.lineTo(QPointF(margin_size + x_axe_off, height_max + margin_size))

            color = QColor(self.colours[col])
            color.setAlpha(200)

            ## Create the gradient effect
            grad = QLinearGradient(QPointF(0.0, 0.0), QPointF(0.0, height_max))
            grad.setColorAt(1.0, color.dark(150))
            grad.setColorAt(0.95, color)
            grad.setColorAt(0.05, color)
            grad.setColorAt(0.0, Qt.white)

            painter.setBrush(QBrush(grad))

            painter.drawPath(path)

        # Graduations
        nbr_grad = xmax - xmin
        dgrad = 1
        while nbr_grad > 10:
            nbr_grad = floor(nbr_grad / 10)
            dgrad = dgrad * 10

        if nbr_grad <= 2:
            dgrad = dgrad / 10
            nbr_grad = 10

        # Prevent for infinite loops.
        if dgrad < 1:
            dgrad = 1

        dx = (float(dgrad) / float(xmax-xmin)) * width_max
        text_dy = fm.height()

        i = 0
        while (i * dgrad) <= xmax - xmin:

            if self.fetcher.fragment.type != 'TrafficStream' or (self.fetcher.fragment.type == 'TrafficStream' and i % 4 == 0):
                grad_width = fm.width("0")
                painter.drawLine(margin_size + x_axe_off + (i*dx), height_max + margin_size, margin_size + x_axe_off + (i*dx), height_max + margin_size + grad_width)
                text = unicode(int(dgrad * i))

                # Legend drawing:
                painter.translate(margin_size + x_axe_off + (i*dx), height_max + margin_size + 2*grad_width)
                painter.rotate(-45.0)
                int_time = (i * dgrad) + xmin
                text = QString('%ds' % (xmax - int_time))

                txt_width = fm.width(text)
                painter.drawText(QRect(-txt_width, -dx, txt_width, 2*dx), Qt.AlignRight|Qt.AlignVCenter, text)
                painter.rotate(45.0)
                painter.translate(-(margin_size + x_axe_off + (i*dx)), -(height_max + margin_size + 2*grad_width))

            i = i + 1

        interval = 0
        height = height_max + margin_size + txt_width * sin(45) + 30
        for k, v in colors.iteritems():
            painter.setPen(v)
            legendRect = QRect(interval, height, 10, 10)
            painter.drawRect(legendRect)
            painter.fillRect(legendRect, QBrush(v))
            painter.setPen(foreground)
            txt_width = fm.width(k)
            txt_height = fm.height()
            painter.drawText(QRect(interval + 10, height, txt_width, txt_height), Qt.AlignRight|Qt.AlignVCenter, k)
            interval += 20 + txt_width

        painter.translate((step_width - widget_size.width()) / 2.0, (step_height - widget_size.height()) / 2.0)
        painter.restore()

