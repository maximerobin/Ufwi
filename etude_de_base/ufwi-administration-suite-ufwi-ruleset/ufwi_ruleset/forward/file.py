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

from os import unlink, rename
from os.path import exists
from shutil import copyfile

def unlinkQuiet(filename):
    try:
        unlink(filename)
    except OSError:
        pass

class File:
    def __init__(self, filename, exist):
        self.filename = filename
        self.exist = exist

    def copyFrom(self, source):
        if not exists(source):
            return
        copyfile(source, self.filename)
        self.exist = True

    def open(self, mode):
        obj = open(self.filename, mode)
        self.exist |= ('w' in mode) or ('a' in mode)
        return obj

    def renameTo(self, new_filename):
        if self.filename == new_filename:
            return
        rename(self.filename, new_filename)
        self.exist = False

    def unlink(self, quiet=False):
        if not self.exist:
            return
        try:
            unlink(self.filename)
            self.exist = False
        except OSError:
            if quiet:
                pass
            else:
                raise

    def __repr__(self):
        return '<File %r exist=%s>' % (self.filename, self.exist)
    __str__ = __repr__

