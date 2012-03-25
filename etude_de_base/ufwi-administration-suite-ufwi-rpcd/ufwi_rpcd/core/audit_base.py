"""
Copyright (C) 2010-2011 EdenWall Technologies
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
from elixir import setup_all
from sqlalchemy import MetaData
from sqlalchemy.orm import scoped_session, sessionmaker
from ConfigParser import SafeConfigParser

from .conf_files import RPCD_CONF_FILES
class Connector(object):
    instance = None

    @classmethod
    def getInstance(cls, db_url=None, db_create=False, echo=False):
        if cls.instance is not None:
            return cls.instance

        if not db_url:
            config = SafeConfigParser()
            config.read(RPCD_CONF_FILES)
            db_url = config.get("audit", "db_url")
            db_create = config.getboolean("audit", "db_create_tables")

        cls.instance = Connector(db_url, db_create, echo)
        return cls.instance

    def __init__(self, db_url, db_create, echo):
        self.db_url = db_url
        self.db_create = db_create
        self._elixir_prepared = False
        self.session = None
        self.metadata = None
        self.echo = echo
        self.prepare_elixir()

    def prepare_elixir(self):
        if self._elixir_prepared:
            return

        self.session = scoped_session(
            sessionmaker(
                autoflush=False,
                )
            )
        self.metadata = MetaData()
        self.metadata.bind = self.db_url
        self.metadata.bind.echo = self.echo
        self._elixir_prepared = True

    def _setecho(self, value):
        self._echo = value
        if self._elixir_prepared:
            self.metadata.bind.echo = value

    def _readecho(self):
        return self._echo

    echo = property(fset=_setecho, fget=_readecho)

    def setup(self):
        setup_all(session=self.session, metadata=self.metadata)
        if self.db_create:
            print "creating database"
            self.metadata.create_all()

    def commit(self):
        self.session.commit()

    def rollback(self):
        self.session.rollback()

