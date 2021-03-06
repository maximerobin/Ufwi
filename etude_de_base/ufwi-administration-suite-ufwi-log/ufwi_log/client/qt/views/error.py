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

from PyQt4.QtGui import QTextEdit, QFont

from ufwi_rpcd.common import tr
from ufwi_log.client.qt.views.base import BaseFragmentView

class ErrorFragmentView(BaseFragmentView, QTextEdit):

    @staticmethod
    def name(): return tr('the error view')

    def __init__(self, fetcher, parent):

        QTextEdit.__init__(self, fetcher.fragment.error, parent)
        BaseFragmentView.__init__(self, fetcher)
        self.setReadOnly(True)
        self.setFont(QFont("Times", 20, QFont.Bold))

    def requestData(self):
        pass

    def updateData(self, result):
        """ Nothing to update... """
        pass
