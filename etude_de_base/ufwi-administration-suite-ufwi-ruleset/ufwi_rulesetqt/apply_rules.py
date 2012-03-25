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

from collections import defaultdict
from PyQt4.QtCore import SIGNAL
from PyQt4.QtGui import QMessageBox
from ufwi_rpcd.common import tr
from time import time
from ufwi_rpcc_qt.html import (Html,
    htmlHeader, htmlParagraph, htmlList, htmlImage, NBSP)
from ufwi_rulesetqt.rule.iptables_dialog import formatMessage
from ufwi_rulesetqt.icons import ERROR_ICON32, WARNING_ICON32

class ApplyRules:
    def __init__(self, window):
        self.window = window
        self.ruleset = window.ruleset
        self.config = window.config
        self.consistency_error = False
        self.before = None
        self.connectSlots()

    def connectSlots(self):
        ui = self.window
        ui.connect(ui.action_apply, SIGNAL("triggered()"), self.applyRules)
        ui.connect(ui.action_apply_non_authenticated, SIGNAL("triggered()"), self.applyRulesWithoutNuFW)
        ui.connect(ui.action_test_ruleset, SIGNAL("triggered()"), self.testRuleset)

    def testRuleset(self):
        try:
            result = self.ruleset('consistencyEngine')
        except Exception, err:
            self.window.exception(err)
            return

        html = htmlHeader(3, tr('Test result:'))
        result_html = self.formatResult(result)
        if not result_html:
            result_html = htmlParagraph(tr("No error."))
        if 'consistency_errors' in result:
            self.consistency_error = bool(result['consistency_errors'])
        else:
            # Old ufwi_ruleset backend
            self.consistency_error = (not result['applied'])
        html += result_html
        self.window.disableRepaint()
        try:
            self.window.setInfo(html, is_error=self.consistency_error, show_dock=True)
            self.consistencyFilter(result)
        finally:
            self.window.enableRepaint()

    def consistencyFilter(self, result):
        if 'consistency_errors' not in result:
            # Old ufwi_ruleset backend
            return
        identifiers_by_domain = defaultdict(set)
        for domain, duplicates in result['consistency_errors'].iteritems():
            identifiers = identifiers_by_domain[domain]
            for id_b, id_a in duplicates:
                identifiers.add(id_a)
                identifiers.add(id_b)
        if 'consistency_warnings' in result:
            for domain, duplicates in result['consistency_warnings'].iteritems():
                identifiers = identifiers_by_domain[domain]
                for id_b, id_a in duplicates:
                    identifiers.add(id_a)
                    identifiers.add(id_b)
        for domain, rules in self.window.rules.iteritems():
            identifiers = identifiers_by_domain[domain]
            rules = self.window.rules[domain]
            rules.filter.setConsistencyFilter(identifiers)

    def applyRulesWithoutNuFW(self):
        self._applyRules(False)

    def applyRules(self):
        use_nufw = self.config.useNuFW()
        self._applyRules(use_nufw)

    def _applyRules(self, use_nufw):
        cancel = self.window.askSave(
            tr("You have to save the rule set to apply the rules."),
            QMessageBox.Save | QMessageBox.Cancel)
        if not cancel:
            return
        if self.consistency_error:
            message = tr("Last apply failed: disable the consistency engine?")
            buttons = QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            choice = QMessageBox.question(self.window,
                tr("Disable consistency engine"),
                message,
                buttons)
            if choice == QMessageBox.Cancel:
                return
            consistency_error = (choice == QMessageBox.No)
        else:
            consistency_error = True
        self.window.freeze(tr("Applying rules..."))
        async = self.ruleset.client.async()
        self.before = time()
        async.call('ufwi_ruleset', 'applyRules', consistency_error, use_nufw,
            callback=self.success,
            errback=self.error)

    def _formatMessages(self, title, messages, icon):
        html = Html()
        errors = []
        for format, args in messages:
            errors.append(formatMessage(self.window, True, format, args))
        if errors:
            text = htmlImage(icon, align="middle") + NBSP + title
            html += htmlParagraph(text)
            html += htmlList(errors)
        return html

    def formatResult(self, result):
        html = self._formatMessages(tr("Errors:"), result['errors'], ERROR_ICON32)
        html += self._formatMessages(tr("Warnings:"), result['warnings'], WARNING_ICON32)
        return html

    def success(self, result):
        duration = time() - self.before
        self.window.unfreeze()
        self.window.clearErrors()
        seconds = u"%.1f" % duration
        html = htmlHeader(3, tr('Rule set'))
        if 'consistency_errors' in result:
            self.consistency_error = bool(result['consistency_errors'])
        else:
            # Old ufwi_ruleset backend
            self.consistency_error = (not result['applied'])
        if result['applied']:
            html += htmlParagraph(tr("Rules applied correctly in %s sec.") % seconds)
        else:
            html += htmlParagraph(tr("Unable to apply rules!"))
        result_html = self.formatResult(result)
        if result_html:
            html += result_html
        self.window.disableRepaint()
        try:
            self.window.setInfo(html, is_error=not result['applied'], show_dock=True)
            self.consistencyFilter(result)
        finally:
            self.window.enableRepaint()

    def error(self, err):
        self.consistency_error = False
        self.window.unfreeze()
        self.window.exception(err,
            tr("Unable to apply rules!"))

    def refreshUndo(self):
        self.consistency_error = False

