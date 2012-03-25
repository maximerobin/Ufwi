
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
from time import mktime
from os.path import basename

from PyQt4.QtCore import Qt, SIGNAL, QString
from PyQt4.QtGui import QAction, QMessageBox
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.common.download import encodeFileContent
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.services_name import ComponentToName
from ufwi_rpcc_qt.start_eas import startEAS
from nuconf.common.ha_statuses import PRIMARY, SECONDARY, ENOHA
from .edw_data import EdwData
from .cell_widget import EdwCell
from .cell_data import AttributeCell, AttributeBool, AttributeComboBox, AttributeFile, COLOR_RED, COLOR_GREEN
from .cell_edw import AttributeCheckBox, AttributeProgressBar, FileDialogButton, GlobalStatus, ServiceStatus
from .strings import APP_TITLE, MULTISITE_COLUMNS
#from .start_eas import start_eas

class Edw(EdwData):
    def __init__(self, window, name, hostname, client, roles):
        EdwData.__init__(self, window, client, name)
        self.name = name
        self.global_status = u''
        self.error = u''
        self.categories = self.client.call("multisite_master", "getFirewallCategories", self.name)
        self.read_only = window.read_only
        self.hostname = hostname
        self.roles = list(roles)

        # NuFace related
        self.generic_links = {}
        if self.haveRole('ruleset_read'):
            self.generic_links = self.client.call('multisite_nuface', 'getGenericLinks', self.name)
        self.send_rules = True
        self.send_rules_status = u''
        self.template_list = []
        self.template_edition_time = ''
        self.template_edition_time_tooltip = ''
        self.template_edition_time_dict = {}
        self.template = u''
        self.current_template = u''
        self.template_index = 0
        self.template_version = u''
        self.template_apply_time = 0
        self.setMissingLinksText(tr('OK'), True)
        self.missing_links = {}
        self.last_seen = 0
        self.last_seen_str = tr('Not available')

        self.ruleset_list = None
        self.ruleset = u''
        self.ruleset_apply_time = 0

        # NuLog related
        self.dropped_packets = tr('Not available')
        self.dropped_packets_max = 0
        self.dropped_packets_min = 0
        self.bandwidth_in = tr('Not available')
        self.bandwidth_in_min = 0
        self.bandwidth_in_max = 0
        self.bandwidth_in_max_at_least = 1
        self.bandwidth_out = tr('Not available')
        self.bandwidth_out_min = 0
        self.bandwidth_out_max = 0
        self.bandwidth_out_max_at_least = 1

        # Nuauth command users
        self.nuauth_users = tr('Not available')
        self.nuauth_users_min = 0
        self.nuauth_users_max = 0
        self.nuauth_users_max_at_least = 1

        self.revision = tr('Not available')
        self.edenwall_type = tr('Not available')

        self.nuconf_update_filepath = ''
        self.nuconf_update_status = ''
        self.nuconf_update_send = True

        # Monitoring
        self.monitoring_load = 0
        self.monitoring_load_min = 0
        self.monitoring_load_max = 100
        self.monitoring_load_max_at_least = 100
        self.monitoring_mem = 0
        self.monitoring_mem_min = 0
        self.monitoring_mem_max = 100

        self.ha_mode = tr('No HA')

        self.cell_classes = {
            'name' :                        AttributeCell(self, [], 'name'),
            'global_status' :               GlobalStatus(self, []),
            'dropped_packets' :             AttributeProgressBar(self, ['log_read'], 'dropped_packets', 'dropped_packets_min', 'dropped_packets_max', COLOR_GREEN, COLOR_RED),
            'nuauth_users' :                AttributeProgressBar(self, ['nuauth_command_read'], 'nuauth_users', 'nuauth_users_min', 'nuauth_users_max', COLOR_GREEN, COLOR_GREEN),
            'bandwidth_in' :                AttributeProgressBar(self, ['log_read'], 'bandwidth_in', 'bandwidth_in_min', 'bandwidth_in_max', COLOR_GREEN, COLOR_RED, '%v b/s'),
            'bandwidth_out' :               AttributeProgressBar(self, ['log_read'], 'bandwidth_out', 'bandwidth_out_min', 'bandwidth_out_max', COLOR_GREEN, COLOR_RED, '%v b/s'),
            'error' :                       AttributeCell(self, [], 'error'),
            'nuface_template' :             AttributeComboBox(self, ['ruleset_write'], 'template_list', 'template_index', self.templateChanged),
            'template_edition_time' :       AttributeCell(self, ['ruleset_write'], 'template_edition_time'),
            'current_template' :            AttributeCell(self, ['ruleset_read'], 'current_template'),
            'template_version' :            AttributeCell(self, ['ruleset_read'], 'template_version'),
            'nuface_status' :               AttributeCell(self, ['ruleset_read'], 'send_rules_status'),
            'revision' :                    AttributeCell(self, ['conf_read'], 'revision'),
            'edenwall_type' :               AttributeCell(self, ['conf_read'], 'edenwall_type'),
            'nuconf_update_filepath' :      AttributeFile(self, ['conf_write'], 'nuconf_update_filepath'),
            'links_validity' :              AttributeBool(self, ['ruleset_write'], 'links_validity', 'links_validity_bool'),
            'send_rules' :                  AttributeCheckBox(self, ['ruleset_write'], 'send_rules'),
            'nuconf_update_send' :          AttributeCheckBox(self, ['conf_write'], 'nuconf_update_send'),
            'last_seen' :                   AttributeCell(self, [], 'last_seen_str'),
            'nuconf_update_browse' :        FileDialogButton(self, ['conf_write'], 'nuconf_update_filepath'),
            'nuconf_update_status' :        AttributeCell(self, ['conf_read'], 'nuconf_update_status'),
            'monitoring_load' :             AttributeProgressBar(self, ['log_read'], 'monitoring_load', 'monitoring_load_min', 'monitoring_load_max', COLOR_GREEN, COLOR_RED),
            'monitoring_mem' :              AttributeProgressBar(self, ['log_read'], 'monitoring_mem', 'monitoring_mem_min', 'monitoring_mem_max', COLOR_GREEN, COLOR_RED, '%v / 0 MB'),
            'ha_mode' :                     AttributeCell(self, ['ha_read'], 'ha_mode'),
        }

        # NuConf related
        self.services_status = {}
        self.refreshServicesStatus()

        edit_links = QAction(tr('Edit generic links'), None)
        edit_links.connect(edit_links, SIGNAL('triggered()'), lambda: self.window.setupGenericLinks(self.name))
        self.cell_classes['links_validity'].setActions([edit_links])

    def getEdwObj(self):
        return self

    def getCell(self, attr):
        val, cell = EdwData.getCell(self, attr)
        if cell:
            if self.window.is_admin:
                unregister_action = QAction(tr("Unregister firewall"), cell)
                unregister_action.connect(unregister_action, SIGNAL("triggered()"), self.unregister)
                cell.addAction(unregister_action)

            action_eas = QAction(tr("Start EAS"), cell)
            action_eas.connect(action_eas, SIGNAL("triggered()"), self.startEAS)
            if not self.global_status in ['error', 'online']:
                action_eas.setEnabled(False)
            cell.addAction(action_eas)
            cell.setContextMenuPolicy(Qt.ActionsContextMenu)

        return val, cell

    def setSystemInfo(self, system_info):
        self.edenwall_type = system_info['type']
        self.emit(SIGNAL('display_cell'), self, 'edenwall_type')

    def setVersion(self, version):
        self.revision = version
        self.emit(SIGNAL('display_cell'), self, 'revision')

    def getServices(self):
        return self.services_status

    def getCategoryCell(self, attr):
        if self.read_only:
            return self.getCategoryVal(attr), EdwCell(self.getCategoryVal(attr))
        return self.getCategoryVal(attr), None

    def getCategoryVal(self, attr):
        if attr in self.categories:
            return unicode(self.categories[attr])
        return u''

    def taskStatus(self, task_component):
        # SCHEDULED, RUNNING, FINNISHED = range(3)
        state = self.client.call(task_component, "status", self.name)

        if self.global_status == 'offline':
            # Running task are moved to scheduled
            state[0] += state[1]
            state[1] = 0
        return tr('%i running, %i scheduled, %i finished') % (state[1], state[0], state[2])

    def setAttrMinMax(self, attr, min, max):
        setattr(self, attr + '_min', min)
        setattr(self, attr + '_max', max)
        self.emit(SIGNAL('display_cell'), self, attr)

    def newService(self, svc):
        if not svc in self.cell_classes.keys():
            self.cell_classes[svc] = ServiceStatus(self, ['conf_read'], svc)
            self.services_status[svc] = ServiceStatusValues.NOT_LOADED

    def setServiceStatus(self, status):
        vals = status[0]
        vals.update(status[1]) # take in account all services

        # Set status to 'not available' by default
        for service in self.services_status.keys():
            self.services_status[service] = ServiceStatusValues.NOT_LOADED

        comp = ComponentToName()
        for svc, status in vals.items():
            if comp.display_name(svc) not in self.cell_classes:
                self.newService(comp.display_name(svc))
            self.services_status[comp.display_name(svc)] = status

        for service in self.services_status.keys():
            self.emit(SIGNAL('display_cell'), self, service)

    def setServiceError(self, err):
        self.services_status = {}
        self.global_status = 'error'
        self.error = unicode(err)
        for service in self.services_status.keys():
            self.emit(SIGNAL('display_cell'), self, service)
        self.emit(SIGNAL('display_cell'), self, 'global_status')
        self.emit(SIGNAL('display_cell'), self, 'error')

    def refreshServicesStatus(self):
        if not self.haveRole('conf_read'):
            return
        if self.global_status == 'online':
            for service in self.services_status.keys():
                self.services_status[service] = ServiceStatusValues.POLLING
                self.emit(SIGNAL('display_cell'), self, service)
            if len(self.services_status) == 0:
                try:
                    services = self.client.call("multisite_master", "callRemote", self.name, "status", "getStatus")
                    self.setServiceStatus(services)
                except RpcdError, e:
                    self.setServiceError(e)
            else:
                self.client.async().call("multisite_master", "callRemote", self.name, "status", "getStatus", callback=self.setServiceStatus, errback=self.setServiceError)

    def setNulogData(self, dropped_packets):
        if not self.haveRole('log_read'):
            return
        self.dropped_packets = int(dropped_packets['table'][0][3])
        self.dropped_packets_tooltip = tr('Dropped packets since last log tables rotation:<br><b>%i packets</b>') % int(dropped_packets['table'][0][3])
        self.emit(SIGNAL('refresh_min_max'), 'dropped_packets')
        self.emit(SIGNAL('display_cell'), self, 'dropped_packets')

    def setNuauthUsers(self, users):
        self.nuauth_users = users
        self.nuauth_users_tooltip = tr('<b>%i</b> users are currently identified') % self.nuauth_users
        self.emit(SIGNAL('display_cell'), self, 'nuauth_users')
        self.emit(SIGNAL('refresh_min_max'), 'nuauth_users')

    def refreshNulogData(self):
        if self.global_status == 'online':
            if self.haveRole('log_read'):
                self.client.async().call("multisite_master", "callRemote", self.name, "nulog", "table", "Stats", {}, callback=self.setNulogData, errback=lambda x:self.setAttrDataError(x, 'dropped_packets'))
            if self.haveRole('conf_read'):
                self.client.async().call("multisite_master", "callRemote", self.name, 'system_info', 'systemInfo', callback=self.setSystemInfo, errback=lambda x:self.setAttrDataError(x, 'edenwall_type'))
                self.client.async().call("multisite_master", "callRemote", self.name, 'nuauth_command', 'getUsersCount', callback=self.setNuauthUsers, errback=lambda x:self.setAttrDataError(x, 'nuauth_users'))
                self.client.async().call("multisite_master", "callRemote", self.name, 'update', 'getHighestApplied', callback=self.setVersion, errback=lambda x:self.setAttrDataError(x, 'nuauth_users'))

    def refreshNuconfUpdateData(self):
        self.cell_classes['nuconf_update_status'].setColor(None)
        self.nuconf_update_status = self.taskStatus('multisite_update')
        self.emit(SIGNAL('display_cell'), self, 'nuconf_update_status')

    def setLoadData(self, ret):
        self.monitoring_load = int(ret['table'][0][0])
        self.monitoring_load_tooltip = tr('Current CPU load:<br><b>%.2f</b>') % (self.monitoring_load / 100.0)
        self.cell_classes['monitoring_load'].setFormat('%.2f' % (self.monitoring_load / 100.0))
        self.emit(SIGNAL('display_cell'), self, 'monitoring_load')
        self.emit(SIGNAL('refresh_min_max'), 'monitoring_load')

    def setBandwidthData(self, ret):
        self.bandwidth_in = int(ret['table'][0][0])
        self.bandwidth_in_tooltip = tr('Current inbound rate:<br><b>%i b/s</b>') % self.bandwidth_in
        self.bandwidth_out = int(ret['table'][0][1])
        self.bandwidth_out_tooltip = tr('Current outbound rate:<br><b>%i b/s</b>') % self.bandwidth_out
        self.emit(SIGNAL('display_cell'), self, 'bandwidth_in')
        self.emit(SIGNAL('refresh_min_max'), 'bandwidth_in')
        self.emit(SIGNAL('display_cell'), self, 'bandwidth_out')
        self.emit(SIGNAL('refresh_min_max'), 'bandwidth_out')

    def setMemoryData(self, ret):
        total = int(ret['table'][0][0]) / 1024
        used = int(ret['table'][0][1]) / 1024
        available = total - used
        self.monitoring_mem_max = total
        self.monitoring_mem = used
        self.monitoring_mem_tooltip = tr('Memory:<br><b>%i MB available</b><br><b>%i MB used</b><br><b>%i MB total</b>') % (available, used, total)
        self.cell_classes['monitoring_mem'].setFormat('%%v / %i MB' % total)
        self.emit(SIGNAL('display_cell'), self, 'monitoring_mem')

    def setAttrDataError(self, ret, attr):
        setattr(self, attr, tr('Not available'))
        self.setError(ret)
        self.emit(SIGNAL('display_cell'), self, 'error')
        self.emit(SIGNAL('display_cell'), self, attr)

    def setStorageData(self, ret):
        for no, partition_path in enumerate(ret['columns']):
            if partition_path[:6] == 'total ':
                continue

            id = 'hdd_' + partition_path.replace('/', '_')
            val = int(ret['table'][0][no]) / 1024 / 1024
            max = int(ret['table'][0][no + 1]) / 1024 / 1024

            setattr(self, id, val)
            setattr(self, id + '_max', max)
            setattr(self, id + '_tooltip', tr('Partition <b>%s</b> used space:<br><b>%s / %s MB</b>') % (partition_path, val, max))

            # set a min and max member if necessary
            try:
                getattr(self, id + '_min')
            except AttributeError:
                setattr(self, id + '_min', 0)

            if id not in self.cell_classes.keys():
                self.cell_classes[id] = AttributeProgressBar(self, ['log_read'], id, id + '_min', id + '_max', COLOR_GREEN, COLOR_RED, '%%v / %i MB' % max)

            if id not in MULTISITE_COLUMNS.keys():
                MULTISITE_COLUMNS[id] = tr('Partition %s') % partition_path

            self.emit(SIGNAL('display_cell'), self, id)

    def setStorageDataError(self, ret):
        self.setError(ret)

    def setHAMode(self, mode):
        self.ha_mode = tr('Not available')

        if mode == PRIMARY:
            self.ha_mode = tr('Primary')
        elif mode == SECONDARY:
            self.ha_mode = tr('Secondary')
        elif mode == ENOHA:
            self.ha_mode = tr('No HA')
        self.emit(SIGNAL('display'), self, 'ha_mode')

    def refreshMonitoring(self):
        if self.haveRole('ha_read'):
            self.client.async().call("multisite_master", "callRemote", self.name, "ha", "getHAMode", callback=self.setHAMode, errback=lambda x:self.setAttrDataError(x, 'ha_mode'))

        if not self.haveRole('log_read'):
            return
        if self.global_status == 'online':
            self.client.async().call("multisite_master", "callRemote", self.name, "nulog", "table", "LoadStream", {}, callback=self.setLoadData, errback=lambda x:self.setAttrDataError(x, 'monitoring_load'))
            self.client.async().call("multisite_master", "callRemote", self.name, "nulog", "table", "TrafficStream", {}, callback=self.setBandwidthData, errback=lambda x:self.setAttrDataError(x, 'bandwidth'))
            self.client.async().call("multisite_master", "callRemote", self.name, "nulog", "table", "MemoryStream", {}, callback=self.setMemoryData, errback=lambda x:self.setAttrDataError(x, 'monitoring_mem'))
            self.client.async().call("multisite_master", "callRemote", self.name, "nulog", "table", "StorageStream", {}, callback=self.setStorageData, errback=self.setStorageDataError)
        else:
            self.monitoring_load = tr('Not available')
            self.monitoring_mem = tr('Not available')
            self.bandwidth_in = tr('Not available')
            self.bandwidth_out = tr('Not available')
            for cell in self.cell_classes.keys():
                if cell[:4] == 'hdd_':
                    setattr(self, cell, tr('Not available'))

    def setRulesetList(self, lst):
        self.ruleset_list = [r[0] for r in lst]
        self.ruleset_list.sort()
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')

    def setRulesetListError(self, err):
        self.ruleset_list = None
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')

    def setRulesetCurrent(self, data):
        self.ruleset = data[1]
        if self.ruleset != u'':
            self.ruleset_apply_time = int(mktime(data[0].timetuple()))
        else:
            self.ruleset_apply_time = 0
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')
        self.emit(SIGNAL('display_cell'), self, 'last_local_apply')

    def setRulesetCurrentError(self, ruleset):
        self.ruleset = u''
        self.ruleset_apply_time = 0
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')
        self.emit(SIGNAL('display_cell'), self, 'last_local_apply')

    def setGenericLinks(self, links):
        if self.generic_links != links:
            self.generic_links = links
            self.updateMissingLinks()

    def setMissingLinksText(self, txt, txt_bool):
        self.links_validity = txt
        self.links_validity_bool = txt_bool
        if txt_bool:
            self.links_validity_tooltip = tr('Links are valid')
        else:
            self.links_validity_tooltip = tr('Links are invalid:<br>%s<br>Click the "%s" button to correct them.') % (txt, self.window.ui.actionEdit_generic_links.text())

    def updateMissingLinks(self):
        if self.haveRole('ruleset_read'):
            if self.template_index == 0 or self.template == '':
                self.setMissingLinksText(tr('OK'), True)
            else:
                self.setMissingLinksText(tr('Querying'), True)
                self.client.async().call("nuface", "getMissingLinks", "template", self.template, self.generic_links, callback=self.setMissingLinks, errback=self.setMissingLinksError)

        self.emit(SIGNAL('display_cell'), self, 'links_validity')

    def setMissingLinks(self, missing_links):
        self.missing_links = missing_links
        if self.missing_links == False:
            self.setMissingLinksText(tr('Invalid links'), False)
        else:
            missing_count = 0
            for type in missing_links.values():
                missing_count += len(type)
            if missing_count != 0:
                self.setMissingLinksText(tr('%i missing') % missing_count, False)
            else:
                self.setMissingLinksText(tr('OK'), True)
        self.emit(SIGNAL('display_cell'), self, 'links_validity')

    def setMissingLinksError(self, error):
        self.cell_classes['nuface_status'].setColor(COLOR_RED)
        self.send_rules_status = tr(QString(unicode(error)))
        self.setMissingLinksText(tr('Invalid links'), False)
        self.emit(SIGNAL('display_cell'), self, 'links_validity')
        self.emit(SIGNAL('display_cell'), self, 'nuface_status')

    def setTemplateEditionTime(self):
        if self.template in self.template_edition_time_dict:
            self.template_edition_time = self.template_edition_time_dict[self.template]
            self.template_edition_time_tooltip = tr('The <b>%s</b> template was last edited on <b>%s</b>') % (self.template, self.template_edition_time_dict[self.template])
        else:
            self.template_edition_time = ''
            self.template_edition_time_tooltip = ''

    def refreshNuFaceData(self):
        if self.haveRole('ruleset_read'):
            #self.cell_classes['nuface_status'].setColor(None)
            #self.template_apply_time, self.send_rules_status, self.current_template, self.template_version = self.client.call("multisite_nuface", "getCurrentConfig", self.name)
            self.send_rules_status = self.taskStatus('multisite_nuface')
            self.emit(SIGNAL('display_cell'), self, 'nuface_status')
            if self.current_template:
                self.template_version_tooltip = tr(str('The current <b>%s</b> template was last edited on <b>%s</b>' % (self.current_template, self.template_version)))
            self.setTemplateEditionTime()

            self.updateMissingLinks()

        self.emit(SIGNAL('display_cell'), self, 'current_template')
        self.emit(SIGNAL('display_cell'), self, 'template_version')
        self.emit(SIGNAL('display_cell'), self, 'template_edition_time')
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')
        self.emit(SIGNAL('display_cell'), self, 'nuface_status')
        self.emit(SIGNAL('display_cell'), self, 'last_sent')

    def setGlobalStatus(self, status):
        self.global_status = status
        if self.global_status != 'error':
            self.setError(u'')
        self.emit(SIGNAL('display_cell'), self, 'global_status')

    def setError(self, error):
        self.error = unicode(error)
        self.emit(SIGNAL('display_cell'), self, 'error')

    def setTemplateList(self, lst, lst_time):
        self.template_list = lst
        self.template_edition_time_dict = lst_time
        if self.template not in lst:
            self.template = u''
            self.template_index = 0
        else:
            self.template_index = lst.index(self.template)

        self.setTemplateEditionTime()
        self.emit(SIGNAL('display_cell'), self, 'nuface_template')
        self.emit(SIGNAL('display_cell'), self, 'template_edition_time')

    def templateChanged(self, index):
        if index >= 0:
            self.template_index = index
        if index == 1:
            self.template = u''
            self.template_edition_time = ''
            self.template_edition_time_tooltip = ''
        elif index > 1:
            self.template = self.template_list[index]
            self.setTemplateEditionTime()
        self.updateMissingLinks()
        self.emit(SIGNAL('display_cell'), self, 'nuface_template')
        self.emit(SIGNAL('display_cell'), self, 'template_edition_time')

    def applyNufaceRules(self, sched_options):
        if not self.haveRole('nuface_write'):
            return
        if not self.send_rules:
            return

        if self.template_index < 1:
            self.cell_classes['nuface_status'].setColor(COLOR_RED)
            self.send_rules_status = tr('No template selected')
            self.emit(SIGNAL('display_cell'), self, 'nuface_status')
            return
        if self.links_validity_bool != True:
            self.cell_classes['nuface_status'].setColor(COLOR_RED)
            self.send_rules_status = tr('Generic links are invalid.')
            self.emit(SIGNAL('display_cell'), self, 'nuface_status')
            return
        self.current_template = self.template
        self.client.call("multisite_nuface", "applyRules", sched_options, self.name, self.template, self.template_edition_time, self.ruleset, u'')
        self.refreshNuFaceData()

    def applyNuconfUpdates(self, sched_options):
        if not self.haveRole('nuconf_write'):
            return
        if not self.nuconf_update_send:
            return

        if self.nuconf_update_filepath == '':
            self.cell_classes['nuconf_update_status'].setColor(COLOR_RED)
            self.nuconf_update_status = tr('No update file selected')
            self.emit(SIGNAL('display_cell'), self, 'nuconf_update_status')
            return

        filename = basename(self.nuconf_update_filepath)
        content = None
        with open(self.nuconf_update_filepath, 'rb') as fd:
            content = fd.read()
        self.client.call("multisite_update", "applyUpdate", sched_options, self.name, filename, encodeFileContent(content))
        self.refreshNuconfUpdateData()

    def setCategory(self, name, value):
        if name in self.categories and self.categories[name] == value:
            return
        self.categories[name] = value
        self.client.call("multisite_master", "setFirewallCategories", self.name, self.categories)
        self.emit(SIGNAL('display_cell'), self, name)

    def setLastSeen(self, last_seen):
        self.last_seen = last_seen
        self.last_seen_str = self.getDeltaDateStr(self.last_seen)
        self.emit(SIGNAL('display_cell'), self, 'last_seen')

    def unregister(self):
        if QMessageBox.question(None, APP_TITLE, tr("You are about to unregister the %s firewall.\nAre you sure you want to continue?") % self.getID(), QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes:
            self.client.async().call("multisite_master", "unregister_firewall", self.getID(), callback=lambda x:self.hostDeleted, errback=self.showError)
            self.global_status = 'unregistering'
            self.emit(SIGNAL('display_cell'), self, 'global_status')

    def hostDeleted(self):
        self.emit(SIGNAL("refresh_edw_list"))
        self.window.EAS_SendMessage('ufwi_rpcd_admin', 'multisiteHostDeleted')

    def showError(self, err):
        QMessageBox.critical(None, APP_TITLE, unicode(err))

    def isHeader(self):
        return False

    def startEAS(self):
        startEAS(self.window.log, ['--host=%s' % self.hostname])
        #start_eas(self.name, self.client, self.window.application)


