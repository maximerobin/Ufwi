# -*- coding: utf-8 -*-

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

$Id$
"""

import base64
import re
from hashlib import sha1, sha256, sha512
from ufwi_rpcd.backend.logger import Logger
from M2Crypto.Rand import rand_bytes

# Number of bytes of the salt
SALT_BYTES = 20

class AbstractAuth(Logger):
    """ Abstract class for authentication methods.
    """

    PARAMETERS = []

    def __init__(self, log_name="auth"):
        Logger.__init__(self, log_name)
        self.users = {}
        self.groups = {}

    def split_auth_method(self, text):
        match = re.match(r'\{([^}]+)\}(.*)', text)
        if match:
            return (match.group(1),match.group(2))
        else:
            return (None,None)

    def hash_password(self, method, plaintext, salt):
        if salt and method != "PLAIN":
            salt = unicode(salt, "ISO-8859-1")
            plaintext = salt + plaintext
        plaintext = plaintext.encode("utf-8")
        if method == "SHA1":
            return sha1(plaintext).hexdigest()
        if method == "SHA256":
            return sha256(plaintext).hexdigest()
        if method == "SHA512":
            return sha512(plaintext).hexdigest()
        elif method == "PLAIN":
            return plaintext
        else:
            return None

    def build_hash(self, method, plaintext):
        if method in ("PLAIN", "EXTERNAL"):
            return u'{%s}%s' % (method, plaintext)

        salt = rand_bytes(SALT_BYTES)
        hash = self.hash_password(method, plaintext, salt)
        salt = base64.b64encode(salt)
        if not hash:
            return u'{PLAIN}%s' % plaintext

        return u'{%s}$%s$%s' % (method, salt, hash)

    def addUser(self, username, method, password, groups):
        if username in self.users:
            return False
        self.users[username] = self.build_hash(method, password)
        for group in groups:
            try:
                self.groups[group].append(username)
            except KeyError:
                self.groups[group] = [username]
        return True

    def delUser(self, username):
        try:
            self.users.pop(username)
            for name, users in self.groups.iteritems():
                if username in users:
                    users.remove(username)
            return True
        except KeyError:
            return False

    def editUser(self, username, method, password, groups):
        if not username in self.users:
            return False

        if password:
            self.users[username] = self.build_hash(method, password)

        for group, users in self.groups.iteritems():
            if not group in groups:
                try:
                    users.remove(username)
                except ValueError:
                    pass
            else:
                if not username in users:
                    users.append(username)
                groups.remove(group)

        # these is now just unexistant groups
        for group in groups:
            self.groups[group] = [username]
        return True

    def addGroup(self, name):
        if not name in self.groups:
            self.groups[name] = []
            return True
        else:
            return False

    def delGroup(self, name):
        try:
            self.groups.pop(name)
            return True
        except KeyError:
            return False

    def authenticate(self, username, challenge):
        """ Default implementation for authentication function, using internal
            dictionary to store passwords.
            Subclasses may re-implement this function for specific usage.
        """
        try:
            (method,text) = self.split_auth_method(self.users[username])
            if text is None: return False
            if method in ("PLAIN", "EXTERNAL"):
                hash = text
                salt = None
            else:
                # password is encoded using $<salt>$<hash>
                (ignored, salt, hash) = text.split('$', 2)
                salt = base64.b64decode(salt)
            ciphertext = self.hash_password(method, challenge, salt)
            if ciphertext == hash:
                return True
            return False
        except KeyError:
            return False

    def getGroups(self, username):
        """ Default implementation for function returning the list of groups
            for a specific user.
            Subclasses may re-implement this function for specific usage.
        """
        groups = []
        for group, users in self.groups.iteritems():
            if username in users:
                groups.append(group)
        return groups

    def getAllGroups(self):
        return self.groups.keys()

    def getUsers(self):
        l = []
        for username, password in self.users.iteritems():
            method, text = self.split_auth_method(password)
            groups = self.getGroups(username)
            l.append((username, method, groups))
        return l

    def getUser(self, username):
        try:
            password = self.users[username]
        except (KeyError, AttributeError):
            raise ValueError("There is no user %s" % username)
        else:
            method, text = self.split_auth_method(password)
            groups = self.getGroups(username)
            return method, groups

    def getStoragePaths(self):
        """
        export data: return None or an iterable of files
        """
        raise NotImplementedError()
