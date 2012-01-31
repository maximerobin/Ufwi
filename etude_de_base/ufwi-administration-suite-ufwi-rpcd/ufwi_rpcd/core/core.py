"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Pierre Chifflier <p.chifflier AT inl.fr>

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
# Setup unicode console
from ufwi_rpcd.common.unicode_stdout import installUnicodeStdout
installUnicodeStdout()

import sys
import warnings
from types import GeneratorType
from os import _exit as os_force_exit, chdir
from ConfigParser import SafeConfigParser
from datetime import datetime
from signal import signal, SIGCHLD, SIG_DFL
from logging import CRITICAL
from copy import deepcopy

from twisted.internet.defer import Deferred, succeed, inlineCallbacks, returnValue
from twisted.internet import reactor
from twisted.application.internet import TCPServer
from twisted import version as TWISTED_VERSION

from ufwi_rpcd.common import EDENWALL
from ufwi_rpcd.common.multisite import MULTISITE_SLAVE, MULTISITE_MASTER, NO_MULTISITE
from ufwi_rpcd.common.odict import odict
from ufwi_rpcd.common.human import humanRepr
from ufwi_rpcd.common.services import HIDE_SERVICE_RESULT

from ufwi_rpcd.backend import tr, AclError, ComponentError
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.error import CoreError

from ufwi_rpcd.core.version import VERSION, WEBSITE
from ufwi_rpcd.core.module_loader import ModuleLoader
from ufwi_rpcd.core.log import setupLog
from ufwi_rpcd.core.service_twisted import RpcdService, RpcdSite
from ufwi_rpcd.core.ssl_m2crypto import startListeningSSL
from ufwi_rpcd.core.publish_xmlrpc import RPCPublisher
from ufwi_rpcd.core.error import (CORE_MISSING_COMPONENT, CORE_MISSING_SERVICE,
    ACL_PERMISSION_DENIED)
from ufwi_rpcd.core import events

# from .audit import AuditEvent
from .conf_files import RPCD_CONF_FILES, get_var_or_default

if EDENWALL:
    SERVER_NAME = "EdenWall server"
else:
    SERVER_NAME = "NuFirewall server"

MAX_RESULT_LENGTH = 100

