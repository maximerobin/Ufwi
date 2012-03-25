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

from sys import exit
from PyQt4.QtCore import Qt, SIGNAL, QMimeData, QChar
from PyQt4.QtGui import (QDrag, QMessageBox, QInputDialog, QIcon,
    QMenuBar, QMenu, QColor, QKeySequence, QLineEdit, QFontMetrics)
from logging import debug

from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.common.odict import odict
from ufwi_rpcd.common.multisite import MULTISITE_SLAVE
from ufwi_rpcd.common.transport import parseDatetime
from ufwi_rpcd.common.human import fuzzyDatetime, humanYesNo

from ufwi_rpcd.client import RpcdError
from ufwi_rpcc_qt.central_window import CentralWindow, STANDALONE
from ufwi_rpcc_qt.html import stripHTMLTags, htmlParagraph, htmlTable, htmlList, Html
from ufwi_rpcc_qt.session_dialog import SessionDialog
from ufwi_rpcc_qt.splash import SplashScreen
from ufwi_rpcc_qt.tools import QDockWidget_setTab

from ufwi_ruleset.common.update import DOMAIN_ORDER, Updates, createUpdatesOdict
from ufwi_ruleset.common.roles import RULESET_FORWARD_WRITE_ROLES

from ufwi_rulesetqt.main_window_ui import Ui_MainWindow
from ufwi_rulesetqt.ruleset import Ruleset
from ufwi_ruleset.version import VERSION
from ufwi_rulesetqt.rule.edit_acl import EditACL
from ufwi_rulesetqt.rule.acl_list import AclIPv4List, AclIPv6List
from ufwi_rulesetqt.rule.nat_list import NatList
from ufwi_rulesetqt.objects_group import ObjectsGroupWidget
from ufwi_rulesetqt.resources import Resources
from ufwi_rulesetqt.protocols import Protocols
from ufwi_rulesetqt.platform import Platforms
from ufwi_rulesetqt.applications import Applications
from ufwi_rulesetqt.user_groups import UserGroups
from ufwi_rulesetqt.operating_systems import OperatingSystems
from ufwi_rulesetqt.periodicity import Periodicities
from ufwi_rulesetqt.durations import Durations
from ufwi_rulesetqt.html import htmlTitle
from ufwi_rulesetqt.ruleset_dialog import RulesetDialog
from ufwi_rulesetqt.custom_rules import CustomRulesDialog
from ufwi_rulesetqt.parameters import ParametersDialog, RulesetConfig
from ufwi_rulesetqt.create_ruleset import CreateRuleset
from ufwi_rulesetqt.template import Template
from ufwi_rulesetqt.apply_rules import ApplyRules
from ufwi_rulesetqt.rule.iptables_dialog import formatRule
from ufwi_rulesetqt.compatibility import Compatibility
from ufwi_rulesetqt.tools import formatWarnings
from ufwi_rulesetqt.icons import ERROR_ICON32, INFORMATION_ICON32
from ufwi_rulesetqt.rule.move_dialog import MoveRuleDialog

HIGHLIGHT_COLOR = QColor(202, 225, 165)

