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

from ufwi_rpcd.common.human import humanYesNo
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.html import Html, htmlBold, htmlImage, NBSP

from ufwi_rulesetqt.objects import formatObjects
from ufwi_rulesetqt.rule.edit_list import EditList, NetworkEditList, ProtocolEditList
from ufwi_rulesetqt.rule.rule import Rule
from ufwi_rulesetqt.tools import getIdentifier, getIdentifiers

class Acl(Rule):
    SMALL_ICONS = {
        u'ACCEPT': ":/icons-20/go-next.png",
        u'DROP':   ":/icons-20/drop.png",
        u'REJECT': ":/icons-20/reject.png",
    }
    ICONS = {
        u'ACCEPT': ":/icons-32/go-next.png",
        u'DROP':   ":/icons-32/drop.png",
        u'REJECT': ":/icons-32/reject.png",
    }
    OBJECT_ATTR = {
        # Acl attribute name => {'name':library name, 'editor':EditorClass}
        # This dictionary is used to build the ACL editor
        'sources': {'name': 'resources', 'editor': NetworkEditList},
        'destinations': {'name':'resources', 'editor': NetworkEditList},
        'protocols': {'name': 'protocols', 'editor': ProtocolEditList},
        'user_groups': {'name':'user_groups','editor': EditList},
    }
    MANDATORY_ATTR = set(('sources', 'protocols', 'destinations'))
    FORMAT = None

    def __init__(self, window, rules, item, rule_type):
        resources = window.object_libraries['resources']
        item['input'] = resources[item['input']]
        item['output'] = resources[item['output']]
        for acl_attr in ['operating_systems', 'applications', 'periodicities', 'durations']:
            item[acl_attr] = [window.object_libraries[acl_attr][id] for id in item[acl_attr]]
            item[acl_attr].sort(key=getIdentifier)

        if window.compatibility.platform:
            for acl_attr in ['source_platforms', 'destination_platforms']:
                item[acl_attr] = [window.object_libraries['platforms'][id] for id in item[acl_attr]]
                item[acl_attr].sort(key=getIdentifier)

        Rule.__init__(self, window, rules, item, rule_type)
        self.right_arrow_character = window.right_arrow_character

    def createValue(self, key, value):
        if key == 'id':
            return int(value)
        else:
            return Rule.createValue(self, key, value)

    def getSmallIcon(self):
        return self.SMALL_ICONS[self['decision']]

    def getIcon(self):
        return self.ICONS[self['decision']]

    def isInput(self):
        return (self['chain'] == u'INPUT')

    def isOutput(self):
        return (self['chain'] == u'OUTPUT')

    def isForward(self):
        return (self['chain'] == u'FORWARD')

    def createChainKey(self):
        if self.isForward():
            return (self['input']['id'], self['output']['id'])
        else:
            return self['chain']

    def getSources(self):
        if self['sources']:
            return self['sources']
        else:
            return self['source_platforms']

    def getDestinations(self):
        if self['destinations']:
            return self['destinations']
        else:
            return self['destination_platforms']

    def createInformation(self):
        options = []

        title = unicode(self)

        extra = []
        template = self.getTemplate()
        if template:
            extra.append(template)
        if not self['enabled']:
            extra.append(tr('disabled'))
        if not self['mandatory']:
            extra.append(tr('optional'))
        if extra:
            title += ' (%s)' % u', '.join(extra)
        decision = htmlImage(self.getIcon(), align="middle")
        decision += NBSP + Html(self['decision'])
        options.extend((
            (tr('Decision'), decision),
            (tr('Chain'), self['chain']),
            (tr('Sources'), formatObjects(self.getSources())),
            (tr('Destinations'), formatObjects(self.getDestinations())),
            (tr('Protocols'), formatObjects(self['protocols'])),
        ))
        if self['user_groups']:
            options.append((tr('User Groups'), formatObjects(self['user_groups'])))
        if self['applications']:
            options.append((tr('Applications'), formatObjects(self['applications'])))
        if self['operating_systems']:
            options.append((tr('Operating Systems'), formatObjects(self['operating_systems'])))
        if self['periodicities']:
            options.append((tr('Time Criteria'), formatObjects(self['periodicities'])))
        if self['durations']:
            options.append((tr('Durations'), formatObjects(self['durations'])))
        log = htmlBold(humanYesNo(self['log']))
        if 'log_prefix' in self:
            log = tr('%s, prefix="%s"') % (log, htmlBold(self['log_prefix']))
        options.extend((
            (tr('Logging'), Html(log, escape=False)),
            (tr('Input'), self['input'].createHTML()),
            (tr('Output'), self['output'].createHTML()),
        ))
        if 'comment' in self:
            options.append((tr('Comment'), self['comment']))
        return title, options

    def createDebugOptions(self, options):
        options.append((tr('Identifier'), self['id']))

    def __repr__(self):
        return '<ACL #%s>' % self['id']
    __str__ = __repr__

    def formatToolTip(self, items):
        if not items:
            return ''

        items = getIdentifiers(items)
        if 1 < len(items):
            return '{%s}' % ', '.join(items)
        else:
            return items[0]

    def getToolTip(self):
        # TODO remove first lines of formatToolTip
        # self['source_platforms'] -> list of string, must be list of platform
        sources = self.getSources()
        destinations = self.getDestinations()
        filters = self.formatToolTip(self['protocols'])
        return "%s --%s--> %s" % (
            self.formatToolTip(sources),
            filters,
            self.formatToolTip(destinations))

    def __unicode__(self):
        chain = self.createChainKey()
        if isinstance(chain, tuple):
            chain = chain[0] + self.right_arrow_character + chain[1]
        order = self.getOrder()
        text =  u'%s #%s' % (chain, 1 + order)
        return self.FORMAT % text

class AclIPv4(Acl):
    FORMAT = tr('IPv4 rule %s')

    def __init__(self, window, item):
        Acl.__init__(self, window, window.acls_ipv4, item, 'acls-ipv4')

class AclIPv6(Acl):
    FORMAT = tr('IPv6 rule %s')

    def __init__(self, window, item):
        Acl.__init__(self, window, window.acls_ipv6, item, 'acls-ipv6')

