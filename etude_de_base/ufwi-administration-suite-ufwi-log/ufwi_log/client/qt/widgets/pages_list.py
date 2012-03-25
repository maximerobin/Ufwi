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

from PyQt4.QtGui import QTreeWidget, QItemDelegate, \
                        QStyleOption, QStyleOptionButton, \
                        QStyle, QTreeWidgetItem, QHeaderView, \
                        QMenu, QMessageBox, QFont, QApplication, \
                        QIcon, QPixmap
from PyQt4.QtCore import QRect, QSize, Qt, SIGNAL, QVariant, QString
from ufwi_rpcd.common import tr

class SheetDelegate(QItemDelegate):

    def __init__(self, treeview, parent=None):

        QItemDelegate.__init__(self, parent)
        self.m_view = treeview

    def paint(self, painter, option, index):
        """ Draw a button-style on root items """
        model = index.model()
        assert model


        if not model.parent(index).isValid():
            # this is a top-level item.
            buttonOption = QStyleOptionButton()

            buttonOption.state = option.state
            buttonOption.state &= ~QStyle.State_HasFocus

            buttonOption.rect = option.rect
            buttonOption.palette = option.palette
            buttonOption.features = QStyleOptionButton.None

            self.m_view.style().drawControl(QStyle.CE_PushButton, buttonOption, painter, self.m_view)

            branchOption = QStyleOption()
            i = 15  ### hardcoded in qcommonstyle.cpp
            r = option.rect
            branchOption.rect = QRect(r.left() + i/2, r.top() + (r.height() - i)/2, i, i)
            branchOption.palette = option.palette
#            branchOption.state = QStyle.State_Children

            if self.m_view.isExpanded(index):
                branchOption.state |= QStyle.State_Open

            self.m_view.style().drawPrimitive(QStyle.PE_IndicatorBranch, branchOption, painter, self.m_view)

            # draw text
            textrect = QRect(r.left() + i*2, r.top(), r.width() - ((5*i)/2), r.height())
            text = self.elidedText(option.fontMetrics, textrect.width(), Qt.ElideMiddle,
                              model.data(index, Qt.DisplayRole).toString())
            self.m_view.style().drawItemText(painter, textrect,Qt.AlignLeft|Qt.AlignVCenter,
                                             option.palette, self.m_view.isEnabled(), text)

            icon_variant = index.data(Qt.DecorationRole)
            icon = QIcon(icon_variant)
            self.m_view.style().drawItemPixmap(
                                               painter, option.rect,
                                               Qt.AlignLeft,
                                               icon.pixmap(icon.actualSize(QSize(20 ,20)))
                                               )

        else:
            QItemDelegate.paint(self, painter, option, index)

    def sizeHint(self, opt, index):

        option = opt;
        sz = QItemDelegate.sizeHint(self, opt, index) + QSize(2, 2)
        return sz