class MainWindow(CentralWindow, Ui_MainWindow):
    ROLES = set(('ruleset_read', 'ruleset_write', 'ruleset_multisite'))
    ICON = ':/icons/Acl.png'

    LIBRARIES = [Resources, Protocols, Platforms, UserGroups, Applications,
        OperatingSystems, Periodicities, Durations]

    # Initialized it here beacuse _formatErrorMessage() may be called very
    # early in the constructor (eg.before the initialization of the ruleset)
    rules = {}

    def __init__(self, application, client, standalone=STANDALONE, parent=None, eas_window=None):
        CentralWindow.__init__(self, client, parent, eas_window)
        self.ui = self
        self._loaded = False
        self.application = application
        self.setupMainWindow(application, standalone)
        self.use_edenwall = self.client.call('CORE', 'useEdenWall')
        if self.use_edenwall:
            self.action_custom_rules.setVisible(False)
        self.createMenu()
        self.EAS_MESSAGES['show_acl'] = self.show_acl
        self.readConfig()

    def readConfig(self):
        # Read the configuration
        try:
            self.config = RulesetConfig(self, self.client)
        except RpcdError:
            self.error(
                tr("Unable to get the firewall configuration! "
                   "Check that the Ruleset component is correctly "
                   "loaded in the Rpcd server. "
                   "Exiting."),
                dialog=(self.standalone == STANDALONE))
            exit(1)

    def load(self):
        if self._loaded:
            return
        self._loaded = True

        # Check if the font is able to render "U+2192: RIGHTWARDS ARROW"
        font = self.font()
        font_metrics = QFontMetrics(font)
        if font_metrics.inFont(QChar(0x2192)):
            self.right_arrow_character = u"\u2192"
        else:
            self.right_arrow_character = u"->"

        self.setupRuleset()

        load_last = True
        if self.standalone == STANDALONE:
            options = self.application.options
            if options.ruleset:
                load_last = False
                self.rulesetOpen("ruleset", options.ruleset)
            elif options.template:
                load_last = False
                self.rulesetOpen("template", options.template)
            elif options.new:
                load_last = False
                self.create_ruleset.create("ruleset", u'')
        if load_last:
            try:
                self.loadLast()
            except Exception, err:
                self.exception(err)

    def createMenu(self):
        menubar = QMenuBar(self)
        menuFile = QMenu(self.tr("&File"), menubar)
        menuEdit = QMenu(self.tr("&Edit"), menubar)
        self.setMenuBar(menubar)

        menuFile.addAction(self.action_new_ruleset)
        menuFile.addAction(self.action_open_ruleset)
        menuFile.addSeparator()
        menuFile.addAction(self.action_properties)
        menuFile.addAction(self.action_save)
        menuFile.addAction(self.action_save_as)
        menuFile.addAction(self.action_close_ruleset)
        menuFile.addSeparator()
        menuFile.addAction(self.action_test_ruleset)
        menuFile.addAction(self.action_apply)
        menuFile.addAction(self.action_apply_non_authenticated)
        menuFile.addAction(self.action_production_ruleset)
        if self.standalone == STANDALONE:
            menuFile.addSeparator()
            menuFile.addAction(self.action_quit)

        menuEdit.addAction(self.action_undo)
        menuEdit.addAction(self.action_redo)
        menuEdit.addSeparator()
        menuEdit.addAction(self.action_fusion)
        menuEdit.addAction(self.action_fullscreen)
        menuEdit.addSeparator()
        if not self.use_edenwall:
            menuEdit.addAction(self.action_custom_rules)
        menuEdit.addAction(self.action_ufwi_conf_sync)
        menuEdit.addAction(self.action_manage_templates)
        menuEdit.addAction(self.action_generic_links)
        menuEdit.addSeparator()
        menuEdit.addAction(self.action_parameters)

        menubar.addAction(menuFile.menuAction())
        menubar.addAction(menuEdit.menuAction())

        # Shortcuts
        self.action_apply.setShortcut(QKeySequence("CTRL+p"))

    def setupMainWindow(self, application, standalone):
        self.application = application
        self.standalone = standalone
        self.ruleset = None
        self._models = odict()
        self._info_contains_error = False
        self.setWindowIcon(QIcon(":icons/appicon.png"))
        self.setupUi(self)
        self.setupCentralWindow(application, standalone)
        self.objgroup = ObjectsGroupWidget(self)
        self.create_ruleset = CreateRuleset(self)
        self.connectSlots()
        self.splash = SplashScreen()
        palette = application.palette()
        brush = palette.highlight()
        brush.setColor(HIGHLIGHT_COLOR)
        self.objgroup_id_text.setAcceptDrops(False)

    def registerModel(self, model):
        self._models[model.name] = model

    def getLibrary(self, name):
        return self.object_libraries[name]

    def getModel(self, name):
        return self._models[name]

    def iterModels(self):
        return self._models.itervalues()

    def setEditMode(self, edit):
        ui = self
        self.edit_mode = edit

        enabled = not self.edit_mode
        ui.action_new_ruleset.setEnabled(enabled)
        ui.action_open_ruleset.setEnabled(enabled)
        ui.action_close_ruleset.setEnabled(enabled)
        ui.action_fullscreen.setEnabled(enabled)
        ui.action_fusion.setEnabled(enabled)
        if self.edit_mode:
            ui.action_save.setEnabled(enabled)
            ui.action_save_as.setEnabled(enabled)
            ui.action_undo.setEnabled(enabled)
            ui.action_redo.setEnabled(enabled)
            ui.action_custom_rules.setEnabled(enabled)
            ui.action_manage_templates.setEnabled(enabled)
            ui.action_generic_links.setEnabled(enabled)
            ui.action_parameters.setEnabled(enabled)
            ui.action_test_ruleset.setEnabled(enabled)
            ui.action_apply.setEnabled(enabled)
            ui.action_apply_non_authenticated.setEnabled(True)
            ui.action_ufwi_conf_sync.setEnabled(enabled)
        else:
            self.refreshUndo()
        if not self.ruleset.read_only:
            for library in self.object_libraries.itervalues():
                library.setEditMode(edit)
        if not edit:
            self.acl_stack.setCurrentIndex(0)

    def setupRuleset(self):
        self.fullscreen = False
        self.edit_mode = False
        self.read_only = False

        self.selection_widgets = []

        self.input_output_rules = (not self.use_edenwall)

        self.ruleset_modified = False
        self.compatibility = Compatibility(self)
        self.ruleset = Ruleset(self.client, self)

        if not self.compatibility.platform:
            self.LIBRARIES.remove(Platforms)
            platform_library = self.object_library.widget(2)
            self.object_library.removeItem(2)
            platform_library.deleteLater()

        # Libraries instanciation
        self.object_libraries = {}
        for library_class in self.LIBRARIES:
            name = library_class.RULESET_ATTRIBUTE
            self.object_libraries[name] = library_class(self)

        # Create objects
        self.edit_acl = EditACL(self)
        if not self.compatibility.auth_quality:
            self.edit_acl.disableAuthQuality()
        self.move_rule_dialog = MoveRuleDialog(self)
        self.acls_ipv4 = AclIPv4List(self)
        self.acls_ipv6 = AclIPv6List(self)
        self.nats = NatList(self)
        self.rules = {
            'acls-ipv4': self.acls_ipv4,
            'acls-ipv6': self.acls_ipv6,
            'nats': self.nats,
        }
        self.highlight_rules = {
            'IPv4': self.acls_ipv4.highlight_format,
            'IPv6': self.acls_ipv6.highlight_format,
            'NAT': self.nats.highlight_format,
        }

        # Template
        self.template = Template(self)
        self.apply_rules = ApplyRules(self)

        # refresh domain (unicode) => callback(*updates, **kw)
        # with highlight=kw['highlight']
        self.refresh_domains = {
            u"generic-links": (self.template.generic_links.refresh, self.template.generic_links.display),
            u"ruleset": (self.template.refresh, self.template.display),
        }
        for domain, rules in self.rules.iteritems():
            self.refresh_domains[domain] = (rules.refresh, rules.display)
            self.refresh_domains[domain+"-chains"] = (rules.refreshChain, rules.displayChain)
            if domain.startswith("acls"):
                self.refresh_domains[domain+"-decisions"] = (rules.refreshDecisions, rules.displayDecisions)
        for library in self.iterLibraries():
            self.refresh_domains[library.REFRESH_DOMAIN] = (library.refresh, library.display)

        # Check read only mode in user session
        if EDENWALL:
            try:
                read_only = not any((role in self.getRoles())
                    for role in RULESET_FORWARD_WRITE_ROLES)
            except Exception:
                read_only = False
            self.setReadOnly(read_only)

        self.reset()
        self.setStatus('Ruleset version %s' % VERSION, 0)

    def setInfo(self, html, background=None, is_error=False, show_dock=False):
        if is_error or show_dock:
            QDockWidget_setTab(self.dock_informations)
        self.textInfo.setHtml(unicode(html))
        if background:
            style = '''QTextEdit {
background: white;
background-image: url(%s);
background-repeat: no-repeat;
background-position: right bottom;
}''' % background
        else:
            style = ''
        self.textInfo.setStyleSheet(style)
        self._info_contains_error = is_error

    def startDragText(self, source, text, icon=None):
        drag = QDrag(source)
        if icon:
            pixmap = icon.pixmap(32)
            drag.setPixmap(pixmap)
        mime_data = QMimeData()
        text = u'ufwi_ruleset_drag:' + text
        mime_data.setText(text)
        drag.setMimeData(mime_data)
        drag.start(Qt.MoveAction)
        return drag

    def undoLast(self):
        try:
            updates = self.ruleset('undo')
        except RpcdError, err:
            self.ufwi_rpcdError(err)
            return
        self.refresh(updates)

    def redoLast(self):
        try:
            updates = self.ruleset('redo')
        except RpcdError, err:
            self.ufwi_rpcdError(err)
            return
        self.refresh(updates)

    def clearErrors(self):
        if self._info_contains_error:
            self.setInfo(u'')

    def disableRepaint(self):
        self.setUpdatesEnabled(False)

    def enableRepaint(self):
        self.setUpdatesEnabled(True)

    def refresh(self, result):
        if self.compatibility.mode == 'GUI2':
            all_updates = result['updates']
            undo_state = result['undoState']
        else:
            all_updates = result
            undo_state = None
        all_updates = createUpdatesOdict(all_updates)
        self.disableRepaint()
        try:
            if all_updates:
                debug("UPDATES: %s" % ', '.join(map(str, all_updates)))
                sorted_domains = all_updates.keys()
                sorted_domains.sort(key=lambda domain: DOMAIN_ORDER[domain])
                for domain in sorted_domains:
                    updates = all_updates[domain]
                    # A refresh callback can fill all_updates to ask to
                    # redisplay references of an updated object
                    self._refreshDomain(True, domain, all_updates, updates)
                highlight = True
                for domain, updates in all_updates.iteritems():
                    self._refreshDomain(False, domain, None, updates, highlight)
                    highlight = False
            self.refreshUndo(undo_state)
            self.clearErrors()
        finally:
            self.enableRepaint()

    def _refreshDomain(self, do_refresh, domain, all_updates, updates, highlight=False):
        """display or refresh one specific domain

            do_refresh: display or refresh
            all_updates: all updates of all domains (odict)
            updates: updates of domain (list)
            highlight: if highlight and display select last modified item
        """
        refresh_display = self.refresh_domains.get(domain)
        if not refresh_display:
            return
        if do_refresh:
            debug("|> refresh %s: %s" % (domain, repr(updates)))
            refresh = refresh_display[0]
            refresh(all_updates, updates)
        else:
            debug("|> display %s: %s" % (domain, repr(updates)))
            display = refresh_display[1]
            display(updates, highlight=highlight)

    def refreshUndo(self, undo_state=None):
        not_editing =  not self.edit_mode
        if self.ruleset.is_open:
            if not undo_state:
                undo_state = self.ruleset('undoState')
            modified, can_undo, can_redo = undo_state
        else:
            modified, can_undo, can_redo = False, False, False
        if self._standalone != STANDALONE:
            self.eas_window.setModified(modified)
        else:
            self.setWindowModified(modified)
        self.ruleset_modified = modified
        has_ruleset = self.ruleset.is_open
        if has_ruleset:
            editable_ruleset = not self.ruleset.read_only
        else:
            editable_ruleset = False
        read_only = self.ruleset.read_only

        self.action_undo.setEnabled(can_undo and not_editing)
        self.action_redo.setEnabled(can_redo and not_editing)

        can_save = has_ruleset and (self.ruleset_modified or not bool(self.ruleset.ruleset_name))
        self.action_save.setEnabled(can_save)

        self.object_library.setEnabled(has_ruleset)
        self.action_save_as.setEnabled(editable_ruleset)
        self.action_custom_rules.setEnabled(editable_ruleset and (not self.ruleset.is_template))
        self.main_tab.setEnabled(has_ruleset)
        self.action_properties.setEnabled(has_ruleset)

        self.action_test_ruleset.setEnabled(has_ruleset)
        can_apply = editable_ruleset and (not self.ruleset.is_template)
        self.action_apply.setEnabled(can_apply)
        self.action_apply_non_authenticated.setEnabled(can_apply)

        manage_templates = editable_ruleset and (self.multisite_type != MULTISITE_SLAVE)
        self.action_manage_templates.setEnabled(manage_templates)

        generic_links = editable_ruleset and (self.multisite_type != MULTISITE_SLAVE)
        self.action_generic_links.setEnabled(generic_links)

        parameters = editable_ruleset or ((not has_ruleset) and (not read_only))
        self.action_parameters.setEnabled(parameters)
        self.action_ufwi_conf_sync.setEnabled(editable_ruleset)

        self.apply_rules.refreshUndo()

    def updateTitle(self):
        if self.ruleset.ruleset_name:
            ruleset = u"%s[*]" % self.ruleset.ruleset_name
        elif self.ruleset.is_open:
            if self.ruleset.is_template:
                ruleset = tr("new rule set template")
            else:
                ruleset = tr("new rule set")
            ruleset = u"<%s>[*]" % ruleset
        else:
            ruleset = None
        self.setCentralWindowTitle(tr("Firewall"), self.ruleset.client, ruleset)

    def currentTabIsIPv6(self):
        return (self.main_tab.currentIndex() == self.acls_ipv6.RULES_STACK_INDEX)

    def reset(self, undo_state=None):
        tab = self.main_tab.currentIndex()
        self.main_tab.setCurrentIndex(0)
        if tab == 0:
            # Ensure that the event handler is called
            self.mainTabChanged(0)
        self.acl_stack.setCurrentIndex(0)
        self.refreshUndo(undo_state)
        if self.ruleset.is_open:
            self.input_output_rules = self.ruleset.input_output_rules
            self.template.display(Updates())
            self.setReadOnly(self.ruleset.read_only)
        self.updateTitle()
        for rules in self.rules.itervalues():
            rules.filter.clear()
            rules.fill()
        for library in self.iterLibraries():
            library.fill()
        self.action_close_ruleset.setEnabled(self.ruleset.is_open)

    def rulesetCreate(self):
        self.create_ruleset.run()

    def rulesetOpenDialog(self):
        RulesetDialog(self)

    def rulesetClose(self, refresh=True):
        if not self.askSave():
            return False
        name = self.ruleset.ruleset_name
        try:
            self.ruleset.close()
        except RpcdError, err:
            self.ufwi_rpcdError(err)
            return False
        if refresh:
            self.reset()
            if name:
                self.information(tr('The "%s" rule set is closed.') % name)
            else:
                self.information(tr('The rule set is closed.'))
        return True

    def rulesetOpen(self, filetype, name):
        if not self.rulesetClose(refresh=False):
            return
        # FIXME: Only call it at startup?
        self.config.getConfig()
        while True:
            try:
                result = self.ruleset.open(filetype, name)
            except RpcdError, err:
                if err.type == 'AlreadyAcquired':
                    # drop role or kill other session
                    try:
                        self.sessionDialog()
                    except RpcdError, session_dial_error:
                        self.exception(session_dial_error)
                    else:
                        continue
                self.ruleset.reset()
                self.reset()
                self.ufwi_rpcdError(err)
                return False
            break

        self.reset(result['undoState'])
        message = tr('The "%s" rule set is loaded.') % self.ruleset.ruleset_name
        message = formatWarnings(message, result.get('warnings'))
        self.information(message, escape=False)
        return True

    def sessionDialog(self):
        msg = tr("The firewall interface is already running."
                 "Kill your sessions to release the lock."
                 "Warning: all your changes will be lost!")
        self.session_dialog = SessionDialog(self.client,
            RULESET_FORWARD_WRITE_ROLES, msg, self.sessionDialogError, self)
        return self.session_dialog.execLoop()

    def sessionDialogError(self, err):
        self.exception(err, dialog=True)

    def rulesetSave(self):
        if not self.ruleset.ruleset_name:
            # New ruleset: call save as
            self.rulesetSaveAs()
            return
        try:
            self.ruleset('rulesetSave')
        except RpcdError, err:
            self.exception(err, dialog=True)
            return False
        self.refreshUndo()
        self.clearErrors()
        self.setStatus(tr("Rule set saved."))
        self.EAS_SendMessage('ew4_multisite', 'update_templates')
        return True

    def rulesetSaveAs(self):
        name = u""
        while True:
            name, ok = QInputDialog.getText(
                self,
                tr("Rule set name"),
                tr("Enter the new rule set name:"),
                QLineEdit.Normal,
                name)
            if not ok:
                return False
            name = unicode(name)
            # spaces are forbidden: replace them by underscores
            name = name.replace(' ', '_')
            try:
                undo_state = self.ruleset.rulesetSaveAs(name)
            except RpcdError, err:
                self.exception(err, dialog=True)
                continue
            break
        self.updateTitle()
        self.refreshUndo(undo_state)
        self.clearErrors()
        self.setStatus(tr('Rule set saved as "%s"') % name)
        self.EAS_SendMessage('ew4_multisite', 'update_templates')
        return True

    def parametersDialog(self):
        ParametersDialog(self, self.config)

    def customRulesDialog(self):
        CustomRulesDialog(self)

    def _formatErrorMessage(self, message, use_html):
        message = unicode(message)
        if self.rules:
            message = formatRule(self, use_html, message)
        # else: no ruleset loaded yet, the message cannot be formatted
        return message

    def displayMessage(self, title, icon, message, dialog, dialog_type,
    escape=True, is_error=False):
        if escape:
            plaintext = message
            html = Html(message)
        else:
            html = message
            plaintext = stripHTMLTags(message)

        # Display the error in the info box
        info = self._formatErrorMessage(html, True)
        info = htmlTitle(title, icon) + htmlParagraph(info, escape=False)
        self.setInfo(info, is_error=is_error)

        # Display the error in the command line
        self.stdoutMessage(title, plaintext)

        # Display a message box
        if (dialog is None) or dialog:
            msgbox = self._formatErrorMessage(html, False)
            self.messageBox(dialog_type, title, msgbox, escape=False)

    def error(self, message, title=None, dialog=False, escape=True):
        if not title:
            title = tr("Firewall error")
        self.displayMessage(title, ERROR_ICON32, message,
            dialog, QMessageBox.Warning, escape=escape,
            is_error=True)

    def setStatus(self, message, timeout=5):
        CentralWindow.setStatus(self, message, timeout)
        self.stdoutMessage(tr("Status"), message)

    def information(self, message, title=None, dialog=False, escape=True):
        if not title:
            title = tr("Firewall information")
        self.displayMessage(title, INFORMATION_ICON32, message,
            dialog, QMessageBox.Information, escape=escape)

    def connectSlots(self):
        self.connect(self.action_undo, SIGNAL("triggered()"), self.undoLast)
        self.connect(self.action_redo, SIGNAL("triggered()"), self.redoLast)
        self.connect(self.action_save, SIGNAL("triggered()"), self.rulesetSave)
        self.connect(self.action_save_as, SIGNAL("triggered()"), self.rulesetSaveAs)
        self.connect(self.action_new_ruleset, SIGNAL("triggered()"), self.rulesetCreate)
        self.connect(self.action_open_ruleset, SIGNAL("triggered()"), self.rulesetOpenDialog)
        self.connect(self.action_close_ruleset, SIGNAL("triggered()"), self.rulesetClose)
        self.connect(self.action_parameters, SIGNAL("triggered()"), self.parametersDialog)
        self.connect(self.action_custom_rules, SIGNAL("triggered()"), self.customRulesDialog)
        self.connect(self.action_quit, SIGNAL("triggered()"), self.close)
        self.connect(self.action_fullscreen, SIGNAL("triggered()"), self.switchFullScreen)
        self.connect(self.textInfo, SIGNAL('anchorClicked(const QUrl&)'), self.anchorClick)
        self.connect(self.main_tab, SIGNAL('currentChanged(int)'), self.mainTabChanged)
        self.connect(self.action_properties, SIGNAL("triggered()"), self.rulesetProperties)
        self.connect(self.action_fusion, SIGNAL("toggled(bool)"), self.setFusion)
        self.connect(self.action_production_ruleset, SIGNAL("triggered()"), self.productionRuleset)
        self.connect(self.action_ufwi_conf_sync, SIGNAL("triggered()"), self.ufwi_confSync)

    def productionRuleset(self):
        # Load last ruleset
        try:
            attr = self.ruleset('productionRules')
        except Exception, err:
            self.exception(err)
            return
        title = tr("Production rule set")
        if attr:
            try:
                name = attr['ruleset']
            except KeyError:
                name = u"(%s)" % tr("none")
            timestamp = parseDatetime(attr['timestamp'])
            timestamp = fuzzyDatetime(timestamp)
            use_nufw = humanYesNo(attr['use_nufw'])
            html = htmlTable((
                (tr("Rule set"), name),
                (tr("Timestamp"), timestamp),
                (tr("Use NuFW?"), use_nufw),
            ))
        else:
            html = htmlParagraph(tr("There are no rules in production."))
        self.messageBox(QMessageBox.Information, title, unicode(html), escape=False)

    def rulesetProperties(self):
        templates = [(identifier, template['name'])
            for identifier, template in self.ruleset.templates.iteritems()]
        templates.sort(key=lambda(identifier, name): identifier)
        templates = htmlList('%s: %s' % (identifier, name)
            for identifier, name in templates)
        html = htmlTable((
            (tr("Type"), self.ruleset.filetype),
            (tr("Name"), self.ruleset.ruleset_name),
            (tr("Templates"), templates),
            (tr("Version"), self.ruleset.format_version),
            (tr("Read only?"), humanYesNo(self.ruleset.read_only)),
        ))
        self.messageBox(QMessageBox.Information, tr("Rule set properties"), unicode(html), escape=False)

    def mainTabChanged(self, tab_index):
        use_ipv6 = (tab_index == self.acls_ipv6.RULES_STACK_INDEX)
        if tab_index == self.nats.RULES_STACK_INDEX:
            show_firewall = True
        else:
            # Hide 'Firewall' in IPv4 and IPv6 ACLs
            show_firewall = self.input_output_rules
        for name in ('resources', 'protocols'):
            library = self.getLibrary(name)
            filter = library.filter
            update = filter.setIPv6(use_ipv6)
            if name == 'resources':
                update |= filter.setFirewallVisibility(show_firewall)
            if update:
                library.display(Updates())

    def switchFullScreen(self):
        self.setFullScreen(not self.fullscreen)

    def setFullScreen(self, fullscreen):
        old_state = self.fullscreen
        if fullscreen == old_state:
            return old_state
        self.fullscreen = fullscreen
        visible = not self.fullscreen
        self.dock_library.setVisible(visible)
        self.dock_informations.setVisible(visible)
        self.toolbar.setVisible(visible)
        self.statusBar().setVisible(visible)
        return old_state

    def anchorClick(self, url):
        url = unicode(url.toString())
        debug("Click: url=%r" % url)
        if ":" not in url:
            return
        action, url = url.split(":", 1)
        if action == "highlight":
            for library in self.iterLibraries():
                identifier = library.getUrlIdentifier(url)
                if identifier is None:
                    continue
                library.highlight(identifier)
                return
        if action in ("highlight", "edit"):
            for rules in self.rules.itervalues():
                identifier = rules.getUrlIdentifier(url)
                if identifier is None:
                    continue
                if action == "highlight":
                    rules.highlight(identifier)
                else:
                    rules.edit(identifier)
                return

    def quit(self):
        if self.ruleset:
            try:
                self.ruleset.close()
            except Exception:
                pass
            self.ruleset = None
        CentralWindow.quit(self)

    def askSave(self, message=None, buttons=None, refresh=True):
        if not self.ruleset_modified:
            # Ruleset already saved
            return True
        if not message:
            message = tr("Rule set edited: save it or lose your changes?")
        if not buttons:
            buttons = QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
        choice = QMessageBox.question(self,
            tr("Rule set edited"),
            message,
            buttons)
        if choice == QMessageBox.Save:
            # Save the ruleset
            if self.ruleset.ruleset_name:
                saved = self.rulesetSave()
            else:
                saved = self.rulesetSaveAs()
            if refresh and saved:
                self.refreshUndo()
            return saved
        elif choice == QMessageBox.Discard:
            # Use discard his changes
            return True
        else:
            # Abort
            return False

    def closeEvent(self, event):
        if self.askSave(refresh=False):
            event.accept()
            self.quit()
        else:
            event.ignore()

    def loadLast(self):
        attr = self.ruleset('productionRules')
        if not attr:
            return
        if 'ruleset' not in attr:
            return
        name = attr['ruleset']
        if self.ruleset.is_open and (self.ruleset.ruleset_name == attr['ruleset']):
            # It's already the current ruleset
            return
        self.rulesetOpen("ruleset", name)

    def freeze(self, message):
        self.setEnabled(False)
        self.splash.setText(message)
        self.splash.show()
        self.application.processEvents()

    def unfreeze(self):
        self.splash.hide()
        self.application.processEvents()
        self.setEnabled(True)

    # Function called from nulog to highligh an ACL
    def show_acl(self, from_app, rules_list, rule_id):
        self.load()

        self.EAS_SendMessage('eas', 'setTab', 'ufwi_rulesetqt')

        # Load last ruleset
        try:
            self.loadLast()
        except Exception, err:
            self.exception(err)
            return

        # Highlight the ACL
        rule_id = int(rule_id)
        if rule_id:
            rules = self.rules[rules_list]
            found = rules.highlight(rule_id)
            if not found:
                self.information(tr("Rule not found (id=%s)") % rule_id)
        else:
            self.information(
                tr("No rule matching this request. "
                   "Connection rejected and logged, "
                   "which is the default behavior when no specific rules are set."),
                dialog=True)

    def setFusion(self, enabled):
        self.ruleset.setFusion(enabled)

    def useFusion(self):
        return self.ruleset.fusion

    def setReadOnly(self, read_only):
        if self.read_only == read_only:
            return
        self.read_only = read_only
        for action in (self.action_save, self.action_save_as,
        self.action_custom_rules, self.action_manage_templates,
        self.action_generic_links, self.action_parameters, self.action_undo, self.action_redo, self.action_apply,
        self.action_ufwi_conf_sync, self.action_apply_non_authenticated):
            action.setVisible(not read_only)
        for rules in self.rules.itervalues():
            rules.setReadOnly(read_only)
        for library in self.iterLibraries():
            library.setReadOnly(read_only)

    def isReadOnly(self):
        return self.read_only

    def iterLibraries(self):
        return self.object_libraries.itervalues()

    def ufwi_confSync(self):
        try:
            result = self.ruleset('ufwi_confSync')
        except Exception, err:
            self.exception(err)
            return
        self.refresh(result)


