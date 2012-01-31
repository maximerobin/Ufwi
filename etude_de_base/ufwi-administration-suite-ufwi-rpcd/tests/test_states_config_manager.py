#!/usr/bin/env python2.5
# -*- coding: utf-8 -*-

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

#from os import unlink
from shutil import rmtree
from tempfile import mkstemp, mkdtemp

from twisted.internet.defer import inlineCallbacks

from nucentral.backend.exceptions import ConfigError
from nucentral.core.config.states import NotInitializedState, IdleState, DraftState, ApplicableState
from nucentral.core.config.manager import ConfigurationManager
from nucentral.core.config.responsible import Responsible, RESET_CONFIG
from nucentral.backend.versionning import VersionningComponent
from nucentral.core.mockup import NullLogger
from nucentral.core.mockup import Core

from .test_variables_store import get_tree

class FakeComponent(NullLogger):
    def __init__(self, core):
        self.core =  core
        self.name = "fake component"

class TestSCM:
    def setup_method(self, method):
        self.directory = mkdtemp(prefix='testconfig')

        core = Core()
        core.config.set("CORE", "vardir", self.directory)
        self.versionning_component = VersionningComponent()
        self.versionning_component.init(core)

        self.fake_component = FakeComponent(core)
        xmlfile, self.xmlfilename = mkstemp(suffix='.xml', dir=self.versionning_component.getRepository("configuration").checkout_directory)
        self.scm = ConfigurationManager(self.fake_component, self.directory)
        assert self.scm.state is NotInitializedState, "found %s" % self.scm.state
        self.scm.initializeConfig(self.versionning_component, self.xmlfilename)

        assert self.scm.state is IdleState, "found %s" % self.scm.state
        self.responsible = Responsible(caller_component="test", action=RESET_CONFIG)
        self.scm.reset(self.responsible)
        assert self.scm.state is IdleState, "found %s" % self.scm.state

    def teardown_method(self, method):
        rmtree(self.directory)

    @inlineCallbacks
    def testDeleteSetGet(self):
        scm = self.scm
        NAME = 'storage_DeleteSetGet'
        input1 =  {'key0':'value0'}
        scm.set(NAME, input1)
        scm.commit(NAME, True, self.responsible)
        assert scm.get(NAME) == input1
        yield scm.apply(self.responsible)
        assert scm.get(NAME) == input1

        scm.delete(NAME)

        input2 =  {'key1':'value1'}
        scm.set(NAME, input2)
        scm.commit(NAME, True, self.responsible)
        assert scm.get(NAME) == input2
        yield scm.apply(self.responsible)
        assert scm.get(NAME) == input2

    @inlineCallbacks
    def testPutApplyReplaceApplyDict(self):
        scm = self.scm
        scm.set("storage", {'section1': {'key11': 'value11'}, 'section2': {'key21': 'value21', 'key22': 'value22'}})
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        scm.set("storage", {'section1': {'key11': 'othervalue11'}, 'section2': {'key21': 'value21', 'key22': 'value22'}})
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        assert scm.get("storage", 'section1', 'key11') == 'othervalue11'

        old = scm.get("storage")
        old['section2']['key21'] = "othervalue21"
        scm.set("storage", old)
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        assert scm.get("storage", 'section2', 'key21') == 'othervalue21'

    def _putValue(self):
        self.scm.set("storage", "section", "key", "value")

    def testPutGetValue(self):
        self._putValue()
        scm = self.scm
        value = scm.get("storage", "section", "key")
        assert value == "value", "expected \"value\", got %s (structure: %s)" % (value, scm._draft_configuration)

        return scm

    def testDelete1(self):
        self._putValue()
        scm = self.scm
        scm.delete("storage", "section", "key")
        try:
            scm.get("storage", "section", "key")
        except ConfigError:
            pass
        else:
            assert False

    def testDelete2(self):
        self._putValue()
        scm = self.scm
        scm.delete("storage")
        try:
            scm.get("storage", "section", "key")
        except ConfigError:
            pass
        else:
            assert False

    def testReplace(self):
        self._putValue()
        scm = self.scm
        scm.set("storage", "section", "key", "value2")
        value = scm.get("storage", "section", "key")
        assert value == "value2", "expected \"value\", got %s (structure: %s)" % (value, scm._draft_configuration)

    def testDeleteReplace(self):
        self._putValue()
        scm = self.scm
        scm.delete("storage", "section")
        scm.set("storage", "section", "key", "value2")
        value = scm.get("storage", "section", "key")
        assert value == "value2", "expected \"value\", got %s (structure: %s)" % (value, scm._draft_configuration)

    def _putcommit(self):
        self._putValue()
        self.scm.commit("dummy message", True, self.responsible)

    @inlineCallbacks
    def testStatesConfigManager(self):
        self._putcommit()
        scm = self.scm
        #this one will be retrieved from the draft configuration
        value = scm.get("storage", "section", "key")
        assert value == "value", "expected \"value\", got %s (structure: %s)" % (value, scm._modified_configuration)
        assert scm.state is ApplicableState, "found %s" % scm.state
        scm.set("storage2", "section", "key", "value")
        assert scm.state is DraftState, "found %s" % scm.state
        #this one will be retrieved from the modified configuration
        value = scm.get("storage", "section", "key")
        assert value == "value", "expected \"value\", got %s (structure: %s)" % (value, scm._modified_configuration)
        scm.commit("dummy message", True, self.responsible)
        assert scm.state is ApplicableState, "found %s" % scm.state
        yield scm.apply(self.responsible)
        assert scm.state is IdleState, "found %s" % scm.state
        value = scm.get("storage", "section", "key")
        assert value == "value", "expected \"value\", got %s (structure: %s)" % (value, scm._running_configuration)
        scm.set("storage3", "section", "key", "value")
        assert scm.state is DraftState, "found %s" % scm.state
        #apply while in draft state mustn't work
        try:
            yield scm.apply(self.responsible)
        except ConfigError:
            pass
        else:
            assert False
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        assert scm.state is IdleState, "found %s" % scm.state
        scm.set("storage4", "section", "key", "value")
        scm.revert(self.responsible)
        assert scm.state is ApplicableState, "found %s" % scm.state
        try:
            value = scm.get("storage4", "section", "key")
        except ConfigError:
            #There was a revert !
            pass
        else:
            assert False
        scm.exportXML(self.xmlfilename)
        scm.importXML()

        #fixme
        #unlink(self.xmlfilename)
        #deleting
        scm.set("storage4", "section", "key", "value")
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        scm.delete("storage4", "section", "key")
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        scm.set("storage", "section", "key2", "value2")
        scm.set("storage", "section2", "key3", "value")
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)

        scm.set('special2', 'section_44', 'subsection_44')
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        scm.set('special3', 'section_45', {'subsection_45': "value_45"})
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        vals = {"section_42": {"subsection_42": "value_42"}, "section_43": {"subsection_43": "value_43"}}
        scm.set("special", vals)
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)

    def testDefaultVal1(self):
        self._putcommit()
        scm = self.scm

        #set key4
        scm.set(u"storage", u"section", {u"key4": False})

        def readKey4():
            read = scm.get(u"storage", u"section", {u"key4": True})
            assert read == {u"key4": False}
            read = scm.get(u"storage", u"section", {u"key4": False})
            assert read == {u"key4": False}
            read = scm.get(u"storage", u"section", u"key4")
            assert read == False

        readKey4()

        scm.commit("dummy message", True, self.responsible)

        readKey4()

    def testDefaultVal2(self):
        #read key5 (non existent)
        read = self.scm.get(u"storage", u"section", {u"key5": True})
        assert read == {u"key5": True}
        read = self.scm.get(u"storage", u"section", {u"key5": False})
        assert read == {u"key5": False}

    @inlineCallbacks
    def testBoolean(self):
        self.scm.set("storage", "section", "false", False)
        self.scm.set("storage", "section", "true", True)

        def readBools(config_manager):
            read = config_manager.get("storage", "section", "false", default=False)
            assert read == False
            read = config_manager.get("storage", "section", "true", default=True)
            assert read == True
            read = config_manager.get("storage", "section", "false", default=True)
            assert read == False
            read = config_manager.get("storage", "section", "true", default=False)
            assert read == True

        readBools(self.scm)

        self.scm.commit(self.xmlfilename, True, self.responsible)
        yield self.scm.apply(self.responsible)

        readBools(self.scm)

    def testEmptyVal(self):
        scm = self.scm

        scm.set(u"storage", u"section", "key0", u"")
        assert scm.get("storage", "section", "key0") == u""

        scm.set(u"storage", u"section", "key1", 0)
        assert scm.get("storage", "section", "key1") == 0

        scm.set(u"storage", {u"key1": u"", "section2": {"key2": u""}})
        assert scm.get("storage", "key1") == u""
        assert scm.get("storage", "section2", "key2") == u""

        scm.set(u"storage", u"section3", "key3", {})
        assert scm.get("storage", "section3", "key3") == {}

        scm.commit("dummy message", True, self.responsible)

        assert scm.get("storage", "section", "key0") == u""
        assert scm.get("storage", "section", "key1") == 0
        assert scm.get("storage", "key1") == u""
        assert scm.get("storage", "section2", "key2") == u""

    def testBasic(self):
        scm = self.scm
        scm.set(u"storage", u"section", u"value")
        assert scm.get("storage", "section") == u"value"

    @inlineCallbacks
    def testDeleteWrite(self):
        scm = self.scm

        scm.set('network', 'a', 'tun0')
        scm.set('network', 'b', 'eth0')
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        assert scm.get() == {'network': {'a': 'tun0', 'b': 'eth0'}}

        scm.delete("network")
        scm.set('network', 'c', 'eth2')
        scm.commit("dummy message", True, self.responsible)
        yield scm.apply(self.responsible)
        assert scm.get() == {'network': {'c': 'eth2'}}


    def test_get_has_no_sideeffect(self):
        scm = self.scm

        conf_contents = scm.get()
        assert conf_contents == {}, "should start with empty config"

        scm.set("values", get_tree())

        conf_contents = scm.get(fake_state=IdleState)
        assert conf_contents.get("values") is None, "before commit, expect empty config"

        conf_contents=scm.get(fake_state=ApplicableState)
        assert conf_contents.get("values") is None, "before commit, expect empty config"

        scm.commit("test_get_has_no_sideeffect", True, self.responsible)

        conf_contents = scm.get(fake_state=IdleState)
        assert conf_contents.get("values") is None, "before apply, expect empty config"

        conf_contents = scm.get(fake_state=ApplicableState)
        assert conf_contents["values"] == get_tree(), "expected the config I saved:\n%s\nbut got:\n %s" % (get_tree(), conf_contents["values"])


