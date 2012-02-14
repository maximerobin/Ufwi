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

from PyQt4.QtCore import SIGNAL, Qt, QRect, QUuid
from PyQt4.QtGui import QMessageBox, QInputDialog, QLineEdit, QLabel, QApplication, QPainter, QPaintEvent, QPixmap

from ufwi_log.client.qt.args import arg_types, Interval

class BaseFragmentView:
    state_colours = ['#e6a9ab', '#cae1a5']

    @staticmethod
    def name(): raise NotImplementedError()

    def __init__(self, fetcher):
        self.fetcher = fetcher
        self.connect(self.fetcher, SIGNAL("want_update"), self.requestData)
        self.fragment = fetcher.fragment
        self.cumulative_mode = False
        self.interval = Interval('daily')

        self.reset_start = False
        self.saved_start = 0
        self.is_closed = False

        self.uuid = QUuid.createUuid().toString()

        # ugl, ugl, ugl, it's ugly yeah \o/
#        print type(self.parent().window)
        if hasattr(self.parent().window, 'current_page'):
            self.current_page = self.parent().window.current_page
        else:
            self.current_page = None
        self.user_settings = None

        # XXX this is ugly
        # TODO kill the crap who has written this.
        top_window = self.parent()
        while top_window:
            try:
                self.user_settings = top_window.user_settings
            except AttributeError:
                top_window = top_window.parent()
            else:
                break

        self.title = QLabel()
        self.title.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.title.setStyleSheet('font: bold 13px')

    #def destroy(self, *args, **kwargs):
    #    import gc
    #    from pprint import pprint
    #    pprint(gc.get_referrers(self))

    #    QWidget.destroy(self, *args, **kwargs)

    def setClosed(self):
        self.is_closed = True

    def destructor(self):
        pass
#        self.fetcher.unref(self.updateData)
#        self.disconnect(self.fetcher, SIGNAL("want_update"), self.requestData)

    def getServerTime(self, callback):
        self.fetcher.getTime(callback)

    def requestAllData(self, time=None):

        if not time:
            return self.getServerTime(self.requestData)

        self.interval.setServerTime(int(float(time)))
        self._argsTime()

        self.fragment.args.update({'no_limit' : True})
        self.fetcher.fetch(self.updateCSVData)
        self.fragment.args.pop('no_limit')

    def requestData(self, time=None):
        if self.fetcher.type == 'streaming' or self.fetcher.type == 'real-time':
            self.fetcher.fetch(self.updateData)
            return
        # search for already set start time (will override range)
        if self.interval != None and self.interval.getMode() != 'search':

            if not time:
                return self.getServerTime(self.requestData)

            self.interval.setServerTime(int(float(time)))
            self._argsTime()

            # FIXME may be unecessary
            #time_args = {'timestamp': starttime}
            #self.fragment.args.update(time_args)

        self.fetcher.fetch(self.updateData)

    def _argsTime(self):
        starttime = self.interval.getStart().toTime_t()
        endtime = self.interval.getEnd().toTime_t()
        time_args = {'start_time': starttime, 'end_time': endtime}
        self.fragment.args.update(time_args)
        starttime = unicode(self.interval.getStart().toString(Qt.ISODate))
        endtime = unicode(self.interval.getEnd().toString(Qt.ISODate))
        time_args = {'session_start_time': starttime, 'session_end_time': endtime}
        self.fragment.args.update(time_args)

        if self.fetcher.args:
            self.reset_start = True

        if self.fragment.args.has_key('start'):
            if self.reset_start:
                self.reset_start = False
                self.saved_start = self.fragment.args['start']
                self.fragment.args['start'] = 0
            else:
                if self.fragment.args['start'] == 0:
                    self.fragment.args['start'] = self.saved_start
                    self.saved_start = 0

    def updateData(self, result): raise NotImplementedError()

#    def isPrintable(self): return False
    def isReady(self): return True

    def getTitle(self): return self.fragment.title

    def getActions(self): return []

    def ask_to_create_page(self, pagename):
        reply = QMessageBox.question(None, self.tr("Create a new view"),
                                           unicode(self.tr(
"""There is no view linked to this kind of data:
    %s
Do you want to create it?""")) % pagename, QMessageBox.Yes | QMessageBox.No)

        if reply != QMessageBox.Yes:
            return None

        return self.createPage(pagename)

    def createPage(self, field):
        ok = False
        try:
            title = arg_types[field].label
        except KeyError:
            title = field

        title, ok = QInputDialog.getText(None, self.tr('Create a new view'),
                                           self.tr('Please enter the new view title:'),
                                           QLineEdit.Normal,
                                           title)

        if ok and title:
            page = self.user_settings.createPage(field)
            page.title = unicode(title)
            arg_types[field].add_pagelink(page.name)
            return page

        return None

    def loadPage(self, field, label, value, pagename, acl=None):
        if not self.current_page:
            return

        compatibility = self.user_settings.compatibility
        arg_data = arg_types[field].data(field, (label, value), compatibility=compatibility, transform_label=False)

        if not pagename:
            pagename = self.current_page.get_pagelink_default(field, arg_data)

        if not pagename:
            return
            #page = self.ask_to_create_page(field)
            #if not page:
            #    return

            #pagename = page.name

        args = self.current_page.get_pagelink_args(field, arg_data, self.fetcher.args)
        if acl:
            args.update(acl)
        self.emit(SIGNAL("open_page"), pagename, args)

    def setCumulative(self, cumulative):
        self.cumulative_mode = cumulative

    def setInterval(self, interval):
        self.interval = interval

    def getToolspace(self):
        return self.title

    def printMe(self, painter, rect):
        # redirect table's painting on a pixmap

        view = self.viewport() if hasattr(self, "viewport") else self

        pixmap = QPixmap.grabWidget(view, view.rect())

        QPainter.setRedirected(view, pixmap)
        event = QPaintEvent(QRect(0, 0, view.width(), view.height()))
        QApplication.sendEvent(view, event)
        QPainter.restoreRedirected(view)

        # print scaled pixmap
        pixmap = pixmap.scaled(rect.width(), rect.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        painter.drawPixmap(rect, pixmap, pixmap.rect())
