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

from logging import warning
import re

from PyQt4.QtGui import QDialog
from ufwi_rpcd.common import tr
from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.html import Html

from ufwi_rulesetqt.rule.iptables_dialog_ui import Ui_Dialog

# Match "IPv4 rule #2" and "NAT rule #10"
RULE_REGEX = re.compile(u"(?P<text>(?P<key>IPv[46]|NAT) rule) #(?P<id>[0-9]+)")
FORMAT_RULE = {
    'IPv4': tr('IPv4 rule %s'),
    'IPv6': tr('IPv6 rule %s'),
    'NAT': tr('NAT rule %s'),
}
RULE_TYPES = {
    'IPv4': 'acls-ipv4',
    'IPv6': 'acls-ipv6',
    'NAT': 'nats',
}

def formatRule(window, use_html, text):
    def addLink(regs):
        identifier = int(regs.group('id'))
        key = regs.group('key')
        text = "#%s" % (identifier // 10)
        rule_type = RULE_TYPES[key]
        rules = window.rules[rule_type]
        try:
            rule = rules[identifier]
        except KeyError:
            return regs.group(0)
        if use_html:
            return unicode(rule.createHTML(icon=False))
        else:
            return unicode(rule)
    if not isinstance(text, (str, unicode)):
        return text
    return RULE_REGEX.sub(addLink, text)

def formatMessage(window, use_html, format, args):
    args = tuple(formatRule(window, use_html, arg) for arg in args)
    text = tr(format)
    if args:
        try:
            text = text % args
        except TypeError, err:
            warning("Unable to format message (format=%r, arguments=%r): %s" % (text, args, err))
    return Html(text, escape=False)

def formatErrors(window, lines, title, errors):
    if not errors:
        return
    lines.append(u"# %s" % title)
    for format, args in errors:
        text = formatMessage(window, False, format, args)
        text = unicode(text)
        lines.append(u"# - %s" % text)
    lines.append(u"")

def formatRules(window, result, key):
    lines = []
    formatErrors(window, lines, tr("Errors:"), result['errors'])
    formatErrors(window, lines, tr("Warnings:"), result['warnings'])
    lines.extend(result[key])
    return lines

class IptablesDialog(QDialog, Ui_Dialog):
    def __init__(self, window):
        self.window = window
        self.ruleset = window.ruleset
        QDialog.__init__(self, window)
        self.setupUi(self)

    def displayRules(self, rule_type, identifiers):
        use_nufw = self.window.config.useNuFW()
        try:
            result = self.ruleset('iptablesRules', rule_type, identifiers, use_nufw)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        lines = formatRules(self.window, result, 'iptables')
        if not lines:
            self.window.information(tr("No iptables rules: selected rules are disabled."))
            return
        self.iptables_text.setPlainText(u'\n'.join(lines))
        self.exec_()

class LdapDialog(QDialog, Ui_Dialog):
    def __init__(self, window):
        self.window = window
        self.ruleset = window.ruleset
        QDialog.__init__(self, window)
        self.setupUi(self)
        self.setWindowTitle(tr("LDAP rules"))

    def displayRules(self, rule_type, identifiers):
        try:
            result = self.ruleset('ldapRules', rule_type, identifiers)
        except RpcdError, err:
            self.window.ufwi_rpcdError(err)
            return
        lines = formatRules(self.window, result, 'ldap')
        if not lines:
            self.window.information(tr("No LDAP rules: selected rules are disabled or not authenticating."))
            return
        self.iptables_text.setPlainText(u'\n'.join(lines))
        self.exec_()

