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

import platform

from PyQt4.QtGui import QAbstractItemView, QHeaderView, QAction, QMenu, QApplication, QClipboard, QLabel
from PyQt4.QtCore import QVariant, Qt, SIGNAL, QRect, QModelIndex

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.args import arg_types
from ufwi_log.client.qt.widgets.table_view import TableView
from ufwi_log.client.qt.views.ufwi_log_base import NulogBaseFragmentView

class TableFragmentView(NulogBaseFragmentView, TableView):

    stretch_list = ['oob_prefix']

    @staticmethod
    def name(): return tr('the table view')

    def __init__(self, fetcher, parent):
        TableView.__init__(self, parent)
        NulogBaseFragmentView.__init__(self, fetcher)

        # Disable edition
        self.setEditTriggers(QAbstractItemView.NoEditTriggers)

        # Define the callback when headers are clicked (sorting function)
        self.connect(self.header, SIGNAL('sectionPressed(int)'), self.sortView)

        self.header.setSortIndicatorShown(True)

    def updateData(self, result):
        if not NulogBaseFragmentView.updateData(self, result):
            return False

        for row in xrange(len(self.data)):
            if self.result['args'].has_key('start'):
                self.my_model.setHeaderData(row, Qt.Vertical, QVariant('%d' % (self.result['args']['start'] + row + 1)))

        # TODO: this function si buggy, please debug it and use it!
        #self.setPaddings()

        stretch_index = None
        # shows a symbol to know if this is the sorted column
        if self.result['args'].has_key('sortby') and self.result['args'].has_key('sort'):
            col_no = 0
            for col, name in enumerate(self.columns):
                if name in self.stretch_list:
                    stretch_index = col_no
                if self.result['args']['sortby'] == name:
                    if self.result['args']['sort'] == 'ASC':
                        self.header.setSortIndicator(col_no, Qt.AscendingOrder)
                    else:
                        self.header.setSortIndicator(col_no, Qt.DescendingOrder)
                col_no += 1

        self.header.setResizeMode(QHeaderView.ResizeToContents)
        # Resize sections to contents
        self.header.resizeSections(QHeaderView.ResizeToContents)
        # Resize automaticaly
        if stretch_index != None:
            self.header.setResizeMode(stretch_index, QHeaderView.Stretch)

        # Give the control of the size back to the user
        #self.header.setResizeMode(QHeaderView.Interactive)


        # Update the context menu of headers
        self.updateHeadersActions()
        self.emit(SIGNAL("showButtons"))

    def sortView(self, index):
        self.sortBy(self.columns[index])

    def mouseMoveEvent(self, event):
        TableView.mouseMoveEvent(self, event)
        if not self.data:
            return

        index = self.indexAt(event.pos())
        # Cursor isn't on a row
        if not index.isValid():
            self.setCursor(Qt.ArrowCursor)
            return

        # get data
        field = unicode(self.columns[index.column()])
        arg_data = self.model().data(self.model().index(index.row(), index.column(), self.rootIndex()), Qt.UserRole).toPyObject()

        arg = arg_types[field]

        hand = False
        if self.cumulative_mode:
            filters = self.fetcher.getArgs()
            args = arg_types[field].get_pagelink_args(field, arg_data)
            for key, value in args.iteritems():
                if key in filters:
                    hand = True
            if not hand and field in filters:
                hand = True
        elif self.current_page:
            hand = bool(self.current_page.get_pagelink_default(field, arg_data))

        if hand:
            self.setCursor(Qt.OpenHandCursor)
        else:
            self.setCursor(Qt.ArrowCursor)

    def copySelection(self):
        indexes = self.selectedIndexes()
        labels = []
        for index in indexes:
            arg_data = self.model().data(index, Qt.UserRole).toPyObject()
            s = arg_data.label
            if isinstance(s, QLabel):
                s = unicode(s.text())
            elif s is None:
                s = u''
            else:
                s = unicode(s)
            labels.append(s)

        text = u'\n'.join(labels)

        clipboard = QApplication.clipboard()
        clipboard.setText(text)

    def mousePressEvent(self, event):

        TableView.mousePressEvent(self, event)
        if event.button() != Qt.RightButton or not self.data:
            return

        index = self.indexAt(event.pos())
        # Cursor isn't on a row
        if not index.isValid():
            return

        if self.indexWidget(index):
            return

        # get data
        field = unicode(self.columns[index.column()])
        arg_data = self.model().data(self.model().index(index.row(), index.column(), self.rootIndex()), Qt.UserRole).toPyObject()

        # Create a menu to display all pages...
        menu = QMenu(self)

        copyAction = QAction(self.tr('Copy text'), self)
        self.connect(copyAction, SIGNAL('triggered()'), self.copySelection)
        menu.addAction(copyAction)

        if self.fragment.type != 'IDSIPSTable':
            packetinfoAction = QAction(self.tr('Packet details'), self)
            self.connect(packetinfoAction, SIGNAL('triggered()'), self._openPacketInfo)
            menu.addAction(packetinfoAction)

        for action in arg_data.actions():
            action.setParent(self)
            menu.addAction(action)

        menu.addSeparator()
        if self.current_page:
            pages = self.current_page.get_pagelinks(field, arg_data)
            if self.user_settings and pages:
                for page in pages:
                    title = self.user_settings['pages'].pages[page].title
                    action = QAction(tr('Open "%s" view') % title, self)

                    # Usefull data used when action is triggered
                    data = [page, field, unicode(arg_data.label), unicode(arg_data.value)]
                    data = QVariant(data)
                    # With PyQt 4.7.3, data type is List instead of StringList:
                    # force the cast to StringList
                    data.convert(QVariant.StringList)
                    action.setData(data)
                    menu.addAction(action)

        #if pages:
        #    menu.addSeparator()

        # And ask user if he wants to create a new page...
        #createPageAction = QAction(self.tr('Create a new view for this entity...'), self)
        #self.connect(createPageAction, SIGNAL("triggered()"), lambda: self.createPageEvent(field, arg_data.label, arg_data.value))
        #menu.addAction(createPageAction)

        self.connect(menu, SIGNAL('triggered(QAction*)'), self.loadPageEvent)

        menu.exec_(event.globalPos())

    def _openPacketInfo(self):
        index = self.selectedIndexes()[0]
        index2 = QModelIndex(index)
        index = index2.sibling(index.row(), 0)
        if not index.isValid():
            return
        self.openPacketInfo(index)

    def createPageEvent(self, field, label, value):
        page = self.createPage(field)
        if not page:
            return

        self.loadPage(field, label, value, page.name)

    def loadPageEvent(self, action):
        if action.data().type() == QVariant.StringList:
            lst = action.data().toStringList()

            pagename = unicode(lst[0])
            field = unicode(lst[1])
            label = unicode(self._removePort(lst[2]))
            value = unicode(self._removePort(lst[3]))

            self.loadPage(field, label, value, pagename)

    def _removePort(self, ip):
        if ':' in ip:
            return ip.split(':')[0]
        return ip

    def mouseDoubleClickEvent(self, event):
        if not self.columns:
            return
        index = self.indexAt(event.pos())
        if not index.isValid():
            return
        self.openPacketInfo(index)

    def openPacketInfo(self, index):
        field = unicode(self.columns[index.column()])
        arg_data = self.model().data(self.model().index(index.row(), index.column(), self.rootIndex()), Qt.UserRole).toPyObject()

        acl_args = {}
        o_index = self.model().index(index.row(), 8, self.rootIndex())

        if index.isValid() and o_index.isValid():
            acl = self.model().data(self.model().index(index.row(), 8, self.rootIndex()), Qt.UserRole).toPyObject()

            if acl and hasattr(acl, 'label') and isinstance(acl.label, QLabel):
                acl_args['acl_label'] = {'tooltip' : acl.label.toolTip(),
                                         'text' : acl.label.text(),
                                         'slot' : lambda: acl.show_acl(acl.value.split(' ')[0].split(':')),
                                         'column' : 'acl',
                                         'value' : acl.value,
                                         }

        if self.cumulative_mode:
            filters = self.fetcher.getArgs()
            args = arg_types[field].get_pagelink_args(field, arg_data)
            filter_added = False
            for key, value in args.iteritems():
                if key in filters:
                    filter_added = True
                    self.emit(SIGNAL('add_filter'), key, value)
                    return
            if field in filters:
                self.emit(SIGNAL('add_filter'), field, value)
            else:
                self.loadPage(field, arg_data.label, arg_data.value, pagename=None, acl=acl_args)
        else:
            self.loadPage(field, arg_data.label, arg_data.value, pagename=None, acl=acl_args)

    def printMe(self, painter, rect):
        painter.save() # save the current scale
        painter.translate(rect.x(), rect.y())

        row_count = len(self.data) + 1
        col_count = len(self.columns)

        if col_count == 0:
            painter.restore() # restore the previous scale
            return

        if row_count < 15:
            cell_h = rect.height() / 15
        else:
            cell_h = rect.height() / row_count

        cell_w = rect.width() / col_count

        # Draw the table
        for row in range(row_count + 1):
            x0 = 0
            y0 = row * cell_h
            x1 = rect.width()
            y1 = y0
            painter.drawLine(x0, y0, x1, y1)

        for col in range(col_count + 1):
            x0 = col * rect.width() / col_count
            y0 = 0
            x1 = x0
            y1 = row_count * cell_h
            painter.drawLine(x0, y0, x1, y1)

        # Draw the cell

        # Compute the optimal font size:
        max_len = 1
        for name in self.columns:
            try:
                title = arg_types[name].label
            except KeyError:
                title = name
            if len(title) > max_len:
                max_len = len(title)

        for row, line in enumerate(self.data):
            for col, cell in enumerate(line):
                labelIndex = self.model().index(row, col, self.rootIndex())
                txt = unicode(labelIndex.data().toString())
                if len(txt) > max_len:
                    max_len = len(txt)

        # Draw the cells
        current_font = painter.font()
        painter.font().setPixelSize(1.5 * cell_w / max_len)
        for row, line in enumerate(self.data):
            for col, cell in enumerate(line):
                labelIndex = self.model().index(row, col, self.rootIndex())
                txt = unicode(labelIndex.data().toString())

                x = col * cell_w
                y = (row + 1) * cell_h
                painter.drawText(QRect(x, y, cell_w, cell_h) , Qt.AlignHCenter | Qt.AlignVCenter, txt)

        painter.font().setBold(True)
        # Draw the titles
        for col, name in enumerate(self.columns):
            title = ''
            try:
                title = arg_types[name].label
            except KeyError:
                title = name

            x = col * cell_w
            y = 0
            painter.drawText(QRect(x, y, cell_w, cell_h) , Qt.AlignHCenter | Qt.AlignVCenter, title)

        painter.restore() # restore the previous scale
