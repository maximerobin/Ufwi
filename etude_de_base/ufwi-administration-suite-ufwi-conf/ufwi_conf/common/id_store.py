
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

from weakref import ref

"""
NOTE ON ID_OFFSET:
To avoid circulary import, they are defined in their own class and listed here for convenience.
Net: 0x0fffffff
Route: 0x1fffffff
Interface: 0x2fffffff
Fingerprint: 0x3fffffff
"""

class IDStore(object):
    instance = None

    def __init__(self):
        self.ids = {}

    @classmethod
    def getInstance(cls):
        if cls.instance is None:
            cls.instance = IDStore()
        return cls.instance

    def registerObject(self, item, unique_id=None):
        if unique_id is None:
            unique_id =  self.genId(item.__class__.ID_OFFSET)
        self.ids[unique_id] = ref(item)
        return unique_id

    def genId(self, offset):
        integer=offset
        while integer in self.ids:
            if self.ids.get(integer) is None:
                break
            integer += 1
        return integer

    def uniqueId(self, unique_id):
        ref_item = self.ids.get(unique_id)
        return ref_item()

class PersistentID(object):
    def __init__(self, **kwargs):
        assert isinstance(self.__class__.ID_OFFSET, int)
        unique_id = kwargs.pop('unique_id', None)
        store = IDStore.getInstance()
        self.unique_id = store.registerObject(self, unique_id=unique_id)

    def isValid(self):
        ok, msg = self.isValidWithMsg()
        return ok

    def isValidWithMsg(self):
        ok = self.unique_id > 0

        if ok:
            msg = 'ok'
        else:
            msg = "unique_id '%s' <= 0" % self.unique_id

        return ok, msg

    def serialize(self):
        serialized = {"unique_id": self.unique_id}
        return serialized

