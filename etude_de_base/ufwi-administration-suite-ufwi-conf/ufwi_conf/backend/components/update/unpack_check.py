#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Unpack an EdenWall upgrade archive and check its contents against the vendor's
signature.


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


import hashlib
import os
import re
import shutil
from subprocess import PIPE, Popen
from error import (NuConfError,
                   UPDATE_BAD_SIG,
                   UPDATE_CANNOT_READ_DESCRIPTION,
                   UPDATE_CANNOT_READ_FILE,
                   UPDATE_CHECKSUM_MISMATCH,
                   UPDATE_CHECKSUM_MISSING,
                   UPDATE_DEPENDS_SYNTAX_ERROR,
                   UPDATE_NO_SHORT_CHANGELOG,
                   UPDATE_NOT_TAR,
                   UPDATE_NO_UPGRADE_NUMBER,
                   UPDATE_UNPACK_DATA_ERROR,
                   UPDATE_UNPACK_ERROR,
                   )

from ufwi_rpcd.common import EDENWALL

DATA_TAR = 'data.tar'
DESCRIPTION_FILENAME = 'description'
FILES_TO_CHECK = [DATA_TAR, 'upgrade']
FILES_TO_UNTAR = FILES_TO_CHECK + [DESCRIPTION_FILENAME + '.asc']

if EDENWALL:
    product_name = "edenwall4"
else:
    product_name = "nufirewall"

UPGRADE_NUMBER_RE = re.compile(r'^%s_upgrade_(\d+)\.tar$' % product_name)
CHECKSUM_LINE_RE = re.compile(r'^Checksum ([-0-9A-Za-z]+) ([0-9A-Fa-f]+) (\S+)')
DEPENDS_LINE_RE = re.compile(r'^([-0-9 ]+)$')
CHUNK_SIZE = 4096 * 1024
SECTION_SEPARATOR = '====='
SHORT_CHANGELOG_RE = re.compile(r'^:short[-_]changelog: (.*)')
RESTART_NEED_RE = re.compile(r'^:restart: (.*)')
BLACKLIST_RE = re.compile(r'^:blacklist: (.*)')
TARGET_TYPE_RE = re.compile(r'^:target-type: (.*)')


# Utility functions:
def upgrade_number_and_dir(archive_name):
    if archive_name.endswith('.tar'):
        upgrade_dir = archive_name[:-4]
    else:
        raise NuConfError(UPDATE_NOT_TAR, archive_name)
    m = UPGRADE_NUMBER_RE.search(archive_name)
    if m:
        return (m.group(1), upgrade_dir)
    else:
        raise NuConfError(UPDATE_NO_UPGRADE_NUMBER,
            "No upgrade number found in archive file name `%s'.",
            archive_name)

def check_desc_sig(gpg_homedir, upgrade_path):
    p = Popen('LC_ALL=C /usr/bin/gpg --homedir "%s" "%s/description.asc"' %
              (gpg_homedir, upgrade_path), shell=True, stderr=PIPE,
              close_fds=True)
    stderr_lines = p.stderr.readlines()
    retcode = p.wait()
    if retcode != 0:
        raise NuConfError(UPDATE_BAD_SIG,
                          'Bad signature for description.asc.')

def check_sums(upgrade_path):
    # Read and store the checksums from description:
    desc_sumsets = {}
    try:
        fd = open(os.path.join(upgrade_path, DESCRIPTION_FILENAME))
        for line in fd.xreadlines():
            m = CHECKSUM_LINE_RE.search(line)
            if m:
                sum_type = m.group(1)
                sum = m.group(2)
                filename = m.group(3)
                if not filename in desc_sumsets:
                    desc_sumsets[filename] = {}
                desc_sumsets[filename][sum_type] = sum
        fd.close()
    except IOError, e:
        raise NuConfError(UPDATE_CANNOT_READ_DESCRIPTION,
                          'Cannot read the description file (%s).', e)
    # Compute the checksums of the unpacked files:
    for filename in FILES_TO_CHECK:
        withpath = os.path.join(upgrade_path, filename)
        if not filename in desc_sumsets:
            raise NuConfError(UPDATE_CHECKSUM_MISSING,
                "No checksum for file `%s' in the description file.",
                filename)
        try:
            if desc_sumsets[filename]['filesize'] != \
                    str(os.stat(withpath)[shutil.stat.ST_SIZE]):
                raise NuConfError(UPDATE_CHECKSUM_MISMATCH,
                    "Checksums (%s) do not match for file `%s'.",
                    'filesize', filename)
        except KeyError:
            raise NuConfError(UPDATE_CHECKSUM_MISSING,
                "No %s checksum for file `%s' in the description file.",
                'filesize', filename)
        hashes = (hashlib.md5(), hashlib.sha1(), hashlib.sha256())
        try:
            fd = open(withpath)
            while True:
                chunk = fd.read(CHUNK_SIZE)
                if chunk:
                    for hash in hashes:
                        hash.update(chunk)
                else:
                    break
            fd.close()
            for num, sum_type in enumerate(('md5', 'sha1', 'sha256')):
                try:
                    if desc_sumsets[filename][sum_type] != \
                            hashes[num].hexdigest():
                        raise NuConfError(UPDATE_CHECKSUM_MISMATCH,
                            "Checksums (%s) do not match for file `%s'.",
                            sum_type, filename)
                except KeyError:
                    raise NuConfError(UPDATE_CHECKSUM_MISSING,
                        "No %s checksum for file `%s' in the description file.",
                        sum_type, filename)
        except IOError, e:
            raise NuConfError(UPDATE_CANNOT_READ_FILE,
                "Cannot read file `%s' while checking checksums (%s).",
                filename, e)

