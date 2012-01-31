
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

from __future__ import with_statement

from base64 import b64encode, b64decode

def encodeFileContent(content):
    return b64encode(content)

def decodeFileContent(content):
    return b64decode(content)

def getEncodedFileContent(path):
    with open(path, "r") as file_obj:
        buf = file_obj.read()
        return encodeFileContent(buf)