class Core(Logger):
    """
    Rpcd core. Main methods:
     - start(): load modules and start the server
    """
    modules_list = { }
    slaves = { }
    master_object = None    # if running in master mode, this is the corresponding object
    master = None           # if we are a slave, this is the connection to the master

    def __init__(self, service_collection):
        Logger.__init__(self, "core")
        self.reactor = reactor
        self.start_time = datetime.now()
        self.service_collection = service_collection
        # protocol ('http' or 'https') => port number (8080 or 8443)
        # dictionary used by the multisite maste
        self.listening = {}
        # component name (str) => Component object. Use an ordered
        # dictionary to be able to unload the components in the reverse order
        # of the creation order.
        self.components = odict()
        # component name => {service name => function}
        self.services = {}
        self.broken_components = []
        self.loadConfig()
        self.reactor.addSystemEventTrigger('before', 'shutdown', self.shutdownEvent)

    def getAddressPort(self, suffix, default_port):
        address = self.conf_get_var_or_default("CORE","bind_address"+suffix, "*")
        if address == "*":
            address = ""

        key = "bind_port"+suffix
        port = self.conf_get_var_or_default("CORE", key, default_port)
        try:
            port = int(port)
        except ValueError:
            raise Exception("%s is not a valid integer (%s)" % (key, port))
        return address, port

    def setupService(self, service):
        service.setServiceParent(self.service_collection)

    def startListening(self):
        bindAddress, bindPort = self.getAddressPort("", 8080)

        self.warning("Adding server at %s:%s" % (bindAddress, bindPort))
        service = TCPServer(bindPort, self.site, interface=bindAddress)
        self.setupService(service)
        self.listening['http'] = bindPort

    def startListeningSSL(self):
        # Read the SSL configuration
        from ufwi_rpcd.core.ssl_config import ServerSSLConfig
        self.ssl_config = ServerSSLConfig(self)
        address = "%s:%s" % (self.ssl_config.address, self.ssl_config.port)

        # Create the SSL server
        self.warning("Adding SSL server at %s (M2Crypto)" % address)
        startListeningSSL(self, self.ssl_config)
        self.listening['https'] = self.ssl_config.port

    def conf_get_var_or_default(self, section, value, default=None, type=None):
        return get_var_or_default(self.config, section, value, default, type)

    @inlineCallbacks
    def _loadBaseComponents(self, unused):
        from ufwi_rpcd.core.acl import AclChecker
        from ufwi_rpcd.core.core_component import CoreComponent
        from ufwi_rpcd.core.lock import LockingComponent
        from ufwi_rpcd.backend.versionning import VersionningComponent
        from ufwi_rpcd.core.config import ConfigComponent
        from ufwi_rpcd.core.session import SessionManager
        from ufwi_rpcd.core.streaming import StreamingComponent
        from ufwi_rpcd.core.users_config import UsersConfigManager
        from ufwi_rpcd.core.notify import Notify

        self.notify = Notify()

        if EDENWALL:
            from ufwi_rpcd.core.audit import Audit
            try:
                yield self.loadComponent(Audit)
            except Exception, err:
                self.critical("Audit component not loaded!. Read trace:")
                self.writeError(err)
                self.info("Starting ufwi-rpcd anyway")

        if EDENWALL:
            from ufwi_rpcd.core.auth.auth import Auth
            from ufwi_rpcd.core.auth.component import AuthComponent
        else:
            from ufwi_rpcd.core.auth.simple_auth import SimpleAuth as Auth
            from ufwi_rpcd.core.auth.simple_component import SimpleAuthComponent as AuthComponent

        self.auth = Auth(self)

        yield self.loadComponent(CoreComponent)
        yield self.loadComponent(LockingComponent)
        yield self.loadComponent(VersionningComponent)
        yield self.loadComponent(ConfigComponent)
        yield self.loadComponent(AuthComponent)
        yield self.loadComponent(SessionManager)
        yield self.loadComponent(AclChecker)
        yield self.loadComponent(StreamingComponent)
        yield self.loadComponent(UsersConfigManager)

    def loadConfig(self):
        """
        Load CORE configuration
        """
        self.config = SafeConfigParser()
        self.config.read(RPCD_CONF_FILES)

        self.var_dir = self.config.get('CORE', 'vardir')

        paths = self.conf_get_var_or_default('CORE','path')
        if paths:
            for path in paths.split(':'):
                sys.path.append(path)

    def createSite(self):
        xmlrpc = RPCPublisher(self)
        service = RpcdService(RPC2=xmlrpc)
        return RpcdSite(service)

    def start(self):
        # Load modules after the reactor has started, to be sure
        # that twisted logging facility is started
        self.reactor.callLater(0, self._startLater)

    def startError(self, failure):
        self.writeError(failure, "Error on Core.start", log_level=CRITICAL)
        self.exit(1)

    def _startLater(self):
        try:
            defer = self._start()
            defer.addErrback(self.startError)
            return defer
        except Exception, err:
            self.startError(err)

    def showWarning(self, message, category, filename, lineno, file=None, line=None):
        if sys.hexversion >= 0x2060000:
            message = warnings.formatwarning(message, category, filename, lineno, line)
        else:
            message = warnings.formatwarning(message, category, filename, lineno)
        for line in message.splitlines():
            self.debug("Python warning: %s" % line)

    def _start(self):
        # Disable Twisted SIGCHLD signal handler
        #
        # createProcesss() uses subprocess.Popen(..., close_fds=True) to
        # create child processes. Twisted SIGCHLD signal handler logs the
        # signal. But the log file is closed (because of close_fds=True) and an
        # OSError(EBADF) is raised.
        #
        # This hack can be avoided by rewritting ufw_rpcd.common.process using
        # reactor.spawnProces():
        # http://twistedmatrix.com/projects/core/documentation/howto/process.html
        signal(SIGCHLD, SIG_DFL)

        # Initialize logging, Python warnings, and display some informations
        setupLog(self)
        warnings.showwarning = self.showWarning
        self.displayInfo()

        # Move to the root directory
        chdir("/")

        defer = succeed(None)
        defer.addCallback(self._loadBaseComponents)
        defer.addCallback(self._loadComponents)
        defer.addCallback(self._configApply)
        defer.addCallback(self._init_done)
        defer.addCallback(self._start2)
        return defer

    def _configApply(self, unused):
        defer = self.config_manager.initialApplyIfNeeded()
        if not defer:
            return
        defer.addErrback(self.writeError, "Error on initial apply")
        return defer

    def _loadComponents(self, unused):
        module_loader = ModuleLoader(self)
        return module_loader.run()

    def _start2(self, unused):
        # Reload old sessions and locks
        self.session_manager.load()
        self.lock_manager.load(self.session_manager)

        # Start listening on TCP and UDP sockets
        self.site = self.createSite()
        self.startListening()

        if self.config.getboolean('CORE', 'enable_ssl'):
            try:
                self.startListeningSSL()
            except Exception, err:
                self.writeError(err, "Error when starting the SSL server", log_level=CRITICAL)
        else:
            self.ssl_config = None

        # Server started
        self.critical("%s %s started" % (SERVER_NAME, VERSION))

        events.emit('ufwirpcdServerStarted')
        self.notify.emit('ufwi-rpcd', 'started')

    @inlineCallbacks
    def _init_done(self, unused):
        for component in self.components.itervalues():
            try:
                yield component.init_done()
            except Exception, err:
                self.writeError(err, "Error during post-initialization of component %s" % component.name)

    def displayInfo(self):
        self.critical("Starting %s %s: %s" % (SERVER_NAME, VERSION, WEBSITE))
        self.warning("Python %s.%s.%s and Twisted %s" % (
            sys.hexversion >> 24,
            (sys.hexversion >> 16) & 255,
            (sys.hexversion >> 8) & 255,
            TWISTED_VERSION.short()))

    def exit(self, exitcode):
        """
        Quit Rpcd with the exit status "exitcode".
        """
        if exitcode:
            self.reactor.addSystemEventTrigger("after", "shutdown", self._exit, exitcode)
        self.reactor.stop()

    def _exit(self, exitcode):
        # Hack for Twisted to exit with the specified exit code
        os_force_exit(exitcode)

    def shutdownEvent(self, *unused_args):
        self.error("Stop %s" % SERVER_NAME)
        while len(self.components):
            name, component = self.components.popitem(last=True)
            try:
                # Destroy components in reverse order than loaded.
                self.debug("Destroy %s component" % name)
                r = component.destroy()
                if isinstance(r, Deferred):
                    r.addCallback(self.shutdownEvent)
                    return r
            except Exception, err:
                self.writeError(err, "Error on destroying module %s" % name)

        self.critical("Exit")

    def checkServiceAcl(self, context, component, service_name, component_check=True):
        if context.isUserContext() and not context.hasSession():
            # A session is needed to do anything
            # different than CORE.clientHello()
            return (
                (component.name == "CORE")
                and service_name in ("clientHello", "createSession")
            )

        if not self.acl.check(context, component, service_name):
            return False

        if component_check and service_name != "getComponentVersion":
            if component.API_VERSION == 2:
                component.checkServiceCall(context, service_name)
            else:
                # Backward compatibility
                if not component.checkAcl(context, service_name):
                    return False
        return True

    def loadComponent(self, component_cls):
        name = component_cls.NAME
        if component_cls.API_VERSION not in (1, 2):
            self.error("Skip component %r: unknown API version (%s)"
                % (name, component_cls.API_VERSION))
            self.broken_components.append(name)
            return succeed(None)
        version = component_cls.VERSION
        self.info("Load component %s (version %s)" % (name, version))
        component = component_cls()
        self.components[name] = component
        try:
            defer = succeed(None)
            defer.addCallback(self._registerServices, component)
            defer.addCallback(lambda unused: component.init(self))
            defer.addErrback(self._unregisterComponent, name)
            return defer
        except:
            self.loadComponentFailed(name)
            raise

    def _registerServices(self, unused, component):
        self.services[component.name] = component.getServiceList()

    def loadComponentFailed(self, name):
        del self.components[name]
        if name in self.services:
            del self.services[name]
        self.broken_components.append(name)

    def _unregisterComponent(self, failure, name):
        self.loadComponentFailed(name)
        return failure

    def missingComponent(self, name):
        return CoreError(CORE_MISSING_COMPONENT,
            tr("No component registered with this name (%s)"),
            repr(name))

    def _getComponent(self, component_name, context=None):
        try:
            return self.components[component_name]
        except KeyError:
            raise self.missingComponent(component_name)

    def checkComponentAcl(self, context, component):
        for service in self.services[component.name]:
            if service == "getComponentVersion":
                # Ignore getComponentVersion(): anyone is allowed to call it
                continue
            if self.acl.check(context, component, service):
                # At least one service is allowed for the specified context
                return True
        return False

    def getComponent(self, context, component_name):
        component = self._getComponent(component_name)
        if self.checkComponentAcl(context, component):
            return component

