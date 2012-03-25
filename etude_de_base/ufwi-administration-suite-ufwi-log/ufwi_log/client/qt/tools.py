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

from datetime import datetime
import re
from time import mktime

from PyQt4.QtGui import QLabel
from PyQt4.QtCore import Qt, SIGNAL

NORMALIZE_REGEX = re.compile("[-/.:]+")

# Date regex: DD-MM
DATE_REGEX_SHORT = re.compile("^([0-3]?[0-9])~([01][0-9])$")

# Date regex: DD-MM-YY
DATE_REGEX_LONG = re.compile("^([0-3]?[0-9])~([01]?[0-9])~([0-9]{1,4})$")

# Datetime regex: "HH:MM:SS" (FR format)
DATETIME_REGEX = re.compile("([0-9]{1,2})~([0-9]{2})~([0-9]{2})$")

NUFACE_URL = None

def parseDatetime(gvalue, endofday=False):

    value = NORMALIZE_REGEX.sub("~", gvalue.strip())

    now = datetime.today()

    split = value.split(' ')
    if len(split) == 2:
        _date, _time = split
    else:
        _date = split[0]
        _time = ''

    year = now.year
    day, month, year = (0, 0, now.year)
    if endofday:
        hour, minute, sec = (23,59,59)
    else:
        hour, minute, sec = (0,0,0)

    regs = DATE_REGEX_SHORT.match(_date)
    if regs:
        try:
            day = int(regs.group(1))
            month = int(regs.group(2))
        except ValueError:
            pass
    regs = DATE_REGEX_LONG.match(_date)
    if regs:
        try:
            day = int(regs.group(1))
            month = int(regs.group(2))
            year = int(regs.group(3))
        except ValueError:
            pass

    regs = DATETIME_REGEX.match(_time)
    if regs:
        try:
            hour = int(regs.group(1))
            minute = int(regs.group(2))
            sec = int(regs.group(3))
        except ValueError:
            pass

    try:
        return int(mktime(datetime(year, month, day, hour, minute, sec).timetuple()))
    except:
        raise Exception("'%s' isn't any valid date or time." % gvalue)

def createLink(img_name, slot, tooltip=""):
    """
        Create a QLabel link connected to a specific slot.

        @param img_name [str] this is the image name in resources
        @paral sloc [func(str)] the slot function
        @return  a QLabel object
    """
    link = QLabel('<a href="#"><img src="%s" /></a>' % img_name)
    #link.setPixmap(QPixmap(img_name))
    link.setCursor(Qt.PointingHandCursor)
    link.setTextInteractionFlags(
            Qt.LinksAccessibleByMouse | Qt.LinksAccessibleByKeyboard)
    link.setToolTip(tooltip)
    link.setStyleSheet('padding-left: 2px; padding-right: 2px')
    link.connect(link, SIGNAL('linkActivated(const QString&)'), slot)
    return link


