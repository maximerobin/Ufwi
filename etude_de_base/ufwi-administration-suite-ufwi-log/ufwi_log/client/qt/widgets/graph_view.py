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

from PyQt4.QtGui import QAbstractItemView, QFontMetrics, QPainter
from PyQt4.QtCore import QRect

class GraphView(QAbstractItemView):

    def __init__(self, parent=None):
        QAbstractItemView.__init__(self, parent)
        self.horizontalScrollBar().setRange(0, 0)
        self.verticalScrollBar().setRange(0, 0)

        self.validItems = 1
        self.totalValue = 0.0
        self.setMouseTracking(True)
        self.highlight = None
        self.old_highlight = None
        self.fm = None

    def dataUpdated(self):

        if not self.model():
            return

        self.validItems = 0
        self.totalValue = 0.0

        for row in xrange(self.model().rowCount(self.rootIndex())):

            index = self.model().index(row, 1, self.rootIndex())
            value = self.model().data(index).toDouble()[0]

            if value > 0.0:
                self.totalValue += value
                self.validItems += 1

        self.viewport().update()

    def isIndexHidden(self, index):
        return False

    def itemRect(self, index):
        return QRect()

    def moveCursor(self, cursorAction, modifiers):
        current = self.currentIndex()
        if cursorAction == QAbstractItemView.MoveLeft or \
           cursorAction == QAbstractItemView.MoveUp:
            if current.row() > 0:
                current = self.model().index(current.row() - 1, current.column(), self.rootIndex())
            else:
                current = self.model().index(0, current.column(), self.rootIndex())
        elif cursorAction == QAbstractItemView.MoveRight or \
             cursorAction == QAbstractItemView.MoveDown:
            if current.row() < self.rows(current) - 1:
                current = self.model().index(current.row() + 1, current.column(), self.rootIndex())
            else:
                current = self.model().index(current.row() - 1, current.column(), self.rootIndex())

        self.viewport().update()
        return current

    def getValueMax(self, col = 1):
        # Find the highest column
        if not self.data:
            return 0
        value_max = int(self.data[0][col])
        for row in range(len(self.data)):
            val = int(self.data[row][col])
            if val > value_max:
                value_max = val
        return value_max

    def getValueMaxAll(self):
        # Find the highest column
        value_max = int(self.data[0][1])
        for row in xrange(len(self.data)):
            for col in xrange(len(self.data[0])-1):
                val = int(self.data[row][col+1])
                if val > value_max:
                    value_max = val
        return value_max

    def getValueMin(self, col = 1):
        # Find the highest column
        value_min = int(self.data[0][col])
        for row in xrange(len(self.data)):
            val = int(self.data[row][col])
            if val < value_min:
                value_min = val
        return value_min

    def getMeanValue(self, col):
        mean = 0
        for row in xrange(len(self.data)):
            mean += int(self.data[row][col])
        mean /= len(self.data)
        return mean

    def mouseReleaseEvent(self, event):
        QAbstractItemView.mouseReleaseEvent(self, event)
        self.selectionRect = QRect()
        self.viewport().update()

    def mouseMoveEvent(self, event):
        if not self.model():
            return
        self.old_highlight = self.highlight
        self.highlight = self.indexAt(event.pos())

        if self.highlight != self.old_highlight:
            self.viewport().update()

    def paintEvent(self, event):
        painter = QPainter(self.viewport())
        painter.setRenderHint(QPainter.Antialiasing)
        self.fm = QFontMetrics(painter.font())
        self.paint(painter, event.rect(), self.viewport().rect(), True)

    def rows(self, index):

        if not self.model():
            return 0
        return self.model().rowCount(self.model().parent(index))

    def rowsInserted(self, parent, start, end):

        if not self.model():
            return
        row = start
        while row <= end:

            index = self.model().index(row, 1, self.rootIndex())
            value = self.model().data(index).toDouble()[0]

            if value > 0.0:
                self.totalValue += value
                self.validItems += 1

            row += 1

        QAbstractItemView.rowsInserted(self, parent, start, end)

    def rowsAboutToBeRemoved(self, parent, start, end):

        if not self.model():
            return
        row = start
        while row <= end:

            index = self.model().index(row, 1, self.rootIndex())
            value = self.model().data(index).toDouble()[0]
            if value > 0.0:
                self.totalValue -= value
                self.validItems -= 1

            row += 1

        QAbstractItemView.rowsAboutToBeRemoved(self, parent, start, end)

    def verticalOffset(self):
        # Qt > 4.2 wants this
        return 0

    def horizontalOffset(self):
        # Qt > 4.2 wants this
        return 0

    def visualRect(self, index):
        # Qt > 4.2 wants this
        return QRect(0, 0, self.viewport().width(), self.viewport().height())

    def printMe(self, painter, rect):
        painter.translate(rect.x(), rect.y())
        widget_size = QRect(0, 0, rect.width(), rect.height())
        self.paint(painter, widget_size, widget_size, False)
        painter.translate(-rect.x(), -rect.y())
