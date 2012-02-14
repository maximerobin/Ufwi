#coding: utf-8

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
"""

from copy import copy, deepcopy
from sys import exit
import random

from PyQt4.QtGui import QMessageBox, QAction, QInputDialog, \
                        QLineEdit, QIcon, QPixmap, QMenuBar, \
                        QMenu, QActionGroup
from PyQt4.QtCore import SIGNAL, QVariant, Qt

from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common.human import humanFilesize

from ufwi_rpcc_qt.application import create_ufwi_rpcd_application
from ufwi_rpcc_qt.central_window import CentralWindow
from ufwi_rpcc_qt.central_window import EMBEDDED
from ufwi_rpcc_qt.central_window import STANDALONE

from ufwi_log.client.qt.widgets.pages_list import PagesListWidget
from ufwi_log.client.qt.frag_splitter import FragSplitter
from ufwi_log.client.qt.args import Args, Interval
from ufwi_log.client.qt.ui.ufwi_log_ui import Ui_UfwiLogWindow
from ufwi_log.client.qt.config_window import ConfigDialog
from ufwi_log.client.qt.dbinfo import DBInfoDialog
from ufwi_log.client.qt.addfrag_window import AddFragDialog
from ufwi_log.client.qt.range_window import ChooseRangeDialog
from ufwi_log.client.qt.user_settings import UserSettings
from ufwi_log.client.qt.user_settings.page import Page
from ufwi_log.client.qt.printer import PrintDialog, RemoteReportDialog as ReportDialog
from ufwi_log.client.qt.info_area import InfoAreaWidget
from ufwi_log.client.qt.widgets.filters_list import FiltersListWidget
from ufwi_log.client.qt.fetchers.base import GenericFetcher
from ufwi_log.client.qt.views.graphics_view import GraphicsView
from ufwi_log.client.qt.views.packetinfo import PacketInfoFragmentView
from ufwi_log.client.qt.autorefresh import AutorefreshDialog
#from ufwi_log.client.qt.ui.autorefresh_ui import Ui_Dialog

## Activate the "layout creation" mode.
# When it's true, when a page is instancied from a template (for any
# argument link), if you change the layout of this page, it's applied
# to the template page.
LAYOUT_CREATION = True

class UfwiLogMainWindow(CentralWindow):
    ROLES = set(('log_read', 'log_write'))
    ICON = ':/icons/monitoring.png'

    def __init__(self, application, client, standalone=EMBEDDED, parent=None, eas_window=None):

        CentralWindow.__init__(self, client, parent, eas_window)
        self.use_edenwall = False
        self.is_loaded = False
        self.standalone = standalone

        self.setupCentralWindow(application, standalone)
        self.setWindowIcon(QIcon(":icons/appicon.png"))
        self.ui = Ui_UfwiLogWindow()
        self.ui.setupUi(self)

        self.frag_widgets = []
        self.user_settings = None
        self.user_settings = UserSettings(self, client)
        self.createMenu(standalone)

        # pages history (used with the prev/next buttons)
        self.history = {'prev': [],
                        'next': []}

        self.client = client
        self.current_page = None
        self.cumulative_mode = False

        self.row_size_estimation = None
        self.row_count_week = None
        self.db_size = None

        self.interval = Interval('hourly')

        self.dbinfo_dialog = None

        self.ui.info_area = InfoAreaWidget(None)
        self.ui.info_area.setReadOnly(True)
        self.ui.info_area.setObjectName("InfoArea")
        self.ui.info_dock.setWidget(self.ui.info_area)

        self.ui.pages_list = PagesListWidget(self.user_settings, self)
        self.ui.pages_dock.setWidget(self.ui.pages_list)

        self.ui.vertical_splitter = FragSplitter(self.client, self)
        self.ui.scrollArea.setWidget(self.ui.vertical_splitter)

        self.ui.filters_list = FiltersListWidget(client, self)
        self.ui.filters_list.setCompatibility(self.user_settings.compatibility)
#        self.ui.titleLayout.addWidget(self.ui.filters_list)
        self.ui.horizontalLayout_2.insertWidget(3, self.ui.filters_list)

        self.interval.setGUI(self.ui.updateinterval)

        index = self.ui.updateinterval.findData(QVariant(self.getInterval().getMode()))
        if index >= 0:
            self.ui.updateinterval.setCurrentIndex(index)

        self.connectSlots()
        self.updated = False

    def isReadOnly(self):
        return not 'log_write' in self.getRoles()

    def connectSlots(self):
        self.ufwi_log_actions = [
                (self.ui.actionAddFragment, self.showAddFragmentDialog),
                (self.ui.actionCreateCustomPage, self.createCustomPage),
                (self.ui.actionInfo, self.showInfoDialog),
                (self.ui.actionSearch, self.showSearchDialog),
                (self.ui.actionPrint, self.showPrintDialog),
                (self.ui.actionCreateReport, self.showReportDialog),
                (self.ui.actionResetSettings, self.resetSettings),
                (self.ui.actionQuit, self.close),
                (self.ui.actionClose, self.closePage),
                (self.ui.actionPrevious, self.prevPage),
                (self.ui.actionNext, self.nextPage)]

        self.ufwi_log_actions.insert(0, (self.ui.actionSettings, self.showConfigDialog))

        for action, slot in self.ufwi_log_actions:
            self.connect(action, SIGNAL("triggered()"), slot)

        self.connect(self.ui.actionUpdate, SIGNAL('triggered()'), self.updateFragments)
        self.connect(self.ui.actionToggleCumulative, SIGNAL("toggled(bool)"), self.toggleCumulative)
        self.connect(self.ui.pages_list, SIGNAL(PagesListWidget.SIG_OPEN_PAGE), self.loadPage)

        title_action = QAction(tr('Change title...'), self.ui.title)
        self.connect(title_action, SIGNAL('triggered()'), self.changeTitle)
        self.ui.title.addAction(title_action)
        self.ui.frame.addAction(title_action)

        self.connect(self.ui.filters_list, SIGNAL('removeFilter'), self.removeFilter)
        self.connect(self.ui.filters_list, SIGNAL('changeFilter'), self.changeFilter)

        self.connect(self.ui.updateinterval, SIGNAL('activated (int)'), self.intervalChanged)
        self.connect(self.ui.actionDisableAnimation, SIGNAL("triggered(bool)"), self.ui.vertical_splitter.disableAnimation)
        #self.connect(self.ui.actionDisableAutoRefresh, SIGNAL("triggered(bool)"), self.ui.vertical_splitter.autoRefresh)
        self.connect(self.ui.actionDisableAutoRefresh, SIGNAL("triggered(bool)"), self.autoRefreshDialog)

    def autoRefreshDialog(self):
        checked = self.ui.vertical_splitter.autoRefresh()
        dialog = AutorefreshDialog(checked)
        if dialog.exec_():
            seconds = None
            checked = dialog.cb_autorefresh.isChecked()
            seconds = dialog.te_seconds.value()
            self.ui.vertical_splitter.setAutoRefresh(checked, seconds)

    def createMenu(self, standalone):
        menubar = QMenuBar(self)
        menuFile = QMenu(self.tr("&File"), menubar)
        menuView = QMenu(self.tr("&View"), menubar)
        self.setMenuBar(menubar)

        menuFile.addAction(self.ui.actionSettings)
        menuFile.addSeparator()
        menuFile.addAction(self.ui.actionInfo)
        menuFile.addAction(self.ui.actionSearch)
        menuFile.addAction(self.ui.actionPrint)
        menuFile.addAction(self.ui.actionCreateReport)
        menuFile.addSeparator()
        menuFile.addAction(self.ui.actionResetSettings)
        if standalone == STANDALONE:
            menuFile.addSeparator()
            menuFile.addAction(self.ui.actionQuit)

        menuView.addAction(self.ui.actionPrevious)
        menuView.addAction(self.ui.actionNext)
        menuView.addAction(self.ui.actionClose)
        menuView.addAction(self.ui.actionCreateCustomPage)
        menuView.addSeparator()
        menuView.addAction(self.ui.actionUpdate)
        menuView.addAction(self.ui.actionToggleCumulative)
        menuView.addAction(self.ui.actionAddFragment)

        self.menuRemoveFragment = QMenu(self.tr("&Delete Fragment"), menuView)
        self.menuRemoveFragment.setEnabled(False)

        menuView.addSeparator()
        self.ui.actionDisableAnimation.setCheckable(True)
        menuView.addSeparator()
        menuView.addAction(self.ui.actionDisableAnimation)
        menuView.addAction(self.ui.actionDisableAutoRefresh)

        menuView.addAction(self.menuRemoveFragment.menuAction())
        menubar.addAction(menuFile.menuAction())
        menubar.addAction(menuView.menuAction())

    def load(self):
        try:
            self.user_settings.load()

            # Remove ConUserTable fragment if nuauth_command is not loaded.
            have_nuauth_command = self.client.call('CORE', 'hasComponent', 'nuauth_command')
            if not have_nuauth_command:
                for page in self.user_settings['pages'].pages.values():
                    for frame in page.frames:
                        for j, (frag_name, frag) in enumerate(frame.frags):
                            if frag_name == 'ConUserTable':
                                frame.frags.pop(j)

        except Exception:
            self.disable_ui()
            raise
        else:
            server_version = self.user_settings.compatibility.ufwi_log_server_version
            self.setStatus("Nulog version %s" % server_version, 0)

            self.is_loaded = True
            self.enable_ui()
            self.loadPage(self.getMainPage())

    def quit(self):
        # Save user settings_
        if self.user_settings:
            self.user_settings.save()
        for fragwidget in self.frag_widgets:
            fragwidget.destructor()
        CentralWindow.quit(self)

    def disable_ui(self):
        self.ui.frame.setEnabled(False)
        for action, slot in self.ufwi_log_actions:
            action.setEnabled(False)

    def enable_ui(self):
        self.ui.frame.setEnabled(True)
        for action, slot in self.ufwi_log_actions:
            action.setEnabled(True)

    def database_error(self, error):
        """ Called when there is a database error, and ask user to reconfigure the UfwiLog backend """

        reply = QMessageBox.question(self, self.tr("Database connection is not configured correctly"),
                                           self.tr("The following error has occurred:\n") +
                                           exceptionAsUnicode(error) + u"\n" +
                                           self.tr("Do you want to configure it now?"),
                                           QMessageBox.Yes | QMessageBox.No);
        if reply == QMessageBox.Yes:
            return ConfigDialog(self.client, self).run()

        return False

    def loadPagesList(self):
        self.ui.pages_list.loadPagesList()

    def loadPage(self, page):
        self.emit(SIGNAL("closed"))
        if self.current_page:
            self.history['next'] = []
            self.history['prev'].append(self.current_page.name)
        return self._loadPage(page)

    def _loadPage(self, page):
        self.ui.pages_list.setEnabled(False)
        try:
            self._doLoadPage(page)
        finally:
            self.ui.pages_list.setEnabled(True)


    def _doLoadPage(self, page):
        """
            Switch page on main window to an other.
            It adds fragments and update them.

            @param page a Page object
        """

        self.ui.pages_list.setEnabled(False)
        self.ui.pages_list.repaint()
        if self.current_page:
            self.client.async().flushQueue()
            frag_widgets = copy(self.frag_widgets)
            for fragwidget in frag_widgets:
                self.removeFragment(fragwidget, delete=False)

            if self.current_page.search_page != page.search_page:
                self.setSearchMode(page.search_page)

        self.current_page = page
        self.loadPagesList()
        self.frag_widgets = []
        if page.title:
            title = page.title
            self.ui.title.setText('<b>%s</b>' % title)
        else:
            title = None
            self.ui.title.setText(tr('<b>(No name)<b>'))
        ctitle = '%s [%s]' % (title, self.interval.display())
        self.setCentralWindowTitle(tr('Logs'), self.client, ctitle)

        if page.force_cumulative:
            self.setCumulative(True)
            self.ui.actionToggleCumulative.setEnabled(False)
        else:
            self.setCumulative(False)
            self.ui.actionToggleCumulative.setEnabled(bool(page.filters))

        index = self.ui.updateinterval.findData(QVariant(self.getInterval()))
        if index >= 0:
            self.ui.updateinterval.setCurrentIndex(index)

        self.ui.pagePrevButton.setEnabled(bool(self.history['prev']))
        self.ui.pageNextButton.setEnabled(bool(self.history['next']))

        self.menuRemoveFragment.clear()
        self.ui.vertical_splitter.reset()

        for frame in self.current_page.frames:
            for fragname, fragment in frame.frags:
                fragwidget = self.addFragment(fragment, frame.pos)
                fragwidget.pos = frame.pos

                if 'acl_label' in page.args:
                    label = page.args.pop('acl_label')
                    if isinstance(fragwidget.view, PacketInfoFragmentView):
                        fragwidget.view.setACL(label)

                # Create Actions
                self.addFragRemoveAction(fragment.title, fragment.name)
                self.addFragPositionAction(frame, len(self.current_page.frames))

        if len(self.menuRemoveFragment.actions()) > 0:
            self.menuRemoveFragment.setEnabled(True)

        if not self.updated:
            self.updateFragments(reconfigure=True)

#        self.ui.pages_list.setEnabled(True)

    def addFragRemoveAction(self, title, name):
        action = QAction(title, self)
        action.setObjectName(name)
        action.setVisible(True)
        self.connect(action, SIGNAL("triggered()"), self.removeSelectedFragment)
        self.menuRemoveFragment.addAction(action)

    def addFragPositionAction(self, frame, nb_frags):
        if len(self.frag_widgets) == 0:
            return

        frag_widget = self.frag_widgets[len(self.frag_widgets) - 1]
        pos = frame.pos

        action_group = QActionGroup(frag_widget)
        for index in xrange(nb_frags):
            action = QAction(unicode(index + 1), frag_widget)
            action.setData(QVariant(frame.pos))
            action_group.addAction(action)
            frag_widget.pos_menu.addAction(action)
            self.connect(action, SIGNAL("triggered(bool)"), self.positionFragment)
            action.setCheckable(True)

            checked = False
            if index == pos:
                checked = True
            action.setChecked(checked)

    def positionFragment(self, checked):
        try:
            action = self.sender()
            pos = int(action.text()) - 1
            old_pos = action.data().toInt()[0]
        except Exception:
            return

        self.changedPositionFragment(pos, old_pos)

    def changedPositionFragment(self, pos, old_pos):
        offset = 1
        if old_pos - pos < 0:
            offset = -1

        child = self.ui.pages_list.currentItem()
        child_index = self.ui.pages_list.indexFromItem(child)

        page_name = child.data(0, Qt.UserRole).toString()
        parent = child.parent()
        section_name = parent.data(0, Qt.UserRole).toString()

        frames_pos = {}

        pos_changed = False
        for section in self.user_settings['pagesindex'].sections:
            if section.name == section_name:
                for page in section.pages:
                    if page[0] == page_name:
                        for frame in page[1].frames:
                            new_frame = deepcopy(frame)
                            if new_frame.pos == old_pos and not pos_changed:
                                new_frame.pos = pos
                                pos_changed = True
                            else:
                                if offset == -1 and (new_frame.pos >= old_pos and new_frame.pos <= pos) \
                                or offset == 1 and (new_frame.pos <= old_pos and new_frame.pos >= pos):
                                    new_frame.pos = new_frame.pos + offset

                            frames_pos[new_frame.pos] = new_frame

        while len(self.frag_widgets) != 0:
            self.frag_widgets[0].emit(SIGNAL('closed'))
            self.removeFragment(self.frag_widgets[0], True)


        self.menuRemoveFragment.clear()
        for pos, frame in sorted(frames_pos.iteritems()):
            for frag in frame.frags:
                self.current_page.addFragment(frag[1], pos)
                frag_widget = self.addFragment(frag[1], pos)
                if frag_widget.pos != pos:
                    frag_widget.pos = pos
                self.addFragRemoveAction(frag[1].title, frag[1].name)

            self.addFragPositionAction(frame, len(frames_pos))

        self.user_settings.save()
        self.user_settings.load()

        child = self.ui.pages_list.itemFromIndex(child_index)
        self.ui.pages_list.emit(SIGNAL("itemPressed(QTreeWidgetItem*,int)"), child, 0)

    def closePage(self):
        self.ui.pages_list.removePage(self.current_page.name)

    def getMainPage(self):
        # try to get the first page in pages list
        try:
            page_name = self.user_settings['pagesindex'].sections[0].pages[0][0]
        except IndexError:
            page_name = 'main'

        return self.ui.pages_list.getPage(page_name)


    def addFragment(self, fragment, pos_hint= -1):
        """
            Add a fragment on window.

            @param fragment [Fragment] object defined in user_settings.py to describe
                                       fragment properties.
            @param pos_hint [int]  if >= 0, ask to put fragment as a special position.
                                   This is a hint because if there isn't enough fragments,
                                   it'll placed at the next available position.
        """

        fragwidget = self.ui.vertical_splitter.addFragment(fragment, self.current_page.args, pos_hint)
        fragwidget.setCumulative(self.cumulative_mode)

        self.connect(fragwidget, SIGNAL('removeFragment()'), lambda: self.removeFragment(fragwidget, delete=True))
        self.connect(fragwidget, SIGNAL('open_page'), self._open_page)
        self.connect(fragwidget, SIGNAL('add_filter'), self.changeFilter)
        self.connect(fragwidget, SIGNAL('EAS_Message'), self.EAS_SendMessage)
        self.frag_widgets.append(fragwidget)
        self.connect(self, SIGNAL("closed"), fragwidget, SIGNAL("closed"))

        return fragwidget


    def removeFragment(self, fragwidget, delete=False):
        """
            Remove fragment from layout.

            @param fragwidget [QWidget]  removed widget
            @param delete [bool]  if true, delete fragment from page.
        """

        if delete:
            self.current_page.removeFragment(fragwidget.getFragment().name)
            self.current_page.setDefault(False)
            if self.user_settings.isOrphan(fragwidget.getFragment()):
                self.user_settings.removeFragment(fragwidget.getFragment())

        self.disconnect(fragwidget, SIGNAL('open_page'), self._open_page)
        self.disconnect(fragwidget, SIGNAL('add_filter'), self.changeFilter)
        #self.disconnect(fragwidget, SIGNAL('removeFragment()'), None)

        self.frag_widgets.remove(fragwidget)
        self.ui.vertical_splitter.removeFragment(fragwidget)

    ###########################
    #     SLOTS               #
    ###########################

    def changeTitle(self):
        if not self.current_page:
            return

        title, ok = QInputDialog.getText(self, tr('Change view title'),
                                               tr('Enter new title:'),
                                               QLineEdit.Normal,
                                               self.current_page.title)

        if ok:
            title = unicode(title)
            self.current_page.title = title
            self.current_page.setDefault(False)
            self.ui.title.setText('<b>%s</b>' % title)
            self.loadPagesList()

    def showConfigDialog(self):
        if ConfigDialog(self.client, self).run():
            self.updateFragments()

    def showAddFragmentDialog(self):
        try:
            if AddFragDialog(self, None, self).run():
                self.updateFragments()
        except Exception, err:
            self.writeError(err, "Error when adding a fragment")

    def removeSelectedFragment(self):
        current_action = self.sender()

        for frag_widget in self.frag_widgets:
            if current_action.objectName() == frag_widget.fragment.name:
                self.user_settings.removeFragment(frag_widget.fragment)
                self.user_settings.save()
                self.user_settings.load()
                self._open_page(self.current_page.name, self.current_page.args)
                break

    def createCustomPage(self):
        # create an empty page
        name = 'custom'
        while self.user_settings['pages'].pages.has_key(name):
            name = '%s_%d' % (name, random.randint(0, 999999))
        self._open_page(name, {})

    def resetSettings(self):
        reply = QMessageBox.question(self, self.tr("Reset layout settings"),
                                           self.tr("Your history, bookmarks and customized views " \
                                                   "will be deleted.\n" \
                                                   "Default views will also be reseted.\n" \
                                                   "\n" \
                                                   "Are you sure?"),
                                           QMessageBox.Yes | QMessageBox.No);
        if reply == QMessageBox.Yes:
            self.user_settings.reset()
            self.loadPage(self.getMainPage())


    def _showInfoDialog(self, row_size_estimation, row_count_week, db_size):
        try:
            row_size_estimation = row_size_estimation[0][0]
            row_count_week = row_count_week[0][0]
            db_size = db_size[0][0]
        except Exception, err:
            self.writeError(err, "Error in info dialog")

        if not self.dbinfo_dialog:
            self.dbinfo_dialog = DBInfoDialog(self)

        self.dbinfo_dialog.ui.label_row_number.setText("%d" % row_size_estimation[0])
        self.dbinfo_dialog.ui.label_row_number_lastweek.setText("%d" % row_count_week[0])
        self.dbinfo_dialog.ui.label_dbsize.setText("%s" % db_size[1])
        total_size = int(db_size[2]) * int(db_size[3])
        total_size_str = humanFilesize(total_size)
        self.dbinfo_dialog.ui.label_total_size.setText("%s" % total_size_str)
        if (total_size == 0):
            total_size = 1;
        pc = (int(db_size[0]) * 100) / total_size
        self.dbinfo_dialog.ui.progressBar.setValue(pc)
        # compute estimation of remaining time to log, according to row_count_week
        if row_count_week[0] > 1000:
            estimated_required_size_per_week = row_count_week[0] * row_size_estimation[1]
            estimated_remaining_time = (total_size) / estimated_required_size_per_week
            # XXX 52 (weeks) is a default value. Maybe we could look at the configured value for rotation in settings
            if estimated_remaining_time < 52:
                self.dbinfo_dialog.ui.label_icon_info.setPixmap(QPixmap(":/icons-32/warning.png"))
            self.dbinfo_dialog.ui.label_info.setText(tr("At this rate, the database can store %.02f weeks of data") % estimated_remaining_time)
        else:
            self.dbinfo_dialog.ui.label_info.setText(tr("There is not enough data to compute an estimation"))
        self.dbinfo_dialog.show()

        self.row_size_estimation = None
        self.row_count_week = None
        self.db_size = None

    def _getRowSizeEstimation(self, size):
        self.row_size_estimation = size
        if self.row_count_week and self.db_size:
            self._showInfoDialog(self.row_size_estimation, self.row_count_week, self.db_size)

    def _getRowCountWeek(self, count):
        self.row_count_week = count
        if self.row_size_estimation and self.db_size:
            self._showInfoDialog(self.row_size_estimation, self.row_count_week, self.db_size)

    def _getDBSize(self, size):
        self.db_size = size
        if self.row_size_estimation and self.row_count_week:
            self._showInfoDialog(self.row_size_estimation, self.row_count_week, self.db_size)

    def showInfoDialog(self):
        # get database information
        try:
            row_size_estimation = self.client.async().call('ufwi_log', 'get_row_size_estimation', callback=self._getRowSizeEstimation)
            row_count_week = self.client.async().call('ufwi_log', 'get_row_count_week', callback=self._getRowCountWeek)
            db_size = self.client.async().call('ufwi_log', 'get_db_size', callback=self._getDBSize)
        except Exception, err:
            self.writeError(err, "Error in info dialog")


    def showSearchDialog(self):
        fragment = self.user_settings.createFragment('PacketTable')
        fragment.type = 'PacketTable'
        fragment.view = 'table'

        window = AddFragDialog(self, fragment, self)
        window.ui.headerWidget.hide()
        window.setWindowTitle(tr("Search"))
        if window.run():
            page = Page("searchPage")
            page.title = tr('Search result')
            page.search_page = True
            page.addFragment(fragment)
            self._open_page(page, fragment.args)
        else:
            self.user_settings.removeFragment(fragment)

    def showPrintDialog(self):
        PrintDialog(self.user_settings, self).run()

    def showReportDialog(self):
        ReportDialog(self.user_settings, self.client, self).run()

    def updateFragments(self, reconfigure=False):
        """
            Update data in fragments
            @param reconfigure [bool] when set, if update fails, we ask user to reconfigure ufwi_log backend
        """

        if not self.is_loaded:
            self.updated = True
            self.load()
        self.updated = False

        for frag in self.frag_widgets:
            frag.setInterval(self.interval)

        if not self.current_page:
            return

        self.ui.filters_list.update(self.current_page.args, self.current_page.filters)

        while True:
            try:
                GraphicsView.UPDATE_ALL = True
                self.ui.vertical_splitter.animation_manager.init()
                for frag in self.frag_widgets:
                    if frag.view.is_graphics_view:
                        frag.updateData()
                    else:
                        frag.updateData()
                return
            except RpcdError, err:
                if reconfigure and err.type == 'DatabaseError':
                    ok = self.database_error(err)
                    if not ok:
                        return
                else:
                    self.ufwi_rpcdError(err)
                    return

    def toggleCumulative(self):
        self.setCumulative(self.ui.actionToggleCumulative.isChecked())

    def setCumulative(self, c):
        if self.cumulative_mode == c:
            return

        self.cumulative_mode = c
        self.ui.actionToggleCumulative.setChecked(c)

        for frag in self.frag_widgets:
            frag.setCumulative(self.cumulative_mode)

    def setInterval(self, value):
        self.ui.vertical_splitter.animation_manager.init()
        if value == 'custom':
            window = ChooseRangeDialog(self, self)
            if window.run():
                # TODO Improve write new range somewhere on UI
                message = unicode(self.tr("""<b>Range selected:</b>
                    <table><tr><td><b>Start:</b></td><td>%s</td></tr>
                    <tr><td><b>End:</b></td><td>%s</td></tr></table>""")) % (self.interval.getStart().toString(), self.interval.getEnd().toString())
                self.ui.info_area.setText(message)
                self.updateFragments(reconfigure=True)
            else:
                index = self.ui.updateinterval.findData(QVariant(self.getInterval().getMode()))
                if index >= 0:
                    self.ui.updateinterval.setCurrentIndex(index)
                return
        elif value == 'search':
            self.interval = Interval(value)
            index = self.ui.updateinterval.findData(QVariant(self.getInterval().getMode()))
            if index >= 0:
                self.ui.updateinterval.setCurrentIndex(index)
            return
        if self.interval.getMode() != value:
            self.interval = Interval(value)
            self.ui.info_area.setText("")
            self.updateFragments(reconfigure=True)
            index = self.ui.updateinterval.findData(QVariant(self.getInterval().getMode()))
            if index >= 0:
                self.ui.updateinterval.setCurrentIndex(index)
        ctitle = '%s [%s]' % (self.current_page.title, self.interval.display())
        self.setCentralWindowTitle(tr('Logs'), self.client, ctitle)

    def getInterval(self):
        return self.interval

    def setSearchMode(self, value):
        if value == True:
            self.ui.updateinterval.addItem(tr('Search mode'), QVariant('search'))
            self.ui.updateinterval.setEnabled(False)
            self.setInterval('search')
        else:
            index = self.ui.updateinterval.findData(QVariant('search'))
            if index > 0:
                self.ui.updateinterval.removeItem(index)
            self.ui.updateinterval.setEnabled(True)
            self.setInterval('daily')

    def set_page_title(self, page):
        args_label = Args(page.args, GenericFetcher(self.client)).labels()
        if args_label:
            if page.title:
                page.title = tr('%s: %s') % (page.title, args_label)
            else:
                page.title = args_label

    def _open_page(self, page, args):
        """
            Creates a new page window.

            @param page [str/Page]  Page object to use in new window, or the page name.
            @param args [dict]  with fragments filter
        """
        if not isinstance(page, Page):
            page = self.ui.pages_list.getPage(page)

        # create a copy of the main
        if 'custom' in page.name:
            newpage = page
        else:
            newpage = self.user_settings.createPage(page.name, 'history')
        newpage.args = args
        if LAYOUT_CREATION:
            # If we are in the layout creation mode, we keep reference to the default page.
            # This is usefull, because when the layout of the page instance is modified, the
            # template instance is too. It is only true if the page is instancied at this runtime.
            newpage.frames = page.frames
        else:
            newpage.frames = [copy(frame) for frame in page.frames] # copy the list object but not the Fragment instances

        newpage.title = page.title
        newpage.pagelinks = page.pagelinks.copy()
        newpage.filters = copy(page.filters)
        newpage.force_cumulative = page.force_cumulative
        newpage.search_page = page.search_page
        #self.set_page_title(newpage)

        # keep only 10 values in history
        for section in self.user_settings['pagesindex'].sections:
            if section.name == 'history':
                if len(section.pages) > 10:
                    section.pages.pop(0)
                    break

        self.loadPage(newpage)

    def removeFilter(self, filter):
        try:
            self.current_page.args.pop(filter)
        except KeyError:
            return

        self.current_page.title = self.current_page.title.split(':')[0]
        self.set_page_title(self.current_page)
        self.ui.title.setText('<b>%s</b>' % self.current_page.title)

        self.updateFragments(reconfigure=True)

    def changeFilter(self, key, value):
        self.current_page.args[key] = value

        self.current_page.title = self.current_page.title.split(':')[0]
#        self.set_page_title(self.current_page)
        self.ui.title.setText('<b>%s</b>' % self.current_page.title)

        self.updateFragments(reconfigure=True)

    def intervalChanged(self, index):
        if (self.interval.getMode() == 'search'):
            return
        new_interval = self.ui.updateinterval.itemData(index).toString()
        if (self.getInterval() != new_interval):
            self.setInterval(new_interval)

    def nextPage(self):
        try:
            while 1:
                try:
                    page = self.user_settings['pages'].pages[self.history['next'].pop(0)]
                except KeyError:
                    continue
                else:
                    break

            self.history['prev'].append(self.current_page.name)
            self._loadPage(page)
        except IndexError:
            self.ui.pageNextButton.setEnabled(False)
            return

    def prevPage(self):
        try:
            while 1:
                try:
                    page = self.user_settings['pages'].pages[self.history['prev'].pop()]
                except KeyError:
                    continue
                else:
                    break

            self.history['next'].insert(0, self.current_page.name)
            self._loadPage(page)
        except IndexError:
            self.ui.pagePrevButton.setEnabled(False)
            return

if __name__ == "__main__":
    app, client = create_ufwi_rpcd_application(
        name="ufwi_log",
        resource="",
        locale="")
    window = UfwiLogMainWindow(app, client, standalone=STANDALONE)
    window.show()
    exit(app.exec_())
