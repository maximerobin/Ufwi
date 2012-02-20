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

from PyQt4.QtGui import QAction, QFrame, QVBoxLayout, QMessageBox, QStackedWidget, \
                        QLabel, QHBoxLayout, QToolButton, QIcon, QWidget, QSizePolicy, \
                        QPalette, QMenu, QDrag

from PyQt4.QtCore import Qt, SIGNAL, QTimer, QMimeData, QByteArray

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_log.client.qt.addfrag_window import AddFragDialog
from ufwi_log.client.qt.args import Interval
from ufwi_log.client.qt.fragtypes import frag_types
from ufwi_log.client.qt.views import views_list, views_list_label
from ufwi_log.client.qt.views.ufwi_log_base import PIECHART, BARCHART

class FragmentFrame(QFrame):

    # Signals:
    SIG_REMOVE_FRAGMENT = 'removeFragment()'
    # Fragment edition switch
    FRAGMENT_EDITION = False

    view = None
    fetcher = None

    def __init__(self, fragment, args, client, animation_manager=None, parent=None, has_menu_pos=True):
        """
            @fragment [Fragment] user_settings.Fragment object to describe fragment
            @client [RpcdClient] client
            @parent [QWidget] parent widget
        """

        #assert isinstance(client, RpcdClient)
        assert frag_types.has_key(fragment.type)

        QFrame.__init__(self, parent)

        self.animation_manager = animation_manager
        self.has_menu_pos = has_menu_pos
        self.fragment = fragment
        self.fetcher = frag_types[fragment.type].fetcher(fragment, args, client)
        self.connect(self.fetcher, SIGNAL(self.fetcher.ERROR_SIGNAL), self.errorHandler)
        self.window = parent
        self.cumulative_mode = False
        self.interval = Interval('daily')

        self.setFragmentColor()

        self.setFrameShadow(QFrame.Sunken)
        self.setFrameShape(QFrame.StyledPanel)
        self.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.toolspace = None
        self.vbox = QVBoxLayout()
#        self.vbox.setContentsMargins(9,0,9,9)
        self.vbox.setContentsMargins(9,0,9,0)
        self.setLayout(self.vbox)

        self.stacked = QStackedWidget(self)
        updating_label = QLabel("<img src=\":/icons/refresh.png\" /><br />%s" % self.tr("Updating..."))
        updating_label.setAlignment(Qt.AlignHCenter|Qt.AlignVCenter)
        self.stacked.addWidget(updating_label)

        # Create all actions for the rightclick context menu
        self.action_list = []
        self.switch_actions = {}

        self.viewlayout = QHBoxLayout()
        self.viewlayout.setContentsMargins(0,0,0,0)
        self.viewlayout.setSpacing(2)
        self.viewlayout.addStretch()
        widget = QWidget()
        widget.setLayout(self.viewlayout)
        self.vbox.addWidget(widget)

        self.line = QFrame(self)
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)
        self.line.setObjectName("line")

        # Menu to choose position of fragment
        if self.has_menu_pos:
            self.pos_menu = QMenu(tr('Position'), self)
#        self.pos_action = QAction(tr('Position'), self.pos_menu)

        def make_lambda(l):
            """ usefull to create the lambda function with a copied parameter. or it'll bug """
            return lambda: QTimer.singleShot(0, lambda: self.setView(l))

        self.buttons = []

        button = QToolButton()
        button.visible = True
        button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Ignored)
        button.setMinimumSize(0,16)
        button.setIcon(QIcon(":/icons/refresh.png"))
        button.setFixedHeight(16)
        button.setToolTip(tr("Refresh"))
        self.connect(button, SIGNAL("clicked()"), self.updateData)
        self.viewlayout.addWidget(button)
        self.buttons.append(button)

        # All of the views available for this kind of fragment.
        if len(frag_types[fragment.type].views) > 1:
            for label in frag_types[fragment.type].views:

                try:
                    item_name = views_list_label[label]
                except KeyError:
                    continue

                # item_name returns a unicode string, but PyQT (Qt 4.2.1) won't convert it to a char*
                # unless we convert it to a non-unicode string ....
                action = QAction(QIcon(':/icons/%s' % label),
                                 tr("Switch to %s") % self.tr(unicode(item_name)), self)
                self.connect(action, SIGNAL("triggered()"), make_lambda(label))
                self.action_list += [action]
                self.switch_actions[label] = action

                button = QToolButton()
                button.visible = True
                button.setBackgroundRole(QPalette.Button)
                button.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Minimum)
                button.setMinimumSize(0,16)
                button.setFixedHeight(16)
                button.setIcon(QIcon(":/icons/%s" % label))
                button.setToolTip(tr("Switch to %s") % self.tr(unicode(item_name)))
                self.connect(button, SIGNAL("clicked()"), make_lambda(label))
                self.viewlayout.addWidget(button)
                self.buttons.append(button)

            # Separator
            action = QAction(self)
            action.setSeparator(True)
            self.action_list += [action]

        # Refresh
        action = QAction(QIcon(':/icons/refresh.png'), tr('Refresh'), self)
        self.connect(action, SIGNAL('triggered()'), self.updateData)
        self.action_list += [action]
        if self.FRAGMENT_EDITION:
            # Edit
            action = QAction(QIcon(':/icons/edit.png'), tr('Edit this fragment...'), self)
            self.connect(action, SIGNAL('triggered()'), self.editFragment)
            self.action_list += [action]
            # Delete
            action = QAction(QIcon(':/icons/moins.png'), tr('Delete this fragment'), self)
            self.connect(action, SIGNAL('triggered()'), self.removeFragment)
            self.action_list += [action]

        self.setView(fragment.view, update=False)

        self.setAcceptDrops(True)
        self.pos = -1

    def mouseMoveEvent(self, event):
        if event.buttons() != Qt.LeftButton:
            return

        mimeData = QMimeData()
        if self.pos == -1:
            return
        mimeData.setData("splitter/fragment", QByteArray.number(self.pos))
        drag = QDrag(self)
        drag.setMimeData(mimeData)
        drag.setHotSpot(event.pos() - self.rect().topLeft())

        dropAction = drag.start(Qt.MoveAction)

        if dropAction == Qt.MoveAction:
            self.close()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):

        data = event.mimeData().data("splitter/fragment").toInt()
        if not data[1]:
            return

        frame_pos = data[0]

        if frame_pos == self.pos:
            return

        event.setDropAction(Qt.MoveAction)
        event.accept()

        self.window.changedPositionFragment(self.pos, frame_pos)

