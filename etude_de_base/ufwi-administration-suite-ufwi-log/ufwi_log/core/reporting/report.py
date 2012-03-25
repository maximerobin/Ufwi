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

from cStringIO import StringIO

from reportlab.graphics.shapes import Drawing
from reportlab.pdfgen.canvas import Canvas
from reportlab.graphics import renderPDF
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle as PS
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import PageBreak
from reportlab.platypus.paragraph import Paragraph
from reportlab.platypus.doctemplate import PageTemplate, BaseDocTemplate
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.frames import Frame
from reportlab.platypus.flowables import Image, KeepTogether, Spacer, Flowable
from reportlab.lib.colors import black, white

import render
import colors

class Report(object):
    render = {'table': render.TableRender,
              'pie':   render.PieRender,
              'histo': render.HistoRender,
              'line':  render.LineRender,
              'gantt': render.GanttRender,
             }

    margin = 30
    big_title_height = 40
    title_height = 50
    frame_margin = 5
    frag_title_height = 20
    frag_margin = 9
    edenwall_height = 60

    def __init__(self, title, enterprise, interval, logo):
        self.title = title
        self.enterprise = enterprise
        self.interval = interval
        self.logo = logo
        self.width, self.height = A4
        self.buf = StringIO()
        self.canvas = Canvas(self.buf, pagesize=A4)

        self.page_title = ''
        self.page_rows = []
        self.page_frags = 0
        self.page_num = 1

        # Build story.
        self.canvas.saveState()
        self.canvas.setStrokeColor(colors.RED)
        self.canvas.setLineWidth(2)
        self.canvas.roundRect(self.margin, self.edenwall_height + self.margin, self.width, self.height, 20, stroke=1, fill=0)

        self.canvas.setFillColor(colors.GREEN2)
        self.canvas.setStrokeColor(colors.GREEN1)
        self.canvas.roundRect(- self.margin, - self.margin, self.width - self.margin, self.edenwall_height + self.margin,
                              20, stroke=1, fill=1)
        # TODO do not hardcode this values.
        img = Image('/var/lib/ufwi_rpcd/edenwall.png', 1209 / (300/(self.edenwall_height-self.margin/2)), self.edenwall_height-self.margin/2)
        img.drawOn(self.canvas, self.margin, self.margin/4)

        self.canvas.restoreState()

        if self.logo:
            img = Image(StringIO(self.logo))
            img._setup_inner()
            img.drawOn(self.canvas, (self.width - self.margin)/2 - img.drawWidth/2, 2*self.height/3)

        offset = 40

        self.canvas.setFillColor(black)
        self.canvas.setFont("Helvetica-Bold", self.big_title_height)
        self.canvas.drawCentredString((self.width-self.margin)/2, self.height/3, title)
        self.canvas.setFont("Helvetica-Bold", self.frag_title_height)
        self.canvas.drawString(offset, self.height - offset, enterprise)

    def __getstate__(self):
        d = self.__dict__.copy()
        del d['canvas']
        return d

    def __setstate__(self, d):
        self.__dict__ = d
        self.canvas = Canvas(self.buf, pagesize=A4)

    def build(self):
        self.canvas.showPage()
        self.canvas.save()
        return self.buf

    def addGraph(self, title, columns, table, render):
        frags = self.page_frags
        for row, cols in enumerate(self.page_rows):
            frags -= cols
            if frags < 0:
                break

        if frags >= 0:
            self.addPage(self.page_title, self.page_rows)
            col = 0
            row = 0
            cols = self.page_rows[0]
        else:
            col = - frags - 1

        # You can read that? Not me.
        x = self.margin + self.frame_margin + (col+1) * self.frag_margin + \
            col * (self.width - 2*self.margin - 2*self.frame_margin - (col+1)*self.frag_margin) / cols
        y = self.margin + self.frame_margin + (row+1) * self.frag_margin + \
            row * (self.height - 2*self.margin - 2*self.frame_margin - self.title_height - 2*self.frag_margin) / len(self.page_rows)
        width = (self.width - 2*self.margin - 2*self.frame_margin - 2*cols*self.frag_margin) / cols
        height = (self.height - 2*self.margin - 2*self.frame_margin - self.title_height - 2*len(self.page_rows)*self.frag_margin) / len(self.page_rows)

        self.canvas.setFillColor(colors.GREEN1)
        self.canvas.roundRect(x, y, width, height, 7, stroke=0, fill=1)
        self.canvas.setFillColor(white)
        x += 1
        y += 1
        width -= 2
        height -= 2

        self.canvas.roundRect(x, y, width, height - self.frag_title_height, 7, stroke=0, fill=1)

        self.canvas.setFillColor(white)
        self.canvas.setFont("Helvetica", 3*self.frag_title_height/4)
        self.canvas.drawCentredString(x + width/ 2, y + height - 3*self.frag_title_height/4, title)

        self.page_frags += 1

        if len(table) > 0:
            klass = self.render[render]
            obj = klass(width, height - self.frag_title_height - 2*self.frame_margin, columns, table)

            r = obj.render()
            if isinstance(r, Drawing):
                renderPDF.draw(obj.render(), self.canvas, x, y + self.frame_margin)
            elif isinstance(r, Flowable):
                r.drawOn(self.canvas, x, y + height - self.frag_title_height - obj.height - self.frame_margin)

        else:
            pass
            #self.append(Paragraph(title, h2))
            #self.append(Paragraph('No data', h2))

            #self.append(KeepTogether([Paragraph(title, h2),
            #                          Paragraph('No data', h2)]))

    def addPage(self, title, rows=[1]):
        self.canvas.showPage()
        self.canvas.saveState()
        self.canvas.setLineWidth(2)
        self.canvas.setStrokeColor(colors.RED)
        self.canvas.roundRect(self.margin, self.margin,
                              self.width - self.margin*2,
                              self.height - self.margin*2,
                              20, stroke=1, fill=0)
        self.canvas.restoreState()
        self.canvas.setFillColor(colors.GREEN1)
        self.canvas.setFont("Helvetica-Bold", self.title_height/3)
        self.canvas.drawString(self.margin*2, self.height - self.margin - 4*self.title_height/5, title)
        self.canvas.setFont("Helvetica-Bold", self.title_height/3)
        self.canvas.drawRightString(self.width - self.margin*2, self.height - self.margin - 4*self.title_height/5, self.interval)
        self.page_num += 1
        self.canvas.setFont("Helvetica-Bold", 12)
        self.canvas.drawCentredString(self.width/2, 0, "Page %d" % self.page_num)

        self.page_title = title
        self.page_rows = rows
        self.page_frags = 0

