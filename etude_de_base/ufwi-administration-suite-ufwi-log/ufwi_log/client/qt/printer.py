# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Laurent Defert <laurent_defert@inl.fr>

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

from copy import copy
import time
from base64 import b64decode, b64encode

from PyQt4.QtGui import QPrinter, QPrintDialog, QPainter, QFont, QFontMetrics, QDialog
from PyQt4.QtGui import QSizePolicy, QImage, QMessageBox, QFileDialog, QDialogButtonBox
from PyQt4.QtGui import QPushButton, QComboBox, QLabel, QVBoxLayout, QWidget
from PyQt4.QtGui import QGroupBox, QGridLayout
from PyQt4.QtCore import QRect, Qt, QTimer, SIGNAL, QVariant, QDateTime, QDate, QString, QPoint, QDir

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.ui.print_ui import Ui_PrintDialog
from ufwi_log.client.qt.fragment_frame import FragmentFrame
from ufwi_log.client.qt.widgets.pages_list import PagesListWidget
from ufwi_log.client.qt.args import arg_types

class ContentTable:

    def __init__(self, printer):
        self.printer = printer
        self.table = []
        self.curpage = 0

    def newPage(self):
        self.curpage += 1

    def addSection(self, title):
        self.table.append({'title':    title,
                           'page_num': self.curpage,
                           'section':  True,
                           'size':     15})

    def addFragment(self, title):
        self.table.append({'title':    title,
                           'page_num': self.curpage,
                           'section':  False,
                           'size':     10})

    def draw(self):
        self.printer.newPage()

        # Simulate to get the start page number (it depends of number of
        # pages taken by the contents table).
        start_page = self.__draw(self.printer.page_number, simulate=True)

        # Draw it.
        self.__draw(start_page)

    def __draw(self, start_page, simulate=False):
        vpos = 0

        vpos += self.printer.drawHCenteredTitle(tr('Table of contents'), vpos)
        vpos += 10

        for row in self.table:
            if row['section']:
                vpos += 2

            size = row['size']

            fontmetrics = QFontMetrics(QFont(self.printer.FONT_NAME, size))

            if vpos + fontmetrics.height() >= self.printer.height():
                vpos = 10
                if not simulate:
                    self.printer.newPage()
                else:
                    start_page += 1

            if not simulate:
                page_num = row['page_num'] + start_page
                title = row['title']
                num_w = fontmetrics.width(unicode(page_num))

                self.printer.drawText(title + '.' * 300, vpos, halign=Qt.AlignLeft, size=size, width=self.printer.width() - num_w)
                self.printer.drawText(unicode(page_num), vpos, halign=Qt.AlignRight, size=size)

            vpos += fontmetrics.height()

        return start_page

class BasePrinter:

    def __init__(self, title=u'', enterprise=u'', logo=None, header_enabled=True, footer_enabled=True,
                       interval_label=u''):

        self.title = unicode(title)
        self.enterprise = unicode(enterprise)
        self.logo = logo
        self.header_enabled = bool(header_enabled)
        self.footer_enabled = bool(footer_enabled)
        self.interval_label = unicode(interval_label)

class RemotePrinter(BasePrinter):
    def showDialog(self, parent):
        self.filename = unicode(QFileDialog.getSaveFileName(parent, parent.tr("Save File"),
                                               "", parent.tr("PDF file (*.pdf)")))
        if not self.filename:
            return False
        elif not self.filename.endswith('.pdf'):
            self.filename += '.pdf'

        return True

