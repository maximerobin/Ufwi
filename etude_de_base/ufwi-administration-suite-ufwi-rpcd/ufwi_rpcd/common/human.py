
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

from inspect import isclass, ismethod, isbuiltin, isfunction
from datetime import datetime
from ufwi_rpcd.common import tr

def typeName(value):
    """
    Type name, readable by an human.

    >>> typeName(1)
    'int'
    >>> class A: pass
    ...
    >>> typeName(A)
    "class 'A'"
    >>> a=A()
    >>> typeName(a)
    'instance (class A)'
    """
    if isclass(value):
        return 'class %r' % value.__name__
    type_str = type(value).__name__
    try:
        cls_name = value.__class__.__name__
        if cls_name == "type":
            cls_name = value.__name__
        if type_str != cls_name:
            type_str += " (class %s)" % cls_name
    except (TypeError, ValueError):
        pass
    return type_str

def humanRepr(obj, max_length=100):
    """
    Short representation of an object, as an unicode string, readable by an
    human. If the result is longer than max_length characters, truncate to
    max_length characters and add '...'.

    Simple types:

    >>> print humanRepr(True)
    True
    >>> print humanRepr(1)
    1
    >>> print humanRepr('text')
    'text'
    >>> print humanRepr(u'very long text', 11)
    u'very long...'

    Functions:

    >>> print humanRepr(len)
    builtin function len()
    >>> print humanRepr(humanRepr)
    function humanRepr()

    Types:

    >>> class A:
    ...     def somme(self, a, b): return a+b
    ...
    >>> print humanRepr(A)
    class 'A'
    >>> a=A()
    >>> print humanRepr(a)
    object of type 'A'
    >>> print humanRepr(A.somme)
    unbounded method A.somme()
    >>> print humanRepr(a.somme)
    method A.somme()
    """
    if isbuiltin(obj):
        return u'builtin function %s()' % obj.__name__

    if isfunction(obj):
        return u'function %s()' % obj.__name__

    if ismethod(obj):
        obj_class = obj.im_class
        text = u'method %s.%s()' % (obj_class.__name__, obj.__name__)
        if obj.im_self:
            return text
        else:
            return u'unbounded %s' % text

    obj_type = type(obj)
    if hasattr(obj, '__name__'):
        # class or function
        obj_type = obj_type.__name__
        if obj_type == 'classobj':
            obj_type = 'class'
        return u'%s %r' % (obj_type, obj.__name__)

    if obj_type not in (bool, int, long, str, unicode, list, tuple, dict) \
    and isclass(obj_type):
        # instance
        obj_type = obj.__class__.__name__
        return u'object of type %r' % obj_type

    text = unicode(repr(obj))
    if (max_length is not None) and (max_length < len(text)):
        text = text[:max_length]
        text += u'...'
        if obj_type == str:
            text += text[0]
        elif obj_type == unicode:
            text += text[1]
    return text

def humanYesNo(value):
    if value:
        return tr("Yes")
    else:
        return tr("No")

def fuzzyTimedelta(value):
    """
    >>> from datetime import timedelta
    >>> fuzzyTimedelta(timedelta(seconds=2390))
    u'39 min 50 sec'
    >>> fuzzyTimedelta(timedelta(seconds=30, microseconds=250000))
    u'30 sec'
    >>> fuzzyTimedelta(timedelta(seconds=1, microseconds=250000))
    u'1.2 sec'
    >>> fuzzyTimedelta(timedelta(microseconds=22000))
    u'22 ms'
    >>> fuzzyTimedelta(timedelta())
    u'0 ms'
    """
    text = []
    if value.days:
        text.append(tr("%s day(s)", "", value.days) % value.days)
    seconds = value.seconds
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        text.append(tr("%s h") % hours)
    if minutes:
        text.append(tr("%s min") % minutes)
    # 1.5 => 1.5 sec
    # 0.120 => 120 ms
    # 0.9
    ms = seconds * 1000 + value.microseconds // 1000
    if ms >= 1000:
        if seconds >= 10:
            # 30 sec
            text.append(tr("%s sec") % seconds)
        else:
            # 1.7 sec
            text.append(tr("%.1f sec") % (ms / 1000.0))
    elif ms or (not text):
        # 50 ms
        text.append(tr("%s ms") % ms)
    text = text[:2]
    return u' '.join(text)

def fuzzyDatetime(value, now=None):
    if now is None:
        now = datetime.now()

    time_text = "%02u:%02u" % (value.hour, value.minute)

    date_diff = value.date() - now.date()
    if date_diff.days == 0:
        date_text = tr("Today")
    elif date_diff.days == -1:
        date_text = tr("Yesterday")
    elif date_diff.days == 1:
        date_text = tr("Tomorrow")
    elif -60 <= date_diff.days <= -1:
        days = -date_diff.days
        date_text = tr("%s day(s) ago", '', days) % days
    else:
        date_text = value.date().strftime("%x")
        date_text = unicode(date_text)
    return tr("%(date)s at %(time)s") % {'date': date_text, 'time': time_text}

# Function copied from the Hachoir project: hachoir-core/hachoir_core/tools.py
def humanFilesize(size):
    """
    Convert a file size in byte to human natural representation.
    It uses the values: 1 KB is 1024 bytes, 1 MB is 1024 KB, etc.
    The result is an unicode string.

    >>> humanFilesize(1)
    u'1 byte'
    >>> humanFilesize(790)
    u'790 bytes'
    >>> humanFilesize(256960)
    u'250.9 KB'
    """
    if size < 10000:
        if size == 1:
            return u"%u byte" % size
        else:
            return u"%u bytes" % size
    units = [tr("KB"), tr("MB"), tr("GB"), tr("TB")]
    size = float(size)
    divisor = 1024
    for unit in units:
        size = size / divisor
        if size < divisor:
            return u"%.1f %s" % (size, unit)
    return u"%u %s" % (size, unit)

