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
from __future__ import with_statement
from datetime import datetime
from grp import getgrnam
from inspect import getmro
try:
    import jinja
except ImportError:
    import jinja2 as jinja
from pwd import getpwnam
from os import chown, chmod, close, fsync, unlink, write
from os.path import exists
from shutil import copy2
from tempfile import mkstemp, NamedTemporaryFile
from time import time
from types import MethodType

from ufwi_rpcd.common.human import humanRepr
from ufwi_rpcd.backend.logger import Logger
from ufwi_rpcd.backend.session_storage import SessionStorage

class Component(Logger):
    # Name used to call a service (eg. "ufwi_ruleset")
    NAME = None

    # Component version: can be read using getComponentVersion() service
    VERSION = None

    # Component API version
    #  - version 2:
    #    Replace checkAcl() by checkServiceCall(). checkServiceCall() must raise an
    #    error if the service call is invalid.
    #  - version 1:
    #    First version. checkAcl() returns a boolean, False if the service call
    #    must be blocked.
    API_VERSION = None

    # Value used as the result if a service result is None
    DEFAULT_RESULT = u'done'

    # List of required components (eg. ("netdesc", "config"))
    REQUIRES = tuple()

    # List of services used by the component in internal (without
    # user interaction). Format is a dictionary with:
    # component name => set of service names.Example to be able to use
    # config.getValue() and config.setValue(): ::
    #
    #    {'config': set(('getValue', 'setValue'))}
    #
    # inheritance: see Component.getAcls()
    ACLS = {}
    __acls = None

    # List of roles: role name => service names and role names (prefixed by '@').
    # Example:
    #
    #    {'ruleset_read': ('rulesetOpen', 'getAcls', 'rulesetClose'),
    #     'ruleset_write': ('@ruleset_read', 'setAcls', 'rulesetDelete')}
    ROLES = {}

    # Argument used for getLogger(domain)
    LOGGER_DOMAIN = None

    def __init__(self):
        self.name = self.NAME
        if not self.name:
            raise ValueError("Component name is not set")

        self._jinja_env = None
        self.TEMPLATE_PATH = None

        Logger.__init__(self, self.name, domain=self.LOGGER_DOMAIN)

        self.version = self.VERSION
        if not self.version:
            raise ValueError("Component version is not set")
        if not isinstance(self.version, str):
            raise ValueError("Component version is not a string")

        self.roles = self._createRoles()
        self.acls = self.getAcls()
        self.session = SessionStorage()

    def _createRoles(self):
        services_list = self.getServiceList()
        roles = {}
        references = {}
        class_roles = self.ROLES
        parents = getmro(self.__class__)[1:]
        for parent_class in parents:
            if not issubclass(parent_class, Component):
                continue
            for role, services in parent_class.ROLES.iteritems():
                if role in class_roles:
                    class_roles[role] |= services
                else:
                    class_roles[role] = services
        for role, mixed_services in class_roles.iteritems():
            role_references = set()
            services = []
            for service in mixed_services:
                if service.startswith("@"):
                    role_references.add(service[1:])
                elif not service in services_list.keys():
                    self.error("Role %r references an unexistent service %r" % (role, service))
                else:
                    services.append(service)
            roles[role] = services
            if role_references:
                references[role] = role_references

        while references:
            found = None
            for role, role_references in references.iteritems():
                for ref in role_references:
                    if ref in references:
                        continue
                    if ref not in roles:
                        raise ValueError("Broken reference in roles: %s" % ref)
                    found = (role, ref)
                    break
                if found:
                    break
            if not found:
                cycles = []
                for role, role_references in references.iteritems():
                    for ref in role_references:
                        cycles.append('%s=>%s' % (role, ref))
                raise ValueError("Cycle in role refences! %s" % ', '.join(cycles))
            role, ref = found
            roles[role] += roles[ref]
            references[role].remove(ref)
            if not references[role]:
                del references[role]
        return roles

    def init(self, core):
        self.TEMPLATE_PATH = core.conf_get_var_or_default('CORE','templatesdir', default='/usr/share/ufwi-rpcd/templates')
        self._jinja_env = jinja.Environment(loader=jinja.FileSystemLoader(self.TEMPLATE_PATH))

    def init_done(self):
        pass

    def destroy(self):
        pass

    def getMethods(self, prefix):
        services = {}
        for attrname in dir(self):
            if not attrname.startswith(prefix):
                continue
            attr = getattr(self, attrname)
            if not isinstance(attr, MethodType):
                continue
            name = attrname[len(prefix):]
            services[name] = attr
        return services

    def getServiceList(self):
        return self.getMethods("service_")

    def service_getComponentVersion(self, context):
        "Read component version string"
        return self.version

    @classmethod
    def getAcls(cls):
        """return ACLS for cls"""
        # A subclass of Component heritate of ACLS
        # group & store ACLS from cls to Component in __acls
        # compute only once
        if cls.__acls is None:
            cls.__acls = {}
            parents = getmro(cls)
            for parent_class in parents:
                if issubclass(parent_class, Component) and hasattr(parent_class, 'ACLS'):
                    parent_tags = getattr(parent_class, 'ACLS')
                    for component, services in parent_tags.iteritems():
                        if component not in cls.__acls:
                            cls.__acls[component] = services
                        else:
                            cls.__acls[component].update(services)

        return cls.__acls

    @classmethod
    def getRequires(cls):
        """return names of required modules for cls
        """
        return cls.getTag('REQUIRES', Component)

    @classmethod
    def getTag(cls, tag, top_cls):
        """return tags of modules cls. Search stop at top_cls level (included)

        tag must be uppercase
        """
        if not tag.isupper():
            raise ValueError("Tag '%s' must be uppercase" % unicode(tag))

        if not issubclass(cls, top_cls):
            return ValueError("'%s': '%s' is not subclass of '%s'" % (tag,
                unicode(cls), unicode(top_cls)))

        attr_name = '_%s' % tag.lower()
        # group & store tags from cls to top_cls in cls.attr_name
        # compute only once
        if not hasattr(cls, attr_name):
            setattr(cls, attr_name, set())
            attr = getattr(cls, attr_name)
            parents = getmro(cls)
            for parent_class in parents:
                if issubclass(parent_class, top_cls) and hasattr(parent_class, tag):
                    parent_tags = getattr(parent_class, tag)
                    attr.update(parent_tags)

        return getattr(cls, attr_name)

    # Only used with API_VERSION==1, replaced by checkServiceCall()
    def checkAcl(self, context, service_name):
        """
        Check if context allows to execute specified service: return True if
        the service call must be blocked, otherwise return False.
        """
        return True

    # New API (API_VERSION >= 2)
    def checkServiceCall(self, context, service_name):
        """
        Check if context allows to execute specified service: raise an error to
        block the service call, otherwise do nothing.
        """
        pass

    def checkRoles(self, roles, service_name):
        "Check if the roles are allowed to execute the specified service."
        for role in roles:
            if role not in self.roles:
                continue
            if service_name in self.roles[role]:
                return True
        return False

    def formatServiceArguments(self, service, arguments):
        arg_len = 150
        total_len = 400
        text = u''
        for argument in arguments:
            if text:
                text += u', '
            space = max(total_len - len(text), 0)
            space = min(space, arg_len)
            argument = humanRepr(argument, space)
            text += argument
            if total_len <= len(text):
                break
        return text

    def logService(self, context, logger, service, text):
        logger.info(context, text)

    def __repr__(self):
        return "<Component %r>" % self.name
    __str__ = __repr__

    def generateTemplates(self, template_variables, confFiles, prefix=''):
        """
        Renders files based on templates

         - template_variables : dictionnary containing templates variables / values.
         - confFiles : dictionnary containing as keys the destination filename of generated files.
                       The value for each entry is a tuple in the form (owner, mode, template_path)
                       where:
                            - owner is string in the form 'user:group'
                            - mode is string like '600'
                            - template_path a string pointing to the source template
         - prefix : log prefix
        """
        template_variables['_generation_time_'] = Component.timestamp()
        conf2tmp = []

        for dest in confFiles:
            fd, tmpfile = mkstemp()
            template_path = confFiles[dest][2]
            conf2tmp.append((template_path, dest, tmpfile))
            self.debug(
                "%sRendering %s in %s (%s)" %
                (prefix, template_path, dest, tmpfile)
                )
            try:
                tmpl = self._jinja_env.get_template(template_path)
                text = tmpl.render(template_variables)
                write(fd, text.encode('utf-8'))
                self.debug(
                    " %sRendering of %s in %s succeeded (%s)" %
                    (prefix, template_path, tmpfile, dest)
                    )
            except Exception:
                for item in conf2tmp:
                    unlink(item[2])
                raise
            finally:
                close(fd)

        # all conf files were generated
        try:
            for template_path, dest_path, tmp_path in conf2tmp:
                item = confFiles[dest_path]
                owner = item[0]
                mode = item[1]
                self.copy(tmp_path, dest_path, mode, owner, prefix)
        finally:
            for item in conf2tmp:
                unlink(item[2])

    def renderTemplate(
        self,
        template_path,
        template_variables,
        mode,
        owner,
        dest=None):
        """
        render one template
        """
        if dest is None:
            dest = template_path

        template_variables['_generation_time_'] = Component.timestamp()

        with NamedTemporaryFile() as temp_file:
            tmpl = self._jinja_env.get_template(template_path)
            text = tmpl.render(template_variables)
            temp_file.write(text.encode('utf-8'))
            temp_file.flush()
            fsync(temp_file.fileno())
            self.debug("Rendering of '%s' in '%s' succeeded (%s)" %
                (template_path, temp_file, dest))
            self.copy(temp_file.name, dest, mode, owner)

    def copy(self, src, dest, mode, owner, log_prefix=''):
        copy2(src, dest)
        chmod(dest, int(mode, 8))
        user, group = owner.split(":")
        self.chownWithNames(dest, user, group)
        self.debug("%s'%s' renamed: '%s'" % (log_prefix, src, dest))

    def chownWithNames(self, filename, user, group):
        if exists(filename):
            uid = getpwnam(user)[2]
            gid = getgrnam(group)[2]
            chown(filename, uid, gid)
        else:
            self.error("can not chown file '%s'" % filename)

    @staticmethod
    def timestamp():
        return unicode(datetime.fromtimestamp(time()))