class Printer(BasePrinter):

    FONT_NAME = 'Courrier'

    def __init__(self, *args, **kwargs):
        BasePrinter.__init__(self, *args, **kwargs)
        self.page_number = 0

        self.printer = QPrinter(QPrinter.HighResolution)
        ## todo: remove-me
        self.printer.setOutputFileName("ufwi_log-page.pdf")
        self.printer.setOutputFormat(QPrinter.NativeFormat)
        #self.printer.setOrientation(QPrinter.Landscape)
        self.printer.setPaperSize(QPrinter.A4)
        self.printer.setResolution(100)

    def _init_painter(self):
        self.painter = QPainter(self.printer)
        self.painter.setRenderHint(QPainter.Antialiasing)
        self.painter.setBackgroundMode(Qt.OpaqueMode)
        self.painter.setBrush(Qt.white)
        self.painter.setFont(QFont(self.FONT_NAME, 9))
        fillrect = QRect(0, 0, self.printer.pageRect().width(), self.printer.pageRect().height())
        self.painter.fillRect(fillrect, self.painter.brush())
        self.page_number = 1

        self._draw_header()
        self._draw_footer()
        self.drawCentralTitle(self.title)
        if self.logo:
            self.painter.drawImage(QPoint(self.width() / 2 - self.logo.width() / 2,
                                          self.height() / 2 + QFontMetrics(self.painter.font()).height() + self.height() / 4 - self.logo.height() / 2),
                                   self.logo)

    def _draw_header(self):
        if not self.header_enabled:
            return

        h = -self.headerHeight()
        self.drawText(QDateTime.currentDateTime().toString('yyyy-MM-dd hh:mm'), h, Qt.AlignLeft)
        h += self.drawText(self.interval_label, h, Qt.AlignRight)
        self.drawText(self.title, h, Qt.AlignLeft)
        self.drawText(self.enterprise, h, Qt.AlignRight)

        self.painter.drawLine(0,
                              self.headerHeight() - 1,
                              self.printer.pageRect().width(),
                              self.headerHeight() - 1)

    def _draw_footer(self):
        if not self.footer_enabled:
            return

        self.painter.drawLine(10,
                              self.printer.pageRect().height() - self.footerHeight(),
                              self.printer.pageRect().width() - 10,
                              self.printer.pageRect().height() - self.footerHeight())
        h = self.height() + 1
        #self.drawText('topleft', h, Qt.AlignLeft)
        h += self.drawText(u'© 2008-2010 EdenWall', h, Qt.AlignRight, size=9)
        self.drawText(unicode(self.page_number), h, Qt.AlignHCenter)
        #self.drawText('bottomright', h, Qt.AlignRight)

    def headerHeight(self):
        if self.header_enabled:
            return 40
        else:
            return 0

    def footerHeight(self):
        if self.footer_enabled:
            return 40
        else:
            return 0

    def height(self):
        return self.printer.pageRect().height() - self.headerHeight() - self.footerHeight()

    def width(self):
        return self.printer.pageRect().width()

    def showDialog(self, parent):
        dialog = QPrintDialog(self.printer, parent)
        if dialog.exec_() != QPrintDialog.Accepted:
            return False

        self._init_painter()
        return True

    def end(self):
        self.painter.end()

    def newPage(self):
        self.printer.newPage()
        self.page_number += 1
        self._draw_header()
        self._draw_footer()

    def drawCentralTitle(self, text):
        self.painter.setBackgroundMode(Qt.TransparentMode)
        f = QFont(self.FONT_NAME, 22)
        f.setWeight(QFont.Bold)
        self.painter.setFont(f)
        height = QFontMetrics(self.painter.font()).height()
        self.painter.drawText(QRect(0,
                                    self.printer.pageRect().height() * 0.5,
                                    self.printer.pageRect().width(),
                                    height),
                              Qt.AlignHCenter | Qt.AlignVCenter,
                              text)
        self.painter.setFont(QFont(self.FONT_NAME, 10))

    def drawHCenteredTitle(self, text, vpos):
        self.painter.setBackgroundMode(Qt.TransparentMode)
        self.painter.setFont(QFont(self.FONT_NAME, 18))
        height = QFontMetrics(self.painter.font()).height()
        self.painter.drawText(QRect(0,
                                    self.headerHeight() + vpos,
                                    self.printer.pageRect().width(),
                                    height),
                              Qt.AlignHCenter | Qt.AlignVCenter,
                              text)
        self.painter.setFont(QFont(self.FONT_NAME, 10))
        return height

    def drawText(self, text, vpos, halign=Qt.AlignLeft, size=10, width=None):
        self.painter.setBackgroundMode(Qt.TransparentMode)
        self.painter.setFont(QFont(self.FONT_NAME, size))
        height = QFontMetrics(self.painter.font()).height()
        if width is None:
            width = self.printer.pageRect().width()
        self.painter.drawText(QRect(0,
                                    self.headerHeight() + vpos,
                                    width,
                                    height),
                              halign | Qt.AlignVCenter,
                              text)

        return height

    def drawFragment(self, frag_widget, vpos, len_frags):

        # Display it on half the page
        scale = 1
        single_frag = False
        if frag_widget.pos == len_frags - 1 and frag_widget.pos % 2 == 0:
            scale = 2
            single_frag = True

        y = self.headerHeight() + vpos
        width = self.printer.pageRect().width() * 0.8 * scale
        height = self.printer.pageRect().height() * 0.5 * 0.8
        x = self.printer.pageRect().width() * 0.1

        if single_frag:
            if frag_widget.view.__class__.__name__ != "TreeFragmentView":
                x = -(width - self.printer.pageRect().width()) / 2.
            else:
                width = width / 2.

        rect = QRect(x, y, width, height)

        # Temporary remove stylesheet to avoid to print background.
        stylesheet_save = frag_widget.styleSheet()
        frag_widget.setStyleSheet('')
        frag_widget.getView().printMe(self.painter, rect)
        frag_widget.setStyleSheet(stylesheet_save)

