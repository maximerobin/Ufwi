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

from itertools import chain

from ufwi_rpcd.client import RpcdError
from ufwi_ruleset.common.update import Updates

class Ruleset:
    def __init__(self, client, window):
        self.client = client
        self.window = window
        self.config = window.config
        self.compatibility = window.compatibility
        self.is_open = False
        self.fusion = False
        self.reset()

    def resetAttributes(self):
        self.is_template = False
        self.ruleset_name = None
        self.read_only = False
        self.templates = {}
        self.filetype = None
        self.format_version = None
        self.input_output_rules = (not self.window.use_edenwall)

    def _refreshModels(self):
        all_updates = {}
        updates =  Updates()
        for model in self.window.iterModels():
            model.refresh(all_updates, updates)

    def _clearModels(self):
        for model in self.window.iterModels():
            model.clear()

    def reset(self):
        if self.is_open:
            self._refreshModels()
        else:
            self.resetAttributes()
            self._clearModels()

    def callService(self, component, service, *args):
        return self.client.call(component, service, *args)

    def __call__(self, service, *args, **kw):
        """
        Call a ufwi_ruleset service.

        Use append_fusion=True option to keep backward compatibility with
        services which requires a fusion argument.
        """
        if kw.get('append_fusion', False) \
        and (not self.compatibility.set_fusion_service):
            args += (self.fusion,)
        return self.callService('ufwi_ruleset', service, *args)

    def readAttributes(self, result=None):
        if result and self.compatibility.mode == 'GUI2':
            attr = result['rulesetAttributes']
        else:
            attr = self('rulesetAttributes')
        self.is_template = attr['is_template']
        self.filetype = attr['filetype']
        # ruleset identifier => template name
        self.templates = {}
        for template in attr['templates']:
            identifier = template.pop('identifier')
            self.templates[identifier] = template
        self.format_version = attr['format_version']
        self.ruleset_name = attr.get('name', u'')
        self.read_only = attr['read_only']
        try:
            self.input_output_rules = attr['input_output_rules']
        except KeyError:
            self.input_output_rules = (not self.window.use_edenwall)
        if result and (self.compatibility.mode == 'GUI2'):
            return result
        else:
            return {'undoState': None}

    def create(self, filetype, parent_template):
        self.close()
        result = self('rulesetCreate', filetype, parent_template)
        self.is_open = True
        result = self.readAttributes(result)
        self.reset()
        return result

    def open(self, filetype, name):
        result = self('rulesetOpen', filetype, name)
        self.is_open = True
        result =  self.readAttributes(result)
        self.reset()
        return result

    def rulesetSaveAs(self, name):
        result = self('rulesetSaveAs', name)
        self.is_open = True
        result = self.readAttributes(result)
        return result['undoState']

    def close(self, check_error=True):
        if not self.is_open:
            return
        try:
            self('rulesetClose')
        except RpcdError:
            if check_error:
                raise
        self.is_open = False
        self.reset()

    def quit(self):
        if hasattr(self, "is_open"):
            self.close(check_error=False)
        self.client.logout()

    def __del__(self):
        self.quit()

    def setFusion(self, enabled):
        if not self.is_open:
            return
        self.fusion = enabled
        window = self.window
        if window.compatibility.set_fusion_service:
            updates = self('setFusion', enabled)
            self.window.refresh(updates)
        else:
            libraries = (
                window.object_libraries['resources'],
                window.object_libraries['user_groups'])
            for library in chain(
            libraries,
            window.rules.itervalues()):
                library.refresh()
                library.display()

