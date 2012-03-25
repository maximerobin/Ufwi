# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
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

from PyQt4.QtGui import QStandardItemModel, QWidget, QHBoxLayout, QVBoxLayout
from PyQt4.QtGui import QColor, QFileDialog, QMessageBox, QDialog
from PyQt4.QtCore import Qt, QVariant, SIGNAL, QModelIndex, QDateTime

from ufwi_log.client.qt.args import arg_types, ArgDataBase
from ufwi_log.client.qt.tools import createLink
from ufwi_log.client.qt.views.base import BaseFragmentView
from ufwi_log.client.qt.csvoption import CSVOption
import codecs

BARCHART = 1
PIECHART = 2
C_PIECHART = 3
TREEVIEW = 4
TABLEVIEW = 5
LINEVIEW = 6

class NulogBaseFragmentView(BaseFragmentView):

    def __init__(self, fetcher):
        BaseFragmentView.__init__(self, fetcher)

        self.my_model = None
        self.data = []
        self.result = None
        self.ready = False
        self.columns = []
        self.filters = None
        self.arg_types = {}
        self.keep_python_ref = []

#    def isPrintable(self): return self.fetcher.isPrintable()
    def isReady(self): return self.ready

    def label_changed(self, arg_data, row, col):
        # Refresh all other cells.
        self.add_lines()

    def get_model_label(self, row, col, arg_data):
        return arg_data.label

    def add_lines(self):
        self.setUpdatesEnabled(False)
        # Keep a reference on python object (if not => seg fault crash)
        self.keep_python_ref = []
        # row is the line number, and line is the content (a list)
        for row, line in enumerate(self.data):
            self.add_line(row, line)
        self.setUpdatesEnabled(True)

    def add_line(self, row, line):
        def make_lambda(func, *args):
            return lambda: func(*args)

        id = ''
        if len(line) < len(self.columns):
            line.extend(['' for i in xrange(len(self.columns) - len(line))])
        for col, cell in enumerate(line):

            # TODO move in backend
            if isinstance(cell, str):
                if "::ffff:" in cell:
                    cell = cell.split("::ffff:")[1]

            if hasattr(self, "user_settings") and self.user_settings:
                arg_data = arg_types[self.columns[col]].data(self.columns[col], cell, self.fetcher, self.user_settings.compatibility)
            else:
                arg_data = arg_types[self.columns[col]].data(self.columns[col], cell, self.fetcher, parent=self)

            if col == 0:
                id = unicode(arg_data.value)

            # We store label in the EditRole which is used by QTableView to display it. The UserRole is used to
            # save the value, to be used when we'll open a new page with this info
            model = {}
            index = self.my_model.index(row, col, QModelIndex())
            label = self.get_model_label(row, col, arg_data)

            if isinstance(label, QWidget) and hasattr(self, 'setIndexWidget'):
                if self.indexWidget(index):
                    self.indexWidget(index).setParent(None)
                self.setIndexWidget(index, label)
                self.connect(label, SIGNAL('want_update'), self.requestData)
                self.connect(arg_data, SIGNAL('EAS_Message'), self.EAS_SendMessage)
            else:
                if hasattr(self, 'setIndexWidget') and self.indexWidget(index):
                    self.indexWidget(index).setParent(None)
                    self.setIndexWidget(index, None)

                if label is None: label = ''
                if self.fetcher.fragment.name == 'TCPTable' and col == 0:
                    if isinstance(label, int):
                        label = unicode(label)
                    label += ' (' + unicode(arg_data.value) + ')'

                model[Qt.EditRole] = QVariant(unicode(label))

            self.connect(arg_data, SIGNAL('label_changed'), make_lambda(self.label_changed, arg_data, row, col))

            self.keep_python_ref.append(arg_data)
            model[Qt.UserRole] = QVariant(arg_data)

            if 'states' in self.result and id in self.result['states']:
                model[Qt.BackgroundRole] = QVariant(QColor(self.state_colours[self.result['states'][id] % len(self.state_colours)]))

            self.my_model.setItemData(index, model)

    def EAS_SendMessage(self, *args, **kwargs):
        self.emit(SIGNAL('EAS_Message'), *args, **kwargs)

    def requestData(self, time=None):
        self.ready = False
        try:
            self.emit(SIGNAL('updating'))
        except RuntimeError, e:
            # This object seems to be removed, so I leave.
            return
        if time or self.fetcher.type == 'streaming' or self.fetcher.type == 'real-time':
            BaseFragmentView.requestData(self, time)
        else:
            BaseFragmentView.getServerTime(self, self.requestData)

    def requestAllData(self, time=None):
        if time:
            BaseFragmentView.requestAllData(self, time)
        else:
            BaseFragmentView.getServerTime(self, self.requestAllData)


    def updateCSVData(self, results):
        if len(results['table']) == 0:
            return

        self.exportCSVData(results['table'])

    def exportCSVData(self, results):
        labels = []
        data = []

        # Get headers names
        for index in xrange(self.my_model.columnCount()):
            header = self.my_model.horizontalHeaderItem(index).text()
            labels.append(header)

        for line in results:
            newline = []
            for index, string in enumerate(line):
                header = self.my_model.horizontalHeaderItem(index).text()
                name = self.arg_types[unicode(header)]
                if name == 'start_time' or name == 'end_time' or name == 'oob_time_sec':
                    if isinstance(string, int):
                        string = QDateTime.fromTime_t(int(string)).toString()
                newline.append(string)

            data.append(newline)

        with codecs.open(self.filename, "w+", encoding="utf8") as f:
            print >>f, self.formatFields(labels)
            for line in data:
                print >>f, self.formatFields(line)

    def updateData(self, result):

        try:
            self.emit(SIGNAL('updated'))
        except RuntimeError, e:
            # This object is removed, probably because user changes tab before
            # receiving data for this fragment.
            # It doesn't matter, just leave this method, and python object
            # will be completly removed.
            return

