#coding: utf8

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


from PyQt4.QtCore import SIGNAL, QTimer
from PyQt4.QtGui import QGroupBox
from PyQt4.QtGui import QHBoxLayout
from PyQt4.QtGui import QLabel
from PyQt4.QtGui import QLineEdit
from PyQt4.QtGui import QMessageBox
from PyQt4.QtGui import QPixmap
from PyQt4.QtGui import QTextBrowser
from PyQt4.QtGui import QVBoxLayout

from ufwi_rpcd.common import tr
from ufwi_conf.client.qt.ip_inputs import IpOrHostnameOrFqdnEdit
from ufwi_conf.client.qt.message_area import MessageArea
from ufwi_conf.client.system.resolv.qhostname_object import QHostnameObject
from ufwi_conf.common.user_dir import AD

from .directory_widget import DirectoryWidget

#Help text, split into several variables for easier translation
help_ps_title = tr("Field usage")
help_ps_general = tr(" Please enter one or several (space separated) authentication servers entries.")
help_ps_pre = tr("An entry can be of the form:")
help_ps_0 = tr('* (default value)')
help_ps_1 = tr('[hostname|fqdn|ip]')
help_ps_2 = tr('[hostname|fqdn|ip]:port')
help_ps = """\
<i>%s</i>
<hr/>
<h3>%s</h3>
<ul>
<li>%s</li>
<li>%s</li>
<li>%s</li>
</ul>
""" % (help_ps_general, help_ps_pre, help_ps_0, help_ps_1, help_ps_2)

help_ps_tooltip = """\
<span>
<h2>%s</h2>
%s
</span>
""" % (help_ps_title, help_ps)
help_ps_message_area = """\
<span>
%s
</span>
""" % (help_ps,)


class ADStatus(QGroupBox):
    NOT_MEMBER_PIXMAP = QPixmap(":/icons-20/off_line.png")
    MEMBER_PIXMAP = QPixmap(":/icons-20/on_line.png")
    UNKNOWN = "<i>%s</i>" % tr("unknown...")
    NOT_MEMBER  = tr("Currently not in an AD domain")

    def __init__(self, parent=None):
        QGroupBox.__init__(self, tr("Active Directory membership status"), parent)
        self._setup_gui()

        self.deleted = False

        self._set_unknown(None)

        self.connect(self, SIGNAL('destroyed()'), self._deactivate)

    def _deactivate(self):
        self.deleted = True

    def _setup_gui(self):
        layout = QVBoxLayout(self)

        self.status_icon = QLabel()
        self.status_text = QLabel()

        hbox = QHBoxLayout()
        layout.addLayout(hbox)
        for widget in (
            self.status_icon,
            self.status_text,
            ):
            hbox.addWidget(widget)

        self.additional_info = QTextBrowser()

        layout.addWidget(self.additional_info)


    def _update_gui(self):
        if self.last_updated == ADStatus.UNKNOWN:
            self.status_text.setText(ADStatus.UNKNOWN)
            for widget in (
                self.status_icon,
                self.additional_info,
                ):
                widget.hide()
            return

        if not self.status:
            self.status_icon.show()
            self.additional_info.hide()
            self.status_icon.setPixmap(ADStatus.NOT_MEMBER_PIXMAP)
            self.status_text.setText(ADStatus.NOT_MEMBER)

        for widget in (
            self.status_icon,
            self.additional_info,
            ):
            widget.show()

        self.status_text.setText(
            tr("AD information:")
        )
        info = (
            tr("Domain name: %s") % self.realm,
            tr("Parent server name: %s") % self.parent_server,
            tr("Last updated: %s") % self.last_updated,
            tr("EdenWall/Active Directory time delta: %s second(s)")
                % self.time_offset,
        )
        self.additional_info.setText("\n".join(info))

    def fetch_data(self, client):
        async = client.async()
        async.call('nuauth', 'ad_info',
            callback=self._update_data,
            errback=self._set_unknown
            )

    def _update_data(self, data):
        if self.deleted:
            return

        #when upgrading, think of using current code if service_version == 1
        self.realm = data.get("realm", ADStatus.UNKNOWN)
        self.status = data.get("current status", False)
        self.time_offset = data.get("time offset", ADStatus.UNKNOWN)
        self.last_updated = data.get("update time", ADStatus.UNKNOWN)
        self.parent_server = data.get("parent server", ADStatus.UNKNOWN)

        self._update_gui()

    def _set_unknown(self, error):
        if error and error.type == 'CoreError':
            self._deactivate()
            self.hide()
        self.realm = \
        self.time_offset = \
        self.last_updated = \
        self.parent_server = ADStatus.UNKNOWN
        self.status = False

        self._update_gui()