class PrinterBaseDialog(QDialog):

    RESIZED_LOGO_PATH = QDir.tempPath()

    def __init__(self, user_settings, parent=None):
        QDialog.__init__(self, parent)

        self.ui = Ui_PrintDialog()
        self.ui.setupUi(self)

        self.user_settings = user_settings
        self.compatibility = user_settings.compatibility

        self.connect(self.ui.logoLoad, SIGNAL('clicked(bool)'), self.openImage)

        self.ui.printButton = QPushButton(tr('Print'))
        self.connect(self.ui.printButton, SIGNAL('clicked(bool)'), self._print_action)
        self.ui.buttonBox.addButton(self.ui.printButton, QDialogButtonBox.ActionRole)

        self._init_options()

    def _init_options(self):
        settings = self.user_settings['printer']
        self.ui.contentTableBox.setChecked(settings.content_table)
        self.ui.headerBox.setChecked(settings.header)
        self.ui.footerBox.setChecked(settings.footer)
        self.ui.titleEdit.setText(settings.title)
        self.ui.enterpriseEdit.setText(settings.enterprise)
        self.ui.logoPath.setText(settings.logo)

    def openImage(self, b):
        s = QFileDialog.getOpenFileName(self)
        self.ui.logoPath.setText(s)

    def run(self):
        return self.exec_()

    def checkInput(self):
        """
        Called to know if the users inputs in dialog are corrects.

        @return [bool]
        """
        raise NotImplementedError()

    def buildPrinter(self):
        """
        This method needs to be overloaded. It returns a Printer instance.
        """
        raise NotImplementedError()

    def preparePrinting(self):
        """
        Prepare printing of pages.
        """
        raise NotImplementedError()

    def _print_action(self, b):
        if not self.checkInput():
            return

        self.printer = self.buildPrinter()

        if not self.printer.showDialog(parent=self):
            del self.printer
            return

        # Save settings
        settings = self.user_settings['printer']
        settings.content_table = self.ui.contentTableBox.isChecked()
        settings.header = self.ui.headerBox.isChecked()
        settings.footer = self.ui.footerBox.isChecked()
        settings.title = unicode(self.ui.titleEdit.text())
        settings.enterprise = unicode(self.ui.enterpriseEdit.text())
        settings.logo = unicode(self.ui.logoPath.text())

        # Disable widgets
        if hasattr(self.ui, 'pages_list'):
            self.ui.pages_list.setEnabled(False)
        self.ui.buttonBox.setEnabled(False)
        self.ui.optionsBox.setEnabled(False)
        self.ui.progressBar.setEnabled(True)
        self.ui.progressBar.setValue(0)
        self.ui.progressLabel.setText(self.tr('Initialization...'))

        self.repaint()

        self.preparePrinting()

    def printPages(self, pages):

        self.ui.progressBar.setValue(0)
        self.ui.progressLabel.setText(self.tr('Printing...'))

        # Main title
        nb_printed = 0
        for page, frag_widgets in pages:

            self.printer.newPage()

            frag_no = 0
            for frag_widget in frag_widgets:
                if frag_widget.height() == 0 or frag_widget.width() == 0 or frag_widget.isHidden():
                    nb_printed += 1
                    continue

                self.printer.drawHCenteredTitle(frag_widget.getView().title.text(),
                                                (self.printer.height() + 10) * (frag_no % 2) * 0.5)

                self.printer.drawFragment(frag_widget, self.printer.height() * (0.05 + (frag_no % 2) * 0.5), len(frag_widgets))

                # Add a new page if we need more place
                if frag_no < len(frag_widgets) - 1 and frag_no % 2:
                    self.printer.drawText(page.title, self.printer.height() - 40, halign=Qt.AlignRight, size=15)
                    if nb_printed < len(frag_widgets) - 1:
                        self.printer.newPage()
                frag_no += 1
                nb_printed += 1

                self.ui.progressBar.setValue(nb_printed)

            self.printer.drawText(page.title, self.printer.height() - 40, halign=Qt.AlignRight, size=15)

        self.printer.end()
        self.end()

    def end(self):
        # Enable widgets
        self.ui.buttonBox.setEnabled(True)
        self.ui.optionsBox.setEnabled(True)
        self.ui.progressBar.setEnabled(False)
        self.ui.progressLabel.setText(self.tr('Done.'))

    def _resizeLogo(self, logo):
        img = QImage(logo)

        if img.width() < 200 and img.height() < 200:
            return logo

        scale_on_width = True if img.width() > img.height() else False

        if scale_on_width:
            img = img.scaledToWidth(300)
        else:
            img = img.scaledToHeight(300)

        split_path = logo.split("/")
        filename = split_path[len(split_path) - 1]

        logo = self.RESIZED_LOGO_PATH + "/" + filename
        img.save(logo)

        return logo


