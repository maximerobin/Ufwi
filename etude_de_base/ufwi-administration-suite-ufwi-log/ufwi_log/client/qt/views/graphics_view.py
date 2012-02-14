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

$Id: histogram.py 13277 2009-10-09 10:28:24Z haypo $
"""

import math
from ufwi_log.client.qt.info_area import InfoArea
from PyQt4.QtGui import QGraphicsView, \
                        QPainter, \
                        QPen, \
                        QGraphicsRectItem, \
                        QGraphicsEllipseItem, \
                        QFontMetrics, \
                        QGraphicsLineItem, \
                        QFont, \
                        QGraphicsSimpleTextItem, \
                        QColor

from PyQt4.QtCore import QTimer, \
                         SIGNAL, \
                         QVariant, \
                         Qt, \
                         QLineF, \
                         QRectF

from .graph import GraphFragmentView
from .ufwi_log_base import PIECHART, BARCHART
from .graphics_scene import GraphicsScene
from .baritem import BarItem
from .pieitem import PieItem


TITLE_AREA = 0.2 # Ratio of the area where the title of the column is printed
COLUMN_SPACE_RATIO = 0.66 # Ratio of the size of one column and the size of the space between 2 columns
RESIZE_INCREMENT = 50

class GraphicsView(GraphFragmentView, QGraphicsView): #QGraphicsView

    INITIAL_SCALE = 0.05

    IN_ANIMATION = False
    UPDATE_ALL = False

    # Custom Item Data
    NO_ROTATION = 0
    ROTATION = 1

    def __init__(self, fetcher, parent=None): #, type=BARCHART):
        QGraphicsView.__init__(self, parent)
        GraphFragmentView.__init__(self, fetcher)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)

        self.my_model = None
        self.scene = GraphicsScene(self)
        self.setScene(self.scene)
        self.values = []
        self.labels = []
        self.formated_data = []
        self.current_max = 0
        self.sorted = True
        self.max_slices = 10
        self.min_slice_percent = 0

        self.fetcher = fetcher
#        self.update_all = False
        self.resized = False

        self.fm = QFontMetrics(QFont())
        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.setTransformationAnchor(QGraphicsView.AnchorViewCenter)

        self.timer = QTimer(self)
        self.connect(self.timer, SIGNAL("timeout()"), self.updateScene)
        self.setRenderHint(QPainter.Antialiasing)

        self.connect(self, SIGNAL("updateData_bis"), self._updateAll)

        self.info_area = InfoArea(self.parent())
        self.max_size_label = 0

        self.setResizeAnchor(QGraphicsView.AnchorViewCenter)
        self.is_result_filled = False
        self.count = 0

        self.setMouseTracking(True)
        self.animation_on = True

    def setModel(self, model):
        self.my_model = model

    def resizeEvent(self, event):
        # only update size of items

        if self.my_model and not self.is_closed:
            animation_on = self.animation_on
            self.animation_on = False
            self.redraw_scene()
            self.animation_on = animation_on
        QGraphicsView.resizeEvent(self, event)

    def timerStart(self):
        self.count = 0
        if self.chart_type == PIECHART:
            self.timer.start(50)
        elif self.chart_type == BARCHART:
            self.timer.start(30)

#    def startAnimation(self):
#        GraphicsView.IN_ANIMATION = True
#        GraphicsView.ALL_ANIMATION_DONE = False
#
#        self.timerStart()

    def redraw_scene(self, simultaneous=False):
        self.scene.clear()
        self.setUpdatesEnabled(False)

        # build objects
        if self.chart_type == BARCHART or self.chart_type == PIECHART:
            if self.current_max > 0 and self.values:
                if self.chart_type == BARCHART:
                    self.build_object_axes(self.formated_data)
                    self.build_objects_barchart(self.formated_data, self.order)
                elif self.chart_type == PIECHART:
                    self.build_objects_piechart(self.formated_data, self.order)
                    self.build_object_legend()

        if not GraphicsView.IN_ANIMATION or simultaneous:
            if self.animation_on:
                GraphicsView.IN_ANIMATION = True
                self.timerStart()
            else:
                self.setUpdatesEnabled(True)
        else:
            self.emit(SIGNAL('replayAnimation'), self.uuid)

        self.emit(SIGNAL("showButtons"))

    def _updateAll(self):
        labels = [ ]
        values = [ ]
        self.order = []

        updated = False

        if not self.my_model:
            return

        for row in range(self.my_model.rowCount()):
            label = self.my_model.data(self.my_model.index(row, 0))
            label = label.toString()
            labels.append(label)
            value = self.my_model.data(self.my_model.index(row, 1))
            value = value.toDouble()[0]
            values.append(value)
            self.order.append(label)

        if not len(values) > 0:
            self.emit(SIGNAL("showButtons"))
            return

        updated = True
#        total_height = self.height()

        # build sorted list of (label,value)
        data = []
        for idx in range(0, len(values)):
            data.append([labels[idx], values[idx]])

        # create a palette of brushes for n objects
        self.create_brushes(len(values))

        self.values = values
        self.labels = labels
        self.formated_data = data
        self.current_max = max(values)
        self.current_sum = sum(values)

        # build objects
        if self.ready:
            self.redraw_scene()

        return updated

    def show(self):
        if self.animation_on:
            self.timerStart()
        else:
            self.setUpdatesEnabled(True)

    def updateData(self, result):
        if self.is_closed:
            return

        self.my_model = None
        self.scene.clear()

        if GraphFragmentView.updateData(self, result):
            self.scene.clear()
            return self._updateAll()
        else:
            self.emit(SIGNAL("showButtons"))

    def build_objects_barchart(self, data, order):
        total_width = self.width()
        bar_width = (total_width / 15)
        total_height = self.height()
        bar_max_height = total_height * 0.75
        y_scale_factor = -1 * (bar_max_height / self.current_max)

        pen = QPen()
        x_offset = 0
        cpt = 0
        sum = 0

        #values.sort(reverse=True)
        for dat in data:
            (label, value) = dat

            rect = QRectF(x_offset, 0, bar_width, value * y_scale_factor)
            bar = BarItem(rect)

            if label in order:
                pos = order.index(label)
            else:
                pos = len(order) + 1

            bar.pos = pos
            bar.pen = pen
            bar.color = self.brushes[cpt]
            bar.value = value
            bar.label = label

            self.scene.addItem(bar)
            text = self.scene.addSimpleText("%s" % label)
            text.setData(self.ROTATION, QVariant(self.ROTATION))
            text.rotate(-45)
            text.moveBy(x_offset + (bar_width - text.boundingRect().width()) / 1.3, math.cos(45) * text.boundingRect().width() + 20)

            x_offset += (bar_width * 1.5)
            sum += value
            cpt += 1
            if (self.max_slices and cpt >= self.max_slices):
                break

    def build_objects_piechart(self, data, order):
        pen = QPen()
        total_height = self.height()
        ellipse_radius = (total_height * 0.75)
        max_color = len(self.brushes)

        cpt = 0
        sum = 0

        for dat in data:
            (label, value) = dat
            start_angle = sum
            span = (value * 360 / self.current_sum)

            rect = QRectF(0, -ellipse_radius, ellipse_radius, ellipse_radius)
            ellipse = PieItem(rect, PIECHART)

            ellipse.setStartAngle(start_angle)
            ellipse.setSpanAngle(span)
            ellipse.setPen(pen)
            ellipse.setColor(self.brushes[cpt % max_color])
            ellipse.pos = order.index(label)
            ellipse.value = value
            ellipse.label = label

            sum += span
            cpt += 1
            self.scene.addItem(ellipse)
#            if (self.max_slices and cpt >= self.max_slices):
#                break


    def build_object_legend(self):
        # add legend
        ellipse_radius = (self.height() * 0.75)
        legend = QGraphicsRectItem(ellipse_radius + 30, 5, 150, -ellipse_radius - 5)
        legend.setData(self.scene.SELECTABLE, QVariant(self.scene.UNSELECTABLE))

        r1 = legend.mapToScene(legend.boundingRect())
        bottomLeft = r1[0]
        topRight = r1[2]

        x_start = bottomLeft.x()
        y_start = topRight.y()
        y_offset = y_start + 15
        cpt = 0

        for index, item in enumerate(self.scene.items()):
            if isinstance(item, QGraphicsEllipseItem):
                label = item.label
                value = item.value
                # XXX 15 is approximatively the height of the text
                # we should determine it
#                if y_offset + 15 > bottomLeft.y():
#                    break

                rect = self.scene.addRect(x_start + 10, y_offset, 10, 10)
                rect.setData(self.scene.SELECTABLE, QVariant(self.scene.UNSELECTABLE))
                rect.setBrush(item.getColor())
                text = self.scene.addSimpleText("%s: %.2f (%.1f %%)" % (label, value, (value * 100 / self.current_sum),), QFont())
                text.setData(self.ROTATION, QVariant(self.NO_ROTATION))
                text.moveBy(x_start + 23, y_offset - 5)
                # automatically resize border to legend
                if text.boundingRect().width() + 25 > legend.boundingRect().width():
                    legend.setRect(bottomLeft.x(), bottomLeft.y(), text.boundingRect().width() + 25, legend.boundingRect().height())
                y_offset += 15
                cpt += 1
        self.scene.addItem(legend)


    def build_object_axes(self, data):
#        if not self.my_model:
#            return
#
        x_width = 5
        if len(data) > 5:
            if len(data) > 10:
                x_width = 10
            else:
                x_width = len(data)

        self.max_size_label = 0
        width = int(self.width() / 10 * x_width)
        xAxe = QGraphicsLineItem(0, 0, width, 0)
        self.scene.addItem(xAxe)

        y_label_height = int(self.height() * 0.75)
        y_axe_height = y_label_height + 10
        yAxe = QGraphicsLineItem(0, 0, 0, -y_axe_height)
        self.scene.addItem(yAxe)

        # Draw arrows for x axe
        line1 = QLineF(width, 0, width - 5, 5)
        line2 = QLineF(width, 0, width - 5, -5)

        self.scene.addLine(line1)
        self.scene.addLine(line2)


        y_max = self.current_max
        # Upper ten or so
#        y_max = int(y_max + (5 - (y_max % 2)))

        y_label = self.scene.addSimpleText("%s" % int(y_max))
        y_label.setData(self.ROTATION, QVariant(self.NO_ROTATION))
        y_label.moveBy(-y_label.boundingRect().width() - 5, -y_label_height - y_label.boundingRect().width() / 2)

        # Used to fit in the view
        if y_label.boundingRect().width() > self.max_size_label:
            self.max_size_label = y_label.boundingRect().width()

        y_label2 = self.scene.addSimpleText("%s" % int(y_max / 2))
        y_label2.setData(self.ROTATION, QVariant(self.NO_ROTATION))
        y_label2.moveBy(-y_label2.boundingRect().width() - 5, -(y_label_height + y_label.boundingRect().width() / 2) / 2)

        # Decoration on axes
        for cpt in [0, 2]:
            rect = QGraphicsRectItem(0, 0 - cpt * y_axe_height / 4, width, -y_axe_height / 4)
            rect.setData(self.scene.SELECTABLE, QVariant(self.scene.UNSELECTABLE))
            # Items in back
            rect.setZValue(-1)
            rect.setBrush(QColor(135, 135, 135, 64))
            rect.setPen(QPen(QColor(0, 0, 0, 0)))
            self.scene.addItem(rect)

    def sizeHint(self):
        size = QGraphicsView.sizeHint(self)
        MIN_WIDTH = 100
        MIN_HEIGHT = 100
        if size.width() < MIN_WIDTH:
            size.setWidth(MIN_WIDTH)
        if size.height() < MIN_HEIGHT:
            size.setHeight(MIN_HEIGHT)
        return size

    def makeColors(self):
        colors = []
        for row in range(0, 10):
            color = QColor(102, row * 25, row * 25)
            colors.append(color)
        return colors

    def create_brushes(self, nb_el):
        self.brushes = []
        self.colors = GraphFragmentView.colours

        cpt = 0
        for color in self.colors:
            self.brushes.append(QColor(color))
            cpt += 1
            if nb_el == cpt:
                break

    def updateScene(self):
        if not self.is_closed:
            self.setUpdatesEnabled(True)

            self.count += 1
            # finished ? stop animation
            if self.count >= 20:
                for item in self.scene.items():
                    if isinstance(item, QGraphicsRectItem) or isinstance(item, QGraphicsEllipseItem):
                        item.resetTransform()
                self.timer.stop()
                self._animation_done()
            else:
            #update all objects
                for item in self.scene.items():
                    if isinstance(item, QGraphicsRectItem) or isinstance(item, QGraphicsLineItem):
                        item.resetTransform()
                        item.scale(1, self.count * self.INITIAL_SCALE)
                    elif isinstance(item, PieItem):
                        current_step = (self.count + 1) * (360 / 20)
                        if (current_step >= item.startAngle):
                            item.setVisible(True)
                            if current_step > item.startAngle + item.spanAngle:
                                QGraphicsEllipseItem.setSpanAngle(item, item.spanAngle * 16)
                            else:
                                QGraphicsEllipseItem.setSpanAngle(item, 16 * (current_step - item.startAngle))
                        else:
                            item.setVisible(False)
                    elif isinstance(item, QGraphicsSimpleTextItem):
                        item.resetTransform()
                        if int(item.data(self.ROTATION).toString()) != self.NO_ROTATION:
                            item.rotate(-45)
        else:
            self.timer.stop()

    def _animation_done(self):
        GraphicsView.IN_ANIMATION = False

        self.emit(SIGNAL("showButtons"))

        if GraphicsView.UPDATE_ALL:
            self.emit(SIGNAL("animation_done(QString)"), self.uuid)


    def getValueMax(self, col=1):
        # Find the highest column
        if not self.formated_data:
            return 0
        value_max = int(self.formated_data[0][col])
        for row in range(len(self.formated_data)):
            val = int(self.formated_data[row][col])
            if val > value_max:
                value_max = val
        return value_max


    def wheelEvent(self, event):
        pos = self.mapToScene(event.pos())
        self.centerOn(pos)
        scale = 1.2

        if event.delta() < 0:
            x = y = 1 / 1.2
        else:
            x = y = 1.2
            scale *= -1
        self.scene.setTextSize(self.scene.getTextSize() + scale)
        self.scale(x, y)