#    def __del__(self):
#        self.destructor()

    def destructor(self):
        if self.view:
            self.freeView()
        if self.fetcher:
            self.disconnect(self.fetcher, SIGNAL(self.fetcher.ERROR_SIGNAL), self.errorHandler)
            self.fetcher.destructor()
            self.fetcher = None

    def getView(self):
        return self.view

    def getFragment(self):
        return self.fragment

    def setCumulative(self, cumulative):
        self.cumulative_mode = cumulative
        if self.view:
            self.view.setCumulative(cumulative)

    def setInterval(self, interval):
        self.interval = interval
        if self.view:
            self.view.setInterval(interval)

    def setFragmentColor(self):

        # XXX: We have to put classes which we colorize, because some objects bug
        # when we try to put a background on them. For example, do NOT colorize
        # QScrollBar, it'll not work anyway:
        # http://doc.trolltech.com/4.4/stylesheet-examples.html#customizing-qscrollbar
        # "The QScrollBar can be styled using its subcontrols like handle,
        # add-line, sub-line, and so on. Note that if one property or
        # sub-control is customized, all the other properties or sub-controls
        # must be customized as well."
        self.setStyleSheet("""
         QFrame, QPushButton, QTableCornerButton, QAbstractSpinBox, QLineEdit {
             background-color: #%06X;
         }

         """ % self.fragment.background_color)

    def editFragment(self):
        if AddFragDialog(self.window, self.fragment, self).run():
            self.setFragmentColor()
            self.setView(self.fragment.view, update=True)

    def removeFragment(self):
        reply = QMessageBox.question(self, self.tr("Delete a fragment"),
                                           unicode(self.tr('Are you sure to delete the fragment "%s" from the view?')) % self.fragment.title,
                                           QMessageBox.Yes|QMessageBox.No)

        if reply == QMessageBox.Yes:
            QTimer.singleShot(0, self._removeFragment_emit)

    def _removeFragment_emit(self):
        self.emit(SIGNAL(self.SIG_REMOVE_FRAGMENT))

#    def resizeEvent(self, event):
#        QFrame.resizeEvent(self, event)
#        self.view.resize(event.size())

    def freeView(self):
        if self.view:
            self.view.destructor()
            self.disconnect(self.view, SIGNAL('open_page'), self._open_page)
            self.disconnect(self.view, SIGNAL('add_filter'), self._add_filter)
            self.disconnect(self.view, SIGNAL('updating'), self._show_animation)
            self.disconnect(self.view, SIGNAL('updated'), self._show_view)
            self.disconnect(self.view, SIGNAL('EAS_Message'), self.EAS_SendMessage)
            self.stacked.removeWidget(self.view)
            self.vbox.removeWidget(self.stacked)
            self.vbox.removeWidget(self.line)
            self.view.setParent(None)
            self.view.hide()
            self.view.deleteLater()
        if self.toolspace:
            self.viewlayout.removeWidget(self.toolspace)
            self.toolspace.setParent(None)
            self.toolspace.hide()
            self.toolspace.deleteLater()

        if self.view and hasattr(self.view, "uuid"):
            if self.animation_manager:
                self.animation_manager.remove(self.view.uuid)
            self.view = None
        self.toolspace = None

    def setView(self, label, update=True):

        # If there isn't any view for this fragment, use the first available view
        # of this kind of fragment.
        if not label:
            assert frag_types.has_key(self.fragment.type)
            assert len(frag_types[self.fragment.type].views) > 0

            label = frag_types[self.fragment.type].views[0]


        for button in self.buttons:
            if label in button.toolTip():
                button.visible = False
            else:
                if not button.isEnabled():
                    button.visible = True