class PrintDialog(PrinterBaseDialog):

    def __init__(self, user_settings, parent=None):
        PrinterBaseDialog.__init__(self, user_settings, parent)

        self.setWindowTitle(self.tr('Print current view'))

    def _init_options(self):
        PrinterBaseDialog._init_options(self)

        # Hide everythings related to time.
        self.ui.lastRadio.hide()
        self.ui.intervalRadio.hide()
        self.ui.lastEdit.hide()
        self.ui.startLabel.hide()
        self.ui.startDate.hide()
        self.ui.endLabel.hide()
        self.ui.endDate.hide()

    def checkInput(self):
        return True

    def buildPrinter(self):
        logo = unicode(self.ui.logoPath.text())
        logo = self._resizeLogo(logo)
        logo = QImage(QString(logo))

        return Printer(title=self.ui.titleEdit.text(),
                       enterprise=self.ui.enterpriseEdit.text(),
                       logo=not logo.isNull() and logo or None,
                       header_enabled=self.ui.headerBox.isChecked(),
                       footer_enabled=self.ui.footerBox.isChecked())

    def preparePrinting(self):
        content_table = ContentTable(self.printer)
        content_table.newPage()
        content_table.addSection(self.parent().current_page.title)
        i = 0

        frames = self.parent().current_page.frames
        frags_widget = self.parent().frag_widgets

        for frame in frames:
            for fragname, fragment in frame.frags:

                # *** Check that fragment is not hidden before adding title on content_table
                is_hidden = False
                for frag_widget in frags_widget:
                    if frag_widget.pos == frame.pos and frag_widget.fragment.title == fragment.title:
                        if frag_widget.isHidden():
                            is_hidden = True
                            break
                if is_hidden:
                    i += 1
                    continue
                # *** END CHECK 

                if i > 0 and not i % 2:
                    content_table.newPage()
                content_table.addFragment(fragment.title)
                i += 1

        self.ui.progressBar.setMaximum(i)

        if self.ui.contentTableBox.isChecked():
            content_table.draw()

        pages = []
        pages.append((self.parent().current_page, self.parent().frag_widgets))
        self.printPages(pages)

def interval_current_week():
    date = QDate.currentDate()
    begin = QDateTime(date.addDays(-(date.dayOfWeek() - 1)))
    return {'start_time': begin.toTime_t()}

