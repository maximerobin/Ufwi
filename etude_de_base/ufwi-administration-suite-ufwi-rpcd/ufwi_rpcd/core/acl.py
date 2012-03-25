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
from twisted.internet.defer import inlineCallbacks, returnValue

from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.backend.error import CoreError, AclError
from ufwi_rpcd.core.getter import getUnicode
# from ufwi_rpcd.core.audit import AuditEvent

from .acl_sqlite import SQLiteAclStorage as AclStorage

# Services open for everyone: anonymous user and component
OPEN_SERVICES = {
    'CORE': set((
        "hasComponent", "getComponentList", "getServiceList",
        "help", "prototype",
    )),
}

# Services open for anonymous users
ANONYMOUS_OPEN_SERVICES = {
    'session': set(("authenticate", "get", "destroy")),
}

# Services open for authenticated users
USER_OPEN_SERVICES = {
    'session': set((
        "list", "keepAlive", "dropRoles", "destroySession",
    )),
    "users_config": set((
        "get", "set", "close", "reset", "clear", "delete", "save",
    )),
    'streaming': set(("subscribe", "unsubscribe")),
    "acl": set(("check", "getMinimalMode")),
    'CORE': set((
        "getMultisiteType", "useEdenWall", "getStatus",
    )),
    # To send the first license, we need to take write role:
    "ufwi_conf": set(('takeWriteRole', 'endUsingWriteRole')),
}

def formatSqliteItem(value):
    if value is not None:
        return value
    else:
        return "NULL"

class AclChecker(Component):
    """
    Component storing all component Access Control Lists (ACL). It's used by
    CORE component to check if a user is allowed to access a service or not.
    """

    NAME = "acl"
    VERSION = "1.0"
    API_VERSION = 2
    ROLES = {
        'nucentral_admin': set(('getAcl', 'setAcl', 'deleteAcl', 'listAllRoles')),
    }

    def init(self, core):
        self.core = core
        self.store = AclStorage(core)
        core.acl = self
        # In minimal mode, only the services in self.minimal_mode_services are
        # allowed.
        self.minimal_mode = False
        self.minimal_mode_services = {
            'acl': set(('getMinimalMode', 'setMinimalMode',
                        'setMinimalModeServices'))}

    def check(self, context, component, service_name):
        """
        Parameters:
         * context: Context object
         * component: Component object
         * service_name: str
        """
        # hardcoded permissions
        if self.hardcodedAcl(context, component, service_name):
            return True

        if context.component:
            return self.checkComponent(context.component, component.name, service_name)
        else:
            return self.checkUser(context.user, component, service_name)

    def checkComponent(self, component, component_name, service_name):
        """
        Check that component is allowed to access to component_name.service_name()
        """
        accept = False
        if '*' in component.acls.keys():
            accept |= service_name in component.acls['*']

        if component_name in component.acls.keys():
            accept |= service_name in component.acls[component_name]

        return accept

    def checkUser(self, user, component, service_name):
        if self.minimal_mode:
            if not component.name in self.minimal_mode_services:
                return False
            if not service_name in self.minimal_mode_services[component.name]:
                return False
        if user:
            if not component.checkRoles(user.roles, service_name):
                return False
        return True

    def hardcodedAcl(self, context, component, service_name):
        if service_name == 'getComponentVersion':
            # Anyone can call *.getComponentVersion()
            return True

        # Service is open for everyone?
        try:
            if service_name in OPEN_SERVICES[component.name]:
                return True
        except KeyError:
            pass

        if context.user:
            try:
                if service_name in ANONYMOUS_OPEN_SERVICES[component.name]:
                    return True
            except KeyError:
                pass
            if context.user.login:
                try:
                    if service_name in USER_OPEN_SERVICES[component.name]:
                        return True
                except KeyError:
                    pass
        return False

    def reload(self):
        self.store = AclStorage(self.core)

    def service_check(self, context, component_name, service_name):
        """
        Check if a service exists. Return False if the service doesn't
        exist or if you are not allowed to use it, and True otherwise.
        """
        try:
            self.core.getService(context, component_name, service_name)
            return True
        except (CoreError, AclError):
            # Missing component, missing service, or permission denied
            return False

    def service_getAcl(self, context, group='', role=''):
        """
        Get the ACLs (group, role): all arguments are optional.
        """
        group = getUnicode("group", group, 0, 100)
        if not group:
            group = None
        role = getUnicode("role", role, 0, 100)
        if not role:
            role = None
        acls = self.store.get_acl(group, role)
        return ( map(formatSqliteItem, acl) for acl in acls )

    @inlineCallbacks
    def service_setAcl(self, context, group, role):
        """
        Add the specified role into group.
        """
        self.store.set_acl(group, role)
        self.info(context, "Group %s is now in %s role" % (group, role))
        yield self.core.notify.emit(self.NAME, 'configModified')

#        event = AuditEvent.fromAclsEvent(context)
#        self.core.audit.emit(event)

    @inlineCallbacks
    def service_deleteAcl(self, context, group='', role=''):
        """
        Delete the ACLs for the specified arguments.
        Return the number of deleted ACLs.
        """
        if group:
            if role:
                self.info(context, "Group %s is removed from role %s" % (group, role))
            else:
                role = None
                self.info(context, "Group %s is removed from all roles" % group)
        else:
            group = None
            if role:
                self.info(context, "Every groups are removed from role %s" % role)
            else:
                role = None
                self.info(context, "Every groups are removed from every roles")
        result = self.store.delete_acl(group, role)
        yield self.core.notify.emit(self.NAME, 'configModified')

#        event = AuditEvent.fromAclsEvent(context)
#        self.core.audit.emit(event)

        returnValue(result)

    def service_listAllRoles(self, context):
        roles = self.core.listAllRoles()
        for role, depends in roles.iteritems():
            roles[role] = list(depends)
        return roles

    def service_getMinimalMode(self, context):
        """
        Get minimal mode (True or False).
        """
        return self.minimal_mode

    def service_setMinimalMode(self, context, minimal_mode):
        """
        Set minimal mode (True or False).
        """
        self.minimal_mode = minimal_mode

    def service_setMinimalModeServices(self, context, component, services):
        """
        Set the list of minimal mode services for a given component.
        """
        self.minimal_mode_services[component] = set(services)

    def service_runtimeFiles(self, context):
        files = []
        for file in self.store.getStoragePaths():
            files.append(
                (file, 'db')
                )
        return {
            'deleted': (),
            'added' : files,
            }

    def service_runtimeFilesModified(self, context):
        """
        recreate self.store
        """
        self.reload()