#        assert views_list.has_key(label)

        self.freeView()

        # Create the view object.
        self.view = views_list[label](self.fetcher, self)
        if label == "histo" or label == 'pie':
            self.view.is_graphics_view = True
            if label == 'histo':
                self.view.chart_type = BARCHART
            else:
                self.view.chart_type = PIECHART
        else:
            self.view.is_graphics_view = False

        if label != "error":
            self.connect(self, SIGNAL("closed"), self.setClosed)
            if self.animation_manager:
                if self.view.is_graphics_view:
                    self.connect(self.view, SIGNAL("animation_done(QString)"), self, SIGNAL("animation_done(QString)"))
                self.animation_manager.addView(self.view)

        self.connect(self.view, SIGNAL("showButtons"), self.showButtonsSlot)
        self.connect(self.view, SIGNAL("autoRefresh"), self.updateData)
                
        self.view.setCumulative(self.cumulative_mode)
        self.view.setInterval(self.interval)
        self.stacked.insertWidget(0, self.view)
        self._show_view()
        self.connect(self.view, SIGNAL('open_page'), self._open_page)
        self.connect(self.view, SIGNAL('add_filter'), self._add_filter)
        self.connect(self.view, SIGNAL('updating'), self._show_animation)
        self.connect(self.view, SIGNAL('updated'), self._show_view)
        self.connect(self.view, SIGNAL('EAS_Message'), self.EAS_SendMessage)

        # Set some features if there are available on each or each type of widget.
        if hasattr(self.view, 'setFrameShape'):
            self.view.setFrameShape(QFrame.NoFrame)
        self.view.setContextMenuPolicy(Qt.ActionsContextMenu)

        # All views can ask me to display a toolspace (a widget with all kind of
        # things in).
        self.view.title.setText(self.view.getTitle())
        self.fragment.view = label

        self.toolspace = self.view.getToolspace()
        self.viewlayout.insertWidget(0, self.toolspace)
        self.vbox.addWidget(self.line)
        self.vbox.addWidget(self.stacked)

        # Set the new menu.
        for action in self.actions():
            self.removeAction(action)

        for view_label, action in self.switch_actions.items():
            action.setEnabled(view_label != self.fragment.view)

        for action in self.action_list:
            self.addAction(action)
            self.view.addAction(action)

        # Add view's eventual menu.
        view_actions = self.view.getActions()
        if view_actions:
            separator = QAction(self)
            separator.setSeparator(True)
            view_actions = [separator] + view_actions

            for action in view_actions:
                self.view.addAction(action)
                self.addAction(action)

        if self.has_menu_pos:
            self.view.addAction(self.pos_menu.menuAction())
            self.addAction(self.pos_menu.menuAction())

        if update:
            self.updateData()

    def setClosed(self):
        if self.view:
            self.view.setClosed()
        self.destructor()

    def errorHandler(self, e):
        """ This method is called when fetcher raises an error. """

        # Store error in fragment, and the ErrorFragmentView will able to
        # load it

        error = exceptionAsUnicode(e)
        self.fragment.error = error

        # We keep last view in the fragment, to prevent setView() method to
        # put 'error' in the fragment.view string attribute.
        last_view = self.fragment.view
        self.setView('error', update=False) # load the error fragment
        self.fragment.view = last_view

    def showButtonsSlot(self):
        for button in self.buttons:
            if hasattr(button, 'visible'):
                if button.visible:
                    button.setEnabled(True)
                else:
                    button.setEnabled(False)

    def updateData(self):

        if hasattr(self.fragment, 'error'):
            self.setView(self.fragment.view, update=False)
            del self.fragment.error

        for button in self.buttons:
            button.setEnabled(False)

        self.view.requestData()

    def _open_page(self, *args, **kwargs):
        self.emit(SIGNAL('open_page'), *args, **kwargs)

    def _add_filter(self, *args, **kwargs):
        self.emit(SIGNAL('add_filter'), *args, **kwargs)

    def EAS_SendMessage(self, *args, **kwargs):
        self.emit(SIGNAL('EAS_Message'), *args, **kwargs)

    def _show_animation(self):
        self.stacked.setCurrentIndex(1)

    def _show_view(self):
        self.stacked.setCurrentIndex(0)