def interval_previous_week():
    date = QDate.currentDate()
    end = QDateTime(date.addDays(-(date.dayOfWeek() - 1)))
    begin = QDateTime(date.addDays(-(date.dayOfWeek() - 1) - 7))
    return {'start_time': begin.toTime_t(),
            'end_time':   end.toTime_t()
           }

def interval_current_month():
    date = QDate.currentDate()
    begin = QDateTime(date.addDays(-date.day() + 1))
    return {'start_time': begin.toTime_t()}

def interval_previous_month():
    date = QDate.currentDate()
    end = QDateTime(date.addDays(-date.day() + 1))
    begin = QDateTime(end.date().addDays(-end.date().addDays(-1).daysInMonth()))
    return {'start_time': begin.toTime_t(),
            'end_time':   end.toTime_t()
           }

class ReportDialog(PrinterBaseDialog):

    lasts = [(tr('Last hour'), 3600, False),
             (tr('Last day'), 86400, False),
             (tr('Last 7 days'), 604800, True),
             (tr('Last 30 days'), 2678400, False)]

    contextual_intervals = [(tr('From last Monday'), interval_current_week),
                            (tr('Previous week'), interval_previous_week),
                            (tr('From the 1st of the current month'), interval_current_month),
                            (tr('Previous month'), interval_previous_month)]

    def __init__(self, user_settings, client, parent=None):
        PrinterBaseDialog.__init__(self, user_settings, parent)
        self.setWindowTitle(self.tr('Create a Report'))

        self.client = client
        self.args = {}

        self._init_timer()
        self._init_pages_list()

    def _init_timer(self):
        """ Init timer used to check if fragments data are fetched. """
        self.timer = QTimer()
        self.timer.setSingleShot(True)
        self.connect(self.timer, SIGNAL('timeout()'), self.checkFragments)

    def _init_pages_list(self):
        self.ui.pages_list = PagesListWidget(self.user_settings, self.parent(), read_only=True)
        self.ui.pages_list.loadPagesList(checkable=True)
        self.ui.pages_list.setSizePolicy(QSizePolicy.Minimum, QSizePolicy.Minimum)
        self.ui.pages_list.collapseAllButOne('reports')
        self.ui.horizontalLayout.insertWidget(0, self.ui.pages_list)

    def _init_options(self):
        PrinterBaseDialog._init_options(self)

        for label, value, selected in self.lasts:
            self.ui.lastEdit.addItem(label, QVariant(value))
            if selected:
                self.ui.lastEdit.setCurrentIndex(self.ui.lastEdit.count() - 1)
        for i, (label, func) in enumerate(self.contextual_intervals):
            # for each contextual interval, the data is a negative number to distinct
            # with intervals.
            # this is the negative number of indexes.
            self.ui.lastEdit.addItem(label, QVariant(-i))

        self.ui.startDate.setDateTime(QDateTime.currentDateTime().addDays(-1))
        self.ui.endDate.setDateTime(QDateTime.currentDateTime())

    def checkInput(self):
        pages = self.ui.pages_list.getCheckedPages()

        if not pages:
            QMessageBox.critical(self, self.tr('Unable to print'), self.tr('Please select at least one view to print!'))
            return False

        return True

    def buildPrinter(self):
        logo = QImage(QString(self.ui.logoPath.text()))
        self.args = {}
        # Determine interval.
        interval_label = ''
        if self.ui.lastRadio.isChecked():
            data, is_int = self.ui.lastEdit.itemData(self.ui.lastEdit.currentIndex()).toInt()
            interval_label = unicode(self.ui.lastEdit.itemText(self.ui.lastEdit.currentIndex()))
            if data > 0:
                self.args['start_time'] = int(time.time()) - data
            else:
                label, func = self.contextual_intervals[-data]
                self.args = func()
        elif self.ui.intervalRadio.isChecked():
            self.args['start_time'] = self.ui.startDate.dateTime().toTime_t()
            self.args['end_time'] = self.ui.endDate.dateTime().toTime_t()
            interval_label = u'%s — %s' % (self.ui.startDate.dateTime().toString('yyyy-MM-dd hh:mm'),
                                           self.ui.endDate.dateTime().toString('yyyy-MM-dd hh:mm'))

        return Printer(title=self.ui.titleEdit.text(),
                       enterprise=self.ui.enterpriseEdit.text(),
                       logo=not logo.isNull() and logo or None,
                       header_enabled=self.ui.headerBox.isChecked(),
                       footer_enabled=self.ui.footerBox.isChecked(),
                       interval_label=interval_label)

    def preparePrinting(self):
        self.ui.pages_list.setEnabled(False)
        pages = self.ui.pages_list.getCheckedPages()
        content_table = ContentTable(self.printer)

        # Build the list of fetching pages, and ask each fragments
        # to fetch data.
        self.fetching_pages = []
        for page in pages:
            content_table.newPage()
            content_table.addSection(page.title)

            page_args = copy(page.args)
            page_args.update(self.args)

            frag_widgets = []
            i = 0
            for frame in page.frames:
                for fragname, fragment in frame.frags:

                    frag_widget = FragmentFrame(fragment, page_args, self.client)
                    if not frag_widget.getView().isPrintable():
                        continue

                    frag_widget.updateData()
                    frag_widgets.append(frag_widget)

                    if i > 0 and not i % 2:
                        content_table.newPage()
                    content_table.addFragment(fragment.title)
                    i += 1

            self.fetching_pages.append((page, frag_widgets))

        if self.ui.contentTableBox.isChecked():
            content_table.draw()

        # Timer will call the checkFragments() method.
        self.timer.start(500)
        self.update()

    def checkFragments(self):
        """ Called every 500ms to check if all data are fetched """

        nb_fetched = 0
        nb_tot = 0
        for page, frag_widgets in self.fetching_pages:
            for frag_widget in frag_widgets:
                if frag_widget.getView().isPrintable():
                    if frag_widget.getView().isReady():
                        nb_fetched += 1
                    nb_tot += 1

        self.ui.progressLabel.setText(self.tr('Fetching data...'))
        self.ui.progressBar.setMaximum(nb_tot)
        self.ui.progressBar.setValue(nb_fetched)

        if nb_fetched < nb_tot:
            self.timer.start(500)
        else:
            self.printPages(self.fetching_pages)

    def end(self):
        PrinterBaseDialog.end(self)
        self.ui.pages_list.setEnabled(True)

