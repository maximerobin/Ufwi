"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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

# interface for ACL Storage
class IAclStorage:
    def __init__(self, core):
        raise NotImplementedError()

    def check_acl(self, group, role):
        raise NotImplementedError()

    def get_acl(self, group=None, role=None):
        raise NotImplementedError()

    def set_acl(self, group, role):
        raise NotImplementedError()

    def delete_acl(self, group=None, role=None):
        raise NotImplementedError()

    def getStoragePaths(self):
        """
        return iterable which contains all paths used by storage
        """
        raise NotImplementedError()
