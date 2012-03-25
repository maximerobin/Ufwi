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

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.html import Html, htmlList, htmlParagraph, htmlImage, NBSP
from ufwi_rulesetqt.icons import WARNING_ICON32

def getIdentifier(object):
    return object['id']

def getIdentifiers(objects):
    return [object['id'] for object in objects]

def getDragUrl(event):
    """Return text from drag event or None"""
    return getDragUrlFromMimeData(event.mimeData())

def getDragUrlFromMimeData(mime_data):
    """Return text from mime_data or None"""
    if not mime_data.hasFormat("text/plain"):
        return None
    url = unicode(mime_data.text())
    if not url.startswith("ufwi_ruleset_drag:"):
        return None
    return url[12:]

def formatWarnings(message, warnings):
    message = htmlParagraph(message)
    if warnings:
        html = htmlImage(WARNING_ICON32, align="middle")
        html += NBSP + Html(tr("Warnings:"))
        message += htmlParagraph(html)
        message += htmlList(
            tr(format) % tuple(arguments)
            for format, arguments in warnings)
    return unicode(message)

