#! /usr/bin/twistd -y
# vim: ft=python

"""
Copyright(C) 2007,2008,2009 INL
Written by Pierre Chifflier <p.chifflier AT inl.fr>

This program is free software; you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, version 3 of the License.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program; if not, write to the Free Software
Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.

$Id$
"""

import sys
from twisted.application.service import Application, IServiceCollection
from ufwi_rpcd.core.core import Core

def createApplication():
    application = Application('ufwi-rpcd')
    try:
        core = Core(IServiceCollection(application))
        core.start()
    except Exception, err:
        print >>sys.stderr, '*******************************'
        print >>sys.stderr, 'Unable to start NuCentral:'
        print >>sys.stderr, err
        print >>sys.stderr, '*******************************'
        sys.exit(1)
    return application

application = createApplication()