def extract_depends(upgrade_path='.'):
    depends = None
    try:
        fd = open(os.path.join(upgrade_path, DESCRIPTION_FILENAME))
        title_line_found = False
        for line in fd.xreadlines():
            if line.startswith('List of upgrades this depends on'):
                title_line_found = True
                break
        if not title_line_found:
            return []
        separators = 0  # To ensure we do not read past the depends section.
        for line in fd.xreadlines():
            if line.startswith(SECTION_SEPARATOR):
                if separators == 1:
                    return []
                separators = 1
            m = DEPENDS_LINE_RE.search(line)
            if m:
                depends = m.group(1)
                break
        fd.close()
    except IOError, e:
        raise NuConfError(UPDATE_CANNOT_READ_DESCRIPTION,
            'Cannot read the description file (%s).', e)
    if depends is None:
        return []
    # Build a list of depends from the concise specs:
    depends_list = []
    for token in depends.split(' '):
        subtokens = token.split('-')
        subtoken_count = len(subtokens)
        if subtoken_count == 1:
            depends_list.append(int(subtokens[0]))
        elif subtoken_count == 2:
            depends_list.extend(range(int(subtokens[0]),
                                      int(subtokens[1]) + 1))
        else:
            raise NuConfError(
                UPDATE_DEPENDS_SYNTAX_ERROR,
                'Syntax error in list of upgrades this depends on.')
    return depends_list

def extract_list(upgrade_path, section_name, list_re):
    result = []
    try:
        fd = open(os.path.join(upgrade_path, DESCRIPTION_FILENAME))
        title_line_found = False
        for line in fd.xreadlines():
            if line.startswith(section_name):
                title_line_found = True
                break
        if not title_line_found:
            return result
        separators = 0  # To ensure we do not read past the section.
        for line in fd.xreadlines():
            if line.startswith(SECTION_SEPARATOR):
                if separators == 1:
                    fd.close()
                    return result
                separators = 1
            m = list_re.search(line)
            if m:
                result += [m.group(1).strip()]
        fd.close()
        return result
    except IOError, e:
        raise NuConfError(UPDATE_CANNOT_READ_DESCRIPTION,
            'Cannot read the description file (%s).', e)

def extract_blacklist(upgrade_path='.'):
    return extract_list(upgrade_path, 'Upgrade blacklist', BLACKLIST_RE)

def extract_restart_needs(upgrade_path='.'):
    return extract_list(upgrade_path, 'List of restart needs',
                        RESTART_NEED_RE)

def extract_target_type(upgrade_path='.'):
    return extract_list(upgrade_path, "Target type", TARGET_TYPE_RE)

def extract_short_changelog(upgrade_path='.'):
    short_changelog = ''
    try:
        fd = open(os.path.join(upgrade_path, DESCRIPTION_FILENAME))
        title_line_found = False
        for line in fd.xreadlines():
            if line.startswith('Changes (summary)'):
                title_line_found = True
                break
        if not title_line_found:
            raise NuConfError(UPDATE_NO_SHORT_CHANGELOG,
                "No summary of changes in the description file.")
        separators = 0  # To ensure we do not read past the section.
        for line in fd.xreadlines():
            if line.startswith(SECTION_SEPARATOR):
                if separators == 1:
                    if not short_changelog:
                        raise NuConfError(UPDATE_NO_SHORT_CHANGELOG,
                            "No summary of changes in the description file.")
                    else:
                        fd.close()
                        return short_changelog
                separators = 1
            m = SHORT_CHANGELOG_RE.search(line)
            if m:
                short_changelog += m.group(1) + '\n'
        fd.close()
    except IOError, e:
        raise NuConfError(UPDATE_CANNOT_READ_DESCRIPTION,
            'Cannot read the description file (%s).', e)


# Main:
def main(gpg_homedir, archive_name, upgrades_dir='.'):
    # Extract the upgrade number from the archive name:
    (upgrade_number, upgrade_dir) = upgrade_number_and_dir(archive_name)
    upgrade_path = os.path.join(upgrades_dir, upgrade_dir)
    normalized_archive_name = "%s_upgrade_%d.tar" % (product_name, int(upgrade_number))

    # Uncompress the upgrade archive:
    if os.path.exists(upgrade_path):
        shutil.rmtree(upgrade_path)
    if os.system('tar -C %s -xf %s %s' % (
            upgrades_dir, os.path.join(upgrades_dir, normalized_archive_name),
            ' '.join(['%s/%s' % (upgrade_dir, f) for f in
                      FILES_TO_UNTAR]))):
        raise NuConfError(UPDATE_UNPACK_ERROR,
                          "Error while unpacking archive `%s'.", archive_name)

    # Check the signature of the description file:
    check_desc_sig(gpg_homedir, upgrade_path)

    # Check the contents against the checksums in the description file:
    check_sums(upgrade_path)

    # Unpack data.tar:
    if os.system('tar -C "%s" -xf %s' % (
            upgrade_path, os.path.join(upgrade_path, DATA_TAR))):
        raise NuConfError(UPDATE_UNPACK_DATA_ERROR,
            "Error while unpacking the main data file (`%s')",
            DATA_TAR)

    depends = extract_depends(upgrade_path)
    short_changelog = extract_short_changelog(upgrade_path)
    restart_needs = extract_restart_needs(upgrade_path)
    blacklist = extract_blacklist(upgrade_path)
    target_type = extract_target_type(upgrade_path)
    return (depends, short_changelog, restart_needs, blacklist, target_type)

