
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

from PyQt4.QtCore import Qt
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QCheckBox
from PyQt4.QtGui import QDoubleSpinBox
from PyQt4.QtGui import QFormLayout
from PyQt4.QtGui import QFrame
from PyQt4.QtGui import QGridLayout
from PyQt4.QtGui import QGroupBox
from PyQt4.QtGui import QLabel

from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcd.common import tr, EDENWALL
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.qt.iplist_editor import NetworkListEdit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.qt.widgets import ScrollArea
if EDENWALL:
    from ufwi_conf.common.ids_ips_cfg import IdsIpsCfg

try:
    from nulog.client.qt.fragment_frame import FragmentFrame
    from nulog.client.qt.user_settings.fragment import Fragment
    HAVE_NULOG = True
except ImportError:
    HAVE_NULOG = False

def mkGroupBox(title):
    group_box = QGroupBox(title)
    sub_form = QFormLayout(group_box)
    group_box.setStyleSheet(u"QGroupBox {font: bold italic large;}")
    return group_box, sub_form

class IdsIpsFrontend(ScrollArea):
    COMPONENT = 'ids_ips'
    LABEL = tr('IDS/IPS')
    REQUIREMENTS = ('ids_ips',)
    ICON = ':/icons/monitoring.png'

    def __init__(self, client, parent):
        ScrollArea.__init__(self)
        if not EDENWALL:
            raise NuConfModuleDisabled("idsips")
        self.client = client
        self.mainwindow = parent
        self._modified = False
        self.error_message = ''
        self._not_modifying = True
        self.config = None

        self.resetConf(no_interface=True)
        self.buildInterface()
        self.updateView()

    @staticmethod
    def get_calls():
        """
        services called by initial multicall
        """
        return (("ids_ips", 'getIdsIpsConfig'),)

    def setModified(self):
        if self._modified or self._not_modifying:
            return

        self._modified = True
        self.emit(SIGNAL('modified'))
        self.mainwindow.setModified(self)

    def mkCheckBox(self, title):
        checkbox = QCheckBox(title)
        self.connect(checkbox, SIGNAL('stateChanged(int)'), self.setModified)
        return checkbox

    def buildInterface(self):
        frame = QFrame()
        grid = QGridLayout(frame)
        self.setWidget(frame)
        self.setWidgetResizable(True)

        title = u'<h1>%s</h1>' % self.tr('Intrusion detection/prevention system')
        grid.addWidget(QLabel(title), 0, 0, 1, 2) #fromrow, fromcol, rowspan, colspan

        self.activation_box = self.mkCheckBox(tr('Enable IDS-IPS'))
        self.connect(self.activation_box, SIGNAL('stateChanged(int)'), self.config.setEnabled)
        grid.addWidget(self.activation_box, 1, 0)

        alerts, sub_form = mkGroupBox(tr('Alerts (IDS)'))

        self.alert_threshold = QDoubleSpinBox()
        sub_form.addRow(tr('Threshold for rule selection'), self.alert_threshold)
        self.connect(self.alert_threshold, SIGNAL('valueChanged(double)'),
                     self.setAlertThreshold)
        self.connect(self.alert_threshold, SIGNAL('valueChanged(double)'), self.setModified)
        self.threshold_message = QLabel()
        self.threshold_message.setWordWrap(True)
        sub_form.addRow(self.threshold_message)

        self.alert_count_message = QLabel()
        self.alert_count_message.setWordWrap(True)
        sub_form.addRow(self.alert_count_message)

        self.threshold_range = MessageArea()
        sub_form.addRow(self.threshold_range)

        grid.addWidget(alerts, 2, 0)

        blocking, sub_form = mkGroupBox(tr('Blocking (IPS)'))

        self.block = self.mkCheckBox(tr('Block'))
        self.connect(self.block, SIGNAL('stateChanged(int)'), self.config.setBlockingEnabled)
        sub_form.addRow(self.block)
        self.drop_threshold = QDoubleSpinBox()
        sub_form.addRow(tr('Rule selection threshold for blocking'), self.drop_threshold)

        self.drop_count_message = QLabel()
        self.drop_count_message.setWordWrap(True)
        sub_form.addRow(self.drop_count_message)

        self.connect(self.drop_threshold, SIGNAL('valueChanged(double)'), self.setDropThreshold)
        self.connect(self.drop_threshold, SIGNAL('valueChanged(double)'), self.setModified)
        self.connect(
            self.block,
            SIGNAL('stateChanged(int)'),
            self.drop_threshold.setEnabled
        )

        grid.addWidget(blocking, 2, 1)

        antivirus, sub_form = mkGroupBox(tr('Antivirus'))

        self.antivirus_toggle = self.mkCheckBox(tr('Enable antivirus '))
        self.connect(self.antivirus_toggle, SIGNAL('stateChanged(int)'), self.config.setAntivirusEnabled)
        self.antivirus_message = QLabel()
        self.antivirus_message.setWordWrap(True)
        sub_form.addRow(self.antivirus_toggle)
        sub_form.addRow(self.antivirus_message)

        network, sub_form = mkGroupBox(tr('Protected networks'))

        self.networks = NetworkListEdit()
        self.connect(self.networks, SIGNAL('textChanged()'), self.setProtectedNetworks)
        self.networks_message = QLabel()
        self.networks_message.setWordWrap(True)
        sub_form.addRow(self.networks)
        sub_form.addRow(self.networks_message)

        grid.addWidget(antivirus, 3, 0)
        grid.addWidget(network, 3, 1)

        if HAVE_NULOG:
            fragment = Fragment('IDSIPSTable')
            fragment.load({'type': 'IDSIPSTable',
                           'title': tr('IDS-IPS Logs'),
                           'view': 'table',
                           'args': {}
                          })
            fragwidget = FragmentFrame(fragment, {}, self.client, parent=self)
            grid.addWidget(fragwidget, 4, 0, 1, 2) #fromrow, fromcol, rowspan, colspan
            fragwidget.updateData()
            self.frag = fragwidget

        self.mainwindow.writeAccessNeeded(
            self.activation_box,
            self.alert_threshold,
            self.block,
            self.drop_threshold,
            self.antivirus_toggle,
            self.networks,
        )

    def closeEvent(self, event):
        if hasattr(self, 'frag'):
            self.frag.destructor()

    def setAlertThreshold(self):
        self.config.alert_threshold = self.alert_threshold.value()

    def setProtectedNetworks(self):
        if self.networks.isValid():
            self.config.networks = self.networks.value()
            self.setModified()

    def setDropThreshold(self):
        self.config.drop_threshold = self.drop_threshold.value()

    def resetConf(self, no_interface=False):
        serialized = self.mainwindow.init_call("ids_ips", u'getIdsIpsConfig')

        self.config = IdsIpsCfg.deserialize(serialized)
        self._modified = False
        if no_interface:
            return
        self.updateView()

    def isValid(self):
        self.error_message = ""
        if self.config.block and \
                self.config.drop_threshold < self.config.alert_threshold:
            self.error_message = \
                tr('Inconsistent configuration (IDS-IPS thresholds): ') + \
                tr("the threshold for blocking rules must be greater than the threshold for alerting.")
            return False
        if self.config.enabled and not self.networks.value():
            self.error_message = tr('You must add some networks in the "Protected networks" area before you can enable the IDS-IPS service.')
            return False

        ok, msg = self.config.isValidWithMsg()
        if not ok:
            self.error_message = msg
            return False
        return True

    def saveConf(self, message):
        serialized = self.config.serialize()
        self.client.call("ids_ips", 'setIdsIpsConfig', serialized, message)
        self.mainwindow.addNeutralMessage(tr("IDS - IPS configuration saved"))
        self._modified = False
        self.update_counts()

    def updateView(self):

        self._not_modifying = True

        italic_start = u'<span style="font-style:italic;">'
        close_span = u'</span>'

        self.activation_box.setChecked(
            Qt.Checked if self.config.enabled else Qt.Unchecked
            )

        self.block.setChecked(
            Qt.Checked if self.config.block else Qt.Unchecked
            )

        try:
            (score_min, score_max) = self.client.call("ids_ips",
                                                      'minmaxScores')
        except RpcdError:
            (score_min, score_max) = (-1, -1)
            self.mainwindow.addToInfoArea(tr('IDS-IPS: Could not compute the min/max scores.'))

        self.alert_threshold.setRange(score_min, score_max)
        self.drop_threshold.setRange(score_min, score_max)
        self.threshold_range.setMessage(tr('Current range'), "%s %s %s %s" %(
                tr("The scores for the current rules range from"),
                score_min, tr("to"), score_max)
            )

        self.alert_threshold.setValue(self.config.alert_threshold)
        self.drop_threshold.setValue(self.config.drop_threshold)
        self.drop_threshold.setEnabled(self.block.checkState())

        help = u'%s %s %s' % (
            italic_start,
            tr("The rules are selected according to a level of confidence with regard to "
            "false positives (the greater the threshold, the fewer rules selected)."),
            close_span
        )
        self.threshold_message.setText(help)

        warning = italic_start + tr('Warning: This may degrade the performances of the firewall') + u'</span>'
        self.antivirus_message.setText(warning)

        self.antivirus_toggle.setChecked(
            Qt.Checked if self.config.antivirus_enabled else Qt.Unchecked
            )

        self.networks_message.setText(u'%s%s%s' % (
            italic_start,
            tr('You may add a network definition per line'),
            close_span
            )
            )

        self.networks.setIpAddrs(self.config.networks)
        self.update_counts()

        self._not_modifying = False

    def isModified(self):
        return self._modified

    def update_counts(self):
        try:
            (alert_count, drop_count, available_count) = \
                self.client.call("ids_ips", 'getSelectedRulesCounts',
                                 [self.alert_threshold.value(),
                                  self.drop_threshold.value()])
        except RpcdError:
            (alert_count, drop_count, available_count) = (-1, -1, -1)
            self.mainwindow.addToInfoArea(tr('IDS-IPS: Could not count the selected rules.'))
        self.alert_count_message.setText(
            tr('A threshold of ') + unicode(self.config.alert_threshold) +
            tr(' selects ') + unicode(alert_count) +
            tr(' rules out of ') + unicode(available_count)
            + tr('.'))
        if self.config.block:
            self.drop_count_message.setText(
                tr('A threshold of ') + unicode(self.config.drop_threshold) +
                tr(' selects ') + unicode(drop_count) +
                tr(' blocking rules out of ') + unicode(available_count)
                + tr('.'))
        else:
            self.drop_count_message.setText('')

