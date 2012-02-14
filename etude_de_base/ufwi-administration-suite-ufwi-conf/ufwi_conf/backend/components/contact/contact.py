#coding: utf-8

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


from __future__ import with_statement

from email.mime.text import MIMEText
from twisted.internet.defer import inlineCallbacks
from twisted.mail.smtp import sendmail
import jinja
import os

from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.common import version
from ufwi_rpcd.common.validators import check_mail
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.contact_cfg import ContactConf

from .error import CONTACT_INVALID_CONFIGURATION
from .error import CONTACT_INVALID_RECIPIENT
from .error import CONTACT_INVALID_SENDER
from .error import NuConfError

#contact only templates:
GENFILE_ALIASES = '/etc/aliases'
# * admin_mail

GENFILE_EMAIL_ADDRESSES = '/etc/email-addresses'
# * sender_mail

class ContactComponent(AbstractNuConfComponent):
    """
    Component to manage admin mail address
    """
    #apply_config is inherited

    NAME = 'contact'
    VERSION = '1.0'

    REQUIRES = ('config', 'resolv', 'hostname', 'ufwi_conf')
    if version == "PRO":
        REQUIRES += ('exim',)
    # Don't depend on license to avoid a depency cycle...
    #REQUIRES = ('config', 'resolv', 'hostname', 'license')

    ACLS = {
        'hostname': frozenset(('getShortHostname',)),
        'license': frozenset(('getID',)),
        'resolv': frozenset(('getDomain',)),
        'exim': frozenset(('getrelayed',)),
    }

    ROLES = {
        'conf_read': set(('getContactConfig',)),
        'conf_write': set((
                '@conf_read',
                'sendMailToAdmin',
                'sendTestMail',
                'setContactConfig',
        )),
    }

    CONFIG_DEPENDS = ()

    def __init__(self):
        AbstractNuConfComponent.__init__(self)
        self.config = None

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        self.body_template = self.read_body_template()
        for genfile in (
            GENFILE_ALIASES,
            GENFILE_EMAIL_ADDRESSES
            ):
            self.addConfFile(genfile, 'root:root', '0644')

    def checkServiceCall(self, context, service_name):
        if 'sendMailToAdmin' == service_name:
            # lock is not needed when sending an email
            return
        return AbstractNuConfComponent.checkServiceCall(self, context, service_name)

    def read_body_template(self):
        try:
            filename = os.path.join(
                self.core.config.get('contact', 'body_templates_path'),
                self.config.language)
            return open(filename).read()

        except:
            return '{{body}}\n'

    def read_config(self, *args, **kwargs):
        self.config = ContactConf.defaultConf()
        try:
            serialized = self.core.config_manager.get(self.NAME)
        except ConfigError:
            self.debug("Not configured, defaults loaded.")
            return

        valid, message = self._setconfig(serialized)
        if not valid:
            self.error(
                "This means that the configuration is incorrect or that there is a bug"
                )

    def _setconfig(self, serialized):
        # TODO: factorize with exim component _setconfig (and maybe other modules)
        config = ContactConf.deserialize(serialized)

        valid, error = config.isValidWithMsg()
        if valid:
            self.config = config
        else:
            self.error(
                "Component %s read incorrect values. Message was: %s" % (self.NAME, error)
                )
        return valid, error

    def apply_config(self, responsible, arg, modified_paths):
        return self.genConfigFiles(responsible)

    @inlineCallbacks
    def genConfigFiles(self, responsible):
        template_variables = self.config.serialize()
        yield self.generate_configfile(template_variables)

    def should_run(self, responsible):
        #inconditionnal True
        return True

    def save_config(self, message, context=None):
        serialized = self.config.serialize()
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.NAME)
            except ConfigError:
                pass

            cm.set(self.NAME, serialized)
            cm.commit(message)

    def verify_config(self):
        pass

    # Services
    def service_getContactConfig(self, context):
        return self.config.serialize()

    def service_setContactConfig(self, context, serialized, message):
        valid, error = self._setconfig(serialized)
        if not valid:
            raise NuConfError(
                CONTACT_INVALID_CONFIGURATION,
                "'%s' failed : '%s'" % (valid, error)
                )

        self.save_config(message, context)

    def service_sendMailToAdmin(self, context, subject, body):
        return self.sendMailToAdmin(subject, body)

    def service_sendTestMail(self, context, sender=None, recipient=None):
        """
        Send a test email. If sender and/or recipient are not specified, values
        of current configuration will be used.
        """

        if sender is None:
            sender = self.config.sender_mail
        else:
            sender = sender.strip()

        if recipient is None:
            recipient = self.config.admin_mail
        else:
            recipient = recipient.strip()

        # TODO fr / en
        # add fqdn
        msg_text = u"""Bonjour,
Ce message de test a été envoyé depuis l'interface d'administration
d'EdenWall. Si vous l'avez reçu, cela confirme que la configuration
en place au moment de l'envoi vous permet de recevoir les messages
système (alertes et informations) de votre pare-feu EdenWall."""
        if context.isUserContext():
            session = context.getSession()
            msg_text += u"\n\nL'envoi ce de message a été déclenché par une action utilisateur.\nInformations de traçage: %s\n" % (session,)

        msg = MIMEText(msg_text.encode('ISO-8859-1'), 'plain', 'ISO-8859-1')
        msg['Subject'] = 'EdenWall : test mail'

        if check_mail(sender):
            msg['From'] = sender
        else:
            raise NuConfError(CONTACT_INVALID_SENDER, "'sender' e-mail : invalid e-mail address")

        if check_mail(recipient):
            msg["To"] = recipient
        else:
            raise NuConfError(CONTACT_INVALID_RECIPIENT, "'recipient' e-mail : invalid e-mail address")

        return self.sendTestMail('127.0.0.1', msg['From'], [msg['To']], msg.as_string())

    # Services

    def _addMyDomain(self, my_domain, template_variables):
        template_variables['my_domain'] = my_domain
    def _addMyHostname(self, my_hostname, template_variables):
        template_variables['my_hostname'] = my_hostname
    def _addMyID(self, my_id, template_variables):
        template_variables['my_id'] = my_id

    def sendMailToAdmin(self, subject, body):
        template_variables = {'body': body, 'subject': subject}
        context = Context.fromComponent(self)
        defer = self.core.callService(context, 'resolv', 'getDomain')
        defer.addCallback(self._addMyDomain, template_variables)
        defer.addCallback(lambda x: self.core.callService(context, 'hostname',
                                                          'getShortHostname'))
        defer.addCallback(self._addMyHostname, template_variables)
        defer.addCallback(lambda x: self.core.callService(context, 'license',
                                                          'getID'))
        defer.addCallback(self._addMyID, template_variables)
        defer.addCallback(self.sendMailToAdmin_cb, template_variables)
        return defer

    def sendMailToAdmin_cb(self, unused, template_variables):
        template_variables['my_fqdn'] = '%s.%s' % (
            template_variables['my_hostname'],
            template_variables['my_domain'])
        jinja_env = jinja.Environment()
        template = jinja_env.from_string(self.body_template)
        rendered_body = unicode(template.render(**template_variables))
        msg = MIMEText(rendered_body.encode('utf-8'), 'plain', 'utf-8')
        msg['Subject'] = u'[EW4 %s] %s' % (
            template_variables['my_hostname'],
            unicode(template_variables['subject']))
        sender = self.config.sender_mail
        if check_mail(sender):
            msg['From'] = sender
        else:
            raise NuConfError(CONTACT_INVALID_SENDER,
                              tr("'sender' e-mail : invalid e-mail address"))
        recipient = self.config.admin_mail
        if check_mail(recipient):
            msg['To'] = recipient
        else:
            raise NuConfError(CONTACT_INVALID_RECIPIENT,
                    tr("'recipient' e-mail : invalid e-mail address"))
        defer = sendmail('127.0.0.1', sender, recipient, msg.as_string())
        defer.addCallback(self.logSuccess)
        return defer

    def sendTestMail(self, server, sender, recipient, msg):
        defer = sendmail(server, sender, recipient, msg)
        defer.addCallback(self.logSuccess)
        return defer

    def logSuccess(self, result):
        # (nb, ((address, code_ret, status), ...)
        self.info("Successfully sent mail to '%s'." % result[1][0][0])

