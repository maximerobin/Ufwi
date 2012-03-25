# -*- coding: utf-8 -*-

"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

from __future__ import with_statement

from cStringIO import StringIO
from time import strftime, localtime, time

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.graphics.shapes import Drawing
from reportlab.graphics.charts.piecharts import Pie
from reportlab.graphics.charts.barcharts import VerticalBarChart
from reportlab.graphics.charts.linecharts import HorizontalLineChart
from reportlab.platypus.tables import Table
from reportlab.platypus.flowables import Image
from reportlab.lib.units import inch

import cairoplot
from colors import RED, GREEN1, ORANGE, GREEN2

COLORS = [RED,GREEN1,ORANGE,GREEN2]

class IRender:
    DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'

    def i2date(self, value):
        try:
            return strftime(self.DATETIME_FORMAT, localtime(int(value)))
        except ValueError:
            return value

    columns = {'oob_time_sec': i2date,
               'start_time':   i2date,
               'end_time':     i2date}

    def __init__(self, width, height, labels, data):
        self.width = width
        self.height = height
        self.labels = labels
        self.data = []
        for line in data:
            current_line = []
            for column, cell in zip(self.labels, line):
                if isinstance(cell, (list,tuple)):
                    value = cell[0]
                else:
                    value = cell
                try:
                    filter = self.columns[column]
                except KeyError:
                    pass
                else:
                    value = filter(self, value)
                current_line.append(value)
            self.data.append(current_line)

    def render(self):
        raise NotImplementedError()

class TableRender(IRender):
    def __init__(self, width, height, labels, data):
        IRender.__init__(self, width, height, labels, data)
        self.table = Table([self.labels] + self.data,
                           style=[#('GRID',(0,0),(-1,-1),0.5,colors.grey),
                                  #('BOX',(0,0),(-1,-1),2,colors.black),
                                  ('LINEABOVE',(0,1),(-1,1),2,colors.black),
                                  #('ALIGN',(0,0),(-1,0),'CENTER'),
                                  ('TOPPADDING', (0,1), (-1,-1), 2),
                                  ('BOTTOMPADDING', (0,1), (-1,-1), 1),
                                 ])
        self.table._calc(width, height)
        for n, w in enumerate(self.table._colWidths):
            print w
            self.table._argW[n] = w + (width - self.table._width) / self.table._ncols
        self.table._calc(width, height)

        self.height = self.table._rowpositions[0]

    def render(self): return self.table

class GanttRender(IRender):
    def __init__(self, width, height, labels, data):
        IRender.__init__(self, width, height, labels, data)

        array = {}
        min_timestamp = -1
        max_timestamp = -1
        for key, first, last in data:
            if not first: first = int(time())
            if not last: last = int(time())

            if isinstance(key, (list,tuple)):
                key = key[0]

            if key in array:
                array[key].append((first, last))
            else:
                array[key] = [(first, last)]
            if min_timestamp < 0 or min_timestamp > first:
                min_timestamp = int(first)
            if max_timestamp < last:
                max_timestamp = int(last)

        pieces = []
        x_labels = []
        y_labels = [unicode(i) for i in xrange(min_timestamp, max_timestamp, 3600*24)]
        for key, lst in array.iteritems():
            if len(pieces) > 10: break
            lst = [((first - min_timestamp) / (3600*24), (last - min_timestamp) / (3600*24)) for first, last in lst]
            pieces.append(lst)
            x_labels.append(key)

        plot = cairoplot.GanttChart('/tmp/tmp.png', pieces, self.width, self.height, x_labels, y_labels)
        plot.render()
        plot.commit()
        with open('/tmp/tmp.png') as f:
            self.image = Image(StringIO(f.read()), self.width, self.height)

    def render(self): return self.image

