"""
Copyright (C) 2008-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

import random
from logging import warning, INFO
from copy import deepcopy

from ufwi_rpcd.client import RpcdError
from ufwi_log.client.qt.args import arg_types
from ufwi_log.client.qt.user_settings.pages_index import PagesIndex
from ufwi_log.client.qt.user_settings.fragment import FragmentsList, Fragment
from ufwi_log.client.qt.user_settings.page import PagesList, Page
from ufwi_log.client.qt.user_settings.links import Links
from ufwi_log.client.qt.user_settings.printer import PrinterSettings
from ufwi_log.client.qt.user_settings.reports import ReportsList
from ufwi_log.client.qt.user_settings.compatibility import Compatibility
from ufwi_rpcd.common import EDENWALL

if EDENWALL:
    from ufwi_log.client.qt.user_settings.default import default_settings
    from ufwi_log.client.qt.user_settings.default_v2 import default_settings_v2
else:
    from ufwi_log.client.qt.user_settings.default_nufirewall import default_settings


class UserSettings:

    """
    User settings class.

    Nulog settings tree is:

    romain              :settings of a user
    |- pages_index      :pages index
    |  |- section1      :section
    |  |  |- title      :section title
    |  |  `- pages      :pages list (IDs)
    |  '
    |- pages            :list of Page objects
    |  |- Page1         :object which describes a page
    |  |- Page2         :likewise
    |  '
    |- frags            :list of Fragment objects
    |  |- Fragment1     :object which describes a fragment
    |  |- Fragment2     :likewise
    |  '
    |- links            :links for all arguments (Links)
    |- reports          :reports types
    |  |- Report1       :object which describes a report
    |  |- Report2       :likewise
    |  '
    `- printer          :printer settings (PrinterSettings)
    """

    sections = {'pagesindex':   PagesIndex,
                'pages':        PagesList,
                'frags':        FragmentsList,
                'links':        Links,
                'printer':      PrinterSettings,
                'reports':      ReportsList,
               }

    def __init__(self, main_window, client):
        self.main_window = main_window
        self.client = client
        self._data = dict()
        self.old_saved = None
        self.compatibility = Compatibility(main_window, client)

    def __contains__(self, key):
        return (key in self._data)

    def __getitem__(self, key):
        return self._data[key]

    def __setitem__(self, key, value):
        self._data[key] = value

    def __delitem__(self, key):
        if key not in self._data:
            return
        del self._data[key]

    def isOrphan(self, obj):
        if isinstance(obj, Fragment):
            for page in self['pages'].pages.values():
                for frame in page.frames:
                    if dict(frame.frags).has_key(obj.name):
                        return False

            return True
        elif isinstance(obj, Page):
            for section in self['pagesindex'].sections:
                for name, page in section.pages:
                    if name == obj.name:
                        return False
            for arg in arg_types.values():
                if arg.pagelinks.count(obj.name) > 0:
                    return False

            return True

        else:
            return False

    def __createObj(self, _class, storage, namebase, randname=True):
        # First we try to create the object with the namebase, and only
        # if it exists yet, we try with randomly integers prefixes
        name = namebase
        if randname:
            while storage.has_key(name):
                name = '%s_%d' % (namebase, random.randint(0,999999))

        obj = _class(name)
        storage[name] = obj

        return obj

    def createPage(self, field, section=None):
        page = self.__createObj(Page, self['pages'].pages, field)
        if section:
            self['pagesindex'].addPage(page, section)

        return page

    def createFragment(self, type, randname=True):
        frag = self.__createObj(Fragment, self['frags'].frags, type, randname)
        frag.type = type
        return frag

    def removeFragment(self, frag):
        if not frag:
            return

        try:
            self['frags'].frags.pop(frag.name)
        except KeyError:
            return

        for page in self['pages'].pages.values():
            page.removeFragment(frag.name)

    def removePage(self, page):
        if not page:
            return

        try:
            self['pages'].pages.pop(page.name)
        except KeyError:
            return

        for section in self['pagesindex'].sections:
            section.removePage(page.name)

    def loadParams(self, params):
        self.old_saved = deepcopy(params)
        for key, value in params.iteritems():

            try:
                if not key in self._data:
                    self[key] = self.sections[key](key)
            except KeyError:
                warning("Warning: %r isn't a correct config key" % (key,))
                continue

            self[key].load(value)

        for section in self['pagesindex'].sections:
            for i, (page_name, page) in enumerate(section.pages):
                try:
                    section.pages[i] = (page_name, self['pages'][page_name])
                except KeyError:
                    del section.pages[i]
        for page in self['pages'].pages.values():
            for frame in page.frames:
                for j, (frag_name, frag) in enumerate(frame.frags):
                    try:
                        frame.frags[j] = (frag_name, self['frags'][frag_name])
                    except KeyError:
                        del frame.frags[j]

    def _checkInputPacket(self):
        modified = False

        for index, page in enumerate(self['pagesindex'].sections[0].pages):
            if page[0] == 'packet_table':
                self['pagesindex'].sections[0].pages.remove(page)

                last_packets_page = ('last_packets', self['pages']['last_packets'])
                input_packets_page = ('input_packet', self['pages']['input_packet'])
                self['pagesindex'].sections[0].pages.insert(index, last_packets_page)
                self['pagesindex'].sections[0].pages.insert(index + 1, input_packets_page)
                modified = True
                break

        return modified

    def _removeAuthFail(self):
        modified = False

        for index, page in enumerate(self['pagesindex'].sections[1].pages):
            if page[0] == 'user_history':
                page[1].frames.pop(1)
                modified = True
                break

        return modified

    def _removeInputPacket(self):
        modified = False

        for index, page in enumerate(self['pagesindex'].sections[0].pages):
            if page[0] == 'input_packets' or page[0] == 'last_packets':
                self['pagesindex'].sections[0].pages.remove(page)

                if not modified:
                    new_page = ('packet_table', self['pages']['packet_table'])
                    self['pagesindex'].sections[0].pages.insert(index, new_page)
                    modified = True

        return modified


    def reset(self):
        self._data = {}
        try:
            self.client.call('users_config', 'delete', 'ufwi_log-qt')
            self.client.call('users_config', 'save')
        except RpcdError, e:
            pass
        self.load()

    def loadDefaultPage(self, page_name):
        for section in self['pagesindex'].sections:
            for page in section.pages:
                if page[0] == page_name:
                    del self._data['pages'].pages[page_name]
                    self.save()
                    self.load()
                    break

    def load(self):
        try:

            if self.compatibility.input_packet_frag:
                settings = default_settings_v2
            else:
                settings = default_settings


            self.loadParams(settings)
            for obj in self._data.itervalues():
                obj.setDefault(True)

            try:
                config = self.client.call('users_config', 'get', 'ufwi_log-qt')
                self.loadParams(config)
            finally:
#                packet_table = auth_table = False
#                if self.compatibility.input_packet_frag:
#                    packet_table = self._checkInputPacket()
#                else:
#                    packet_table = self._removeInputPacket()

                auth_table = False
                if not self.compatibility.authfail:
                    auth_table = self._removeAuthFail()

#                if packet_table or auth_table:
                if auth_table:
                    self.save()

        except RpcdError, err:
            # No config available, I don't care about
            return

    def save(self):
        params = {}
        for key, value in self._data.iteritems():
            params[key] = value.properties()

        if self.old_saved == params:
            return
        else:
            self.old_saved = deepcopy(params)

        try:
            try:
                self.client.call('users_config', 'delete', 'ufwi_log-qt')
            except RpcdError:
                # there isn't any configuration yet
                pass

            self.client.call('users_config', 'set', 'ufwi_log-qt', params)
            self.client.call('users_config', 'save')
        except RpcdError, err:
            self.main_window.writeError(err,
                "Error on saving configuration",
                log_level=INFO)
            try:
                self.client.call('users_config', 'close')
            except RpcdError:
                pass
