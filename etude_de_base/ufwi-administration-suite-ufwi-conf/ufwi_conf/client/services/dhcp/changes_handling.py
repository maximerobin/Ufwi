
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
from PyQt4.QtGui import QMessageBox

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcc_qt.html import htmlList
if EDENWALL:
    from ufwi_conf.common.dhcpcfg import DHCPRange, UNSET

from .adjust import adjust_ip

#changes directives
_DELETE_RANGE = "_delete range_"
_IGNORE = "_ignore changes_"
_TRANSLATE = "_translate range_"

_HELP_TEXT = unicode(htmlList((
    tr("Clicking \"Yes\" will change the DHCP range."),
    tr("Clicking \"Ignore\" will not change the DHCP range. Double-check the DHCP server configuration before saving."),
    tr("Clicking \"Cancel\" will cancel your changes to the network configuration")
)))

_HTML = u"""
<table>
    %(title)s<br />
    %(ask)s<br />
    <tr>
        <td><h2>%(start)s</h2></td>
        <td>%(cur_start)s</td>
        <td><img src=":/icons-32/go-next"/></td>
        <td>%(simu_start)s</td>
    </tr>
    <tr>
        <td><h2>%(end)s</h2></td>
        <td>%(cur_end)s</td>
        <td><img src=":/icons-32/go-next"/></td>
        <td>%(simu_end)s</td>
    </tr>
    <tr>
        <td><h2>%(router)s</h2></td>
        <td>%(cur_router)s</td>
        <td><img src=":/icons-32/go-next"/></td>
        <td>%(simu_router)s</td>
    </tr>
</table>
"""
_TITLE = tr("DHCP: Translate a range?")

_GENERIC_TEXT = "<h2>%s</h2>" % tr("This change affects the DHCP server configuration")

def accept_suppression(dhcprange, parent_widget):
    """
    The net we refer to is not available anymore, do we want this or not
    Let the user choose.
    """
    deletable_tr = tr("Consequence: the following DHCP range will be deleted:")
    deletable_html = u"<ul>"
    deletable_html += "<li>%s %s: %s > %s</li>" % (
        deletable_tr,
        unicode(dhcprange.net),
        unicode(dhcprange.start),
        unicode(dhcprange.end)
        )
    deletable_html += u"</ul>"
    title = tr("DHCP configuration")
    message_box = QMessageBox(parent_widget)
    message_box.setWindowTitle(title)
    message_box.setText(_GENERIC_TEXT)
    message_box.setInformativeText(deletable_html)
    message_box.setStandardButtons(
        QMessageBox.Yes | QMessageBox.Cancel
    )

    clicked_button = message_box.exec_()
    if clicked_button == QMessageBox.Yes:
        return True, _DELETE_RANGE
    return False

def accept_translation(dhcprange, parent_widget, has_custom_dns):
        simulation = _translate_range(
            dhcprange,
            has_custom_dns
            )

        message_box = QMessageBox(parent_widget)
        message_box.setWindowTitle(_TITLE)
        message_box.setText(_GENERIC_TEXT)
        message_box.setInformativeText(
            _translation_information(simulation, dhcprange)
            )
        message_box.setStandardButtons(
            QMessageBox.Yes | QMessageBox.Ignore | QMessageBox.Cancel
        )
        clicked_button = message_box.exec_()
        if clicked_button == QMessageBox.Yes:
            return True, _TRANSLATE, simulation
        elif clicked_button == QMessageBox.Ignore:
            return True, _IGNORE
        return False

def _new_ip(ipy_ip, ipy_net):
    """
    Still UNSET if was UNSET, else, translated
    """
    if not isinstance(ipy_ip, IP):
        return UNSET
    else:
        return adjust_ip(ipy_net, ipy_ip)

def _translate_range(dhcprange, has_custom_dns):
    """
    move the range variables to match its net
    """

    new_start = _new_ip(dhcprange.start, dhcprange.net.net)
    new_end = _new_ip(dhcprange.end, dhcprange.net.net)
    new_router = _new_ip(dhcprange.router, dhcprange.net.net)

    return {
        'start': new_start,
        'end': new_end,
        'router': new_router,
        'custom_dns': has_custom_dns,
        }

def _translation_information(simulation, dhcprange):
        cur_router = _valuefromrouter(dhcprange.router)
        new_router = _valuefromrouter(simulation['router'])
        return _HTML % {
                'title' : tr("You changed the network address for the '<i>%s</i>' network") % dhcprange.net.label,
                'ask' : tr("Do you want to adjust the self.dhcprange?"),
                'start' : tr("Start IP"),
                'cur_start' : dhcprange.start,
                'simu_start' : unicode(simulation['start']),
                'end' : tr("End IP"),
                'cur_end' : dhcprange.end,
                'simu_end' : unicode(simulation['end']),
                'router' : tr("Router IP"),
                'cur_router' : cur_router,
                'simu_router' : unicode(new_router),
            }

def _valuefromrouter(router):
    value = DHCPRange.ip_or_unset(router)
    if isinstance(value, (unicode, str)) and router == UNSET:
        return tr("No gateway set.")
    return value

