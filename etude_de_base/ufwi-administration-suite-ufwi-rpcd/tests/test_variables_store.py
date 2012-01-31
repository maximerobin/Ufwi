
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

from tempfile import mkstemp
from copy import deepcopy

from nucentral.backend.exceptions import ConfigError
from nucentral.backend.value import Value
from nucentral.backend.variables_store import VariablesStore

tree = {
        u"plant": {
            u"tree": {
                u"oak": 42,
                u"pine": 3.6,
                u"spruce": u"nice"
            },
            u"energy": {
                u"nuclear": {
                    u"materials": {
                        u"1": u"heavy water",
                        u"2": u"homer",
                        u"3": u"uranium",
                        u"4": u"He3"},
                    u"waste": u"plutonium"
                    }
                }
            },
        u"animal": u"instinct",
        }

def get_tree():
    return deepcopy(tree)

def test_build():
    v = VariablesStore()
    return v

##

def test_readInexistentValue():
    v = test_build()
    try:
        v.get('ENOVALUE')
    except ConfigError:
        pass
    else:
        assert False

##

def test_writeSimpleValue():
    v = test_build()
    v.set("key", "value")
    return v

def test_readSimpleValue():
    v = test_writeSimpleValue()
    assert v.get("key") == "value"

##

def test_writeDeepValue():
    v = test_build()
    v.set("store", "section", "key", "value")
    return v

def test_readDeepValue():
    v = test_writeDeepValue()
    assert v.get("store", "section", "key") == "value"

##

def test_writeEmptyDict():
    v = test_build()
    v.set("key", {})
    print v
    return v

def test_readEmptyDict():
    v = test_writeEmptyDict()
    assert v.get("key") == {}

##

def test_writeDict():
    v = test_build()
    v.set("key", {"subkey0": "value", "subkey1": {}})
    return v

def test_readDict():
    v = test_writeDict()
    assert v.get("key", 'subkey0') == 'value'
    assert v.get("key", 'subkey1') == {}
    assert v.get("key") == {'subkey0': 'value', 'subkey1': {}}
    file, filename = mkstemp(suffix='.xml')
    print v
    v.save(filename)
    v.load(filename)
    print v
    assert v.get("key") == {'subkey0': 'value', 'subkey1': {}}

##

def _test_writeLong(value=long(15)):
    v = test_build()
    v.set("keyLong", value)
    return v

def _test_readLong(value=long(15)):
    v = _test_writeLong(value)
    assert v.get("keyLong") == value

def test_gen_long_tests():
    base_values = (
        0,
        1,
        15,
        1234567890123456789012345678901234567890123456789012345678901234567890,
        9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999
        )
    for value in base_values:
        for method in _test_writeLong, _test_readLong:
            yield method, value
            yield method, - value

def _test_writeFloat(value=33.33):
    v = test_build()
    v.set("keyFloat", value)
    return v

def _test_readFloat(value=33.33):
    v = _test_writeFloat(value)
    assert v.get("keyFloat") == value

def test_gen_float_tests():
    base_values = (
        0,
        1,
        15,
        1234567890123456789012345678901234567890123456789012345678901234567890,
        9999999999999999999999999999999999999999999999999999999999999999999999999999999999999999999,
        0.00000000000000000000000000000000000000000000000000000000000000000000000000000000000000001,
        0.1,
        0.015,
        3.14159,
        1234567890.1234567890,
        0.111111111111111111111111111111111111111111111,
        )
    for value in base_values:
        for method in _test_writeFloat, _test_readFloat:
            yield method, value
            yield method, - value

def test_override():
    v1 = test_build()
    v2 = test_build()

    v1values = get_tree()
    v1.set("values", v1values)
    v2.set("values", "plant", "tree", "oak", {"furniture": "table", "lipstick": "unapplicable"})
    assert v2.get("values", "plant", "tree", "oak") == {"furniture": "table", "lipstick": "unapplicable"}
    v1.override(v2)
    assert not any(isinstance(item, Value) for item in v2.iterleafs())
    assert v2.get("values", "plant", "tree", "oak") == 42
    assert v2.get("values") == v1values, "v2values: %s != v1values: %s" % (repr(v2.get("values")), repr(v1values))
    assert v2.get() == v1.get(), "v2values: %s != v1values: %s" % (repr(v2.get()), repr(v1.get()))

