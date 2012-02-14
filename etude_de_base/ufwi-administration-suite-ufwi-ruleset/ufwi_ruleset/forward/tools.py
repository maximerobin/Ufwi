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

def zipall(*iterators):
    """
    >>> list(zipall("abc", "XYZ"))
    [('a', 'X'), ('b', 'X'), ('c', 'X'), ('a', 'Y'), ('b', 'Y'), ('c', 'Y'), ('a', 'Z'), ('b', 'Z'), ('c', 'Z')]
    >>> list(zipall("abc", iter(range(1))))
    [('a', 0), ('b', 0), ('c', 0)]
    >>> list(zipall("abc"))
    ['a', 'b', 'c']
    >>> list(zipall())
    []
    >>> list(zipall("ab", "XY", iter([])))
    [('a', 'X', None), ('b', 'X', None), ('a', 'Y', None), ('b', 'Y', None)]
    """
    if not iterators:
        return
    if len(iterators) == 1:
        for value in iterators[0]:
            yield value
        return
    empty_set = (None,)
    datas = tuple((tuple(iterator) or empty_set) for iterator in iterators)
    indexes = [0] * len(datas)
    while True:
        yield tuple( data[indexes[index]] for index, data in enumerate(datas) )
        index = 0
        indexes[index] += 1
        while indexes[index] == len(datas[index]):
            indexes[index] = 0
            index += 1
            if index == len(datas):
                return
            indexes[index] += 1

def reverseDict(data):
    """
    >>> reverseDict({1: "un", 2: "deux"})
    {'un': 1, 'deux': 2}
    """
    return dict( (value, key) for key, value in data.iteritems() )

def getIdentifier(object):
    return object.id

def getIdentifiers(objects):
    return [object.id for object in objects]

def combinaisons2(objects):
    """
    Return all possible combinaisons. Return a geneartor.

    >>> tuple(combinaisons2('ABC'))
    (('A', 'B'), ('A', 'C'), ('B', 'A'), ('B', 'C'), ('C', 'A'), ('C', 'B'))
    >>> tuple(combinaisons2('ABA'))
    (('A', 'B'), ('A', 'A'), ('B', 'A'), ('B', 'A'), ('A', 'A'), ('A', 'B'))
    """
    objects = tuple(objects)
    n = len(objects)
    for indexa in xrange(n):
        for indexb in xrange(n):
            if indexb == indexa:
                continue
            yield (objects[indexa], objects[indexb])

if __name__ == "__main__":
    import doctest
    doctest.testmod()

