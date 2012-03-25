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

from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.html import htmlSpan, Html, htmlImage, htmlLink, NBSP

from ufwi_rulesetqt.objects import BaseObject
from ufwi_rulesetqt.tools import getIdentifier

class Rule(BaseObject):
    # Attribute name (str) => library name (str)
    OBJECT_ATTR = None
    MANDATORY_ATTR = set()

    def __init__(self, main, rules, attr, rule_type):
        # Main window
        self.main = main

        # attr contains a list of id,
        # replace them with the instance of the object they represent
        for acl_attr, library_obj in self.OBJECT_ATTR.iteritems():
            library_name = library_obj['name']
            library = main.object_libraries[library_name]
            attr[acl_attr] = [library[identifier] for identifier in attr[acl_attr]]
            attr[acl_attr].sort(key=getIdentifier)

        self.rule_type = rule_type
        self.ruleset = main.ruleset

        self.controler = rules
        self.model = rules.model

        BaseObject.__init__(self, self.controler, attr)

    def getTemplate(self):
        if (not self.ruleset.templates) or (self['id'] % 10) == 0:
            return None
        ruleset_id = self['id'] % 10
        return self.ruleset.templates[ruleset_id]['name']

    def formatID(self, with_template=True):
        text = '#%s' % (self['id'] // 10)
        if with_template:
            template = self.getTemplate()
            if template:
                text += u' (%s)' % template
        return text

    def getBackground(self):
        if self['enabled']:
            return ":/backgrounds/acl",
        else:
            return ":/backgrounds/acl-disabled",

    def createHTML(self, text=True, link=True, icon=True, tooltip=True):
        identifier = unicode(self)
        identifier = Html(identifier)
        if icon:
            image = self.getSmallIcon()
        else:
            image = None
        if image:
            html = htmlImage(image)
            if text:
                html += NBSP + identifier
        else:
            html = identifier
        if tooltip:
            tooltip_text = self.getToolTip()
            if tooltip_text:
                html = htmlSpan(html, title=tooltip_text)
        if link:
            url = self.controler.highlight_format % self['id']
            html = htmlLink(url, html)
        return html

    def getToolTip(self):
        return None

    def __eq__(self, other):
        if other.__class__ != self.__class__:
            return False
        return other['id'] == self['id']

    def getChain(self):
        return self.model.getChain(self)

    def getOrder(self):
        chain = self.getChain()
        return chain.index(self)

    def highlight(self):
        self.controler.highlight(self['id'])

    # --- abstract methods ---

    @abstractmethod
    def createChainKey(self):
        pass

    @abstractmethod
    def __unicode__(self):
        pass