class ADBaseWidget(DirectoryWidget):
    def __init__(self, config, specific_config, mainwindow, parent=None):
        DirectoryWidget.__init__(self, config, specific_config, mainwindow, parent=None)
        self.qhostname_object = QHostnameObject.getInstance()
        self.buildInterface(config)
        self.updateView()
        self._poll()

    def register_qobjects(self):
        self.qhostname_object.registerCallbacks(
            self.acceptHostnameChange,
            self.handleHostnameChange,
            attach=self
            )

    def _poll(self):
        self.ad_status.fetch_data(self.mainwindow.client)
        timer = QTimer()
        timer.setSingleShot(True)
        timer.setInterval(20000) # ms
        timer.start()
        self.connect(timer, SIGNAL('timeout()'), self._poll)
        self.connect(self, SIGNAL('destroyed()'), timer.stop)

    def unregister_qobjects(self):
        self.qhostname_object.forget(self)

    def updateView(self, config=None):
        if config is None:
            config = self.specific_config
        self.setText(self.controller_ip, config.controller_ip)
        self.setDefaultText(self.user, config.user)
        self.setDefaultText(self.password, config.password)
        self.setDefaultText(self.workgroup, config.workgroup)
        self.setDefaultText(self.domain, config.domain)
        self.setDefaultText(self.dns_domain, config.dns_domain)
        self.setText(self.wins_ip, config.wins_ip)
        self.displayHostname()

    def acceptHostnameChange(self):
        button = QMessageBox.warning(
            self,
            tr("Hostname change"),
            tr("Warning: this hostname change will cause the appliance to register again on Active Directory."),
            QMessageBox.Cancel | QMessageBox.Ok

        )
        if button == QMessageBox.Ok:
            self.signalModified()
            return True

        return False

    def handleHostnameChange(self):
        self.displayHostname()

    def displayHostname(self):
        self.netbios_name.setText(u"<b>%s</b>" % unicode(self.qhostname_object.hostnamecfg.hostname))

    def buildInterface(self, config):

        fqdn_tooltip = tr("IP address, FQDN or Hostname")

        self.controller_ip = QLineEdit()
        self.texts.add(self.controller_ip)
        self.connect(self.controller_ip, SIGNAL('textChanged(QString)'), self.setControllerIp)
        self.form.addRow(tr('Authentication server'), self.controller_ip)
        self.controller_ip.setToolTip(help_ps_tooltip)
        self.connect(self.controller_ip, SIGNAL('returnPressed()'), self.signalModified)

        self.ps_message_area = MessageArea()
        self.empty_ps_label = QLabel()
        self.form.addRow(self.empty_ps_label, self.ps_message_area)
        self.empty_ps_label.hide()
        self.ps_message_area.hide()
        self.ps_message_area.setMessage(help_ps_title, help_ps_message_area)

        self.wins_ip = IpOrHostnameOrFqdnEdit(accept_empty=True)
        self.texts.add(self.wins_ip)
        self.connect(self.wins_ip, SIGNAL('textChanged(QString)'), self.setWinsIp)
        self.form.addRow(tr('WINS server (optional)'), self.wins_ip)
        self.wins_ip.setToolTip(
            "%s\n%s" % (
                fqdn_tooltip, tr("This field is useful if the AD and EdenWall appliances don't share the same subnet")
            )
        )
        self.connect(self.wins_ip, SIGNAL('returnPressed()'), self.signalModified)

        for args in (
            ('domain', tr('Active Directory Domain'), self.setDomain),
            ('dns_domain', tr('Active Directory DNS Domain (if different from the AD domain)'), self.setDNSDomain),
            ('workgroup', tr('Workgroup (optional)'), self.setWorkgroup)
        ):
            setattr(self, args[0], self.addTextInput(*args[1:]))
            #flagWriteAccess(text_input)


        self.netbios_name = QLabel()
        self.form.addRow(tr("Netbios name"), self.netbios_name)

        for args in (
            ('user', tr('Name used to join the domain'), self.setUser),
            ('password', tr('Password used to join the domain'), self.setPassword, False)
        ):
            setattr(self, args[0], self.addTextInput(*args[1:]))
            #flagWriteAccess(text_input)

        #flagWriteAccess(password_server)
        self.connect(self.controller_ip, SIGNAL('textEdited(QString)'), self.helpPS)
        self.connect(self.controller_ip, SIGNAL('editingFinished()'), self.noHelpPS)

        self.ad_status = ADStatus()
        self.form.addRow('', self.ad_status)

    def helpPS(self, text):
        self.ps_message_area.show()

    def noHelpPS(self):
        self.controller_ip.setText(
            unicode(
                self.controller_ip.text()
                ).strip()
            )
        self.ps_message_area.hide()

    def setControllerIp(self, server):
        self.specific_config.controller_ip = unicode(server).strip()
        self.signalModified()

    def setWinsIp(self, server):
        self.specific_config.wins_ip = unicode(server)
        self.signalModified()

    def setDomain(self, domain):
        self.specific_config.domain = domain

    def setDNSDomain(self, domain):
        self.specific_config.dns_domain = domain

    def setUser(self, user):
        self.specific_config.user = user

    def setPassword(self, password):
        self.specific_config.password = password

    def setWorkgroup(self, workgroup):
        self.specific_config.workgroup = workgroup

    def signalModified(self):
        self.config.org = self.specific_config
        DirectoryWidget.signalModified(self)

class ADWidget(ADBaseWidget):

    def buildInterface(self, config):
        ADBaseWidget.buildInterface(self, config)

    def updateView(self):
        if self.config.org.protocol != AD:
            self.config.org = self.specific_config
        sub_config = self.config.org
        ADBaseWidget.updateView(self, config=sub_config)

