
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

class _weak_callable:

    def __init__(self,obj,func):
        self._obj = obj
        self._meth = func

    def __call__(self,*args,**kws):
        if self._obj is not None:
            return self._meth(self._obj,*args,**kws)
        else:
            return self._meth(*args,**kws)

    def __getattr__(self,attr):
        if attr == 'im_self':
            return self._obj
        if attr == 'im_func':
            return self._meth
        raise AttributeError, attr

class WeakMethod:
    """ Wraps a function or, more importantly, a bound method, in
    a way that allows a bound method's object to be GC'd, while
    providing the same interface as a normal weak reference. """

    def __init__(self,fn):
        try:
            self._obj = ref(fn.im_self)
            self._meth = fn.im_func
        except AttributeError:
            # It's not a bound method.
            self._obj = None
            self._meth = fn

    def __call__(self):
        if self._dead(): return None
        return _weak_callable(self._obj and self._obj(),self._meth)

    def _dead(self):
        return self._obj is not None and self._obj() is None
