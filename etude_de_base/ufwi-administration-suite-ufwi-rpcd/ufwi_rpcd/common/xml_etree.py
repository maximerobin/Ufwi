
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

from StringIO import StringIO

etree = None

if not etree:
    try:
        # Python 2.5 ElementTree
        from xml.etree import ElementTree as etree
    except ImportError, err:
        pass

if not etree:
    try:
        # Python 2.4 cElementTree
        import cElementTree as etree
    except ImportError:
        pass

if not etree:
    try:
        # Python 2.4 ElementTree
        from elementtree import ElementTree as etree
    except ImportError:
        pass

if not etree:
    try:
        from lxml import etree
    except ImportError:
        pass

if not etree:
    raise ImportError("Cannot import an ElementTree compliant module")

def indent(elem, prefix=u'\n'):
    _indent(elem, prefix)
    elem.tail = u'\n'

def _indent(elem, prefix=u'\n'):
    # Code based on indent() function from:
    # http://suif.stanford.edu/svn/cunkel/pylib/trunk/cu/et.py

    if not elem:
        # No children
        return

    new_prefix = prefix + u'   '
    if elem.text:
        elem.text += new_prefix
    else:
        elem.text = new_prefix

    last = len(elem) - 1
    for index, child in enumerate(elem):
        if index == last:
            add = prefix
        else:
            add = new_prefix
        if child.tail:
            child.tail += add
        else:
            child.tail = add
        _indent(child, new_prefix)

def save(root_node, filename=None):
    tree = etree.ElementTree(root_node)
    indent(root_node)

    # XML serialization: use StringIO to avoid writing
    # a partial XML file on serialization error
    output = StringIO()
    tree.write(output, encoding="UTF-8")

    if filename is None:
        return output

    # Finally write the content
    with open(filename, 'w') as output_file:
        output_file.write(output.getvalue())

