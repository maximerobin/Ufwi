#coding: utf-8
"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Francois Toussenel <ftoussenel AT inl.fr>

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

from logging import ERROR, CRITICAL
import os
import re
from sgmllib import SGMLParser
import shutil
import socket
import sqlite3
import subprocess
import time
from twisted.internet.defer import inlineCallbacks, returnValue
from twisted.internet.threads import deferToThread
from urllib2 import build_opener, ProxyHandler, HTTPError, URLError

from ufwi_rpcd.backend.cron import scheduleDaily
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend import tr
from ufwi_rpcd.common.download import decodeFileContent
from ufwi_rpcd.common.error import exceptionAsUnicode
from ufwi_rpcd.common.process import createProcess
from ufwi_rpcd.common.service_status_values import ServiceStatusValues
from ufwi_rpcd.core.context import Context
from ufwi_rpcd.core.lock import LockError
from ufwi_conf.backend.ufwi_conf_component import AbstractNuConfComponent
from ufwi_conf.common.httpout_cfg import HttpOutConf
from ufwi_conf.common.update_cfg import UpdateCfg
from ufwi_conf.common.update import (
    UPGRADE_RESTART_NEED_NAMES, UPGRADE_STATUS_DEPENDENCIES_MISSING,
    UPGRADE_STATUS_FAILED, UPGRADE_STATUS_IN_PROGRESS,
    UPGRADE_STATUS_NEED_RESTART, UPGRADE_STATUS_NEW,
    UPGRADE_PREFIX, UPGRADE_RE,
    upgrade_number)

from .error import (NuConfError,
    UPDATE_ALREADY_APPLIED,
    UPDATE_ALREADY_APPLIED_OR_DELETED,
    UPDATE_BLACKLISTED,
    UPDATE_CANNOT_APPLY_BECAUSE_DEPEND_NOT_APPLIED,
    UPDATE_NOT_CONFIGURED,
    UPDATE_NO_UPGRADE_NUMBER,
    UPDATE_REMOTE_DIRECTORY_NOT_FOUND,
    UPDATE_REMOTE_UPGRADE_NOT_FOUND,
    UPDATE_WRONG_TARGET_TYPE)
from .unpack_check import extract_restart_needs
from .unpack_check import main as unpack_check

RESTART_RPCD = '/dev/shm/restart_ufwi_rpcd'
RESTART_SYSTEM = '/dev/shm/restart_system'
UPDATE_LOCK = 'applyUpdate'
UPDATE_APPLIED = 'applied'
UPDATE_LOCK_MESSAGE = tr('An upgrade is already being applied or upgrades are being downloaded.')
RPCD_SERVER_UPDATE_LOCK = "/var/lock/ufwi_rpcd-server-update.lock"
UPDATE_RPCD_STARTED_SINCE_REBOOT_FLAG = \
    '/dev/shm/update_ufwi_rpcd_started_since_reboot.flag'
NEEDS2FLAG_FILENAMES = {
    'ufwi_rpcd': RESTART_RPCD,
    'system': RESTART_SYSTEM,
}
MODEL_PATH = '/var/lib/ufwi_rpcd/license/model'

# Database indexes:
(UPLOADED_NUM, UPLOADED_DATE, UPLOADED_CHANGELOG, UPLOADED_DEPENDS,
 UPLOADED_STATUS, UPLOADED_MISSING) = range(6)
(HISTORY_ID, HISTORY_NUM, HISTORY_UPLOAD_DATE, HISTORY_CHANGELOG,
 HISTORY_DEPENDS, HISTORY_SUCCEEDED, HISTORY_APPLY_DATE, HISTORY_APPLY_USER
 ) = range(8)

def _depends_list_to_str(depends_list):
    """Convert an integer list into a string starting with ' ' and ending
    with ' '; the numbers are separated with ' ' too.  Thus one can use
    "WHERE missing LIKE '% 12 %'" to test if upgrade 12 is missing."""
    return ' ' + ' '.join([str(i) for i in depends_list]) + ' '

def _str_to_depends_list(s):
    """Convert a "depends list string" back to an integer list."""
    return [int(num) for num in s.split()]

def commit_close(db):
    db.commit()
    db.close()

def now():
    return time.strftime('%Y-%m-%d %H:%M:%S', time.localtime())

def to_result(succeeded):
    if succeeded:
        return "success"
    return "failure"

class UpgradeSGMLParser(SGMLParser):
    def __init__(self, resource):
        SGMLParser.__init__(self)
        self.upgrade_list = []
        self.feed(resource)
        self.close()

    def start_a(self, attributes):
        for name, value in attributes:
            if name != 'href':
                return
            m = UPGRADE_RE.search(value)
            if m:
                self.upgrade_list.append(int(m.group(1)))

    def getUpgradeList(self):
        return self.upgrade_list