#        if len(result['table']) == 0:
#            return False

        self.result = result
        self.data = self.result['table']
        self.rowcount = self.result['rowcount']

        if not self.my_model or len(self.columns) != len(self.result['columns']):
            self.columns = self.result['columns']
            self.my_model = QStandardItemModel(0, len(self.columns), self)
            self.setModel(self.my_model)

        # Set column titles
        for col, name in enumerate(self.columns):
            title = ''
            try:
                title += arg_types[name].label
                self.arg_types[title] = name
            except KeyError:
                title += name
                self.arg_types[title] = name

            self.my_model.setHeaderData(col, Qt.Horizontal, QVariant(title))

        # If this is not an iterable table (with 'start' and 'limit' args), hide useless links.
        if not self.result['args'].has_key('start') or not self.result['args'].has_key('limit'):
            self.firstLink.hide()
            self.prevLink.hide()
            self.nextLink.hide()
            self.lastLink.hide()
        else:
            if self.result['args']['start'] == 0:
                self.firstLink.hide()
                self.prevLink.hide()
            else:
                self.firstLink.show()
                self.prevLink.show()

            if self.result['args']['limit'] > len(self.data):
                self.nextLink.hide()
                self.lastLink.hide()
            else:
                self.nextLink.show()
                # XXX TODO As it currently does NOT work, as the total entries numbers is
                # missing, this link is always hidden.
                self.lastLink.hide()

        if self.my_model.rowCount:
            if self.my_model.rowCount(QModelIndex()) != len(self.data):
                self.my_model.removeRows(0, self.my_model.rowCount(QModelIndex()), QModelIndex())
                self.my_model.insertRows(0, len(self.data), QModelIndex())

        # cleanup
        children = self.findChildren(ArgDataBase)
        for child in children:
            child.setParent(None)
            child.deleteLater()

        self.add_lines()

        self.ready = True
        return True

    def sortBy(self, column_name):
        if ('sort' in self.fragment.args and self.fragment.args['sort'] == 'ASC') or ('sortby' in self.fragment.args and self.fragment.args['sortby'] != column_name):
            self.fragment.args['sort'] = 'DESC'
        else:
            self.fragment.args['sort'] = 'ASC'

        self.fragment.args['sortby'] = column_name
        self.requestData()

    ###
    # Slots.

    def firstAction(self, string):
        try:
            if self.result['args']['start'] == 0:
                return

            self.fragment.args['start'] = 0
        except:
            return
        self.requestData()

    def prevAction(self, string):
        try:
            self.fragment.args['start'] = self.result['args']['start'] - self.result['args']['limit']

            if self.fragment.args['start'] < 0:
                self.fragment.args['start'] = 0

            if self.fragment.args['start'] == self.result['args']['start']:
                return
        except:
            return
        self.requestData()

    def nextAction(self, string):
        # FIXME: Currently rowcount is the number of entries got from this query.
