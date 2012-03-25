#coding: utf-8
"""
Copyright(C) 2008,2009,2010 EdenWall Technologies

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
from logging import error
from PyQt4.QtCore import PYQT_VERSION_STR, Qt, QT_VERSION, QT_VERSION_STR, SIGNAL
from PyQt4.QtGui import (QIcon, QMessageBox, QPushButton, QTextCursor,
    QVBoxLayout, QStandardItem, QStandardItemModel, QAbstractItemView)
from weakref import ref
import platform

from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcd.common.abstract_cfg import DatastructureIncompatible
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common import tr, EDENWALL
from ufwi_rpcd.common.tools import abstractmethod
from ufwi_rpcc_qt.central_window import CentralWindow, STANDALONE
from ufwi_rpcc_qt.colors import COLOR_CRITICAL, COLOR_FANCY, COLOR_SUCCESS, COLOR_WARNING
from ufwi_rpcc_qt.html import htmlBold, htmlColor, Html, BR
from ufwi_rpcc_qt.session_dialog import SessionDialog
from ufwi_conf.client import NuConfPageKit
from ufwi_conf.client.main_window_ui import Ui_MainWindow
from ufwi_conf.client.multicall import InitMultiCall
from ufwi_conf.client.qt.ufwi_conf_form import NuConfForm, NuConfModuleDisabled
from ufwi_conf.client.qt.input_widgets import TextWithDefault
from ufwi_conf.client.qt.widgets import ScrollArea

from .config_apply import Applier, formatTimestamp
from .restart_eas import restart_eas

STATUS_SAVED_BUT_NOT_APPLIED = [ tr("<i>Configuration is saved but not applied</i>"), "orange" ]

_REAPPLY_WARN_TITLE = tr("About to apply the whole configuration again.")
_REAPPLY_WARN = """
%s<br/>
<ul>
<li>%s</li>
<li>%s</li>
</ul>
%s
""" % (
tr(
    "You are about to trigger a new application of <b>the whole appliance "
    "system configuration</b>."
    ),
tr("This process can cause a service disruption during a few minutes."),
tr("Changes that are saved but not applied will be lost."),
tr("This service requires the Admin role."),
)
_REAPPLY_BEGIN_MSG = tr("Applying the whole configuration again.<br/>")
_REAPPLY_SUCCESS_MSG = tr("Configuration reapplied successfully.")
_REAPPLY_ERROR_MSG = tr("Configuration reapplied: errors occured.")
_REAPPLY_ROLLBACK_MSG = tr(
                "Configuration reapplication: errors occured. "
                "Reapplying in fail-safe mode."
                )

class NuconfItem(QStandardItem):
    def __init__(self, label, page, parent=None, icon=None):
        self.page = page
        if page.IDENTIFIER:
            self.identifier = page.IDENTIFIER
        else:
            self.identifier = page.COMPONENT
        self.icon = icon
        QStandardItem.__init__(self, label)
        if self.icon:
            icon = QIcon(self.icon)
            self.setIcon(icon)

    def setModified(self, modified):
        font = self.font()
        font.setBold(modified)
        self.setFont(font)

def _page_priority(page):
    if hasattr(page, 'get_priority'):
        return page.get_priority()
    return 0

def _cmp_pages(a, b):
    return cmp(_page_priority(a), _page_priority(b))

class NuConfMainWindow(CentralWindow, Ui_MainWindow):
    INSTANCES = set()
    WRITE_ACCESS_BUTTONS = []
    READONLY = False
    LOADED = False
    _ufwi_conf_frontends = []
    _modified = False
    # LOADED True if load have been called on an instance of NuConfMainWindow

    def debugmsg(self, message):
        """
        CentralWindow has a bool 'debug' attribute. -> another name here
        """
        self.client.info("[%s] %s" % (self.tab_name, message))

    def __page_requirements_fullfilled(self, frontend_class):
        name = frontend_class.LABEL
        requirements = frontend_class.REQUIREMENTS
        if not requirements:
            return True
        if not all(requirement in self.available_backends for requirement in requirements):
            self.debugmsg(
                "Frontend \"%s\" not loaded: not all backend requirements fullfilled (%s)." %
                (name, ', '.join(requirements))
                )
            return False
        return True

    def __mk_item(self, frontend_class):
        name = frontend_class.LABEL
        page = None
        try:
            if issubclass(frontend_class, ScrollArea):
                page = frontend_class(self.client, parent=self)
                if hasattr(page, "loaded") and callable(page.loaded):
                    page.loaded()
            else:
                page = frontend_class(self, (), name)
            NuConfMainWindow._ufwi_conf_frontends.append(page)
        except Exception, err:
            self.__handle_frontend_build_error(name, err)
            return None

        page.setParent(self)
        self.main_stack.addWidget(page)
        self.page_count += 1
        return NuconfItem(name, page, parent=self, icon=frontend_class.ICON)

    def __handle_frontend_build_error(self, name, err):
            if isinstance(err, DatastructureIncompatible):
                if err.server_more_recent:
                    self.addCriticalHTMLMessage(
                        tr("Error while loading configuration module for: ") + \
                        htmlBold(name) + '.' + BR  + \
                        tr("Reason: the server software version is too recent for this frontend.") + \
                        BR
                    )
                else:
                    self.addCriticalHTMLMessage(
                        tr("Error while loading configuration module for: ") + \
                        htmlBold(name) + '.' + BR  + \
                        tr("Reason: the frontend is too recent for the server software version.") + \
                        BR
                    )
            elif isinstance(err, NuConfModuleDisabled) and (not EDENWALL):
                return
            self.writeError(err, "Error on loading module %s" % name)
            html = tr("Load error: ") + htmlBold(name)
            html += BR
            html += tr("Reason: %s") % exceptionAsUnicode(err)
            html += BR
            self.addCriticalHTMLMessage(html)

    def __build_gui(self, tab_name, application, standalone):
        self.setupUi(self)
        self.setupCentralWindow(application, standalone)

        self.setCentralWindowTitle(u'%s[*]' % tab_name, self.client)

        self.menu_dock.setWindowTitle(tr('Modules'))
        self.info_dock.setWindowTitle(tr('Information'))
        self.InfoArea = NuConfPageKit.createText(self, "InfoArea")
        self.info_dock.setWidget(self.InfoArea)
        self.toolBar.setObjectName(tr('Toolbar'))
        self.toolBar.setWindowTitle(tr('Toolbar'))

        if standalone != STANDALONE:
            from PyQt4.QtGui import QKeySequence
            self.action_Quit.setShortcut(QKeySequence())

        if QT_VERSION >= 0x40400:
            self.menu.setHeaderHidden(True)
        else:
            self.menu.setHeaderLabel("")

        self.menu.setEditTriggers(QAbstractItemView.NoEditTriggers)


    def pageSystemInit(self):
        self.page_count = 0  # Count of pages in main_stack.
        self.current_page_index = 0

    @staticmethod
    def get_calls():
        if EDENWALL:
            return (
                ('session', 'get'),
                ('acl', 'getMinimalMode'),
                ('CORE', 'getComponentList'))
        else:
            return (
                ('session', 'get'),
                ('CORE', 'getComponentList'))

    @abstractmethod
    def getTree(self, minimal_mode, model):
        pass

    def __init__(
    self,
    application,
    client,
    tab_name,
    parent=None,
    standalone=STANDALONE,
    eas_window=None):
        CentralWindow.__init__(self, client, parent, eas_window)
        Ui_MainWindow.__init__(self)
        NuConfMainWindow.INSTANCES.add(self)
        self.contextual_toolbar = None

        self.__loaded = False
        self.__build_gui(tab_name, application, standalone)
        self.__ufwi_conf_items_model = QStandardItemModel()
        self.menu.setModel(self.__ufwi_conf_items_model)

        self.statusBarTimeout = 15000
        self.pageSystemInit()
        self.modules_to_apply = []
        self.forms = {}
        self.widgets = {}
        self.index2menuItem = []  # To find a menu item with its index.
        #self.pages = self.getPages()
        self.applier = Applier(self)
        self.tab_name = tab_name
        self.init_multicall = InitMultiCall(self.client, self)


        self.available_backends = self.init_call('CORE', 'getComponentList')
        # Retrieve the menu tree and page specifications:
        if EDENWALL:
            NuConfMainWindow.minimalMode = self.init_call('acl', 'getMinimalMode')
        else:
            NuConfMainWindow.minimalMode = False
        try:
            license_info = self.init_call('license', 'getLicenseInfo')
            NuConfMainWindow.model = license_info.get('model', '')
        except Exception:
            NuConfMainWindow.model = ''

        pages = self.getTree(
            NuConfMainWindow.minimalMode,
            NuConfMainWindow.model
            )

        active_pages = []
        for frontend_class in pages:
            if self.__page_requirements_fullfilled(frontend_class):
                active_pages.append(frontend_class)
        self.PAGES = active_pages

    # TODO need to be removed (duplicate with isReadOnly)
    readonly = property(lambda self: NuConfMainWindow.READONLY)



    def isReadOnly(self):
        return NuConfMainWindow.READONLY

    def setReadOnlyMode(self, activate):
        """
        if activate is True activate read only mode
        if activate is False deactivate read only mode
        """
        if NuConfMainWindow.READONLY == activate:
            return

        NuConfMainWindow.READONLY = activate

        if NuConfMainWindow.READONLY:
            self.addToInfoArea(tr("The 'Services' and 'System' tabs are read only."))
        else:
            self.addToInfoArea(tr("The 'Services' and 'System' tabs can be edited."))

        to_remove = []
        for weakref in NuConfMainWindow.WRITE_ACCESS_BUTTONS:
            #execute wearkef to get the actual object or None if the ref is dead
            widget = weakref()
            if widget is None:
                to_remove.append(weakref)
            else:
                widget.setEnabled(not NuConfMainWindow.READONLY)
        #manual garbage collection
        for item in to_remove:
            self.WRITE_ACCESS_BUTTONS.remove(item)

    def sessionModified(self):
        """
        called when the session have been modified
        """
        read_only = not 'ufwi_conf_write' in self.getRoles()
        self.setReadOnlyMode(read_only)

    def findItem(self, name):
        # return a list of 0 or 1 NuconfItem
        return self.__ufwi_conf_items_model.findItems(name, Qt.MatchFixedString)

    def writeAccessNeeded(self, *args):
        for widget in args:
            NuConfMainWindow.WRITE_ACCESS_BUTTONS.append(ref(widget))
            widget.setEnabled(not self.isReadOnly())

    def setModified(self, frontend_class, modified=True):
        if self.isReadOnly():
            return

        if self._standalone != STANDALONE:
            self.eas_window.setModified(modified)
        else:
            self.setWindowModified(modified)

        NuConfMainWindow._modified = modified
        for action in chain(self.iterSaveActions(), self.iterResetActions()):
            action.setEnabled(modified)

        if frontend_class is not None:
            items = self.findItem(frontend_class.LABEL)
        else:
            items = self.iteritems()
        for item in items:
            item.setModified(modified)

    def iterSaveActions(self):
        for app in NuConfMainWindow.INSTANCES:
            yield app.action_Save

    def iterResetActions(self):
        for app in NuConfMainWindow.INSTANCES:
            yield app.actionReset

    def isModified(self):
        return NuConfMainWindow._modified

    def connectSlots(self):

        actions = [
            (self.action_Quit, self.close),
            (self.action_Next, self.next_page),
            (self.action_Previous, self.previous_page),
            (self.actionApp_ly, self.apply_all),
            (self.actionReset, self.reset_all),
            (self.action_Save, self.save_all),
            (self.action_RevertEdenWall, self.revert_edenwall),
            (self.action_Reapply, self.reapply),
        ]

        if self._standalone == STANDALONE:
            actions.append((self.action_AboutNuConf, self.about))
        else:
            self.menuHelp.removeAction(self.action_AboutNuConf)
            self.action_AboutNuConf.setVisible(False)
            self.action_AboutNuConf.setEnabled(False)
            self.action_AboutNuConf.deleteLater()

        for action in actions:
            self.connect(action[0], SIGNAL('triggered()'), action[1])

        for signature in (
            "activated(QModelIndex)",
            "clicked(QModelIndex)"):
            self.connect(self.menu, SIGNAL(signature), self.switch_page)

    def information(self, title, message):
        QMessageBox.information(self, title, message)

    def getTimestamp(self):
        return formatTimestamp()

    def addHTMLToInfoArea(self, html, category=None, prefix=None):
        """html: unicode with HTML tags or Html instance"""
        if not isinstance(html, Html):
            html = Html(html, escape=False)

        if category is not None:
            html = htmlColor(html, category)
            if category == COLOR_CRITICAL:
                html = htmlBold(html)
            elif category == COLOR_SUCCESS:
                html = htmlBold(html)

        if prefix is not None:
            html = prefix + html

        html = unicode(html)
        for app in NuConfMainWindow.INSTANCES:
            app.InfoArea.moveCursor(QTextCursor.End)
            app.InfoArea.insertHtml(html)
            app.InfoArea.moveCursor(QTextCursor.End)

    def addToInfoArea(self, message, category=None):
        timestamp = self.getTimestamp()
        html = Html(message) + BR
        self.addHTMLToInfoArea(html, category, timestamp)

    def addNeutralMessage(self, message):
        self.addToInfoArea(message, category=None)

    def addWarningMessage(self, message):
        self.addToInfoArea(message, category=COLOR_WARNING)

    def addFancyMessage(self, message):
        self.addToInfoArea(message, category=COLOR_FANCY)

    def addCriticalMessage(self, message):
        self.addToInfoArea(message, category=COLOR_CRITICAL)

    def addCriticalHTMLMessage(self, message):
        """message: unicode with HTML tags or Html instance"""
        self.addHTMLToInfoArea(message, COLOR_CRITICAL)

    def about(self):
        QMessageBox.about(self, tr('About NuConf'),
            '<p><b>NuConf</b></p>\n' +
            '<p>Copyright &copy; 2008 INL</p>\n' +
            '<p>' + tr('This front-end program is licensed under the '
                + 'GNU General Public License, version 2.') + '</p>'
            '<p>Python %s - Qt %s - PyQt %s ' % (platform.python_version(),
                QT_VERSION_STR, PYQT_VERSION_STR) + tr('on') + ' ' +
            platform.system() + '</p>')

    def addToPath(self, name_path, name):
        if not name_path:
            return name_path
        else:
            return name_path + (name,)

    def iteritems(self):
        for row in xrange(0, self.__ufwi_conf_items_model.rowCount()):
            yield self.__ufwi_conf_items_model.item(row)

    def allitems(self):
        return list(self.iteritems())

    def setAllNotModified(self):
        for app in NuConfMainWindow.INSTANCES:
            app.setModified(None, False)

    def load(self):
        """
        called the first time that window is displayed/selected
        """
        frontend_classes = tuple(self.PAGES)
        self.init_multicall.listConfigCalls(frontend_classes, self.get_calls)
        self.init_multicall.run()
        self._load()
        self.connectSlots()
        for frontend_class in self.PAGES:
            item = self.__mk_item(frontend_class)
            if item is not None:
                self.__ufwi_conf_items_model.appendRow(item)

        self.switchToolbar()

        assert len(self.allitems()) == self.page_count

        def _findAppNameByInstance(app):
            for name, instance in app.eas_window.apps.iteritems():
                if app is instance:
                    return name

        self.acquireRight()

        self.writeAccessNeeded(
            self.actionApp_ly,
            self.action_Save,
            self.actionReset,
            self.action_RevertEdenWall
            )

        self.setAllNotModified()

        disable = self._standalone != STANDALONE and self.page_count == 0
        self.eas_window.setEnabledApplication(self, not disable)


        if self._standalone != STANDALONE:
            for app in NuConfMainWindow.INSTANCES:
                if app.__loaded:
                    continue
                if app is not self:
                    app_name = _findAppNameByInstance(app)
                    self.eas_window.load_app(app_name)
        NuConfMainWindow._ufwi_conf_frontends.sort(_cmp_pages)
        NuConfMainWindow._ufwi_conf_frontends.reverse()
        self.__loaded = True

        self.init_multicall.clean() # after load, cached responses of init
                                    # multicall must not be used

    @abstractmethod
    def _load(self):
        pass

    def acquireRight(self):
        """
        check if other session using ufwi_conf_write exists.

        no other session with ufwi_conf_write locked: acquire lock
        ufwi_conf_write locked by other session: kill other session or use
            read-only mode
        """
        if not NuConfMainWindow.LOADED:
            NuConfMainWindow.LOADED = True

            if EDENWALL and ('ufwi_conf_write' not in self.getRoles()):
                self.setReadOnlyMode(True)
                return

            # acquire lock on ufwi_conf_write
            msg = tr("The configuration interface is already running. Kill sessions to release the lock or use the read-only mode.")
            while True:
                try:
                    acquired = self.client.call('ufwi_conf', 'takeWriteRole')
                except RpcdError:
                    msg = tr(
                        "Warning, if several users connect to this appliance simultaneously, "
                        "overlapping operations on the 'System' or 'Services' tab may lead to "
                        "an inconsistent configuration."
                        )
                    self.addHTMLToInfoArea(
                    """
                    <p align="justify" style="background-color: #d3696c; font-size:large; padding:20;">
                    <br/>
                    %s
                    <br/>
                    </p>
                    <p style=""/p>
                    """ % msg
                    )
                    break
                if not acquired:
                    session_dialog = SessionDialog(self.client, ['ufwi_conf_write'], msg, self.sessionDialogError, self)
                    try:
                        session_killed = session_dialog.execLoop()
                    except Exception:
                        self.addToInfoArea(tr("Can not get exclusive access to the 'Services' and the 'System' tabs"))
                    else:
                        # we have killed other session or dropped right
                        if session_killed:
                            # retry to acquire
                            continue
                        else:
                            self.addToInfoArea(tr("Configuring the 'Services' and the 'System' tabs is not allowed."))
                    session_after = self.client.call('session', 'get')
                    if self.getSession() != session_after:
                        self.setSession(session_after)
                break

    def sessionDialogError(self, err):
        QMessageBox.critical(self, tr("Error"), unicode(err))

    def delete_frontends(self):
        """
        delete 'lost' window (frontends which have raised exception)
        """
        for child in self.children():
            if isinstance(child, (ScrollArea, NuConfForm)):
                child.close()

    def remove_page_from_tree(self, tree, page_name):
        for index, frontend_class in enumerate(tree):
            if frontend_class.LABEL == page_name:
                del tree[index]
                return

    def resetView(self):
        """
        Abort modifications made on the GUI and reloads all values
        """

    # Slots:

    def switch_page(self, modelindex):
        self.current_page_index = modelindex.row()
        self.main_stack.setCurrentIndex(self.current_page_index)
        self.switchToolbar()

    def switchToolbar(self):
        current_page = self.main_stack.currentWidget()

        if self.contextual_toolbar is not None:
            self.removeToolBar(self.contextual_toolbar)

        if hasattr(current_page, 'contextual_toolbar'):
            contextual_toolbar = current_page.contextual_toolbar
        else:
            contextual_toolbar = None

        if contextual_toolbar is not None:
            self.addToolBar(contextual_toolbar)
            contextual_toolbar.show()

        self.contextual_toolbar = contextual_toolbar

    def next_page(self):
        if self.current_page_index >= self.page_count - 1:
            self.current_page_index = 0
        else:
            self.current_page_index += 1
        self.main_stack.setCurrentIndex(self.current_page_index)
        self.menu.setCurrentItem(
                self.index2menuItem[self.current_page_index])

    def previous_page(self):
        if self.current_page_index <= 0:
            self.current_page_index = self.page_count - 1
        else:
            self.current_page_index -= 1
        self.main_stack.setCurrentIndex(self.current_page_index)
        self.menu.setCurrentItem(
                self.index2menuItem[self.current_page_index])

    def getCommitMessage(self):
        input_box = QMessageBox()
        input_box.setWindowTitle(tr("Commit message"))
        input_box.setText(tr("Enter changes summary below"))
        input_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)

        box = QVBoxLayout()
        input_line = TextWithDefault(tr("Supply a commit message."))
        input_box.setFocusProxy(input_line)
        ok_button = input_box.button(QMessageBox.Ok)
        ok_button.setFocusProxy(input_line)
        cancel_button = input_box.button(QMessageBox.Cancel)
        cancel_button.setFocusProxy(input_line)
        input_box.adjustSize()
        box.addWidget(input_line)
        input_box.layout().addLayout(box, 1, 1)
        ok = input_box.exec_() == QMessageBox.Ok
        text = unicode(input_line.text())
        return text, ok

    def get_name(self, specified_page):
        for instance in NuConfMainWindow.INSTANCES:
            for item in instance.allitems():
                if specified_page is item.page:
                    return unicode(item.text())
        return tr("Indefinite page")

    def apply_done(self):
        self.emit(SIGNAL('EAS_Message'), 'nudpi.client.qt', 'network_modification')

    def save_all(self):
        """
        foreach frontend get state. If all frontends are valid, call saveConf
        for each frontend.
        """
        errors = {}
        checkedModules = []
        for module in NuConfMainWindow._ufwi_conf_frontends:
            errors_found = False
            if not module.isModified():
                continue
            if isinstance(module, NuConfForm) and hasattr(module, 'item'): # NuConfForm
                module.checkConf()  # Appends to module.errors.
                if  module.errors:
                    errors[module.item.name] = module.errors[:]
                    module.errors = []
                    errors_found = True
            else:
                errors_found = not module.isValid()
                if errors_found:
                    module_name = self.get_name(module)
                    if hasattr(module, 'error_message') and \
                            module.error_message != "":
                        errors[module_name] = module.error_message
                    else:
                        errors[module_name] = tr('invalid configuration')
            if not errors_found:
                checkedModules.append(module)

        if errors:
            title = tr('Error(s) while saving the configuration.')
            error_message = ""
            for key, value in errors.iteritems():
                error_message += "<li>%s: %s</li>\n" % (key, value)
            message = "<h2>%s</h2>\n\n<ul>%s</ul>" % (title, error_message)
            message += "\n" + tr(
                "See the information zone below for details, if any.")
            QMessageBox.critical(self, tr('Configuration error'), message)
            return False
        commit_message = ""
        while commit_message == "":
            commit_message, ok = self.getCommitMessage()
            if not ok:
                return False
            if commit_message == "":
                QMessageBox.critical(
                    self,
                    tr("Not saving"),
                    tr("Not saving.\nCommit message can not be empty.")
                    )

        try:
            self.__saveModules(checkedModules, commit_message)
        except RpcdError, err:
            if err.type == "ConfigError":
                QMessageBox.critical(
                    self,
                    tr("Error while saving"),
                    tr("Unable to save. Perhaps the EdenWall configuration is locked by the "
                    "application process.")
                    )
                return False
            else:
                raise

        if checkedModules:
            text = unicode(tr("%s: configuration saved.")) % self.getTabName()
            self.addToInfoArea(text, category=COLOR_SUCCESS)
            self.setStatus(text, self.statusBarTimeout)

        for i in checkedModules:
            if not i in self.modules_to_apply:
                self.modules_to_apply.append(i)

        self.setAllNotModified()
        if self._standalone != STANDALONE:
            self.eas_window.setModified(True, STATUS_SAVED_BUT_NOT_APPLIED)

        return True

    def __saveModules(self, modules, commit_message):
        """modules is an iterable"""
        for module in modules:
            try:
                module.saveConf(commit_message)
            except Exception:
                self.addCriticalMessage(
                    tr(
                    "Problem while saving configuration for module %s."
                    ) % module.LABEL
                )
                raise

    def revert_edenwall(self):
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Question)
        msg_box.setText(
            "<h2>"
            + tr("Really revert the last saved configuration to the running configuration?")
            + "</h2>"
            )

        revert_button = QPushButton(
            QIcon(":/icons-32/clear.png"),
            tr("Yes, clear changes"),
            msg_box
            )
        cancel_button = QPushButton(
            QIcon(":/icons-32/edit.png"),
            tr("No, keep currently saved changes"),
            msg_box
            )
        msg_box.addButton(revert_button, QMessageBox.AcceptRole)
        msg_box.addButton(cancel_button, QMessageBox.RejectRole)

        msg_box.setDefaultButton(cancel_button)
        ret = msg_box.exec_()

        if ret == QMessageBox.RejectRole:
            return
        elif ret == QMessageBox.AcceptRole:
            self.addToInfoArea(
                tr("Reverting configuration state to running configuration"),
                category=COLOR_FANCY
                )
            async = self.client.async()
            async.call('config', 'reset',
                callback=self._reset_success,
                errback=self._reset_failure
                )

    def _reset_success(self, value):
        self.addToInfoArea(
            tr("Revert done, appliance ready."),
            category=COLOR_FANCY
            )
        msg_box = QMessageBox()
        msg_box.setIcon(QMessageBox.Warning)
        msg_box.setText(
            "<h2>"
            + tr("Displayed information may not reflect the saved values on the appliance. "
                "Restart EdenWall Administration Suite?")
            + "</h2>"
            )

        msg_box.setInformativeText(
            tr(
            "Be aware that, as EdenWall Administration Suite is now out of sync with the "
            "appliance, you should avoid saving until it is restarted or it may lead to "
            "inconsistencies in the EdenWall configuration."
            )
        )

        restart_button = QPushButton(
            QIcon(":/icons-32/refresh.png"),
            tr("Restart EdenWall Administration Suite"),
            msg_box
            )
        cancel_button = QPushButton(
            QIcon(":/icons-32/warning.png"),
            tr("Keep EdenWall Administration Suite open"),
            msg_box
            )
        msg_box.addButton(restart_button, QMessageBox.AcceptRole)
        msg_box.addButton(cancel_button, QMessageBox.RejectRole)

        msg_box.setDefaultButton(cancel_button)
        ret = msg_box.exec_()

        if ret == QMessageBox.RejectRole:
            return
        elif ret == QMessageBox.AcceptRole:

            restart_eas()

    def _reset_failure(self, value):
        self.addToInfoArea(
            "Could not revert. Perhaps you don't have the necessary rights?",
            category=COLOR_CRITICAL
            )

    def apply_all(self):
        if NuConfMainWindow._modified:
            msg_box = QMessageBox()
            msg_box.setText(
                "<h2>"
                + tr("There are pending modifications in EdenWall Administration Suite.")
                + "</h2>"
                )
            msg_box.setInformativeText(
                tr(
                    "Do you want to save your changes?"
                    )
                + "<ul><li>"
                + tr(
                    'Click <b>Save</b> to save pending changes before '
                    'triggering the application of previously registered modifications.'
                )
                + "</li><li>"
                + tr(
                    'Click <b>Discard</b> to discard pending changes before '
                    'triggering the application of previously registered modifications.'
                    )
                + "</li><li>"
                + tr('Click <b>Cancel</b> to keep editing the configuration.')
                + "</li></ul>"
                )
            msg_box.setStandardButtons(
                QMessageBox.Save
                | QMessageBox.Discard
                | QMessageBox.Cancel
                )
            msg_box.setDefaultButton(QMessageBox.Save)
            ret = msg_box.exec_()
            if ret == QMessageBox.Save:
                if not self.save_all():
                    return
            elif ret == QMessageBox.Discard:
                self.actionReset.trigger()
            else:
                return

        self.applier.start()

    def reset_all(self):
        self.init_multicall = InitMultiCall(self.client, self)
        for module in NuConfMainWindow._ufwi_conf_frontends:
            if not module.isModified():
                continue
            self.init_multicall.addCallsForFrontend(module.__class__)

        # fetch needed data
        self.init_multicall.run()
        for module in NuConfMainWindow._ufwi_conf_frontends:
            if not module.isModified():
                continue
            if isinstance(module, NuConfForm) and hasattr(module, 'item'):
                error(tr('Resetting the %s view') % module.item.name)
            module.resetConf()
        self.init_multicall.clean()
        self.setAllNotModified()
        if self._standalone != STANDALONE:
            self.eas_window.setModified(False)

        text = unicode(tr("Configuration reset"))
        self.addToInfoArea(text)
        self.setStatus(text, self.statusBarTimeout)

    def disableAllApps(self):
        """
        disable all tabs
        """
        self.actionApp_ly.setDisabled(True)
        if self._standalone != STANDALONE:
            self.eas_window.tabWidget.setEnabled(False)
            self.eas_window.action_show_session.setDisabled(True)
            self.eas_window.unloadApps()

    def quit(self):
        for item in self.iteritems():
            item.page.unload()
        CentralWindow.quit(self)

    def init_call(self, component, service):
        if self.init_multicall.isCached(component, service):
            return self.init_multicall.getResponse(component, service)
        else:
            return self.client.call(component, service)

    def getTabName(self):
        return self.tab_name

    def getPage(self, identifier):
        """
        Get a page by its identifier. The identifier is the IDENTIFIER class
        type, or COMPONENT class attribute if IDENTIFIER is not set.
        """
        for inst in self.INSTANCES:
            for item in inst.iteritems():
                if item.identifier == identifier:
                    return item.page
        raise KeyError(tr('There is no page with the identifier "%s"') % identifier)

    def reapply(self):
        self._reapply_inhibited = False
        confirm = QMessageBox.warning(
            self,
            _REAPPLY_WARN_TITLE,
            _REAPPLY_WARN,
            QMessageBox.Ok | QMessageBox.Cancel
            )
        if confirm != QMessageBox.Ok:
            return

        self.addCriticalHTMLMessage(_REAPPLY_BEGIN_MSG)
        client = self.client.clone("reapply")
        async = self.client.async()
        async.call(
            "config", "reApplyAll",
            callback=self._reapply_success,
            errback=self._reapply_error
            )

        self.applier.start_polling(
            final_success_message=_REAPPLY_SUCCESS_MSG,
            rollback_error_message=_REAPPLY_ROLLBACK_MSG,
            final_error_message=_REAPPLY_ERROR_MSG,
        )

    def _reapply_success(self, result):
        pass

    def _reapply_error(self, result):
        self.addCriticalHTMLMessage("%s: %s\n" % (tr("Error"), result.unicode_message))