class UpdateComponent(AbstractNuConfComponent):
    NAME = "update"
    VERSION = "2.0"
    MASTER_KEY = NAME

    ACLS = {
        'contact': set(('sendMailToAdmin',)),
        'update': set(('downloadNewUpgrades', 'uploadedUpgrades',
                       'warnNewUpgrades')),
    }

    REQUIRES = ('contact',)

    CONFIG_DEPENDS = frozenset(('httpout',))

    ROLES = {
        'conf_read': set((
                'getAppliedList',
                'getBlacklist',
                'getBlacklistedAndPresent',
                'getDownloadProgress',
                'getHighestApplied',
                'getKnownUpgradeNums',
                'getUpdateConfig',
                'history',
                'needRestart',
                'uploadedUpgrades')),
        'conf_write': set((
                'applyAll',
                'applyUpgrades',
                'checkConfiguration',
                'deleteUpgradeArchives',
                'downloadNewUpgrades',
                'saveConfiguration',
                'sendUpgradeArchive',
                'setUpdateConfig',
                'warnNewUpgrades',
        )),
        'multisite_read': set(('@conf_read',)),
        'multisite_write': set(('@ufwi_conf_write',)),
    }

    def __init__(self):
        AbstractNuConfComponent.__init__(self)
        self.values = {}
        self.update_cfg = None
        self._modified = False

    def checkServiceCall(self, context, service_name):
        # warnNewUpgrades calls only uploadedUpgrades which is read only
        # and downloadNewUpgrades which has its own lock
        if not service_name in ['downloadNewUpgrades', 'warnNewUpgrades']:
            AbstractNuConfComponent.checkServiceCall(self, context, service_name)

    def init(self, core):
        AbstractNuConfComponent.init(self, core)
        self.core = core
        self.lock = None
        try:
            self.main_server = self.core.config.get('update', 'main_server')
        except:
            self.main_server = None

        try:
            self.update_dir = self.core.config.get('update', 'update_dir')
            self.upgrades_dir = self.core.config.get('update', 'upgrades_dir')
            self.gpg_homedir = self.core.config.get('update', 'gpg_homedir')
            try:
                self.timeout = float(self.core.config.get('update',
                                                          'timeout'))
            except Exception:
                self.warning("Download timeout set to 30 seconds (default)")
                self.timeout = 30
        except Exception, err:
            raise NuConfError(UPDATE_NOT_CONFIGURED,
                tr("Missing or incorrect 'update' configuration in /etc "
                   "Rpcd configuration file, disabling module 'update' (%s)"),
                exceptionAsUnicode(err))
        if not os.path.exists(self.update_dir):
            self.info(
                "The update directory `%s' did not exist.  Creating it." %
                self.update_dir)
            try:
                os.mkdir(self.update_dir)
            except OSError, err:
                self.writeError(err,
                    "Could not create the update directory `%s'" % self.update_dir,
                    log_level=CRITICAL)
        self.update_after_restart = os.path.join(
            self.update_dir, 'after_restart')
        try:
            if not os.path.exists(self.update_after_restart):
                os.mkdir(self.update_after_restart)
        except OSError, err:
            self.writeError(err,
                "Could not create a directory necessary for update, `%s'"
                % self.update_after_restart,
                log_level=CRITICAL)
        self.applying_flag_fn = os.path.join(self.update_dir, 'applying_num')
        self.blacklist_filename = os.path.join(self.update_dir, 'blacklist')
        self.upgrade_log_filename = os.path.join(self.update_dir,
                                                 'upgrade.log')
        try:
            self.max_upgrade_log_files = int(self.core.config.get(
                    'update', 'max_upgrade_log_files'))
        except Exception:
            self.max_upgrade_log_files = 10
        self.init_db_uploaded()
        self.init_db_history()
        self.files_to_download_count = 0
        self.downloaded_files_count = 0
        self.downloading = 0
        self.downloading_error = ''

        scheduleDaily(6, 20, self.callWarnNewUpgrades)
        self.check()
        try:
            # An upgrade application may have been interrupted, in case of
            # power failure, for instance.
            self.warn_interrupted_upgrade()
        except Exception:
            self.error("Error: Could not send a warning e-mail about "
                       "an interrupted upgrade application.")

        self.update_software_version()

    def update_software_version(self):
        try:
            with open('/etc/ew_version') as fp:
                line = fp.readline()
        except IOError, err:
            self.warning("Unable to open software version file: %s" % err)
            return
        version = line.rstrip()

        if not version.endswith('R'):
            return
        version = version[:-1]
        try:
            with open('/etc/ew_version', 'w') as fp:
                print >>fp, version
        except IOError, err:
            self.warning("Unable to update software version file: %s" % err)
            return

    def init_done(self):
        # Has the system been rebooted?
        just_rebooted = not os.path.exists(
            UPDATE_RPCD_STARTED_SINCE_REBOOT_FLAG)
        try:
            with open(UPDATE_RPCD_STARTED_SINCE_REBOOT_FLAG, 'w'):
                pass
        except Exception, err:
            self.writeError(err,
                'Could not mark the system as restarted',
                log_level=CRITICAL)
        # Register upgrades which needed a system_reboot:
        try:
            if just_rebooted:
                self._register_upgrades_after_restart('system')
            else:
                self._register_upgrades_after_restart('ufwi_rpcd')
        except Exception, err:
            self.writeError(err,
                'Could not register upgrades after restart',
                log_level=ERROR)

    def _register_upgrades_after_restart(self, subsystem):
        db_uploaded = self._connect_uploaded()
        cursor_uploaded = db_uploaded.cursor()
        cursor_uploaded.execute(
            "SELECT num FROM uploaded WHERE status = ?",
            (UPGRADE_STATUS_NEED_RESTART,))
        need_restart_nums = [row[0] for row in cursor_uploaded.fetchall()]
        commit_close(db_uploaded)
        for num in need_restart_nums:
            if not self._unregister_after_restart(num, subsystem):
                self._register_applied_now(num)

    def _unregister_after_restart(self, num, subsystem):
        """Unregister after restart of the subsystem and return the remaining
        restart needs.
        """
        filename = os.path.join(self.update_after_restart, str(num))
        if not os.path.exists(filename):
            return []
        if subsystem == 'system':
            try:
                os.unlink(filename)
            except Exception, err:
                self.writeError(err,
                    'Could not delete restart needs file for upgrade %s' % num,
                    log_level=CRITICAL)
            return []
        try:
            with open(filename) as fd:
                needs = [need.strip() for need in fd.readlines()]
        except Exception, err:
            self.writeError(err,
                'Could not read restart needs for upgrade %s' % num,
                log_level=CRITICAL)
            return []
        try:
            needs.remove(subsystem)
            if needs:
                with open(filename, 'wb') as fd:
                    fd.write('\n'.join(needs))
                    fd.write('\n')
            else:
                os.unlink(filename)
        except ValueError:
            pass
        return needs

    def _connect_uploaded(self):
        return sqlite3.connect(os.path.join(self.update_dir, 'uploaded.db'))
    def connect_uploaded(self):
        self.db_uploaded = self._connect_uploaded()
        return self.db_uploaded.cursor()
    def disconnect_uploaded(self, commit=True):
        try:
            if not self.db_uploaded:
                return
        except AttributeError:
            pass
        if commit:
            self.db_uploaded.commit()
        self.db_uploaded.close()
    def init_db_uploaded(self):
        cursor = self.connect_uploaded()
        cursor.execute('CREATE TABLE IF NOT EXISTS uploaded (num INTEGER PRIMARY KEY, upload_date DATETIME, changelog TEXT, depends TEXT, status TEXT, missing TEXT)')
        self.disconnect_uploaded()

    def _connect_history(self):
        return sqlite3.connect(os.path.join(self.update_dir, 'history.db'))
    def connect_history(self):
        self.db_history = self._connect_history()
        return self.db_history.cursor()
    def disconnect_history(self, commit=True):
        try:
            if not self.db_history:
                return
        except AttributeError:
            pass
        if commit:
            self.db_history.commit()
        self.db_history.close()
    def init_db_history(self):
        cursor = self.connect_history()
        cursor.execute('CREATE TABLE IF NOT EXISTS history (id INTEGER PRIMARY KEY AUTOINCREMENT, num INTEGER NOT NULL, upload_date DATETIME, changelog TEXT, depends TEXT, succeeded INTEGER, apply_date DATETIME, apply_user TEXT)')
        self.disconnect_history()

    def db_in_progress_to_new(self):
        """Change status of upgrade(s) from "in progress" to "new" (to be used
        for interrupted upgrade(s), on component loading).
        """
        db_uploaded = self._connect_uploaded()
        cursor = db_uploaded.cursor()
        cursor.execute('UPDATE uploaded SET status = ? WHERE status = ?',
                       (UPGRADE_STATUS_NEW, UPGRADE_STATUS_IN_PROGRESS))
        commit_close(db_uploaded)

    def guess_edenwall_type(self):
        self.this_edenwall_type = None
        with open(MODEL_PATH) as fd:
            model = fd.readline()
        model = model.strip()
        if model == "emf" or model == "EMF":
            self.this_edenwall_type = "emf"
        elif model != "":
            self.this_edenwall_type = "firewall"
        return self.this_edenwall_type
    def _check_target_type(self, target_type):
        try:
            self.guess_edenwall_type()
        except Exception:
            pass
        if not target_type or self.this_edenwall_type is None:
            return True  # No target checking.
        for type_ in target_type:
            if self.this_edenwall_type.lower() == type_.lower():
                return True
        return False

    def check(self):
        pass

    def fail(self, message):
        self.critical(message)
        self.core.exit(1)

    def read_config(self, *args, **kwargs):
        self.update_cfg = self._read_config()
        try:
            serialized = self.core.config_manager.get('httpout')
        except (ConfigError, KeyError):
            self.warning('HttpOut not configured, default values loaded.')
            self.httpout_cfg = HttpOutConf()
        else:
            self.httpout_cfg = HttpOutConf.deserialize(serialized)

    def _read_config(self):
        try:
            serialized = self.core.config_manager.get(self.MASTER_KEY)
            return UpdateCfg.deserialize(serialized)
        except (ConfigError, KeyError):
            self.warning('Update not configured, default values loaded.')
            return UpdateCfg()

    def warn_interrupted_upgrade(self):
        if not os.path.exists(self.applying_flag_fn):
            return True
        try:
            with open(self.applying_flag_fn) as fd:
                line = fd.readline()
                if not line:
                    self.error('The interrupted upgrade number file is unexpectedly empty.')
            upgrade_num, login = line.split(' ', 1)
            upgrade_num = int(upgrade_num)
            login = login.strip()
        except IOError, err:
            self.writeError(err,
                u'Cannot open the existing file of interrupted upgrade',
                log_level=ERROR)
            return False
        except ValueError:
            self.error('The interrupted upgrade file does not contain a number.')
            return False
        except Exception:
            self.error("The interrupted upgrade file does not contain the ugrade number and the applier's login.")
            return False

        context = Context.fromComponent(self)
        self.core.callService(context, 'contact', 'sendMailToAdmin',
                    'The upgrade %s was interrupted' % upgrade_num,
                    'The upgrade %s, which the user %s began to apply, was interrupted before it was fully applied.  A likely cause of this interruption is a power failure or a similar event.  You will have to apply it again.'
                              % (upgrade_num, login))
        self.db_in_progress_to_new()
        self.delete_applying_flag()
        return True

    def apply_config(self, *unused):
        self._reset()

    def _reset(self):
        self.read_config()

    def save_config(self, message, context=None):
        self.debug('Saving Update module configuration.')
        serialized = self.update_cfg.serialize()
        with self.core.config_manager.begin(self, context) as cm:
            try:
                cm.delete(self.MASTER_KEY)
            except:
                pass

            cm.set(self.MASTER_KEY, serialized)
            cm.commit(message)

    def logError(self, failure):
        self.writeError(failure)

    def get_blacklist(self):
        """ Return the list of blacklisted upgrade numbers (int list).
        """
        try:
            with open(self.blacklist_filename) as fd:
                return [int(line) for line in fd.readlines()]
        except Exception:
            return []

    def add_to_blacklist(self, upgrade_num, blacklist):
        """ Add the given list items to the blacklist.

        Return True if the blacklist has changed, False otherwise.
        """
        if not blacklist:
            return False
        self.info('The upgrade %s blacklists the following upgrades: %s.' %
                  (upgrade_num, ', '.join([str(num) for num in blacklist])))
        old_blacklist = set(self.get_blacklist())
        blacklist_to_add = set([int(el) for el in blacklist]) - old_blacklist
        if not blacklist_to_add:
            return False
        try:
            with open(self.blacklist_filename, 'a') as fd:
                fd.write('\n'.join([str(num) for num in blacklist_to_add])
                         + '\n')
        except Exception, err:
            self.writeError(err,
                'Could not add upgrade numbers to upgrade blacklist',
                log_level=CRITICAL)
            return False
        return True

    def log_restart_needs(self, upgrade_num, restart_needs):
        if not restart_needs:
            return
        if 'system' in restart_needs:
            restart_needs = ['system']
        self.error(
            'The upgrade %s will require the following to be restarted: %s.'
            % (upgrade_num, ', '.join(
                    [UPGRADE_RESTART_NEED_NAMES.get(need, 'the system')
                     for need in restart_needs])))

    # Functions used by services:
    def _register_applied_now(self, upgrade_num):
        self._update_missing(upgrade_num)
        self.delete_upgrade(upgrade_num)
        if not self.is_applied(upgrade_num):
            with open(os.path.join(self.update_dir, UPDATE_APPLIED), 'a') as fd:
                fd.write('%d\n' % upgrade_num)

    def _register_applied(self, upgrade_num):
        """Register upgrade_num as applied, now (return True) or for after
        a needed restart (return False).
        """
        path = os.path.join(self.upgrades_dir,
                            self.upgrade_num2directory(upgrade_num))
        restart_needs = extract_restart_needs(path)
        if not restart_needs:
            self._register_applied_now(upgrade_num)
            return True  # No need to restart anything, registered as applied.

        # Needs restart.
        try:
            with open(os.path.join(self.update_after_restart,
                                   str(upgrade_num)), 'w') as fd:
                fd.write('\n'.join(restart_needs))
                fd.write('\n')
        except Exception:
            self.critical(
                'Could not register application of upgrade %s for after restart.'
                % upgrade_num)

        # Update the database:
        db_uploaded = self._connect_uploaded()
        cursor_uploaded = db_uploaded.cursor()
        cursor_uploaded.execute(
            "UPDATE uploaded SET status = ? WHERE num = ?",
            (UPGRADE_STATUS_NEED_RESTART, upgrade_num))
        commit_close(db_uploaded)

        # Ensure the corresponding restart flags are present:
        try:
            for need in restart_needs:
                if not need in NEEDS2FLAG_FILENAMES:
                    self.warning("Unknown restart need `%s'." % need)
                    continue
                with open(NEEDS2FLAG_FILENAMES[need], 'w') as fd:
                    pass
        except Exception, err:
            self.writeError(err,
                "Could not set a restart flag",
                log_level=ERROR)

        return False  # Need restart, so not fully registered as applied.

    def _update_missing(self, upgrade_num):
        """Update the field 'missing' in the database for all the upgrades
        which depend on the given applied upgrade. If there is no more missing
        upgrades, then also change the status field from dependencies_missing
        to new.
        """
        db = self._connect_uploaded()
        cursor = db.cursor()
        cursor.execute(
            'SELECT num,missing FROM uploaded WHERE status=? AND missing LIKE "%% %d %%"'
            % upgrade_num, (UPGRADE_STATUS_DEPENDENCIES_MISSING,))
        upgrades = cursor.fetchall()
        for (num, missing) in upgrades:
            missing_nums = _str_to_depends_list(missing)
            missing_nums.remove(upgrade_num)
            if missing_nums:
                status = UPGRADE_STATUS_DEPENDENCIES_MISSING
            else:  # No more missing upgrade, status becomes 'New':
                status = UPGRADE_STATUS_NEW
            new_missing = _depends_list_to_str(missing_nums)
            cursor.execute(
                'UPDATE uploaded SET status = ?, missing = ? WHERE num = ?',
                (status, new_missing, num))
        commit_close(db)

    def add_upgrade(self, filename):
        try:
            archive_num = self.upgrade_number(filename)
        except:
            os.remove(os.path.join(self.upgrades_dir, filename))
            raise
        try:
            # Unpack and check the archive and retrieve its short changelog:
            (depends_list, short_changelog, restart_needs, blacklist, target_type) \
                = unpack_check(self.gpg_homedir, filename, self.upgrades_dir)
            # Is this upgrade for this EdenWall's type (firewall/EMF)?
            if not self._check_target_type(target_type):
                raise NuConfError(
                    UPDATE_WRONG_TARGET_TYPE,
                    tr('The %s upgrade is not meant for this type of appliance (EMF or firewall).'),
                    archive_num)
            self.add_to_blacklist(archive_num, blacklist)
            # Is this upgrade already applied?
            already_applied = self.is_applied(archive_num)
            if already_applied:
                raise NuConfError(
                    UPDATE_ALREADY_APPLIED,
                    tr('The upgrade %s has already been applied.'),
                    archive_num)
            elif archive_num in self.get_blacklist():
                raise NuConfError(
                    UPDATE_BLACKLISTED,
                    tr('The upgrade %s has been superseded by another upgrade.'),
                    archive_num)
            else:
                applied_list = self.applied_list()
                missing_list = list(set(depends_list) - set(applied_list))
                if missing_list:
                    status = UPGRADE_STATUS_DEPENDENCIES_MISSING
                else:
                    status = UPGRADE_STATUS_NEW
                self.log_restart_needs(archive_num, restart_needs)

            # Insert the upgrade into the database:
            cursor = self.connect_uploaded()
            cursor.execute("DELETE FROM uploaded WHERE num = ?",
                           (archive_num,))
            cursor.execute(
                "INSERT INTO uploaded VALUES (?, datetime('now'), ?,?,?,?)",
                (archive_num, short_changelog,
                 _depends_list_to_str(depends_list), status,
                 _depends_list_to_str(missing_list)))
            # Do not update missing field here any more.  It will be updated
            # when the upgrade is fully applied (see _register_applied_now).
            self.disconnect_uploaded()
            return archive_num
        except:
            self.delete_upgrade(archive_num)
            raise

    def applied_list(self):
        applied_upgrades_list = [0]  # Upgrade number 0 is always applied.
        try:
            with open(os.path.join(self.update_dir, UPDATE_APPLIED)) as fd:
                for line in fd.xreadlines():
                    m = re.compile(r'^([0-9]+)').search(line)
                    if m:
                        applied_upgrades_list.append(int(m.group(1)))
        except IOError:
            pass
        return applied_upgrades_list
    def is_applied(self, upgrade_num):
        if upgrade_num == 0:  # Upgrade number 0 is always applied.
            return True
        try:
            with open(os.path.join(self.update_dir, UPDATE_APPLIED)) as fd:
                for line in fd.xreadlines():
                    try:
                        if int(line) == upgrade_num:
                            return True
                    except ValueError: pass
        except IOError: pass
        return False

    def available_or_applied_set(self, passed_cursor=None):
        if passed_cursor is None:
            cursor = self.connect_uploaded()
        else:
            cursor = passed_cursor
        cursor.execute('SELECT num FROM uploaded')
        available_list = [upgrade[0] for upgrade in cursor.fetchall()]
        if passed_cursor is None:
            self.disconnect_uploaded()
        return set(available_list + self.applied_list())

    def delete_upgrade(self, archive_num, passed_cursor=None):
        # First delete the files on disk:
        try:
            os.remove(os.path.join(self.upgrades_dir,
                                   self.upgrade_num2filename(archive_num)))
        except OSError:
            pass
        try:
            shutil.rmtree(os.path.join(self.upgrades_dir,
                          self.upgrade_num2directory(archive_num)))
        except OSError:
            pass
        # Delete from database:
        if passed_cursor is None:
            db_uploaded = self._connect_uploaded()
            cursor = db_uploaded.cursor()
        else:
            cursor = passed_cursor
        cursor.execute('DELETE FROM uploaded WHERE num = ?',
                       (archive_num,))
        if passed_cursor is None:
            commit_close(db_uploaded)

    def apply_upgrade(self, context, upgrade_num):
        db_uploaded = self._connect_uploaded()
        cursor_uploaded = db_uploaded.cursor()
        cursor_uploaded.execute("SELECT * FROM uploaded WHERE num = ?",
                                (upgrade_num,))
        try:
            uploaded_upgrade = cursor_uploaded.fetchall()[0]
        except IndexError:
            commit_close(db_uploaded)
            raise NuConfError(
                UPDATE_ALREADY_APPLIED_OR_DELETED,
                'The upgrade %d has already been applied or deleted.',
                upgrade_num)
        # Check that all dependencies are already applied:
        depends_set = set(_str_to_depends_list(
                uploaded_upgrade[UPLOADED_DEPENDS]))
        depends_unapplied_set = depends_set - set([0] + self.applied_list())
        if depends_unapplied_set:
            depends_unapplied = ', '.join(
                ["%d" % i for i in sorted(depends_unapplied_set)])
            missing_list = list(depends_set -
                                self.available_or_applied_set(cursor_uploaded))
            if missing_list:
                status = UPGRADE_STATUS_DEPENDENCIES_MISSING
            else:
                status = UPGRADE_STATUS_NEW

            cursor_uploaded.execute("UPDATE uploaded SET status = ? WHERE num = ?",
                                    (status, upgrade_num))
            commit_close(db_uploaded)
            raise NuConfError(UPDATE_CANNOT_APPLY_BECAUSE_DEPEND_NOT_APPLIED,
                              'Could not apply upgrade %d because the following upgrade(s) it depends on were not applied first: %s.',
                              upgrade_num, depends_unapplied)
        cursor_uploaded.execute(
            'UPDATE uploaded SET status = ? WHERE num = ?',
            (UPGRADE_STATUS_IN_PROGRESS, upgrade_num))
        commit_close(db_uploaded)

        command = os.path.join(self.upgrades_dir,
                               self.upgrade_num2directory(upgrade_num),
                               'upgrade')
        try:
            with open(self.applying_flag_fn, 'w') as applying_fd:
                applying_fd.write(u'%s %s\n' % (upgrade_num, context.ownerString()))
        except Exception, err:
            self.writeError(err,
                'Could not create the file to check interrupted upgrade',
                log_level=ERROR)
        try:
            with open(RPCD_SERVER_UPDATE_LOCK, 'w') as lock_fd:
                lock_fd.write('')
        except Exception:
            pass

        self.rotate_upgrade_logs()
        upgrade_log_fd = None
        try:
            upgrade_log_fd = open(self.upgrade_log_filename, 'w')
            upgrade_log_fd.write('Applying upgrade %s on %s.\n\n' % (
                    upgrade_num, now()))
            upgrade_log_fd.flush()
        except Exception, err:
            self.writeError(err,
                'Cannot write upgrade log',
                log_level=CRITICAL)
        if upgrade_log_fd:
            process = createProcess(self, command, stdout=upgrade_log_fd,
                                    stderr=subprocess.STDOUT)
            upgrade_log_fd.flush()
        else:
            process = createProcess(self, command)
        retcode = process.wait()
        self.delete_applying_flag()
        try:
            os.unlink(RPCD_SERVER_UPDATE_LOCK)
        except Exception:
            pass
        succeeded = False
        if retcode == 0:
            self.info(context, 'Successfully applied upgrade %d.' %
                      upgrade_num)
            succeeded = True
        else:
            self.info(context,
                'Tried to apply upgrade %d, which failed with exit code %d.'
                % (upgrade_num, retcode))

        if upgrade_log_fd:
            try:
                upgrade_log_fd.write(
                    '\nFinished applying upgrade %s on %s (result: %s).\n'
                    % (upgrade_num, now(), to_result(succeeded)))
            except Exception, err:
                self.writeError(err,
                    'Cannot write to upgrade log any more',
                    log_level=CRITICAL)
            try:
                upgrade_log_fd.close()
            except Exception, err:
                self.writeError(err,
                    'Cannot close upgrade log',
                    log_level=CRITICAL)

        # Register this applied upgrade into history:
        db_history = self._connect_history()
        cursor_history = db_history.cursor()
        cursor_history.execute("INSERT INTO history (num, upload_date, changelog, depends, succeeded, apply_date, apply_user) VALUES (?, ?, ?, ?, ?, datetime('now'), ?)",
                tuple(uploaded_upgrade[:4]) + (succeeded, context.ownerString()))
        commit_close(db_history)
        if succeeded:
            self._register_applied(upgrade_num)
        else:
            db_uploaded = self._connect_uploaded()
            cursor_uploaded = db_uploaded.cursor()
            cursor_uploaded.execute(
                "UPDATE uploaded SET status = ? WHERE num = ?",
                (UPGRADE_STATUS_FAILED, upgrade_num))
            commit_close(db_uploaded)
        return succeeded

    def callWarnNewUpgrades(self):
        context = Context.fromComponent(self)
        defer = self.core.callService(context, 'update', 'warnNewUpgrades')
        if defer:
            defer.addErrback(self.writeError)

    def delete_applying_flag(self):
        try:
            os.unlink(self.applying_flag_fn)
        except Exception, err:
            self.writeError(err,
                'Could not delete the file to check interrupted upgrade',
                log_level=ERROR)

    def download_upgrade(self, num):
        filename = self.upgrade_num2filename(num)
        url = "%s/%s" % (self.get_update_server(), filename)
        try:
            resource = self.open_url(url)
        except HTTPError:
            raise NuConfError(
                UPDATE_REMOTE_UPGRADE_NOT_FOUND,
                tr('The %s upgrade was not found.'), url)
        with open(os.path.join(self.upgrades_dir, filename), 'w') as fd:
            fd.write(resource.read())

    def get_known_upgrade_nums(self):
        db_uploaded = self._connect_uploaded()
        cursor = db_uploaded.cursor()
        cursor.execute('SELECT num FROM uploaded')
        known_upgrade_nums = [row[0] for row in cursor.fetchall()]
        commit_close(db_uploaded)
        db_history = self._connect_history()
        cursor = db_history.cursor()
        cursor.execute('SELECT num FROM history WHERE succeeded != 0')
        known_upgrade_nums = list(set(known_upgrade_nums +
                                      self.applied_list() +
                                      [row[0] for row in cursor.fetchall()]))
        commit_close(db_history)
        return known_upgrade_nums

    def get_update_directory_listing(self):
        dir_listing_resource = self.open_url(self.get_update_server())
        dir_listing = dir_listing_resource.read()
        dir_listing_resource.close()
        return dir_listing

    def get_update_server(self):
        if self.update_cfg.use_custom_mirror:
            return self.update_cfg.update_mirror
        return self.main_server

    def open_url(self, url):
        """Open a given URL.  The caller should close it after use."""
        existing_default_timeout = socket.getdefaulttimeout()
        if not existing_default_timeout:
            existing_default_timeout = 180
        socket.setdefaulttimeout(self.timeout)
        if self.httpout_cfg.use_proxy:
            if self.httpout_cfg.user:
                credentials = self.httpout_cfg.user
            else:
                credentials = ''
            if self.httpout_cfg.password:
                credentials += ':%s' % self.httpout_cfg.password
            if credentials:
                credentials += '@'
            proxy_handler = ProxyHandler({
                    'http': 'http://%s%s:%s/' % (credentials,
                         self.httpout_cfg.host, self.httpout_cfg.port),
                    'https': 'https://%s%s:%s/' % (credentials,
                         self.httpout_cfg.host, self.httpout_cfg.port),
                    })
            opener = build_opener(proxy_handler)
        else:
            opener = build_opener()
        result = opener.open(url)
        socket.setdefaulttimeout(existing_default_timeout)
        return result

    def rotate_upgrade_logs(self):
        filename = self.upgrade_log_filename + '.%d' % (
            self.max_upgrade_log_files - 1)
        try:
            if os.path.exists(filename):
                os.unlink(filename)
        except Exception, err:
            self.writeError(err,
                "Cannot remove upgrade log file `%s'" % filename,
                log_level=CRITICAL)
        try:
            for i in range(self.max_upgrade_log_files - 1, 0, -1):
                filename = self.upgrade_log_filename + '.%d' % (i - 1)
                if os.path.exists(filename):
                    os.rename(filename,
                              self.upgrade_log_filename + '.%d' % i)
            if os.path.exists(self.upgrade_log_filename):
                os.rename(self.upgrade_log_filename,
                          self.upgrade_log_filename + '.1')
        except Exception, err:
            self.writeError(err,
                "Error while rotating upgrade logs",
                log_level=CRITICAL)

    def upgrade_num2directory(self, upgrade_num):
        return '%s%s' % (UPGRADE_PREFIX, upgrade_num)

    def upgrade_num2filename(self, upgrade_num):
        return '%s.tar' % self.upgrade_num2directory(upgrade_num)

    def upgrade_number(self, archive_name):
        number = upgrade_number(archive_name)
        if number is None:
            raise NuConfError(UPDATE_NO_UPGRADE_NUMBER,
                "No upgrade number found in archive file name `%s'.",
                archive_name)
        return number

    # Deferred threads:
    def doApplyUpgrades(self, context, upgrade_nums):
        try:
            for upgrade_num in upgrade_nums:
                if not self.apply_upgrade(context, upgrade_num):
                    # Failed upgrade. Stop the series.
                    self.db_in_progress_to_new()
                    break
        except:
            if self.lock:
                self.core.lock_manager.releaseVolatile(UPDATE_LOCK, self.lock)
                self.lock = None
            raise
        # Log is done in self.apply_upgrade.
        if self.lock:
            self.core.lock_manager.releaseVolatile(UPDATE_LOCK, self.lock)
            self.lock = None

    def doDownloadNewUpgrades(self, context):
        self.downloading_error = ''
        # Build the list of upgrades we already have:
        known_upgrade_nums = self.get_known_upgrade_nums()

        # Fetch the list of upgrades available on the update server:
        try:
            dir_listing = self.get_update_directory_listing()
        except HTTPError:
            self.downloading = 0
            error_text = tr('Remote update directory not found.  Please check the update server configuration or the outgoing proxy configuration.')
            self.downloading_error = error_text
            raise NuConfError(UPDATE_REMOTE_DIRECTORY_NOT_FOUND, error_text)
        except URLError, err:
            self.downloading = 0
            try:
                error_arg = err.reason[1]
            except Exception:
                if str(err) == "<urlopen error timed out>":
                    error_arg = "Timed out"
                else:
                    error_arg = exceptionAsUnicode(err)
            error_text = tr("Remote update directory not found. Please check the update server configuration (%s)")
            self.downloading_error = error_text % error_arg
            raise NuConfError(UPDATE_REMOTE_DIRECTORY_NOT_FOUND, error_text, error_arg)
        except Exception, err:
            self.downloading = 0
            self.writeError(err, "Remote update directory not found")
            error_text = tr('Remote update directory not found.  Please check the update server configuration or your network.')
            self.downloading_error = error_text
            raise NuConfError(UPDATE_REMOTE_DIRECTORY_NOT_FOUND, error_text)
        finally:
            if self.lock:
                self.core.lock_manager.releaseVolatile(UPDATE_LOCK, self.lock)
                self.lock = None
        try:
            avail_upgrade_nums = UpgradeSGMLParser(dir_listing).getUpgradeList()

            nums_to_download = set(avail_upgrade_nums) - set(known_upgrade_nums)
            try:
                os.mkdir(self.upgrades_dir)
            except OSError:  # Typically because the directory exists.
                pass
            self.downloaded_files_count = 0
            self.files_to_download_count = len(nums_to_download)
            for num in nums_to_download:
                self.download_upgrade(num)
                filename = self.upgrade_num2filename(num)
                try:
                    self.add_upgrade(filename)
                except NuConfError:  # Typically, already applied.
                    continue
                except Exception, err:
                    self.writeError(err,
                        "Error while adding downloaded upgrade %s." % num,
                        log_level=ERROR)
                    continue
                self.info(context, "Downloaded upgrade archive `%s'." %
                          filename)
                self.downloaded_files_count += 1
        finally:
            self.files_to_download_count = 0
            self.downloading = 0
            if self.lock:
                self.core.lock_manager.releaseVolatile(UPDATE_LOCK, self.lock)
                self.lock = None


    # Services:
    def service_applyAll(self, context):
        cursor = self.connect_uploaded()
        cursor.execute("SELECT num FROM uploaded")
        upgrade_nums = [upgrade[0] for upgrade in cursor.fetchall()]
        self.disconnect_uploaded()
        return self.service_applyUpgrades(context, upgrade_nums)

    def service_applyUpgrades(self, context, upgrade_nums):
        # Check whether all dependencies are (or will be) satisfied:
        cursor = self.connect_uploaded()
        # This set will grow in the following loop:
        applied_list = self.applied_list()
        avail_set = set([0] + applied_list)
        nums_to_upgrade = []
        for num in upgrade_nums:
            if num in applied_list:
                self.warning(
                    'Cannot apply upgrade %s because it was already applied.'
                    % num)
                continue
            if num in self.get_blacklist():
                self.error(
                    'Cannot apply upgrade %s because it has been blacklisted by an already applied upgrade which supersedes it.'
                    % num)
                continue
            cursor.execute("SELECT * FROM uploaded WHERE num = ?", (num,))
            try:
                upgrade = cursor.fetchall()[0]
            except IndexError:
                self.disconnect_uploaded()
                raise NuConfError(UPDATE_ALREADY_APPLIED_OR_DELETED,
                    'The upgrade %d has already been applied or deleted.',
                    num)
            if upgrade[UPLOADED_STATUS] == UPGRADE_STATUS_NEED_RESTART:
                self.info('Cannot apply upgrade %d because it was already applied and will be deleted after the restart it needs.' % num)
                continue
            depends_set = set(_str_to_depends_list(upgrade[UPLOADED_DEPENDS]))
            depends_not_included_set = depends_set - avail_set
            if depends_not_included_set:
                self.disconnect_uploaded()
                depends_not_included = ', '.join(
                    ["%d" % i for i in sorted(depends_not_included_set)])
                raise NuConfError(
                    UPDATE_CANNOT_APPLY_BECAUSE_DEPEND_NOT_APPLIED,
                    tr('Before you can apply upgrade %d, you must apply upgrade(s) %s.'),
                    num, depends_not_included)
            avail_set.add(num)
            nums_to_upgrade.append(num)
        self.disconnect_uploaded()

        # Acquire lock and asynchronously apply the upgrades:
        try:
            self.lock = self.core.lock_manager.acquireVolatile(UPDATE_LOCK,
                                                               lambda _: None)
        except LockError:
            self.info(context, UPDATE_LOCK_MESSAGE)
            return False
        defer = deferToThread(self.doApplyUpgrades, context, nums_to_upgrade)
        defer.addErrback(self.logError)
        return True

    def service_checkConfiguration(self, context):
        return True

    def service_downloadNewUpgrades(self, context):
        # Acquire lock and asynchronously download the upgrades:
        try:
            self.lock = self.core.lock_manager.acquireVolatile(UPDATE_LOCK,
                                                               lambda _: None)
        except LockError:
            self.info(context, UPDATE_LOCK_MESSAGE)
            return False
        self.downloading = 1
        defer = deferToThread(self.doDownloadNewUpgrades, context)
        defer.addErrback(self.logError)
        return defer

    def service_history(self, context):
        cursor = self.connect_history()
        cursor.execute("SELECT * FROM history")
        history = cursor.fetchall()
        self.disconnect_history()
        return history

    def service_sendUpgradeArchive(self, context, filename, encoded_bin):
        # Check filename
        self.upgrade_number(filename)
        try:
            os.mkdir(self.upgrades_dir)
        except OSError:  # Typically because the directory exists.
            pass
        with open(os.path.join(self.upgrades_dir, filename), 'w') as fd:
            fd.write(decodeFileContent(encoded_bin))
        archive_num = self.add_upgrade(filename)
        self.info(context, "Uploaded upgrade archive `%s'." % filename)
        return archive_num

    def service_deleteUpgradeArchives(self, context, archive_nums):
        """Delete the specified archives and its directory and delete its
        entry from the database; update dependencies."""
        if not archive_nums:
            return None
        really_deleted_nums = []  # Only upgrades not being applied.
        cursor = self.connect_uploaded()
        for archive_num in archive_nums:
            cursor.execute('SELECT status FROM uploaded WHERE num = ?',
                           (archive_num,))
            try:
                upgrade_status = cursor.fetchall()[0][0]
                if upgrade_status == UPGRADE_STATUS_IN_PROGRESS:
                    self.info(context,
                        'Cannot delete upgrade %d which is being applied.'
                        % archive_num)
                    continue
                elif upgrade_status == UPGRADE_STATUS_NEED_RESTART:
                    self.info(context,
                              'Cannot delete upgrade %d which is already applied; this upgrade will be deleted after the restart it needs.'
                              % archive_num)
                    continue
            except IndexError:
                continue
            # If not already applied, update 'missing' for all the upgrades
            # which depend on the deleted upgrade:
            if not self.is_applied(archive_num):
                cursor.execute(
                    'SELECT num,missing FROM uploaded WHERE status IN (%s) AND depends LIKE "%% %d %%"'
                    % ("'%s', '%s'" % (
                            UPGRADE_STATUS_DEPENDENCIES_MISSING,
                            UPGRADE_STATUS_NEW), archive_num))
                upgrades = cursor.fetchall()
                for (num, missing) in upgrades:
                    # Use set to ensure we do not add the same num several
                    # times.
                    new_missing_list = list(set(_str_to_depends_list(missing)
                                                + [archive_num]))
                    new_missing = _depends_list_to_str(new_missing_list)
                    cursor.execute(
                        'UPDATE uploaded SET status=?, missing=? WHERE num=?',
                        (UPGRADE_STATUS_DEPENDENCIES_MISSING, new_missing,
                         num))
            # Finally, delete the upgrade:
            self.delete_upgrade(archive_num, cursor)
            really_deleted_nums.append(archive_num)
        self.disconnect_uploaded()
        if really_deleted_nums:
            self.info(context, "Deleted upgrade archive(s): %s." %
                      ', '.join(('%d' % num for num in really_deleted_nums)))
        return really_deleted_nums

    def service_getAppliedList(self, context):
        """Return the list of applied upgrades numbers (integers)."""
        return self.applied_list()

    def service_getHighestApplied(self, context):
        """Return the highest applied upgrade number as an integer,
        ignoring 666 and numbers >= 9000000."""
        applied_list = self.applied_list()
        return max(filter(lambda x: x != 666 and x < 9000000, applied_list))

    def service_getDownloadProgress(self, context):
        return (self.downloaded_files_count, self.files_to_download_count,
                self.downloading, self.downloading_error)

    def service_getKnownUpgradeNums(self, *unused):
        return self.get_known_upgrade_nums()

    def service_needRestart(self, context):
        result = ''
        if os.path.exists(RESTART_RPCD):
            result = 'ufwi_rpcd'  # May be overwritten below.
            os.unlink(RESTART_RPCD)
        if os.path.exists(RESTART_SYSTEM):
            result = 'system'  # Restarting system also restarts ufwi_rpcd.
            os.unlink(RESTART_SYSTEM)
        return result

    def service_getBlacklist(self, context):
        return self.get_blacklist()

    def service_getBlacklistedAndPresent(self, context):
        blacklist = set(self.get_blacklist())
        db = self._connect_uploaded()
        cursor = db.cursor()
        cursor.execute("SELECT num FROM uploaded")
        uploaded_upgrades = cursor.fetchall()
        db.close()
        uploaded_nums = set([row[0] for row in uploaded_upgrades])
        return list(uploaded_nums.intersection(blacklist))

    def service_uploadedUpgrades(self, context):
        cursor = self.connect_uploaded()
        cursor.execute("SELECT * FROM uploaded")
        uploaded_upgrades = cursor.fetchall()
        self.disconnect_uploaded()
        return uploaded_upgrades

    def service_saveConfiguration(self, context, message):
        self.save_config(message, context)

    def service_getUpdateConfig(self, context):
        return self.update_cfg.serialize()

    def service_setUpdateConfig(self, context, serialized, message):
        self.update_cfg = UpdateCfg.deserialize(serialized)
        if self.update_cfg.isValid(raise_error=True):
            self.save_config(message, context)

    @inlineCallbacks
    def service_warnNewUpgrades(self, context, *args):
        if not self.update_cfg.auto_check:
            returnValue(None)
        try:
            cur_upgrades = yield self.core.callService(context, 'update', 'uploadedUpgrades')
            yield self.core.callService(context, 'update', 'downloadNewUpgrades')
            new_upgrades = yield self.core.callService(context, 'update', 'uploadedUpgrades')
            if set(new_upgrades) - set(cur_upgrades):
                self.core.callService(context, 'contact', 'sendMailToAdmin',
                    tr('New upgrades available'),
                    tr('There are new upgrades available for your EdenWall appliance.'))
        except Exception, err:
            self.writeError(err)

    def service_status(self, context):
        """
        Implementation compulsory because NOT_A_SERVICE
        is not expected from a UnixServiceComponent
        """
        return self.NAME, ServiceStatusValues.NOT_A_SERVICE

