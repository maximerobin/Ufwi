
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

from ufwi_rpcd.common.tools import deprecated
from sys import version_info

def namedlist(class_name, *arguments):
    """
    namedlist is inspired by Python 2.6 collections.namedtuple(), but it's
    modifiable. It's used for a transition from a tuple/list API to an object
    with attributes API. That's why, using indexes displays a deprecation
    warning.

    Create a new type:

    >>> Point = namedlist('Point', 'x', 'y')
    >>> print Point.__doc__
    Point(x, y)

    Get attributes by index or by attribute:

    >>> p = Point(x=1, y=2)
    >>> print p
    Point(x=1, y=2)
    >>> p[0], p[1]
    (1, 2)
    >>> p.x, p.y
    (1, 2)

    Change an attribute:

    >>> p[0] = 10
    >>> print p
    Point(x=10, y=2)
    >>> p.y = 20
    >>> print p
    Point(x=10, y=20)

    Iterator:

    >>> tuple(p)
    (10, 20)
    >>> list(p)
    [10, 20]

    XML-RPC export ignores None values:

    >>> p.exportXMLRPC()
    {'y': 20, 'x': 10}
    >>> Point(x=8, y=None).exportXMLRPC()
    {'x': 8}
    >>> print Point(x=8).y
    None
    """
    if version_info < (2, 6) and 'class_name' in arguments:
        # In the following code, 'name' becomes a local variable when locals()
        # is called and so Named gets a name attribute. This is a Python bug
        # fixed in Python 2.6.
        #
        # def pouet(name):
        #     class Named:
        #         locals()
        #         __name__ = name
        #     return Named
        #
        # Named = pouet("hello world!")
        # assert not hasattr(Named, "name"), "nested scope bug!"
        # print "ok"
        raise ValueError(
            'Because of a Python bug (version < 2.6), '
            'a namedlist cannot have an attribute called "class_name".')
    class NamedList(object):
        __name__ = class_name
        __doc__ = '%s(%s)' % (class_name, ', '.join(arguments))
        # index to key
        PARAMETERS = tuple(arguments)

        def __init__(self, *args, **kw):
            items = dict((key, None) for key in self.PARAMETERS)
            object.__setattr__(self, '_items', items)
            for index, value in enumerate(args):
                key = self.PARAMETERS[index]
                self._items[key] = value
            for key, value in kw.iteritems():
                if key not in self.PARAMETERS:
                    raise TypeError("unexpected keyword argument %r" % key)
                self._items[key] = value

        def __getattr__(self, key):
            return self._items[key]

        def __setattr__(self, key, value):
            self._items[key] = value

        @deprecated
        def __getitem__(self, key):
            key = self.PARAMETERS[key]
            return self._items[key]

        @deprecated
        def __setitem__(self, key, value):
            key = self.PARAMETERS[key]
            self._items[key] = value

        def exportXMLRPC(self):
            xmlrpc = {}
            for key in self.PARAMETERS:
                value = self._items[key]
                if value is None:
                    continue
                xmlrpc[key] = value
            return xmlrpc

        def __iter__(self):
            for key in self.PARAMETERS:
                yield self._items[key]

        def __repr__(self):
            args = (('%s=%r' % (key, self._items[key])) for key in self.PARAMETERS)
            args = ', '.join(args)
            return '%s(%s)' % (class_name, args)

    return NamedList