#        if context.isUserContext():
#            # Emit an audit event
#            event = AuditEvent.fromACL(
#                context,
#                component=component_name
#                )
#
#            self.audit.emit(event)

        if context.isAnonymous():
            raise self.missingComponent(component_name)
        else:
            raise AclError(ACL_PERMISSION_DENIED,
                tr("You are not allowed to access the %s component"),
                repr(component_name))

    def hasComponent(self, context, name):
        try:
            self.getComponent(context, name)
            return True
        except (CoreError, AclError):
            return False

    def missingService(self, component, service):
        return CoreError(CORE_MISSING_SERVICE,
            tr("The %s component has no %s() service"),
            component, service)

    def getService(self, context, component_name, service_name,
    component_check=True):
        """
        Get a service from his component name and its name.
        Return (component, service).
        """
        # Get the service
        component = self._getComponent(component_name)
        try:
            service = self.services[component_name][service_name]
        except KeyError:
            raise self.missingService(component_name, service_name)

        # Check context ACLs
        if self.checkServiceAcl(context, component, service_name,
        component_check=component_check):
            # Context is allowed to access to the service
            return component, service

        # Access denied: Emit an audit event
        long_service = u"%s.%s()" % (component_name, service_name)
#        event = AuditEvent.fromACL(
#            context,
#            component=component_name,
#            service=long_service
#            )
#        self.audit.emit(event)

        # Raise an error
        if context.isAnonymous():
            # For anonymous users, use the same error (missing service) if a
            # service doesn't exist or if the access is denied
            raise self.missingService(component_name, service_name)
        else:
            # Use the real error for authenticated user
            raise AclError(ACL_PERMISSION_DENIED,
                tr("You are not allowed to access the %s service"),
                long_service)

    def logService(self, context, component, service, arguments, result):
        logger = self
        if context.component:
            try:
                logger = self._getComponent(context.component.name)
            except ComponentError:
                pass
        service_text = "%s.%s" % (component.name, service)
        text = component.formatServiceArguments(service, arguments)
        text = u"%s(%s)" % (service_text, text)
        if result is not None:
            if service_text not in HIDE_SERVICE_RESULT:
                result = humanRepr(result, MAX_RESULT_LENGTH)
            else:
                result = '***'
            text += ' -> %s' % (result,)
        if context.component:
            text = "Component calls %s" % text
        else:
            text = "User calls %s" % text
        component.logService(context, logger, service, text)

    @inlineCallbacks
    def callService(self, context, component_name, service, *arguments, **kw):
        """
        Call a service. Always return a Deferred object.
        """
        component, func = self.getService(context, component_name, service)
        self.logService(context, component, service, arguments, None)

        # Copy arguments to prevent the component from modifying them
        args = []
        for arg in arguments:
            args.append(deepcopy(arg))

        result = yield func(context, *args)
        if isinstance(result, GeneratorType):
            result = list(result)
        if result is None:
            result = component.DEFAULT_RESULT
        self.logService(context, component, service, arguments, result)
        returnValue(result)

    def _hasComponent(self, name):
        return (name in self.components)

    def getMultisiteType(self):
        """
        Returns the type of firewall in the multisite context.
        """
        if self._hasComponent('multisite_slave'):
            return MULTISITE_SLAVE
        elif self._hasComponent('multisite_master'):
            return MULTISITE_MASTER
        else:
            return NO_MULTISITE

    def getComponentList(self, context):
        for name, component in self.components.iteritems():
            if not self.checkComponentAcl(context, component):
                # Permission denied: ignore this component
                continue
            yield name

    def getServiceList(self, context, component_name):
        component = self.getComponent(context, component_name)
        services = []
        for name in self.services[component_name]:
            if not self.checkServiceAcl(context, component, name,
            component_check=False):
                continue
            services.append(name)
        if services == ["getComponentVersion"]:
            services = []
        return services

    def listAllRoles(self):
        roles = {}
        for component in self.components.itervalues():
            for role, services in component.ROLES.iteritems():
                if role not in roles:
                    roles[role] = set()
                for service in services:
                    if not service.startswith('@'):
                        continue
                    roles[role].add(service[1:])
        return roles

