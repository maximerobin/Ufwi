# -*- coding: utf-8 -*-

# To work properly, this component depends on:
# - The PGP keyring, in gpg_homedir (defaults to
#   /var/lib/ufwi_rpcd/license/gpg).
# - An existing directory to contain license.db (defaults to
#   /var/lib/ufwi_rpcd/license).

# $Id$

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

import hashlib
import os
import re
import sqlite3
from StringIO import StringIO
from base64 import decodestring
from bz2 import decompress
from subprocess import PIPE

from ufwi_rpcd.backend.cron import scheduleDaily
from ufwi_rpcd.backend import tr
from ufwi_rpcd.backend.process import createProcess, runCommand
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.core.context import Context
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.backend.unix_service import runCommandAndCheck
from ufwi_conf.common.license import (DPI_OPTION_NAME, INDEX_OPTION,
                                   option_decode, WARN_DAYS)

from .error import (
    NuConfError,
    LICENSE_BAD_SIG,
    LICENSE_DPI_ACTIVATION_ERROR,
    LICENSE_GETID_ERROR,
    LICENSE_GET_LICENSES_ERROR,
    LICENSE_MISSING_FIELDS,
)

VPN_SUPPORT_DIR = '/etc/vpn-support'
CERTIFICATE_PATH = VPN_SUPPORT_DIR + '/support-cert.pem'
DEFAULT_LICENSE_DIR = '/var/lib/ufwi_rpcd/license'
DEFAULT_LICENSE_GPG_DIR = DEFAULT_LICENSE_DIR + '/gpg'
KEY_PATH = VPN_SUPPORT_DIR + '/support-key.pem'
MAIN_RE = re.compile(r'^[0-9]+u$')
MODEL_PATH = '/var/lib/ufwi_rpcd/license/model'
QOSMOS_LICENSE = "/usr/lib/qosmos/libfullafc.so"

_MAX_CLIENTS = {
"E120": 100,
"E230": 500,
"E260": 1000,
"E3200": 1500,
"E3400": 2500,
"E4300": 8000,
"E4500": 8000,
}
_DEFAULT_MAX_CLIENTS = 100

_NF_CONNTRACK_MAX = {
    "E120": 200000,  # (two hundred thousand)
    "E230": 4000000,  # (four million)
    "E260": 4000000,  # (four million)
    "E3200": 8000000,  # (eight million)
    "E3400": 8000000,  # (eight million)
    "E4300": 32000000,  # (thirty-two million)
    "E4500": 32000000,  # (thirty-two million)
}

class LicenseComponent(AbstractNuConfComponent):
    NAME = "license"
    VERSION = "1.0"

