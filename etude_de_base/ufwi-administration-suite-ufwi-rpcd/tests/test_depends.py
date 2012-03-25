#!/usr/bin/env python
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


from nucentral.backend.deps import Depends

def testDepends():
    deps = Depends()
    #
    #
    # *** explanation of the test ***
    #
    # -textual
    #
    #e depends on (c + d)
    #a depends on nothing
    #c depends on (f + a)
    #b depends on a
    #
    #i depends on nothing
    #
    #h depends on g
    #
    #... see below:
    #
    # -graphical
    #
    # a--b--d--e
    # \       /
    #  `--c--'
    #    /
    # f-'
    #
    # g--h
    #
    # i

    #Preparing the above situation
    for name in (u"a", u"f", u"g", u"i"):
        deps.addDepObject(name, set())

    deps.addDepObject(u"b", set((u"a",)))
    deps.addDepObject(u"d", set((u"b", u"c")))
    deps.addDepObject(u"c", set((u"a",u"f")))
    deps.addDepObject(u"e", set((u"d",)))
    deps.addDepObject(u"h", set((u"g",)))

    #And now the big tests !
    for data, expected in (
        ((u"a"), ([u"a", u"b", u"c", u"d", u"e"], [u"a", u"c", u"b", u"d", u"e"])),
        ((u"b"), ([u"b", u"d", u"e"],)),
        ((u"c"), ([u"c", u"d", u"e"],)),
        ((u"d"), ([u"d", u"e"],)),
        ((u"e"), ([u"e"],)),
        ((u"f"), ([u"f", u"c", u"d", u"e"],)),
        ((u"g"), ([u"g", u"h"],)),
        ((u"h"), ([u"h"],)),
        ((u"i"), ([u"i"],)),
        ):
        received = deps.getOrderedDependences(data)
        ok = False
        for possibility in expected:
            if possibility == received:
                ok = True
                print "ok for \"%s\": got %s, matching %s" % (data, received, possibility)
        assert ok, "for \"%s\", got %s instead of %s" % (data, received, expected)

if __name__ == "__main__":
    testDepends()