class PagesListWidget(QTreeWidget):

    # Signals
    SIG_OPEN_PAGE = 'openPage(PyQt_PyObject)'

    def __init__(self, user_settings, parent=None, read_only=False):

        QTreeWidget.__init__(self, parent)
        self.header().hide()
        self.header().setResizeMode(QHeaderView.Stretch)
        self.setRootIsDecorated(False)

        self.window = parent
        self.read_only = read_only
        self.user_settings = user_settings
        self.setItemDelegate(SheetDelegate(self, self))
        self.connect(self, SIGNAL('itemPressed(QTreeWidgetItem*,int)'), self.pagesListPressed)

    def pagesListPressed(self, item, i):
        """ Expand item with only a simple click """

        buttons = QApplication.mouseButtons()

        if buttons == Qt.RightButton:
            return

        if not item:
            return

        if not item.parent():
            self.setItemExpanded(item, not self.isItemExpanded(item))
            return

        page_name = unicode(item.data(0, Qt.UserRole).toString())
        self.emit(SIGNAL(self.SIG_OPEN_PAGE), self.getPage(page_name))

    def contextMenuEvent(self, e):
        if self.read_only:
            return

        item = self.itemAt(e.pos())

        if item and item.parent():
            # item is a page
            page_name = unicode(item.data(0, Qt.UserRole).toString())
            menu = QMenu(page_name)
            if unicode(item.parent().data(0, Qt.UserRole).toString()) == 'history':
                menu.addAction(self.tr("Bookmark this view"), lambda: self.moveInCustom(page_name))
                menu.addSeparator()

            menu.addAction(self.tr('Delete view'), lambda: self.removePage(page_name))
            menu.addAction(self.tr('Reset view'), lambda: self.resetPage(page_name))

            e.accept()
            menu.exec_(e.globalPos())

    def moveInCustom(self, page_name):
        """
        Move page into the "Bookmarks" section.
        """

        page = self.user_settings['pages'].pages[page_name]
        for section in self.user_settings['pagesindex'].sections:
            section.removePage(page_name)
            if section.name == 'bookmarks':
                section.addPage(page)

        self.loadPagesList()

    def resetPage(self, page_name):
        self.user_settings.loadDefaultPage(page_name)
        self.loadPagesList()
        self.emit(SIGNAL(self.SIG_OPEN_PAGE), self.getPage(page_name))

    def removePage(self, page_name):
        if QMessageBox.question(self, self.tr("Close view"),
                                      self.tr("Are you sure you want to delete this view?"),
                                      QMessageBox.Yes|QMessageBox.No) == QMessageBox.Yes:
            removed_page = self.getPage(page_name)
            self.user_settings.removePage(removed_page)

            if page_name == self.window.current_page.name:
                try:
                    while 1:
                        try:
                            page = self.user_settings['pages'].pages[self.window.history['prev'].pop()]
                        except KeyError:
                            continue
                        else:
                            break
                except IndexError:
                    page = self.window.getMainPage()
                self.window._loadPage(page)
            else:
                self.loadPagesList()

    def getPage(self, name):
        """
            Get a page from its name

            @param name [str] Page name
        """
        if not self.user_settings['pages'].pages.has_key(name):
            return self.user_settings.createPage(name, 'bookmarks')
        else:
            return self.user_settings['pages'].pages[name]

    def collapseAllButOne(self, section):
        self.collapseAll()
        for i in xrange(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            if unicode(top.data(0, Qt.UserRole).toString()) == section:
                self.expandItem(top)
                break

    def getCheckedPages(self):
        pages = []
        for i in xrange(self.topLevelItemCount()):
            top = self.topLevelItem(i)
            for j in xrange(top.childCount()):
                child = top.child(j)
                if child.checkState(0) == Qt.Checked:
                    pages.append(self.getPage(unicode(child.data(0, Qt.UserRole).toString())))

        return pages

    def loadPagesList(self, checkable=False):
        self.clear()
        for section in self.user_settings['pagesindex'].sections:
            root = QTreeWidgetItem([section.title])
            root.setData(0, Qt.UserRole, QVariant(QString(section.name)))
            root.setData(0, Qt.DecorationRole, QVariant(QIcon(section.icon)))
            self.addTopLevelItem(root)

            for page_id, page in section.pages:
                if not page:
                    page = self.getPage(page_id)
                if page.title:
                    page_title = page.title
                else:
                    page_title = tr('(No name)')
                item = QTreeWidgetItem([page_title])
                item.setData(0, Qt.UserRole ,QVariant(QString(page_id)))
                if checkable:
                    item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
                    item.setCheckState(0, Qt.Unchecked)
                root.addChild(item)
                if page == self.window.current_page:
                    f = QFont()
                    f.setWeight(QFont.Bold)
                    item.setData(0, Qt.FontRole, QVariant(f))
                    self.setCurrentItem(item)

        self.expandAll()

