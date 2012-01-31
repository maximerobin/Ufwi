
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

from os import makedirs
from errno import EEXIST
import re
from inspect import getargspec
from warnings import warn

SPACES_REGEX = re.compile(ur"^\s+")

def toUnicode(text):
    r"""
    >>> toUnicode('ascii')
    u'ascii'
    >>> toUnicode(u'utf\xe9'.encode('UTF-8'))
    u'utf\xe9'
    >>> toUnicode(u'unicode')
    u'unicode'
    """
    if isinstance(text, unicode):
        return text
    if not isinstance(text, str):
        text = str(text)
    try:
        return unicode(text, "utf8")
    except UnicodeError:
        pass
    return unicode(text, "ISO-8859-1")

def mkdirNew(path):
    try:
        makedirs(path)
    except OSError, err:
        errno = err.errno
        if errno == EEXIST:
            pass
        else:
            raise

def minmax(min_value, value, max_value):
    """
    Restrict value to [min_value; max_value]

    >>> minmax(-2, -3, 10)
    -2
    >>> minmax(-2, 27, 10)
    10
    >>> minmax(-2, 0, 10)
    0
    """
    return min(max(min_value, value), max_value)

def inverseDict(data):
    """
    Inverse a dictionary.

    >>> inverseDict({"0x10": 16, "0x20": 32})
    {32: '0x20', 16: '0x10'}
    """
    result = {}
    for key, value in data.iteritems():
        result[value] = key
    return result

def getFirst(iterable):
    """
    >>> getFirst(set([5]))
    5
    >>> getFirst(set())
    Traceback (most recent call last):
        ...
    IndexError: input is empty
    """
    for item in iterable:
        return item
    raise IndexError("input is empty")

def safeFilenameRegex(minlen, maxlen=255):
    # VFAT max filename: 255 UTF-16 characters
    # NTFS max filename: 255 UTF-16 characters
    # ext3 max filename: 255 bytes
    if not(1 <= minlen <= maxlen <= 255):
        raise ValueError("Invalid filename length: %s..%s" % (minlen, maxlen))
    return re.compile(ur'^[a-zA-Z0-9][a-zA-Z0-9_.-]{%s,%s}$' % (minlen-1, maxlen-1))

def deprecationWarning(message, stacklevel=2):
    warn(message, category=DeprecationWarning, stacklevel=stacklevel)

def deprecated(func):
    """
    Deprecated decorator. Example:

        @deprecated
        def oldapi():
            return "old"
    """
    def deprecated(*args, **kw):
        deprecationWarning("WARNING: deprecated call to %s" % func.__name__, 3)
        return func(*args, **kw)
    deprecated.__name__ = func.__name__
    deprecated.__doc__ = func.__doc__
    return deprecated

def timedelta2seconds(delta):
    """
    Convert a datetime.timedelta() objet to a number of second (an integer,
    ignore microseconds).

    >>> from datetime import timedelta
    >>> timedelta2seconds(timedelta(seconds=2, microseconds=40000))
    2
    >>> timedelta2seconds(timedelta(minutes=1, milliseconds=250))
    60
    """
    return delta.seconds + delta.days * 60*60*24

def readDocumentation(var):
    """
    Read the documentation string and remove indentation.
    Result is a generator of unicode lines.
    """
    # Read documentation string
    doc = var.__doc__
    if not doc:
        return

    # Convert to Unicode
    if not isinstance(doc, unicode):
        try:
            doc = unicode(doc, "UTF-8")
        except UnicodeDecodeError:
            doc = unicode(doc, "ISO-8859-1")

    # Remove empty lines at the end and at the beginning
    lines = doc.splitlines()
    while not lines[-1].strip():
        del lines[-1]
    while not lines[0].strip():
        del lines[0]
    if not lines:
        return

    # Computes smallest indentation width
    indent = None
    for line in lines:
        if not line:
            continue
        match = SPACES_REGEX.search(line)
        if not match:
            indent = None
            break
        width = match.end(0)
        if indent is None:
            indent = width
        else:
            indent = min(indent, width)

    if indent:
        # Return reindented documentation
        for line in lines:
            yield line[indent:]
    else:
        # Return original documentation (without empty lines)
        for line in lines:
            yield line

def getPrototype(func, skip=0):
    """
    Get the prototype of a function.
    skip is the number of skipped arguments.

    Examples:

    >>> getPrototype(getPrototype)
    'getPrototype(func, skip=0)'
    >>> class A:
    ...     def method(self, a, b, c=42, *args, **kw):
    ...        global getPrototype
    ...        local = a * b
    ...        return local / c
    ...
    >>> getPrototype(A.method)
    'method(a, b, c=42, *args, **kw)'
    >>> getPrototype(A.method, skip=2)
    'method(c=42, *args, **kw)'
    """
    try:
        func = func.im_func
        is_method = True
    except AttributeError:
        is_method = False
    args, varargs, varkw, defaults = getargspec(func)
    if is_method:
        skip += 1
    arguments = list(args)
    if defaults:
        index = len(arguments)-1
        for default in reversed(defaults):
            arguments[index] += "=%s" % default
            index -= 1
    if varargs:
        arguments.append("*" + varargs)
    if varkw:
        arguments.append("**" + varkw)
    return "%s(%s)" % (func.func_name, ", ".join(arguments[skip:]))

def abstractmethod(func):
    """
    Decorator indicating that the method is an abstract method and have to be
    implementated. The new function will raise a NotImplementedError with a
    nice message (display the class and the method names).

    Exemple: ::

        class Abstract:
            @abstractmethod
            def hello(self):
                pass

        class Concrete(Abstract):
            def hello(self):
                print "hello"

        Concrete().hello() # ok
        Abstract().hello() # raise a NotImplementedError
    """
    def abstract(self, *args, **kw):
        raise NotImplementedError(
            "Abstract method %s.%s() have no concrete implementation"
            % (self.__class__.__name__, func.__name__))
    return abstract

def formatList(items, separator, maxlen):
    r"""
    Join text items using the separator. If the output text length (including
    separators) is bigger than maxlen, truncate the list and add '...'.

    >>> print formatList(['a', 'b'], ',\n', 100)
    a,
    b
    >>> formatList("abcdef", ", ", 100)
    'a, b, c, d, e, f'
    >>> formatList("abcdef", ", ", 6)
    'a, b, ...'
    >>> formatList("abcdef", ", ", 1)
    'a, ...'
    >>> formatList("abcdef", ", ", 0)
    '...'
    """
    total_len = 0
    result = []
    for text in items:
        text_len = len(text)
        if result:
            text_len += len(separator)
        if maxlen < total_len + text_len:
            result.append('...')
            break
        total_len += text_len
        result.append(text)
    return separator.join(result)

