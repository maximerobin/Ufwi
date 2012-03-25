"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Victor Stinner <victor.stinner AT edenwall.com>
           Pierre-Louis Bonicoli <bonicoli AT edenwall.com>

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

from ufwi_rpcd.common.tools import toUnicode

class UnicodeException(Exception):
    def __init__(self, message):
        self.unicode_message = toUnicode(message)
        message = self.unicode_message.encode('ASCII', 'replace')
        Exception.__init__(self, message)

    def __unicode__(self):
        return self.unicode_message

class RpcdError(UnicodeException):
    def __init__(self, type, message, traceback=None, err_id=None):
        """id : (application, component, code)"""
        if message:
            message = toUnicode(message)
        else:
            message = u"[%s]" % type
        UnicodeException.__init__(self, message)
        self.type = type
        self.traceback = traceback
        if err_id:
            self.id = err_id
        else:
            self.id = (None, None, None)
        self.application, self.component, self.code = self.id

class SessionError(RpcdError):
    def __init__(self, message, traceback=None):
        RpcdError.__init__(self, "SessionError", message, traceback)

