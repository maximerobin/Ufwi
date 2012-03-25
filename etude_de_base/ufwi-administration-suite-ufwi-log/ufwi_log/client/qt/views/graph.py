# -*- coding: utf-8 -*-

"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>
           Laurent Defert <lds AT inl.fr>

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

from PyQt4.QtGui import QAction, QMenu, QGraphicsEllipseItem
from PyQt4.QtCore import SIGNAL,QModelIndex

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.args import arg_types
from ufwi_log.client.qt.info_area import InfoArea
from ufwi_log.client.qt.views.ufwi_log_base import NulogBaseFragmentView, PIECHART, BARCHART

class GraphFragmentView(NulogBaseFragmentView):

    colours = ['#487118',
               '#7AB41D',
               '#F8E930',
               '#F29324',
               '#EA752C',
               '#C1292E',
               '#8C0A14',
               '#5F3269',
               '#874B94',
               '#212483',
               '#528FC8',
               '#196D38',
               # rest of the list is the original one (pre Harmony)
               '#47BE4F',
               '#CC0099', '#E0DD8D', '#FF8A2B', '#4B5DFF', '#6DF8BE', '#9C56FF',
               '#BE7344', '#CCBE78', '#E0ACD0', '#FF37E1', '#45709E', '#676FFF',
               '#4CAC84', '#35FF1A', '#806170', '#C3BF46', '#E0829A', '#E6CBB7']

    show_count = False

    def __init__(self, fetcher, parent=None):

        NulogBaseFragmentView.__init__(self, fetcher)

        self.info_area = InfoArea(self.parent())

        self.colsort_actions = []
        self.colsort_menu = QMenu(self)
        self.hide_count = False
        self.ready = False


    def getActions(self):
        action = QAction(tr('Sort by'), self)
        action.setMenu(self.colsort_menu)

        return [action]

    def setColsortActions(self):

        self.colsort_menu.clear()
        self.colsort_actions = []

        def make_lambda(col):
            return lambda: self.sortBy(col)

        for col in self.columns:
            action = QAction(arg_types[col].label, self)
            # TODO: might be radiobuttons instead of checkbox.
            action.setCheckable(True)
            self.connect(action, SIGNAL('triggered()'), make_lambda(col))
            self.colsort_menu.addAction(action)
            self.colsort_actions += [action]

    def get_model_label(self, row, col, arg_data):
        if col == 1:
            return arg_data.value
        else:
            return arg_data.label

    def updateData(self, result):

        if self.is_closed:
            return

        if not NulogBaseFragmentView.updateData(self, result):
            return False

        if len(self.columns) != len(self.colsort_actions):
            self.setColsortActions()

        if self.result['args'].has_key('sortby'):
            for i, col in enumerate(self.columns):
                self.colsort_actions[i].setChecked(self.result['args']['sortby'] == col)

        self.ready = False

        if self.result['args'].has_key('start') and self.result['args']['start'] == 0 and \
                self.chart_type == PIECHART:
            self.fetcher.count(self.updateData_bis)
            return True
        else:
            self.ready = True
            return True

    def updateData_bis(self, count):
        if not count:
            count =0
        count = int(count)

        if self.is_closed:
            return

        if not self.ready:
            # Number of entries shown (note lines, but values in pie)
            shown_count = 0
            row = 0

            for row, line in enumerate(self.data):
#                if len(line[1]) > 0:
                shown_count += int(line[1])

            # Add a part for "the" other entries
#            if shown_count < count:
            self.my_model.insertRows(row+1, 1, QModelIndex())
            self.add_line(row+1, ['Other', count - shown_count])

            self.ready = True
            if self.data:
                self.emit(SIGNAL("updateData_bis"))
                return True
            return False

