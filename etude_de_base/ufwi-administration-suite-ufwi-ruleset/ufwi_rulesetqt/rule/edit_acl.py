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
from PyQt4.QtCore import SIGNAL, Qt, QRegExp

from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.tools import QComboBox_setCurrentText

from ufwi_rulesetqt.rule.edit_list import EditList
from ufwi_rulesetqt.rule.edit_line import EditLine
from ufwi_rulesetqt.rule.edit import EditRule
from ufwi_rulesetqt.rule.acl import Acl
from ufwi_rulesetqt.rule.tools import fillDecisionCombo

DEFAULT_DECISION = 'ACCEPT'
DEFAULT_LOG = False
DEFAULT_LOG_PREFIX = u''

LABEL_TO_AUTH_QUALITY = {
    0: 2, # Java applet (Hello)
    1: 3, # NuFW authentication (SASL)
    2: 4, # Certificate authentication (SSL)
}
AUTH_QUALITY_TO_LABEL = {
    0: 0, # None -> Java applet (Hello)
    1: 0, # By IP -> Java applet (Hello)
    2: 0, # Java applet (Hello)
    3: 1, # NuFW authentication (SASL)
    4: 2, # Certificate authentication (SSL)
    5: 2, # SSL HARD -> Certificate authentication (SSL)
}
DEFAULT_AUTH_QUALITY_LABEL = 1 # NuFW authentication (SASL)

ASCII_REGEXP = QRegExp('^[\x20-\x7e]*$')

