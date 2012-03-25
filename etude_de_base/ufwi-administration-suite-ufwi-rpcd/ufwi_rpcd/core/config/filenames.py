
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
from shutil import copyfile, move
from os import umask, unlink
from os.path import join, split, exists, basename

from ufwi_rpcd.common.tools import inverseDict

VARIANTS = (
    SAVED,
    OLD_SAVED,
    DIFF_CANDIDATE,
    SAVED_DIFF,
    SAVE_DIFF_CANDIDATE,
    OLD_SAVED_DIFF,
    SAVE_CANDIDATE,
    APPLIED,
    LAST_WORKING,
    INVALID,
    SAVED_DIFF_BACKUP,
    SAVED_BACKUP,
) = """\
saved
old_saved
diff_candidate
saved_diff
save_diff_candidate
old_saved_diff
save_candidate
applied
last_working
invalid
saved_diff_backup
saved_backup
""".split()

class VersionnedFilenames(object):
    def __init__(self, base, versionning_component):
        """
        base: for instance "configuration/configuration.xml"
        """
        self.versionning_component = versionning_component
        path_base = split(base)
        self.repository = versionning_component.getRepository(path_base[0])
        file_part = path_base[1]
        self.path_part = self.repository.checkout_directory

        #Just for introspection: object attributes.
        self.saved = \
        self.old_saved = \
        self.diff_candidate = \
        self.saved_diff = \
        self.save_diff_candidate = \
        self.old_saved_diff = \
        self.save_candidate = \
        self.application_candidate = \
        self.last_working = \
        self.invalid = \
        self.saved_diff_backup = \
        self.saved_backup = None

        self.possible_filenames = set()

        for prefix in VARIANTS:
            filename = join(self.path_part, "%s-%s" % (prefix, file_part))
            self.possible_filenames.add(filename)
            setattr(self, prefix, filename)

        self.possible_filenames.add(file_part)
        self.possible_filenames.add("paths_file")
        self.applied = join(self.path_part, file_part)

        self.paths_file = join(self.path_part, "paths_file")
        self.repository.setWhiteList(self.possible_filenames)

        self.saves2backups = {
            self.saved_diff: self.saved_diff_backup,
            self.saved: self.saved_backup,
        }

    def _commit(self, message):
        self.repository.commit(message)

    def _rotate(self, draft, destination, backup=None):
        """
        draft -> destination -> backup (optional)

        Don't create a backup copy if the destination doesn't exist.
        """
        if backup and exists(destination):
            self.versionning_component.debug(
                'filesystem COPY: %s -> %s' %
                (basename(destination), basename(backup))
                )
            copyfile(destination, backup)
        self.versionning_component.debug(
            'filesystem MOVE: %s -> %s' %
            (basename(draft), basename(destination))
            )
        move(draft, destination)

    def configApply(self, message):
        # Copy configuration.xml to last_working_configuration.xml,
        # and commit the new files
        umask(0077)
        # running -> previous
        # candidate -> running
        deleted_list = []
        if exists(self.saved):
            self._rotate(self.saved, self.applied)
        if exists(self.saved_diff):
            self.repository.delete(self.saved_diff)
            deleted_list.append(self.saved_diff)
        try:
            self.repository.delete(self.save_diff_candidate)
            deleted_list.append(self.save_diff_candidate)
        except Exception:
            pass
        if exists(self.applied):
            copyfile(self.applied, self.last_working)
            copy_message = "\n-copied %s -> %s" % (
                    self.applied,
                    self.last_working
                    )
        else:
            copy_message = ''

        if deleted_list:
            deleted_message = "\n-deleted files:\n%s" % "\n".join(
                "\t %s" % filename for filename in deleted_list
                )
        else:
            deleted_message = ''

        commit_message = "%s%s%s" % (
                message, deleted_message, copy_message
                )

        self._commit(commit_message)

    def rotateCommit(self, message):
        """
        saved -> previous_saved

        save_candidate -> saved
        """
        umask(0077)
        self._rotate(self.save_candidate, self.saved, self.old_saved)
        self._rotate(self.save_diff_candidate, self.saved_diff, self.old_saved_diff)
        self._commit(message)

    def recallLastRunning(self):
        umask(0077)
        copyfile(self.last_working, self.applied)

    def _removeFiles(self, files, message, alwayscommit):
        repo_modified = False

        for filename in files:
            try:
                self.repository.delete(filename)
            except Exception:
                if exists(filename):
                    unlink(filename)
            else:
                repo_modified = True

        if repo_modified or alwayscommit:
            self._commit(message)

    def removeDiff(self, message, alwayscommit=False):
        files = (self.saved_diff, self.save_diff_candidate)
        self._removeFiles(files, message, alwayscommit)

    def removeSavedFiles(self, message, alwayscommit=False):
        files = (self.saved_diff, self.save_diff_candidate, self.saved)
        self._removeFiles(files, message, alwayscommit)

    def rollback(self):
        if exists(self.last_working):
            self.recallLastRunning()
        self.removeSavedFiles(
            "Rollback: recall last running configuration",
            alwayscommit=True
            )

    def restore_saved_config(self):
        return self._backup_restore(
            inverseDict(self.saves2backups),
            "Restored the backup of the saved configuration"
            )

    def backup_saved_config(self):
        return self._backup_restore(
            self.saves2backups, "Backuped the saved configuration"
            )

    def _backup_restore(self, file_translations, message):
        """
        file_translations is a dict of
        old_filename -> new_filename

        all old_filenames are supposed to exist or not, consistently,
        but we don't fail if they don't, and writeError instead
        """
        old_files_exists = tuple(
            exists(old_filename)
            for old_filename in file_translations
            )

        none_exists = not any(old_files_exists)

        #Check that all files exist, or none of them
        if not none_exists and not all(old_files_exists):
            #message construction: one file per line
            message = "\n - ".join(
                "'%s' existence: %s" % (filename, old_files_exists[index])
                for index, filename in enumerate(file_translations)
                )
            self.versionning_component.info(
                "Inconsistency:\n - %s" % message
                )

        if none_exists:
            #nothing to do
            return False

        for index, filenames in enumerate(file_translations.iteritems()):
            if not old_files_exists[index]:
                continue

            old_filename, new_filename = filenames
            try:
                move(old_filename, new_filename)
            except Exception, err:
                self.versionning_component.writeError(
                    err,
                    "While moving '%s' to '%s'." % (old_filename, new_filename)
                    )

        self._commit(message)

        return True

