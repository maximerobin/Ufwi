
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

from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QWidget, QFont, QMessageBox
from ufwi_rpcd.common import tr
from .edw_data import EdwData
from .cell_data import BlankCell, AttributeComboBox, AttributeCell
from .cell_edw_generic import GenericGlobalStatus, GenericSumAttributeCell, GenericCheckBox, GenericFileDialogButton, GenericServiceStatus
from .strings import APP_TITLE

class GenericEdw(EdwData):
    BG_COLOR = "#55aadd"
    def __init__(self, window, edw_list, client):
        EdwData.__init__(self, window, client, tr('All firewalls'))
        self.name = tr('All firewalls')
        self.edw_list = edw_list
        self.dropped_packets_min = -1
        self.dropped_packets_max = 0

        # NuFace related
        self.send_rules = True
        self.template_list = []
        self.template = u''
        self.template_index = 0

        # NuConf related
        self.nuconf_update_send = True

        self.cell_classes = {
            'name' :                    AttributeCell(self, [], 'name'),
            'current_template' :        BlankCell(),
            'template_version' :        BlankCell(),
            'template_edition_time' :   BlankCell(),
            'links_validity' :          BlankCell(),
            'nuface_status' :           BlankCell(),
            'revision' :                BlankCell(),
            'edenwall_type' :           BlankCell(),
            'last_seen' :               BlankCell(),
            'nuconf_update_filepath' :  BlankCell(),
            'user_count' :              BlankCell(),
            'bandwidth_in' :            BlankCell(),
            'bandwidth_out' :           BlankCell(),
            'error' :                   BlankCell(),
            'global_status' :           GenericGlobalStatus(edw_list, []),
            'dropped_packets' :         GenericSumAttributeCell(edw_list, [], 'dropped_packets'),
            'nuauth_users' :            GenericSumAttributeCell(edw_list, [], 'nuauth_users'),
            'nuface_template' :         AttributeComboBox(self, ['nuface_write'], 'template_list', 'template_index', self.templateChanged),
            'send_rules' :              GenericCheckBox(self, edw_list, ['nuface_write'], 'send_rules'),
            'nuconf_update_browse' :    GenericFileDialogButton(self, edw_list, ['nuconf_write'], 'nuconf_update_filepath'),
            'nuconf_update_send' :      GenericCheckBox(self, edw_list, ['nuconf_write'], 'nuconf_update_send'),
            'nuconf_update_status' :    BlankCell(),
            'monitoring_load' :         BlankCell(),
            'monitoring_mem' :          BlankCell(),
        }

        widget = QWidget()
        self.font = QFont(widget.font())
        self.font.setBold(True)
        for cell in self.cell_classes.itervalues():
            cell.setFont(self.font)
            cell.setColor(self.BG_COLOR)

    def getServices(self):
        return {}

    def getCell(self, attr):
        if attr not in self.cell_classes.keys():
            self.refreshServices()
            self.refreshHdd()
        if attr not in self.cell_classes.keys():
            cell = BlankCell()
            cell.setFont(self.font)
            cell.setColor(self.BG_COLOR)
            return u'', cell.getCell()
        return EdwData.getCell(self, attr)

    def getVal(self, attr):
        if attr not in self.cell_classes.keys():
            self.refreshServices()
            self.refreshHdd()
        return EdwData.getVal(self, attr)

    def getCategoryCell(self, attr):
        cell = BlankCell()
        cell.setFont(self.font)
        cell.setColor(self.BG_COLOR)
        return u'', cell.getCell()

    def getCategoryVal(self, attr):
        return u''

    def setRulesetList(self, lst):
        self.ruleset_list = [r[0] for r in lst]
        self.ruleset_list.sort()
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')

    def setRulesetListError(self, err):
        self.ruleset_list = None
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')

    def setRulesetCurrent(self, data):
        self.ruleset_apply_time = data[0]
        self.ruleset = data[1]
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')
        self.emit(SIGNAL('display_cell'), self, 'last_local_apply')

    def setRulesetCurrentError(self, ruleset):
        self.ruleset = u''
        self.ruleset_apply_time = 0
        self.emit(SIGNAL('display_cell'), self, 'nuface_rules')
        self.emit(SIGNAL('display_cell'), self, 'last_local_apply')

    def refreshNuFaceData(self):
        return

    def setError(self, error):
        self.error = error
        self.emit(SIGNAL('display_cell'), self, 'error')

    def setTemplateList(self, lst, lst_time):
        self.template_list = lst
        if self.template not in lst:
            self.template = u''
        self.emit(SIGNAL('display_cell'), self, 'nuface_template')

    def askConfirmation(self, text):
        return QMessageBox.question(None, APP_TITLE, text, QMessageBox.Yes | QMessageBox.No) == QMessageBox.Yes

    def templateChanged(self, index):
        if index >= 0:
            self.template_index = index
        if index < 1:
            return
        host_count = self.countRole(['nuface_write'])
        if self.askConfirmation(tr("This will assign the template to %i hosts.\nAre you sure you want to do this?") % host_count):
            if index == 1:
                self.template = u''
            else:
                self.template = self.template_list[index]

            for edw in self.edw_list:
                if not edw.haveRole('nuface_write'):
                    continue
                edw.template = self.template
                edw.template_index = index
                edw.updateMissingLinks()
                self.emit(SIGNAL('display_cell'), edw, 'nuface_template')

        self.emit(SIGNAL('display_cell'), self, 'nuface_template')

    def refreshAttrMinMax(self, attr):
        first_val = True

        for edw in self.edw_list:
            try:
                val = getattr(edw, attr)
            except AttributeError:
                # The async call may not yet have finished for this edw
                continue
            if not isinstance(val, int):
                continue

            if first_val:
                first_val = False
                min = val
                max = val

            if val < min:
                min = val

            if val > max:
                max = val

            try:
                max_at_least = getattr(edw, attr + '_max_at_least')
                if max < max_at_least:
                    max = max_at_least
            except AttributeError:
                pass

        setattr(self, attr + '_min', min)
        setattr(self, attr + '_max', max)

        for edw in self.edw_list:
            edw.setAttrMinMax(attr, min, max)

    def isHeader(self):
        return True

    def refreshServices(self):
        for edw in self.edw_list:
            for svc in edw.getServices().iterkeys():
                if svc not in self.cell_classes.keys():
                    self.cell_classes[svc] = GenericServiceStatus(self.edw_list, [], svc)
                    self.cell_classes[svc].setFont(self.font)
                    self.cell_classes[svc].setColor(self.BG_COLOR)

    def refreshHdd(self):
        for edw in self.edw_list:
            for hdd in edw.cell_classes.iterkeys():
                if hdd[:4] == 'hdd_' and hdd not in self.cell_classes:
                    self.cell_classes[hdd] = BlankCell()
                    self.cell_classes[hdd].setColor(self.BG_COLOR)

    def haveRole(self, perm):
        # Generic firewalls don't check roles
        # It's done on a per firewall basis
        return True

    def haveRoles(self, perm):
        # Generic firewalls don't check roles
        # It's done on a per firewall basis
        return True

    def countRole(self, perm):
        count = 0
        for edw in self.edw_list:
            if edw.haveRoles(perm):
                count += 1
        return count
