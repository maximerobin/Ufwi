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

from PyQt4.QtGui import QSplitter, QTabWidget
from PyQt4.QtCore import Qt

from ufwi_log.client.qt.fragment_frame import FragmentFrame
from ufwi_log.client.qt.views.animation_manager import AnimationManager

class FragSplitter(QSplitter):

    MAX_HORIZONTAL_FRAGS = 2

    def __init__(self, client, parent):
        QSplitter.__init__(self, Qt.Vertical, parent)
        self.client = client
        self.window = parent
        self.animation_manager = AnimationManager(parent)
        self.reset()

    def disableAnimation(self, animation_on):
        self.animation_manager.setEnableAnimation(animation_on)

    def reset(self):
        self.animation_manager.reset()
    def setAutoRefresh(self, enable, seconds):
        self.animation_manager.setAutoRefresh(enable, seconds)

    def autoRefresh(self):
        return self.animation_manager.autoRefresh()

    def addFragment(self, fragment, global_args, pos_hint=-1, menu_pos=True):
        """
            Add a fragment on window.

            @param fragment [Fragment] object defined in user_settings.py to describe
                                       fragment properties.
            @param pos_hint [int]  if >= 0, ask to put fragment as a special position.
                                   This is a hint because if there isn't enough fragments,
                                   it'll placed at the next available position.
        """
        fragwidget = FragmentFrame(fragment, global_args, self.client, self.animation_manager, self.window, menu_pos)

        hor_splitter = None
        widget_index = 0
        for hor_splitter_i in xrange(self.count()):

            hor_splitter = self.widget(hor_splitter_i)

            # If position is already used, but hint wants to put fragment here, we do it.
            if pos_hint >= 0 and pos_hint < ((hor_splitter_i + 1) * self.MAX_HORIZONTAL_FRAGS):
                widget_index = pos_hint - hor_splitter_i * self.MAX_HORIZONTAL_FRAGS
                break

            # The hor_splitter isn't full
            if hor_splitter.count() < self.MAX_HORIZONTAL_FRAGS and \
                        (not pos_hint or pos_hint / self.MAX_HORIZONTAL_FRAGS < hor_splitter_i):
                widget_index = hor_splitter.count()
                break

            # not available position in this splitter
            hor_splitter = None

        # New line
        if hor_splitter is None:
            hor_splitter = QSplitter(Qt.Horizontal)
            self.addWidget(hor_splitter)

        if widget_index >= hor_splitter.count():
            # Add at end of line.
            hor_splitter.insertWidget(widget_index, fragwidget)
        else:
            # Add at the same position of an other frame.
            tabwidget = hor_splitter.widget(widget_index)
            if isinstance(tabwidget, QTabWidget):
                # There is already a TabWidget, we just add fragwidget in.
                tabwidget.addTab(fragwidget, fragwidget.getFragment().title)
            else:
                # This is a frame, so we remove it from splitter, insert a tabwidget,
                # and add the two frames (last and new) in.
                tabwidget.setParent(None)
                fragwidget1 = tabwidget
                tabwidget = QTabWidget()
                tabwidget.setTabPosition(QTabWidget.South)
                tabwidget.addTab(fragwidget1, fragwidget1.getFragment().title)
                tabwidget.addTab(fragwidget, fragwidget.getFragment().title)
                hor_splitter.insertWidget(widget_index, tabwidget)

        # TODO it does nothing...
        hor_splitter.setSizes([1 for i in xrange(hor_splitter.count())])

        return fragwidget

    def removeFragment(self, fragwidget):
        """
            Remove fragment from layout.

            @param fragwidget [QWidget]  removed widget
        """

        fragwidget.destructor()
        # find widget in splitters
        # XXX this is an ugly waterfall.
        for hor_splitter_i in xrange(self.count()):
            hor_splitter = self.widget(hor_splitter_i)
            for widget_i in xrange(hor_splitter.count()):
                widget = hor_splitter.widget(widget_i)
                if isinstance(widget, QTabWidget):
                    tabwidget = widget
                    for tabwidget_i in xrange(tabwidget.count()):
                        widget = tabwidget.widget(tabwidget_i)
                        if widget == fragwidget:
                            tabwidget.removeTab(tabwidget_i)
                            if tabwidget.count() <= 1:
                                tabwidget.setParent(None)
                                tabwidget.hide()
                                tabwidget.deleteLater()
                                if tabwidget.count() == 1:
                                    hor_splitter.insertWidget(widget_i, tabwidget.widget(0))
                            break
                elif widget == fragwidget:
                    # the only way to remove a widget from a splitter
                    widget.setParent(None)
                    widget.hide()
                    widget.deleteLater()
                    break
