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

from PyQt4.QtGui import QTextEdit

from ufwi_log.client.qt.views.base import BaseFragmentView
from ufwi_rpcd.common import tr

class StatsFragmentView(BaseFragmentView, QTextEdit):

    @staticmethod
    def name(): return tr('the stats view')

    @staticmethod
    def getArgs(client, fragname):
        return client.call('ufwi_log', 'table_filters', fragname)

    def __init__(self, fetcher, parent):

        QTextEdit.__init__(self, parent)
        BaseFragmentView.__init__(self, fetcher)

        self.setReadOnly(True)
        self.document().setDefaultStyleSheet("""
                    table {
                        border-color: #BCBCBC;
                        border-style: solid;
                        border-collapse: collapse;
                    }
                    table td {
                        padding-top: 2px;
                        padding-bottom: 2px;
                        padding-left: 2px;
                        padding-right: 10px;
                    }

                    table th {
                        text-align: center;
                        padding-top: 5px;
                        padding-bottom: 5px;
                    }
                    """)

    def updateData(self, result):

        result = result['table']

        average1 = len(result) > 0 and result[0] or '0.00'
        average5 = len(result) > 1 and result[1] or '0.00'
        average15= len(result) > 2 and result[2] or '0.00'
        nb_pckts = len(result) > 3 and result[3] or '0'

        self.setHtml(tr("""<center>
                            <table border=1 cellpadding="0" cellspacing="0">
                                <tr><th colspan=2>Dropped packets</th></tr>
                                <tr><td>1 min:</td><td>%s pcks/s</td></tr>
                                <tr><td>5 min:</td><td>%s pcks/s</td></tr>
                                <tr><td>15 min:</td><td>%s pcks/s</td></tr>
                                <tr><td>Total:</td><td>%s pckts</td></tr>
                            </table>
                           </center>""") % (average1, average5, average15, nb_pckts))
