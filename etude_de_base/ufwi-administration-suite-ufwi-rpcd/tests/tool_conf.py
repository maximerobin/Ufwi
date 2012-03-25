
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
from os import mkdir, rename
from os.path import join, exists
from shutil import rmtree, copyfile
from contextlib import closing
import tempfile

from base64 import b64encode
from hashlib import sha1
from random import randint

# try importing Python native sqlite support (>= 2.5). If not found, try pysqlite2
try:
    import sqlite3 as sqlite
except ImportError, e:
    from pysqlite2 import dbapi2 as sqlite

class ConfigError(Exception):
    pass

def conf(srcdir, username, password, username2, password2):
    oldconf = "/etc/nucentral/nucentral.conf.test"
    if exists(oldconf):
        raise Exception("%s already exists" % oldconf)

    # Source
    sql_file = join(srcdir, 'doc/sql/acl_sqlite_debug.sql')
    if not exists(sql_file):
        raise ConfigError("Can't create SQL schema - '%s' does not exist" % sql_file)

    # Create working directory
    nucentral_vardir = tempfile.mkdtemp("nucentral")

    copyfile(join(srcdir, "default.nucentral.conf"), join(nucentral_vardir, "default.nucentral.conf"))

    mkdir(join(nucentral_vardir, "mods-enabled"))
    mkdir(join(nucentral_vardir, "repositories"))

    authfile_filename = join(nucentral_vardir, "users.txt")
    with open(authfile_filename, "w") as authfile:
        print >>authfile, "%s:{PLAIN}%s" % (username, password)
        salt = ''.join(chr(randint(0,255)) for i in xrange(20))
        hash = unicode(salt, "ISO-8859-1") + unicode(password2)
        hash = hash.encode("utf-8")
        hash = sha1(hash).hexdigest()
        hash = '{SHA1}$%s$%s' % (b64encode(salt), hash)
        print >>authfile, "%s:%s" % (username2, hash)

    groupfile_filename = join(nucentral_vardir, "groups.txt")
    with open(groupfile_filename, "w") as groupfile:
        print >>groupfile, "admin:admin"
        print >>groupfile, "users:user"

    conf_filename = join(nucentral_vardir, 'nucentral.conf')
    with open(conf_filename, 'w') as conf:
        print >>conf, "[CORE]"
        print >>conf, "enable_ssl = no"
        print >>conf, "vardir = %s" % nucentral_vardir
        print >>conf, "max_session_duration = 5"
        print >>conf, "streaming_udp_port = 8080"
        print >>conf, "auth = testauth"
        print >>conf, "[testauth]"
        print >>conf, "type = file"
        print >>conf, "authfile = %s" % authfile_filename
        print >>conf, "groupfile = %s" % groupfile_filename
        print >>conf, "[log]"
        print >>conf, "stdout_level = DEBUG"
        print >>conf, "file_level = DEBUG"
        print >>conf, "use_stdout = yes"
        print >>conf, "print_level = CRITICAL"
        print >>conf, "filename = %s" % join(nucentral_vardir, "nucentral.log")
        print >>conf, "[modules]"
        print >>conf, "dir = mods-enabled"
        print >>conf, "[audit]"
        print >>conf, "db_url = postgres://edenaudit:1234@localhost/edenaudit"
        print >>conf, "db_create_tables = False"

    # create acl file
    acl_db = join(nucentral_vardir, 'acl.db')
    with closing(sqlite.connect(database=acl_db, timeout=10.0)) as db:
        with open(sql_file,'r') as f:
            sql_data = f.read()
            db.executescript(sql_data)

    rename("/etc/nucentral/nucentral.conf", oldconf)
    copyfile(conf_filename, "/etc/nucentral/nucentral.conf")
    return nucentral_vardir

def conf_stop(nucentral_vardir):
    rename("/etc/nucentral/nucentral.conf.test", "/etc/nucentral/nucentral.conf")
    rmtree(nucentral_vardir)

