
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

from logging import DEBUG
from os import unlink
from os import mkdir
from os.path import basename
from os.path import exists
from os.path import isabs
from os.path import join
from pysvn import Client, ClientError, Revision, opt_revision_kind
from errno import ENOENT

from ufwi_rpcd.common import tr
from ufwi_rpcd.common.logger import LoggerChild
from ufwi_rpcd.backend.component import Component
from ufwi_rpcd.common.process import createProcess, waitProcess

from .error import VersionningError

"""
See developper documentation at http://pysvn.tigris.org/docs/pysvn_prog_guide.html
"""

class Repository(LoggerChild):
    """
    By default, a commit will add any files it finds in the repository dir (it's his after all).
    You can change this behaviour with setWhiteList(white_list), where white_list is an iterable of file names
    """

    def __init__(self, logger, checkout_directory, client=None):
        LoggerChild.__init__(self, logger)

        if client is None:
            client = Client()

        self.client = client
        self.checkout_directory = checkout_directory

        self.use_white_list = False
        self.white_list = None

    def retry(self, function, args=(), kwargs={}, no_log=False):
        # Log the action
        arg_text = [repr(arg) for arg in args]
        for key, value in kwargs.iteritems():
            arg_text.append('%s=%r' % (key, value))
        text = 'pysvn.%s(%s)' % (function.__name__, ', '.join(arg_text))
        if not no_log:
            self.debug("Call %s" % text)

        # Try one
        try:
            return function(*args, **kwargs)
        except ClientError, err:
            if not no_log:
                self.writeError(err, "pysvn error on %s" % text, DEBUG)

        # Error: cleanup and retry
        self.client.cleanup(self.checkout_directory)
        result = function(*args, **kwargs)
        self.debug("But retry was ok")
        return result

    def setWhiteList(self, white_list):
        """
        The white list should be an iterable of file names
        """
        self.use_white_list = True
        self.white_list = map(basename, white_list)

    def update(self, revision_nb=0):
        if revision_nb == 0:
            revisions = self.retry(self.client.update, (join(self.checkout_directory, '.'),))
            revision = revisions[0] #got a list
            if revision.kind == opt_revision_kind.number:
                self.debug(
                    "Updated %s to r%s (latest)." %
                    (self.checkout_directory, revision.number)
                    )
            return
        revision = Revision(opt_revision_kind.number, revision_nb)
        self.retry(
            self.client.update,
            args=(join(self.checkout_directory, '.'),),
            kwargs={'revision': revision}
            )

        self.debug(
            "Updated %s to r%s (explicitely)." %
            (self.checkout_directory, revision_nb)
            )

    def commit(self, message, delete_missing=True):
        """
        adds any unknown file and commits everything
        Handle the delete_missing flag with extreme care.
        """
        if not message:
            raise VersionningError(tr("Commit message cannot be empty."))
        statuses = self.retry(self.client.status, args=(self.checkout_directory,))
        for status in statuses:
            full_path = status['path']
            if not status['is_versioned']:
                if self.use_white_list:
                    file_name = basename(full_path)
                    if file_name not in self.white_list:
                        #skip file
                        self.warning("skipping %s" % file_name)
                        continue
                #in whitelist
                self.retry(self.client.add, args=(full_path,))
            elif delete_missing and not exists(full_path):
                self.info('Versionned but not present: deleting %s' % full_path)
                self.delete(full_path)

        self.retry(self.client.checkin, args=(self.checkout_directory, message))
        self.update()

    def correctPath(self, filename):

        if isabs(filename):
            return filename
        return join(self.checkout_directory, filename)

    def delete(self, filename):
        # When we ask 'versionning' to remove a file from the svn,
        # -> if it was not in the svn yet, unlink
        # -> if it does not exist, pass

        filename = self.correctPath(filename)

        try:
            self.retry(self.client.remove, args=(filename,), no_log=True)
        except:
            if exists(filename):
                raise
            #if file does not exist, chances are it is normal that it cannot be deleted
        else:
            self.debug("svn DELETED %s" % filename)
        finally:
            if not exists(filename):
                return
            try:
                unlink(filename)
                self.debug("filesystem DELETED %s" % filename)
            except OSError, err:
                if err.errno != ENOENT:
                    raise

class VersionningComponent(Component):
    API_VERSION = 1
    NAME = 'versionning'
    VERSION = '1.0'
    REQUIRES = ()

    def __init__(self):
        Component.__init__(self)
        self.repositories = {}
        self.client = Client()

    def init(self, core):
        vardir = core.config.get('CORE', 'vardir')
        self.repositories_base = join(vardir, "repositories")
        self.checkout_base = join(vardir, "versionned")
        for directory in (self.repositories_base, self.checkout_base):
            if not exists(directory):
                mkdir(directory)

    def getRepository(self, name):
        if name not in self.repositories:
            self.createOrLoadRepository(name)

        return self.repositories[name]

    def createOrLoadRepository(self, name):
        repository_directory = join(self.repositories_base, name)
        checkout_directory = join(self.checkout_base, name)

        must_create = not exists(repository_directory)
        assert must_create != exists(checkout_directory)

        if must_create:
            self.createRepository(repository_directory, checkout_directory)

        repository = Repository(self, checkout_directory, client=self.client)
        if must_create:
            repository.update()
        self.repositories[name] = repository

    def createRepository(self, repository_directory, checkout_directory):
        process = createProcess(self, ["svnadmin", "create", repository_directory])
        result = waitProcess(self, process, 20)
        if result != 0:
            raise VersionningError("error creating repository %s" % repository_directory)

        self.client.checkout("file://%s" % repository_directory, checkout_directory)

    def service_listRepositories(self, context):
        for key, value in self.repositories.iteritems():
            yield key, value.checkout_directory

    def service_commit_all(self, context, message):
        for repository in self.repositories.values():
            repository.commit(message, delete_missing=True)

