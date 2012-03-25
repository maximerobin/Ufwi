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

from ufwi_log.client.qt.widgets.pie_view import PieView

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.views.graph import GraphFragmentView

class PieFragmentView(GraphFragmentView, PieView):

    show_count = True

    @staticmethod
    def name(): return tr('the pie view')

    def __init__(self, fetcher, parent=None):

        PieView.__init__(self, parent)
        GraphFragmentView.__init__(self, fetcher)

    def printMe(self, painter, rect):
        PieView.printMe(self, painter, rect)

    def mouseMoveEvent(self, event):
        PieView.mouseMoveEvent(self, event)
        GraphFragmentView.mouseMoveEvent(self, event)