#        if self.result['args']['start'] + self.result['args']['limit'] > self.result['rowcount']:
#            return
        # Trying here to avoid problem with not yet loaded page
        try:
            self.fragment.args['start'] = self.result['args']['start'] + self.result['args']['limit']

            if self.fragment.args['start'] == self.result['args']['start']:
                return
        except:
            return
        self.requestData()


    def lastAction(self, string):
        try:
            self.fragment.args['start'] = self.result['rowcount'] - self.result['args']['limit']
            self.fragment.args['start'] += self.result['args']['limit'] - self.result['rowcount'] % self.result['args']['limit']

            if self.fragment.args['start'] < 0:
                self.fragment.args['start'] = 0

            if self.fragment.args['start'] == self.result['args']['start']:
                return
        except:
            return
        self.requestData()

    def pauseAction(self, string):
        self.fetcher.pause(True)
        self.pauseLink.hide()
        self.playLink.show()

    def playAction(self, string):
        self.fetcher.pause(False)
        self.playLink.hide()
        self.pauseLink.show()

    def csvAction(self, string):

        export_all = False
        if self.user_settings and self.user_settings.compatibility.csvexport_all:
            csvdialog = CSVOption(self)
            if csvdialog.exec_() == QDialog.Rejected:
                return

            export_all = csvdialog.rb_alldata.isChecked()

        self.filename = unicode(QFileDialog.getSaveFileName(self, self.tr("Save File"),
                                               "", self.tr("CSV file (*.csv)")))
        if not self.filename:
            return
        elif not self.filename.endswith('.csv'):
            self.filename += '.csv'

        if export_all:
            if QMessageBox.warning(self, "CSV export",
                                         "Exporting all  data on a period can be very long. Do you want to continue?",
                                         QMessageBox.Ok,
                                         QMessageBox.Cancel) == QMessageBox.Cancel:
                return
            self.requestAllData()
        else:
            self.exportCSVData(self.data)

#        if button == QMessageBox.Cancel:
#            return


    def formatField(self, field):
        text = unicode(field)
        text = text.replace(u'"', u'""')
        return u'"%s"' % text
#
    def formatFields(self, fields):
        return u','.join(self.formatField(field) for field in fields)

    def getToolspace(self):

        toolspace = QWidget()
        vbox = QVBoxLayout(toolspace)
        vbox.setContentsMargins(0, 0, 0, 0)

        # Add the titlebar with arrows
        titlebar = QWidget()

        # The navigation buttons
        self.firstLink = createLink(':/icons-20/go-first.png', self.firstAction, self.tr("First view"))
        self.prevLink = createLink(':/icons-20/go-prev.png', self.prevAction, self.tr("Previous view"))
        self.nextLink = createLink(':/icons-20/go-next.png', self.nextAction, self.tr("Next view"))
        self.lastLink = createLink(':/icons-20/go-last.png', self.lastAction, self.tr("Last view"))
        self.playLink = createLink(':/icons-20/play.png', self.playAction, self.tr("Play"))
        self.pauseLink = createLink(':/icons-20/pause.png', self.pauseAction, self.tr("Pause"))
        self.csv = createLink(':/icons-20/save_disk.png', self.csvAction, self.tr("CSV export"))

        hbox = QHBoxLayout(titlebar)
        hbox.addStretch()
        hbox.addWidget(self.firstLink)
        hbox.addWidget(self.prevLink)
        hbox.addWidget(self.csv)
        hbox.addWidget(self.title)
        if hasattr(self.fetcher, 'pause'):
            hbox.addWidget(self.playLink)
            self.playLink.hide()
            hbox.addWidget(self.pauseLink)
        hbox.addWidget(self.nextLink)
        hbox.addWidget(self.lastLink)
        hbox.addStretch()

        vbox.addWidget(titlebar)
        toolspace.setFixedHeight(35)

        return toolspace