class RemoteReportDialog(ReportDialog):
    def _init_timer(self):
        return

    def _init_pages_list(self):
        vbox = QVBoxLayout()

        # Reports group
        self.ui.reports_group = QGroupBox(tr('Reports'))
        reports_layout = QVBoxLayout()
        reports_layout.addWidget(QLabel(tr("Select a report type:")))
        self.ui.reports_list = QComboBox()
        self.connect(self.ui.reports_list, SIGNAL('currentIndexChanged(int)'), self.reportTypeChanged)
        self.vargs = []
        for name, report in self.user_settings['reports'].reports.iteritems():
            self.ui.reports_list.addItem(report.title, QVariant(report.name))
        reports_layout.addWidget(self.ui.reports_list)
        self.ui.args = QGridLayout()
        w = QWidget()
        w.setLayout(self.ui.args)
        reports_layout.addWidget(w)
        reports_layout.addStretch()

        self.ui.reports_group.setLayout(reports_layout)
        vbox.addWidget(self.ui.reports_group)

        # Plan group
        #self.ui.plan_group = QGroupBox(tr('Plan'))
        #self.ui.plan_group.setCheckable(True)
        #self.ui.plan_group.setChecked(False)
        #plan_layout = QVBoxLayout()
        #self.ui.plan_group.setLayout(plan_layout)

        #vbox.addWidget(self.ui.plan_group)

        # Add vbox on left
        w = QWidget()
        w.setLayout(vbox)
        self.ui.horizontalLayout.insertWidget(0, w)

        self.ui.printButton.setText(tr("OK"))

    def reportTypeChanged(self, i):
        for arg_label, arg_value in self.vargs:
            if arg_label:
                self.ui.args.removeWidget(arg_label)
                arg_label.hide()
            if arg_value:
                self.ui.args.removeWidget(arg_value)
                arg_value.hide()
        self.vargs = []

        report_type = unicode(self.ui.reports_list.itemData(i).toString())
        report = self.user_settings['reports'].reports[report_type]

        args = report.filters

        if not args:
            return

        for arg in args:
            # Get the widget which will be used
            try:
                compatibility = self.user_settings.compatibility
                arg_value = arg_types[arg].filter(self.client, arg, '', compatibility)
            except KeyError:
                continue
            if not isinstance(arg_value, QWidget):
                continue

            # Add a checkbox to activate or no this argument.
            arg_label = QLabel(arg_types[arg].label)

            self.ui.args.addWidget(arg_label, len(self.vargs), 0)
            self.ui.args.addWidget(arg_value, len(self.vargs), 1)

            self.vargs.append((arg_label, arg_value))

    def checkInput(self):
        return True

    def buildPrinter(self):
        logo = unicode(self.ui.logoPath.text())
        self.args = {}

        logo = self._resizeLogo(logo)

        for arg_label, arg_filter in self.vargs:
            self.args[arg_filter.filter_arg] = arg_filter.getValue()

        # Determine interval.
        interval_label = ''
        if self.ui.lastRadio.isChecked():
            data, is_int = self.ui.lastEdit.itemData(self.ui.lastEdit.currentIndex()).toInt()
            interval_label = unicode(self.ui.lastEdit.itemText(self.ui.lastEdit.currentIndex()))
            if data > 0:
                self.args['start_time'] = int(time.time()) - data
            else:
                label, func = self.contextual_intervals[-data]
                self.args = func()
        elif self.ui.intervalRadio.isChecked():
            self.args['start_time'] = self.ui.startDate.dateTime().toTime_t()
            self.args['end_time'] = self.ui.endDate.dateTime().toTime_t()
            interval_label = u'%s — %s' % (self.ui.startDate.dateTime().toString('yyyy-MM-dd hh:mm'),
                                           self.ui.endDate.dateTime().toString('yyyy-MM-dd hh:mm'))

        return RemotePrinter(title=self.ui.titleEdit.text(),
                             enterprise=self.ui.enterpriseEdit.text(),
                             logo=logo,
                             header_enabled=self.ui.headerBox.isChecked(),
                             footer_enabled=self.ui.footerBox.isChecked(),
                             interval_label=interval_label)

    def report_error(self, err):
        self.end()
        self.ui.progressBar.setMaximum(1)
        self.ui.progressBar.setValue(0)
        self.ui.progressLabel.setText(tr('Error: %s') % err)

    def preparePrinting(self):
        try:
            self.ui.reports_group.setEnabled(False)
            logo = ''
            if self.printer.logo:
                with open(self.printer.logo, 'rb') as f:
                    logo = b64encode(f.read())

            report_type = unicode(self.ui.reports_list.itemData(self.ui.reports_list.currentIndex()).toString())
            report = self.user_settings['reports'].reports[report_type]

