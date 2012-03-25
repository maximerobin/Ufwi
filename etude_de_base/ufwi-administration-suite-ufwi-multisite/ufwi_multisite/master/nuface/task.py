
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

from twisted.internet.defer import succeed
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.error import RpcdError
from nuface.config import NUFACE_DIR
from ..common.task import MultiSiteTask

class RuleApplicationTask(MultiSiteTask):
    def __init__(self, core, ctx, fw, sched_options, template, generic_links):
        self.template = template
        self.generic_links = generic_links
        MultiSiteTask.__init__(self, core, ctx, fw, sched_options)

    def getDescription(self):
        return tr('Apply template %s') % self.template

    def callback(self):
        d = succeed(None)
        if self.template != '':
            d.addCallback(lambda x:self.core.callService(self.ctx, 'nuface', 'getMissingLinks', 'template', self.template, self.generic_links))
            d.addCallback(self.checkLinks)

        d.addCallback(self.pushTemplate)
        d.addCallback(self.pushApplyRules)
        d.addCallback(self.applyOk)
        return d

    def checkLinks(self, links):
        if links != {}:
            count = 0
            for link in links.itervalues():
                count += len(link)
            raise RpcdError(tr("%i generic links are not defined, please set them before applying the template") % count)

    def stop_callback(self):
        return self.deleteTemplate()

    @classmethod
    def getRole(cls):
        return 'nuface_'

    def distantCall(self, *args, **kw):
        d = self.core.callService(self.ctx, 'multisite_master', 'callRemote', *args, **kw)
        return d

    def pushTemplate(self, unused):
        self.fw.info(tr("Applying ruleset %s to firewall %s") % (self.template, self.fw.name))
        self.template_url = u''
        if self.template == u'':
            return succeed("done")
        f = open('%s/templates/%s.xml' % (NUFACE_DIR, self.template), 'r')
        data = f.read()
        d = self.core.callService(self.ctx, 'multisite_transport', 'hostFile', data)
        d.addCallback(self.setTemplateUrl)
        return d

    def setTemplateUrl(self, template_url):
        self.template_url = template_url
        return "done"

    def pushApplyRules(self, ret):
        return self.distantCall(self.fw.name, 'nuface', 'applyMultisite', self.template_url, self.generic_links)

    def applyOk(self, ret):
        self.fw.info(tr("Ruleset %s correctly applied to firewall %s") % (self.template, self.fw.name))
        self.status = tr("Ruleset applied")
        return "done"

    def deleteTemplate(self):
        if self.template_url != u'':
            self.core.callService(self.ctx, 'multisite_transport', 'removeFile', self.template_url)
            self.template_url = u''
        return "done"
