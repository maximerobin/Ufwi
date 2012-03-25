
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

from twisted.python.failure import Failure

from ..common.task import MultiSiteTask
from ufwi_rpcd.backend import tr

class UpdateTask(MultiSiteTask):
    def __init__(self, core, ctx, fw, sched_options, filename, encoded_bin):
        self.archive_no = -1
        self.filename = filename
        self.encoded_bin = encoded_bin
        self.bin_status = True
        MultiSiteTask.__init__(self, core, ctx, fw, sched_options)

    def callback(self):
        d = self.distantCall('nuconf', 'takeWriteRole')
        d.addCallback(lambda x:self.pushUpdate())
        d.addBoth(self.releaseLock)
        return d

    def stop_callback(self):
        return self.deleteArchive()

    def getDescription(self):
        return tr('Apply update %s') % self.filename

    def pushUpdate(self, err = None):
        self.bin_status = True
        d = self.pushUpdateFile()
        d.addCallback(self.pushApplyUpdate)
        d.addCallback(self.applyOk)
        return d

    def distantCall(self, *args, **kw):
        d = self.core.callService(self.ctx, 'multisite_master', 'callRemote', self.fw.name, *args, **kw)
        return d

    def pushUpdateFile(self):
        self.bin_status = True
        self.fw.info(tr("Applying update %s to firewall %s") % (self.filename, self.fw.name))
        d = self.distantCall('update', 'sendUpgradeArchive', self.filename, self.encoded_bin)
        return d

    def pushApplyUpdate(self, ret):
        return self.distantCall('update', 'applyUpgrades', [ret])

    def applyOk(self, ret):
        self.fw.info(tr("Update %s correctly applied to firewall %s") % (self.filename, self.fw.name))
        self.status = tr("Update applied")
        return "done"

    def releaseLock(self, result):
        self.distantCall('nuconf', 'endUsingWriteRole')
        if isinstance(result, Failure):
            return result
        return None

    def deleteArchive(self, ret):
        if self.archive_no != -1:
            self.distantCall('update', 'deleteArchive', self.archive_no)
        self.archive_no = -1
        return "done"

    def setError(self, err):
        self.bin_status = False
        MultiSiteTask.setError(self, err)

    def getStatus(self):
        return self.bin_status, self.status

    @classmethod
    def getRole(self):
        return 'nuconf_'
