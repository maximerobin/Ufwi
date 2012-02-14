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

from IPy import IP
import weakref

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.human import humanYesNo
from ufwi_rpcd.common.tools import abstractmethod, formatList

from ufwi_rpcc_qt.html import (Html,
    htmlBold, htmlLink, htmlImage, htmlSpan, NBSP, BR)

from ufwi_ruleset.common.update import Update, Updates

class BaseObject(dict):
    def __init__(self, library, item):
        self.library = library
        dict.__init__(self,
            ((key, self.createValue(key, value))
            for key, value in item.iteritems()))

    def updateReferences(self, all_updates):
        get_model = self.library.window.getModel
        for domain, identifier in self['references']:
            update = Update(domain, 'update', identifier)
            if domain not in all_updates:
                all_updates[domain] = Updates()
            updates = all_updates[domain]
            updates.addUpdate(update)

            if domain != self.library.REFRESH_DOMAIN:
                continue
            model = get_model(domain)
            object = model[identifier]
            if isinstance(object, Group):
                object.updateReferences(all_updates)

    def update(self, item, update_references, all_updates, updates):
        delete_keys = set(self.iterkeys()) - set(item.iterkeys())
        for key in delete_keys:
            del self[key]
        for key, value in item.iteritems():
            if key == 'children' and key in self:
                children = self[key]
                children.updateObjects(self.library, value, all_updates, updates)
                for child in children.itervalues():
                    child['parent'] = weakref.ref(self)
            else:
                self[key] = self.createValue(key, value)
        if update_references:
            self.updateReferences(all_updates)

    def createChildren(self, value):
        children = Objects(self.library, value)
        for child in children.itervalues():
            child['parent'] = weakref.ref(self)
        return children

    def createValue(self, key, value):
        if key == 'address':
            return IP(value)
        elif key == 'comment':
            return unicode(value)
        elif key == 'addresses':
            return [ IP(network) for network in value ]
        elif key == 'children':
            return self.createChildren(value)
        elif key == 'address_types':
            return set(value)
        elif key == 'objects':
            # Sort group objects by identifier
            value = list(value)
            value.sort()
            return value
        else:
            return value

    def isEditable(self):
        return self['editable']

    def allowCreate(self):
        return True

    def information(self, highlight=True):
        self.library.information(self, highlight=highlight)

    def getToolTip(self):
        return None

    def formatID(self):
        identifier = self['id']
        if 'physical_id' in self:
            identifier = '%s (%s)' % (identifier, self['physical_id'])
        return identifier

    def createHTML(self, text=True, link=True, icon=True, tooltip=False):
        identifier = self.formatID()
        if icon:
            image = self.getSmallIcon()
        else:
            image = None
        if image:
            html = htmlImage(image, align="middle")
            if text:
                html += NBSP + identifier
        else:
            html = Html(identifier)
        if link:
            url = self.library.highlight_format % self['id']
            html = htmlLink(url, html)
        if tooltip:
            tooltip_text = self.getToolTip()
            if tooltip_text:
                html = htmlSpan(html, title=tooltip_text)
        return html

    def createDebugOptions(self, options):
        options.append((tr('Editable'), humanYesNo(self['editable'])))
        if 'physical_id' in self:
            options.append((tr('Physical ID'), self['physical_id']))
        if 'from_template' in self:
            options.append((tr('From template'), self['from_template']))

    def createReferencesHTML(self, glue=None, icon=True):
        if not self['references']:
            return tr("(none)")
        references = []
        get_model = self.library.window.getModel
        if glue:
            glue = Html(glue)
        else:
            glue = BR
        for update_domain, object_id in self['references']:
            model = get_model(update_domain)
            try:
                object = model[object_id]
            except KeyError:
                html = u'Broken reference: %s[%s]' % (update_domain, object_id)
                html = htmlBold(html)
            else:
                html = object.createHTML(icon=icon, tooltip=True)
            references.append(html)
        return glue.join(references)

    def isGeneric(self):
        return False

    def __repr__(self):
        return "<%s id=%r>" % (self.__class__.__name__, self["id"])

    def __unicode__(self):
        raise self["id"]

    def getParents(self):
        return set()

    def getChildren(self):
        return set()

    def __eq__(self, other):
        return self['id'] == other['id']

    def getSmallIcon(self):
        return self.getIcon()

    #--- abstract methods ------------

    def getIcon(self):
        return None

    def getBackground(self):
        return None

    @abstractmethod
    def createInformation(self):
        # return (title, html table lines)
        pass

class Object(BaseObject):
    def createValue(self, key, value):
        if key in ('id', 'physical_id'):
            return unicode(value)
        else:
            return BaseObject.createValue(self, key, value)

class Group(Object):
    def information(self, highlight=True):
        self.library.information(self, highlight=highlight)

    def _getObject(self, identifier):
        return self.library[identifier]

    def getObjectList(self):
        return [ self._getObject(id) for id in self['objects']]

    def getSmallIcon(self):
        return ":/icons-20/groupe_objets.png"

    def getIcon(self):
        return ":/icons-32/groupe_objets.png"

    def getBackground(self):
        return ":/backgrounds/group.png"

    def getToolTip(self):
        objects = (
            "%s (%s)" % (identifier, self._getObject(identifier).getToolTip())
            for identifier in self['objects']
        )
        text = formatList(objects, u",\n", 500)
        return tr("Group:\n%s") % text

    def createInformation(self):
        title = tr('Group')
        objects = (self.library[identifier] for identifier in self['objects'])
        objects = formatObjects(objects)
        options = [
            (tr('Identifier'), htmlBold(self['id'])),
            (tr('Objects'), objects),
            (tr('References'), self.createReferencesHTML()),
        ]
        return title, options

    def getParents(self):
        parents = set()
        for object in self.getObjectList():
            parents.add(object['id'])
            parents |= object.getParents()
        return parents

    def getChildren(self):
        children = set()
        for object in self.getObjectList():
            children.add(object['id'])
            children |= object.getChildren()
        return children

    def allowCreate(self):
        return False

class Objects(dict):
    def __init__(self, controler, items):
        self.updateObjects(controler, items)

    def createObject(self, controler, item):
        if 'objects' in item:
            return controler.GROUP_CLASS(controler, item)
        else:
            return controler.CHILD_CLASS(controler, item)

    def updateObjects(self, controler, items, all_updates=None, updates=None):
        if updates is not None:
            update_identifiers = updates.partialUpdate()
            if update_identifiers is None:
                update_identifiers = set()
        else:
            update_identifiers = set()
        delete_keys = set(self.iterkeys()) - set(item['id'] for item in items)
        for key in delete_keys:
            del self[key]
        for item in items:
            key = item['id']
            try:
                object = self[key]
            except KeyError:
                object = self.createObject(controler, item)
            else:
                # if update_references is True, update() fills all_update to
                # ask to redisplay the references the updated object
                update_references = (key in update_identifiers)
                object.update(item, update_references, all_updates, updates)
            self[key] = object

def formatObjects(objects):
    if not objects:
        return htmlBold(tr("(any)"))
    return BR.join(object.createHTML(tooltip=True) for object in objects)

