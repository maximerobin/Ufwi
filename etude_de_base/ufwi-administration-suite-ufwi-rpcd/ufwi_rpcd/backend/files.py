"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Sebastien Tricaud <s.tricaud AT inl.fr>

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

import tempfile
from os.path import join as path_join
from ufwi_rpcd.common.tools import mkdirNew

FILES_GLOBAL = "files"
FILES_USER   = "files-user"

class FilesDirectory:

    def __init__(self, core, type="tmp"):
        self.core = core
        self.vardir = self.core.config.get('CORE','vardir')
        self.files_path_tmp = path_join(self.vardir,FILES_GLOBAL,"tmp")
        self.files_path_resident = path_join(self.vardir,FILES_GLOBAL,"resident")
        mkdirNew(self.files_path_tmp)
        mkdirNew(self.files_path_resident)
        self.user_files_path_tmp = path_join(self.vardir,FILES_USER,"tmp")
        self.user_files_path_resident = path_join(self.vardir,FILES_USER,"resident")
        mkdirNew(self.user_files_path_tmp)
        mkdirNew(self.user_files_path_resident)
        self.type = type

    def getDir(self, user=None):
        if user:
            if type == "tmp":
                return self.user_files_path_tmp
            else:
                return self.user_files_path_resident
        else:
            if type == "tmp":
                return self.files_path_tmp
            else:
                return self.user_files_path_resident


class FileTmp:

    def __init__(self, core):
        self.fdir = FilesDirectory(core, "tmp")
        self.core = core

    def open(self, user=None):
        """
        Opens a temporary file in the appropriate path
        """
        if user:
            return tempfile.TemporaryFile(dir=self.fdir.getDir(user))
        else:
            return tempfile.TemporaryFile(dir=self.fdir.getDir())


class FileResident:

    def __init__(self, core):
        self.fdir = FilesDirectory(core, "resident")
        self.core = core

    def open(self, user=None):
        """
        Opens a resident file, in the appropriate path
        """
        if user:
            return self.fdir.getDir(user)
        else:
            return self.fdir.getDir()