#            text = self.printer.enterprise + '\n' + self.printer.title
            if self.user_settings.compatibility.print_enterprise:
                self.client.async().call('reporting', 'new', self.printer.title,
                                                             self.printer.enterprise,
                                                             self.printer.interval_label,
                                                             logo,
                                                             report.scenario,
                                                             self.args,
                                          callback=self.printed, errback=self.report_error)
            else:
                self.client.async().call('reporting', 'new', self.printer.title,
                                                             self.printer.interval_label,
                                                             logo,
                                                             report.scenario,
                                                             self.args,
                                          callback=self.printed, errback=self.report_error)
            self.ui.progressLabel.setText(self.tr('Fetching data...'))
            self.ui.progressBar.setMaximum(0)
            self.ui.progressBar.setValue(0)

        except Exception, err:
            self.report_error(err)
            raise

    def printed(self, result):
        try:
            path = self.printer.filename
            self.ui.progressLabel.setText(self.tr('Creating...'))
            self.ui.progressBar.setMaximum(1)
            self.ui.progressBar.setValue(0)

            result = b64decode(self.client.call('reporting', 'build'))
            with file(path, 'wb') as f:
                f.write(result)

            self.ui.progressBar.setValue(1)
            self.end()
        except Exception, err:
            self.report_error(err)
            raise

    def end(self):
        PrinterBaseDialog.end(self)
        self.ui.reports_group.setEnabled(True)