class EditACL(EditRule):
    OBJECT_CLASS = Acl

    def __init__(self, window):
        EditRule.__init__(self, window, None, "acl")
        self.setupEdit(
            window.acl_enabled,
            window.acl_mandatory,
            window.acl_comment)

        self.decision = window.acl_decision
        self.applications = EditList(self, window.acl_applications, False, self.object_list, True,
            window.object_libraries['applications'], window.object_libraries['operating_systems'])
        self.highlight_list['applications'] = self.applications
        self.highlight_list['operating_systems'] = self.applications
        self.use_log = window.acl_use_log
        self.log_prefix = window.acl_log_prefix
        self.log_prefix.setAcceptDrops(False)
        self.setRegExpValidator(self.log_prefix, ASCII_REGEXP)
        self.auth_quality = self.getWidget('auth_quality')

        window.connect(self.use_log, SIGNAL("stateChanged(int)"), self.toggleLog)

        editor = self.object_list['user_groups']
        window.connect(editor.widget, SIGNAL('objectDrop()'), self.switchNuFW)
        window.connect(editor.menu.delete_action, SIGNAL('triggered()'), self.switchNuFW)

        self.connectOkButton(self.getWidget('save_button'))

        self.time_period = EditLine(self,
            (window.object_libraries["periodicities"], window.object_libraries["durations"]),
            self.getWidget("time_period"), self.getWidget("clear_time_period"))
        self.highlight_list['periodicities'] = self.time_period
        self.highlight_list['durations'] = self.time_period

        self.object_list['protocols'].setEmptyAllowed(window.compatibility.platform)

        fillDecisionCombo(self.decision)

    def getLibrary(self, lst_name):
        """override"""
        lst_type = self.OBJECT_CLASS.OBJECT_ATTR[lst_name]['name']
        libraries = [self.window.object_libraries[lst_type]]
        if self.window.compatibility.platform and lst_name in ['sources', 'destinations']:
            libraries.append(self.window.object_libraries['platforms'])
        return libraries

    def toggleLog(self, state):
        use_log = (state == Qt.Checked)
        self.window.acl_log_prefix_label.setEnabled(use_log)
        self.log_prefix.setEnabled(use_log)

    def checkRuleAttributes(self, attr):
        if self.window.input_output_rules:
            return True
        if (u'Firewall' in attr['sources']) or (u'Firewall' in attr['destinations']):
            self.window.error(tr("INPUT/OUPUT rule creation is denied on EdenWall."))
            return False
        return True

    def useNuFW(self):
        return (self.object_list['user_groups'].widget.count() != 0)

    def save(self):
        window = self.window
        attr = {
            'mandatory':  self.mandatory.isChecked(),
            'decision': unicode(self.decision.currentText()),
            'log': window.acl_use_log.isChecked(),
            'log_prefix': unicode(window.acl_log_prefix.text()),
        }
        if self.useNuFW():
            attr['applications'] = self.applications.getFromLibrary(window.object_libraries['applications'])
            attr['operating_systems'] = self.applications.getFromLibrary(window.object_libraries['operating_systems'])
            if self.auth_quality:
                index = self.auth_quality.currentIndex()
                index = LABEL_TO_AUTH_QUALITY[index]
                attr['auth_quality'] = index
            self.time_period.save(attr)
        else:
            attr['applications'] = tuple()
            attr['operating_systems'] = tuple()
            attr["periodicities"] = tuple()
            attr["durations"] = tuple()

        for lst_name in self.OBJECT_CLASS.OBJECT_ATTR.keys():
            # sources and destinations widgets melt resource objects and platform objects
            if lst_name in ['sources', 'destinations']:
                lst_type = self.OBJECT_CLASS.OBJECT_ATTR[lst_name]['name']
                attr[lst_name] = self.object_list[lst_name].getFromLibrary(window.object_libraries[lst_type])
            else:
                attr[lst_name] = self.object_list[lst_name].getAll()

        if self.window.compatibility.platform:
            attr['source_platforms'] = self.object_list['sources'].getFromLibrary(window.object_libraries['platforms'])
            attr['destination_platforms'] = self.object_list['destinations'].getFromLibrary(window.object_libraries['platforms'])

        self._save(attr)

    def _create(self, rules):
        if rules.rule_type == "acls-ipv6":
            title = tr("Create a new IPv6 rule")
        else:
            title = tr("Create a new IPv4 rule")
        self.groupbox.setTitle(title)
        QComboBox_setCurrentText(self.decision, DEFAULT_DECISION)
        self.applications.clear()
        self.use_log.setChecked(DEFAULT_LOG)
        self.log_prefix.setText(DEFAULT_LOG_PREFIX)
        if self.auth_quality:
            self.auth_quality.setCurrentIndex(DEFAULT_AUTH_QUALITY_LABEL)
        self.time_period.clear()
        self.switchNuFW()

    def _editRule(self, acl):
        if self.window.compatibility.platform:
            platforms_lists = {'source_platforms': self.object_list['sources'],
                'destination_platforms': self.object_list['destinations']}
            for lst_name, lst in platforms_lists.iteritems():
                lst.append(acl[lst_name])
        title = unicode(acl)
        self.groupbox.setTitle(title)
        QComboBox_setCurrentText(self.decision, acl['decision'])
        self.applications.fill(acl['applications'] + acl['operating_systems'])
        self.use_log.setChecked(acl['log'])
        self.log_prefix.setText(acl.get('log_prefix', u''))
        if self.auth_quality:
            try:
                index = acl['auth_quality']
                index = AUTH_QUALITY_TO_LABEL[index]
            except KeyError:
                index = DEFAULT_AUTH_QUALITY_LABEL
            self.auth_quality.setCurrentIndex(index)
        self.time_period.edit(acl)
        self.switchNuFW()


    def disableAuthQuality(self):
        self.getWidget('auth_quality_label').hide()
        self.auth_quality.hide()
        self.auth_quality = None

    def switchNuFW(self):
        use_nufw = self.useNuFW()
        self.applications.setEnabled(use_nufw)
        self.ui.acl_applications_label.setEnabled(use_nufw)
        self.time_period.setEnabled(use_nufw)
        self.ui.acl_time_period_label.setEnabled(use_nufw)
        if self.auth_quality:
            self.auth_quality.setEnabled(use_nufw)
            self.ui.acl_auth_quality_label.setEnabled(use_nufw)