class PieRender(IRender):
    def __init__(self, width, height, labels, data):
        IRender.__init__(self, width, height, labels, data)

        #self.w = self.width
        #self.h = self.height
        #data = {}
        #for value in self.data:
        #    data[value[0]] = int(value[1])

        #plot = cairoplot.PiePlot('/tmp/tmp.png', data, self.w*2, self.h*2, gradient=True)
        ##plot.font_size *= 2
        #plot.render()
        #plot.commit()
        #with open('/tmp/tmp.png') as f:
        #    self.image = Image(StringIO(f.read()), self.w, self.h)
        pc = Pie()
        pc.width = min(self.height,self.width - 150)
        pc.height = min(self.height - 50,self.width)
        pc.width = pc.height = min(pc.height, pc.width)
        pc.x = self.width / 2 - pc.width / 2
        pc.y = self.height / 2 - pc.height / 2
        pc.data = [int(line[1]) for line in self.data]
        pc.labels = [line[0] for line in self.data]

        for i in xrange(len(self.data)):
            pc.slices[i].fillColor = COLORS[i % len(COLORS)]
            pc.slices[i].strokeColor = COLORS[i % len(COLORS)]
        self.drawing = Drawing(self.width, self.height)
        self.drawing.add(pc)

    def render(self): return self.drawing

class HistoRender(IRender):
    def __init__(self, width, height, labels, data):
        IRender.__init__(self, width, height, labels, data)

        #self.w = self.width
        #self.h = self.height
        #data = [[int(line[1])] for line in self.data]
        #labels = [line[0] for line in self.data]
        #plot = cairoplot.VerticalBarPlot('/tmp/tmp.png', data, self.w*2, self.h*2, x_labels=labels, grid=True, display_values=True)
        ##plot.font_size *= 2
        #plot.render()
        #plot.commit()
        #with open('/tmp/tmp.png') as f:
        #    self.image = Image(StringIO(f.read()), self.w, self.h)
        bc = VerticalBarChart()
        bc.x = 40
        bc.y = 50
        bc.height = self.height - 60
        bc.width = self.width - 60
        bc.data = [[int(line[1]) for line in self.data]]
        bc.strokeColor = colors.white
        bc.bars.strokeColor = RED
        bc.bars.fillColor = RED
        bc.bars[0].fillColor = RED
        bc.valueAxis.valueMin = 0
        bc.valueAxis.valueMax = max([int(line[1]) for line in self.data])
        bc.valueAxis.valueStep = bc.valueAxis.valueMax/10
        if not bc.valueAxis.valueStep:
            bc.valueAxis.valueStep = 1
            bc.valueAxis.valueMax = 10
        bc.categoryAxis.labels.boxAnchor = 'ne'
        bc.categoryAxis.labels.dx = 8
        bc.categoryAxis.labels.dy = -2
        bc.categoryAxis.labels.angle = 30
        bc.categoryAxis.categoryNames = [line[0] for line in self.data]
        self.drawing = Drawing(self.width, self.height)
        self.drawing.add(bc)

    def render(self): return self.drawing

class LineRender(IRender):
    def __init__(self, width, height, labels, data):
        IRender.__init__(self, width, height, labels, data)

        data = [int(line[1]) for line in self.data]
        labels = [line[0] for line in self.data]
        plot = cairoplot.DotLinePlot('/tmp/tmp.png', data, self.width*2, self.height*2, x_labels=labels, grid=True, axis=True, dots=True, series_colors=['red'])
        #plot.font_size *= 2
        plot.render()
        plot.commit()
        with open('/tmp/tmp.png') as f:
            self.image = Image(StringIO(f.read()), self.width, self.height)
        #lc = HorizontalLineChart()
        #lc.x = 50
        #lc.y = 0
        #lc.height = self.height
        #lc.width = self.width
        #lc.data = [[int(line[1]) for line in self.data]]
        #lc.joinedLines = 1
        #lc.valueAxis.valueMin = 0
        #lc.valueAxis.valueMax = max([int(line[1]) for line in self.data])
        #lc.valueAxis.valueStep = lc.valueAxis.valueMax/10
        #if not lc.valueAxis.valueStep:
        #    lc.valueAxis.valueStep = 1
        #    lc.valueAxis.valueMax = 10
        #lc.categoryAxis.labels.boxAnchor = 'ne'
        #lc.categoryAxis.labels.dx = 8
        #lc.categoryAxis.labels.dy = -2
        #lc.categoryAxis.labels.angle = 30
        #lc.categoryAxis.categoryNames = [line[0] for line in self.data]
        #self.drawing = Drawing(0, lc.height)
        #self.drawing.add(lc)

    def render(self): return self.image
