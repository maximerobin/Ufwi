"""
Copyright (C) 2009-2011 EdenWall Technologies

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

from ufwi_rpcc_qt.html import Html, htmlImage, htmlHeader

def htmlTitle(title, *icons):
    title = Html(title)
    for icon in icons:
        if not icon:
            continue
        title += u' ' + htmlImage(icon)
    return htmlHeader(3, title)

def htmlMultiColTable(options):
    html = Html(u'<center><table border="0" cellpadding="5" cellspacing="0" valign="middle" align="middle">', escape=False)
    for line in options:
        html += Html(u'<tr>', escape=False)
        for cell in line:
            html += Html(u'<td><center>%s</center></td>' % cell, escape=False)
        html += Html(u'</tr>', escape=False)
    html += Html(u'</table></center>', escape=False)
    return Html(html, escape=False)

