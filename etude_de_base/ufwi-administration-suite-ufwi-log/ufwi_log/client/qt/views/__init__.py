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

from line import LineFragmentView
from error import ErrorFragmentView
from packetinfo import PacketInfoFragmentView
from stats import StatsFragmentView
from graphics_view import GraphicsView
from table import TableFragmentView
from ufwi_rpcd.common import tr

views_list = {'pie':         GraphicsView,
              'histo':       GraphicsView,
              'table':       TableFragmentView,
              'line':        LineFragmentView,
              'error':       ErrorFragmentView,
              'packetinfo':  PacketInfoFragmentView,
              'stats':       StatsFragmentView,
             }

views_list_label = {'histo':   tr("the histogram view"),
                    'pie':     tr("the pie view"),
                    'table':   tr("the table view"),
                   }
