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

from ufwi_rpcd.common import tr

from ufwi_ruleset.common.rule import (NAT_TRANSLATE,
    NAT_PREROUTING_ACCEPT, NAT_POSTROUTING_ACCEPT)

from ufwi_rulesetqt.rule.edit_list import EditList
from ufwi_rulesetqt.rule.rule import Rule
from ufwi_rulesetqt.objects import formatObjects

NAT_TYPE_LABELS = {
    NAT_TRANSLATE: tr("Translate"),
    NAT_PREROUTING_ACCEPT: tr("ACCEPT Destination NAT"),
    NAT_POSTROUTING_ACCEPT: tr("ACCEPT Source NAT"),
}

NAT_CHAIN_LABELS = {
    'PREROUTING': tr('Destination NAT'),
    'POSTROUTING': tr('Source NAT'),
}

class Nat(Rule):
    # Acl attribute name => {'name':library name, 'editor':EditorClass}
    # This dictionary is used to build the NAT editor
    OBJECT_ATTR = {
        'sources': {'name':'resources', 'editor':EditList},
        'destinations': {'name':'resources', 'editor':EditList},
        'filters': {'name':'protocols', 'editor':EditList},
        'nated_sources': {'name':'resources', 'editor':EditList},
        'nated_destinations': {'name':'resources', 'editor':EditList},
        'nated_filters': {'name':'protocols', 'editor':EditList},
    }

    MANDATORY_ATTR = set((
        'sources', 'destinations',
        # nated sources and destinations are exclusive
        'nated_sources', 'nated_destinations',
    ))

    def __init__(self, window, item):
        Rule.__init__(self, window, window.nats, item, 'nats')

    def getIcon(self):
        return ":/icons-20/go-next.png"

    def createChainKey(self):
        return self['chain']

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
        if self.main.compatibility.nat_support_accept:
            type = self.get('type', NAT_TRANSLATE)
            translate = (type == NAT_TRANSLATE)
            label = NAT_TYPE_LABELS[type]
            options.append((tr('Type'), label))
        else:
            translate = False
        chain = self['chain']
        chain_label = NAT_CHAIN_LABELS[chain]
        options.extend((
            (tr('Chain'), chain_label),
            (tr('Sources'), formatObjects(self['sources'])),
            (tr('Protocols'), formatObjects(self['filters'])),
            (tr('Destinations'), formatObjects(self['destinations'])),
        ))
        if translate:
            if chain == u"POSTROUTING":
                options.extend(((tr('Translated source'), formatObjects(self['nated_sources'])),))
            else:
                options.extend(((tr('Translated protocols'), formatObjects(self['nated_filters'])),
                    (tr('Translated destinations'), formatObjects(self['nated_destinations'])),
                ))
        if 'comment' in self:
            options.append((tr('Comment'), self['comment']))
        return title, options

    def createDebugOptions(self, options):
        options.append((tr('Identifier'), self['id']))

    def __unicode__(self):
        order = 1 + self.getOrder()
        text =  u'#%s' % order
        if self['chain'] == 'PREROUTING':
            return tr('Destination NAT rule %s') % text
        else:
            return tr('Source NAT rule %s') % text