#    PIDFILE = "/var/run/..."
#    EXE_NAME = "..."

    #INIT_SCRIPT = "..."

    ACLS = {
        'acl': set(('getMinimalMode', 'setMinimalMode',
                    'setMinimalModeServices')),
        'contact': set(('sendMailToAdmin',)),
    }

    REQUIRES = ('contact',)

    ROLES = {
        'conf_read': set((
                'checkValidity',
                'getID',
                'getModelAndID',
                'getLicensesExpiredIn',
                'getLicenseInfo',
                'getValidLicenses',
                "needNucentralRestart",
                )),
        'conf_write': set(('sendLicense',)),
        'multisite_read': set(('@conf_read',)),
        'multisite_write': set(('@conf_write',)),
    }

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        self.core = core
        self.license_dir = DEFAULT_LICENSE_DIR
        self.gpg_homedir = DEFAULT_LICENSE_GPG_DIR
        try:
            self.license_dir = self.core.config.get('license', 'license_dir')
            self.gpg_homedir = self.core.config.get('license', 'gpg_homedir')
        except Exception, err:
            self.error("Missing or incorrect 'license' configuration in /etc "
                       "Rpcd configuration file (%s)." %
                       exceptionAsUnicode(err))
        if not os.path.exists(self.license_dir):
            self.error(
                "The activation key directory `%s' did not exist.  Creating it." %
                self.license_dir)
            try:
                os.mkdir(self.license_dir)
            except OSError, err:
                self.error(
                    "Could not create the activation key directory `%s': %s" %
                    (self.license_dir, err))
        if not os.path.exists(self.gpg_homedir):
            self.error(
                "The activation key public keyring directory `%s' does not exist.  You will not be able to register any activation key."
                % self.gpg_homedir)
        self.addConfFile('/etc/sysctl.d/nf_conntrack_max.conf', 'root:root', '0644')
        self.addConfFile('/etc/default/mpt-statusd', 'root:root', '0644')
        self.init_db()
        self.need_ufwi_rpcd_restart = False
        component_context = Context.fromComponent(self)
        defer = self.core.callService(component_context, 'acl',
            'setMinimalModeServices', 'license',
            ['checkValidity', 'getID', 'getValidLicenses', 'sendLicense'])
        defer.addCallback(lambda x: self.core.callService(component_context,
            'acl', 'setMinimalModeServices', 'contact', ['sendMailToAdmin']))
        defer.addCallback(lambda x: self.core.callService(component_context,
            'acl', 'setMinimalModeServices', 'resolv', ['getDomain']))
        defer.addCallback(lambda x: self.core.callService(component_context,
            'acl', 'setMinimalModeServices', 'hostname', ['getShortHostname']))
        defer.addCallback(self.check_validity)
        defer.addErrback(self.writeError)
        scheduleDaily(6, 15, self.warn_if_expire_soon)

    def createSubscriptions(self):
        """
        Override the default implementation.
        We don't need 'em subscriptions
        """
        return

    def read_config(self, *args, **kwargs):
        # nothing to do
        pass

    # Methods for our database:

    def connect_db(self):
        self.db = sqlite3.connect(os.path.join(self.license_dir,
                                               'licenses.db'))
        return self.db.cursor()
    def disconnect_db(self, commit=True):
        try:
            if not self.db:
                return
        except AttributeError:
            pass
        if commit:
            self.db.commit()
        self.db.close()
    def init_db(self):
        """The database holds one license per entry (an entry may have several
        options."""

        try:
            cursor = self.connect_db()
            cursor.execute('CREATE TABLE IF NOT EXISTS licenses (hexdigest TEXT PRIMARY KEY, owner TEXT, validity TEXT, option TEXT, end_date DATE, upload_date DATE)')
            self.disconnect_db()
        except Exception, err:
            self.error(u'Could not connect to (nor create) the activation keys database: %s' % err)

    # Methods used by services:

    def check_license_sig(self, filename):
        p = createProcess(self,
                ('/usr/bin/gpg', '--homedir', self.gpg_homedir, filename),
                stderr=PIPE, locale=False)
        retcode = p.wait()
        if retcode != 0:
            raise NuConfError(LICENSE_BAD_SIG,
                              'Bad signature for activation key.')

    def check_validity(self, unused=None):
        try:
            licenses = self.get_valid_licenses()
        except NuConfError, err:
            licenses = []
            self.error('Could not list the valid activation keys: %s' % err)
        def has_main_license():
            for license in licenses:
                if self.is_main_license(license, INDEX_OPTION):
                    return True
            return False
        if has_main_license():
            minimal_mode = False
        else:
            minimal_mode = True

        component_context = Context.fromComponent(self)
        defer = self.core.callService(component_context, 'acl',
                                      'setMinimalMode', minimal_mode)
        defer.addErrback(self.writeError)
        return not minimal_mode

    def get_id(self, padding=True):
        """Return this appliance unique identifier"""
        try:
            p = createProcess(self, ("ifconfig", "eth0"),
                    stdout=PIPE, locale=False)
            line = p.stdout.readline()
            retcode = p.wait()
            if retcode != 0:
                raise NuConfError(
                    LICENSE_GETID_ERROR,
                    tr('Could not get the unique identifier.'))

            fields = line.strip().split()
            id_str = fields[4].replace(':', '')
            if padding:
                return "%015d" % int(id_str, 16)
            else:
                return "%d" % int(id_str, 16)
        except:
            raise NuConfError(
                LICENSE_GETID_ERROR,
                tr('Could not get the unique identifier.'))

    def get_licenses_expired_in(self, days):
        cursor = self.connect_db()
        cursor.execute("SELECT option FROM licenses WHERE end_date != '' AND end_date = date('now', '+%d days')" % int(days))
        licenses = cursor.fetchall()
        self.disconnect_db()
        return licenses

    def get_model(self):
        try:
            with open(MODEL_PATH) as fd:
                line = fd.readline()
                if line:
                    return line.strip()
                else:
                    raise ValueError('Empty file.')
        except IOError:
            self.info('No EdenWall model file.  Using the default value.')
        except Exception, err:
            self.error('Cannot read EdenWall model: %s' % err)
        return ''

    def __get_max_clients(self):
        model = self.get_model()
        max_clients = _MAX_CLIENTS.get(model, _DEFAULT_MAX_CLIENTS)
        return max_clients

    def get_owner(self):
        cursor = self.connect_db()
        cursor.execute("SELECT end_date, option, owner FROM licenses WHERE end_date = '' OR end_date >= date('now') ORDER BY end_date")
        licenses = cursor.fetchall()
        self.disconnect_db()
        (end_date_index, option_index, owner_index) = (0, 1, 2)

        licenses = [license for license in licenses if
                    self.is_main_license(license, option_index)]
        if not licenses:
            return ''

        if not licenses[0][end_date_index]:  # Unlimited.
            return licenses[0][owner_index]

        return licenses[-1][owner_index]

    def get_valid_licenses(self):
        try:
            cursor = self.connect_db()
            cursor.execute("SELECT owner, end_date, COALESCE(CAST(julianday(end_date) - julianday('now') AS integer), '') AS days, option FROM licenses WHERE end_date = '' OR end_date >= date('now')")
            licenses = cursor.fetchall()
            self.disconnect_db()
            return licenses
        except:
            raise NuConfError(LICENSE_GET_LICENSES_ERROR,
                              tr('Could not list the installed activation keys.'))

    def is_main_license(self, license, index):
        options = license[index].split()
        for option in options:
            return bool(MAIN_RE.search(option))

    def _activate_dpi(self, qosmos_license_bz2):
        # Install Qosmos license.
        dir_name = os.path.dirname(QOSMOS_LICENSE)
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
        with open(QOSMOS_LICENSE, "w") as fd:
            qosmos_license = decompress(decodestring(qosmos_license_bz2))
            fd.write(qosmos_license)
            self.info("Installed Qosmos license.")
        # Enable nudpi component (will be available after next ufwi_rpcd
        # restart).
        try:
            dest = "/var/lib/ufwi_rpcd/mods-enabled/nudpi"
            if os.path.exists(dest):
                self.debug("The DPI configuration module seems "
                           "to be already activated.")
            else:
                os.symlink("/var/lib/ufwi_rpcd/mods-available/nudpi", dest)
                self.info("Activated DPI configuration module.")
        except OSError, err:
            self.error("Could not create DPI symbolic link (%s)." % err)
            raise NuConfError(LICENSE_DPI_ACTIVATION_ERROR, tr(
                    "Could not activate DPI configuration module."))
        return True

    def _handle_single_license(self, context, license_text):
        if not license_text:
            return True
        # do nothing if this license has already been registered:
        hexdigest = self._hexdigest(license_text)
        filename = os.path.join(self.license_dir, hexdigest)
        filename_gpg = '%s.gpg' % filename
        already_registered = os.path.exists(filename_gpg)

        if not already_registered:
            # Write the file on disk to mark it as already registered.
            fd = open(filename_gpg, 'w+b')
            fd.write(license_text)
            fd.close()
        try:
            self.check_license_sig(filename_gpg)
            license = self._parse_license(filename, hexdigest)
            identifiers = license['Identifiers'].split()
            if not (license['Identifiers'] == 'any' or
                    self.get_id() in identifiers or
                    self.get_id(padding=False) in identifiers):
                return False
            # Register the license in the database.
            self._register_license(license, already_registered)
            if not already_registered:
                try:
                    self._write_certificate_and_key(license)
                except Exception, err:
                    self.critical(
                        'Could not copy VPN support certificate and/or key (%s).',
                        err)
                model = self._write_model(license)
                self._update_sysctl_nf_conntrack_max(model)
                self._update_default_mpt_statusd(model)
        except:
            if os.path.exists(filename_gpg):
                os.unlink(filename_gpg)
            raise
        finally:
            if os.path.exists(filename):
                os.unlink(filename)

        # NuDPI
        qosmos_license = license.get("Qosmos", "")
        try:
            if qosmos_license:
                self._activate_dpi(qosmos_license)
                self.need_ufwi_rpcd_restart = True
        except NuConfError:
            raise
        except Exception, err:
            self.critical("Could not activate DPI (%s)." % err)
            raise NuConfError(LICENSE_DPI_ACTIVATION_ERROR,
                              'Could not activate DPI.')

        return bool(qosmos_license) or not already_registered


    def _hexdigest(self, content):
        hash = hashlib.sha256()
        hash.update(content)
        return hash.hexdigest()

    def _parse_license(self, filename, hexdigest):
        license = {
            "Identifiers": None,
            "Owner": None,
            "Validity": None,
            "Option": [],
        }
        optional_fields = {
            'Certificate': None,
            'Key': None,
            'Model': '',
            'Qosmos': None,
        }
        fd = open(filename)
        for line in fd:
            try:
                key, value = line.split(' ', 1)
            except ValueError:
                continue
            key = key[:-1]
            if key == 'Identifier':
                key = 'Identifiers'
            elif key == "Option":
                license['Option'].append(value.strip())
                continue
            elif key == "Qosmos":
                license["Qosmos"] = license.get("Qosmos", "") + value.strip()
                continue
            if key in license or key in optional_fields:
                license[key] = value.strip()
        fd.close()
        if license['Option']:
            license['Option'] = ' '.join(license['Option'])
        else:
            license['Option'] = ''
        missing_fields = [key for key in license.keys() if license[key] is
                          None]
        if license.get('Key', '') and not license.get('Certificate', ''):
            missing_fields.append('Certificate')
        if missing_fields:
            raise NuConfError(
                LICENSE_MISSING_FIELDS,
                tr("There are missing fields in the license: "),
                ', '.join(missing_fields))
        license['hexdigest'] = hexdigest
        return license

    def _register_license(self, license, already_registered=False):
        if "Qosmos" in license:
            license["Option"] += " " + DPI_OPTION_NAME
        cursor = self.connect_db()
        if already_registered:
            cursor.execute("UPDATE licenses SET option = ? WHERE hexdigest=?",
                           (license['Option'], license['hexdigest']))
            self.disconnect_db()
            return
        if license['Validity'] == 'unlimited':
            cursor.execute(
                "INSERT INTO licenses VALUES (?, ?, 'unlimited', ?, '', date('now'))",
                (license['hexdigest'], license['Owner'], license['Option'])
            )
            self.disconnect_db()
            return
        try:
            days = int(license['Validity'])
            cursor.execute(
                "INSERT INTO licenses VALUES (?, ?, ?, ?, date('now', '%d days'), date('now'))" % days,
                (license['hexdigest'], license['Owner'], license['Validity'],
                 license['Option'])
            )
        except ValueError:
            cursor.execute(
                "INSERT INTO licenses VALUES (?, ?, ?, ?, ?, date('now'))",
                (license['hexdigest'], license['Owner'], license['Validity'],
                 license['Option'], license['Validity'])
            )
        finally:
            self.disconnect_db()

    def _iter_licenses(self, decoded_content):
        text = ''
        for line in StringIO(decoded_content):
            text += line
            if line.startswith('-----END PGP SIGNATURE-----'):
                yield text
                text = ''
        yield text

    def _update_sysctl_nf_conntrack_max(self, model):
        nf_conntrack_max = _NF_CONNTRACK_MAX.get(model, 0)
        if nf_conntrack_max > 0:
            self.generate_configfile({"nf_conntrack_max": nf_conntrack_max},
                                     ("/etc/sysctl.d/nf_conntrack_max.conf",))
            try:
                runCommandAndCheck(self, ["sysctl", "-w",
                                          "net.netfilter.nf_conntrack_max=%d"
                                          % nf_conntrack_max])
            except Exception:
                self.critical(
                    "Error while setting the maximum number of simultaneous connexions.")

    def _update_default_mpt_statusd(self, model):
        if model.startswith("E4"):  # Enable then start.
            run_mpt_statusd = "yes"
            self.generate_configfile({"run_mpt_statusd": run_mpt_statusd},
                                     ("/etc/default/mpt-statusd",))
            try:
                runCommandAndCheck(self, ["/etc/init.d/mpt-statusd", "start"])
            except Exception:
                self.critical(
                    "Error while starting the RAID status monitor.")
        else:  # Stop then disable.
            run_mpt_statusd = "no"
            try:
                runCommandAndCheck(self, ["/etc/init.d/mpt-statusd", "stop"])
            except Exception:
                self.error(
                    "Error while stopping the RAID status monitor.")
            self.generate_configfile({"run_mpt_statusd": run_mpt_statusd},
                                     ("/etc/default/mpt-statusd",))

    def warn_if_expire_soon(self):
        context = Context.fromComponent(self)
        if not self.check_validity():
            message = tr("Warning: your EdenWall appliance does not have a valid license.")
            self.core.callService(context, 'contact', 'sendMailToAdmin',
                                  message, message)

        body = ''
        licenses = self.get_licenses_expired_in(WARN_DAYS)
        for license in licenses:
            for option in license[0].split():
                body += tr("Your activation key for ") + option_decode(option) + \
                    tr(" will expire in less than") + " %d " % WARN_DAYS + \
                    tr("days") + '.\n\n'
        if body:
            self.core.callService(
                context, 'contact', 'sendMailToAdmin',
                tr('Activation key expiration in less than') + ' %d ' % WARN_DAYS +
                tr('days'), body)

    def _write_certificate_and_key(self, license):
        def write_lines(fd, text, chunk_size):
            text_buffer = StringIO(text)
            while True:
                chunk = text_buffer.read(chunk_size)
                if not chunk:
                    break
                fd.write(chunk)
                fd.write('\n')
        if not ('Certificate' in license and 'Key' in license):
            return False
        if not os.path.exists(VPN_SUPPORT_DIR):
            os.mkdir(VPN_SUPPORT_DIR)
            os.chmod(VPN_SUPPORT_DIR, 0775)
        with open(CERTIFICATE_PATH, 'w') as fd:
            fd.write('-----BEGIN CERTIFICATE-----\n')
            write_lines(fd, license['Certificate'], 64)
            fd.write('-----END CERTIFICATE-----\n')
        with open(KEY_PATH, 'w') as fd:
            os.chmod(KEY_PATH, 0600)
            fd.write('-----BEGIN RSA PRIVATE KEY-----\n')
            write_lines(fd, license['Key'], 64)
            fd.write('-----END RSA PRIVATE KEY-----\n')
        return True

    def _write_model(self, license):
        model = license.get('Model', '')
        if model:
            with open(MODEL_PATH, 'w') as fd:
                fd.write(unicode(model) + '\n')
            runCommand(self, ['/usr/bin/killall', 'edenserial'])
        return model


    # Services:

    def service_checkValidity(self, context):
        return self.check_validity()

    def service_getID(self, context):
        """Return this appliance unique identifier"""
        return self.get_id()

    def service_getModelAndID(self, context):
        """Return this appliance model name and unique identifier"""
        model = self.get_model()
        ID = self.get_id()
        return (model, ID)

    def service_getLicenseInfo(self, context):
        """Return a dict containing this appliance model name, ID and owner
        """
        model = self.get_model()
        ID = self.get_id()
        owner = self.get_owner()
        return {'model': model, 'ID': ID, 'owner': owner}

    def service_getLicensesExpiredIn(self, context, days):
        """Return the option field of licenses which will expire in exactly
        the given number of days."""
        return self.get_licenses_expired_in(days)

    def service_getValidLicenses(self, context):
        """Return the list of valid licenses"""
        return self.get_valid_licenses()

    def service_sendLicense(self, context, encoded_bin):
        decoded_content = decodeFileContent(encoded_bin)
        found_license_for_me = False
        for license_text in self._iter_licenses(decoded_content):
            if self._handle_single_license(context, license_text):
                found_license_for_me = True
        self.check_validity()
        return found_license_for_me

    def service_getMaxClients(self, context):
        return self.__get_max_clients()

    def service_needNucentralRestart(self, context):
        return self.need_ufwi_rpcd_restart

