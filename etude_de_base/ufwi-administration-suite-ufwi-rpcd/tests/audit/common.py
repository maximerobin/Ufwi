from os import getenv
from os.path import join
from tempfile import mkdtemp
from nucentral.core.audit_base import Connector

def setup_connector():
    sqlite = getenv("NUCENTRAL_USE_SQLITE")
    if sqlite:
        directory = mkdtemp(prefix='testaudit')
        base = join(directory, "audit.db")
        base = "sqlite:////%s" % base
        return Connector.getInstance(db_url=base, db_create=True, echo=True)
    connector = Connector.getInstance()
    connector.echo=True
    return connector

