from ufwi_rpcd.common import tr
from ufwi_rpcd.common.network import HOSTNAME_OR_FQDN_REGEX_PART
from ufwi_rpcd.common.validators import check_dn
import re

_HOST_PORT_RE = re.compile(r"^ldap[s]{0,1}://%s:[0-9]+$" % HOSTNAME_OR_FQDN_REGEX_PART)

def _fixuriitem(uri, supplied_port=None):
    for word in uri.split():
        word = word.strip()

        if not word.startswith(('ldap://', 'ldaps://')):
            if word.endswith(":636"):
                proto = "ldaps"
            else:
                proto = "ldap"
            word = "%s://%s" % (proto, word)

        if not _HOST_PORT_RE.match(word):
            if supplied_port:
                port = supplied_port
            else:
                port = "636" if word.startswith("ldaps") else "389"
            word = "%s:%s" % (word, port)

        yield word

def cleanuri(uri, default_port=None):
    return ' '.join(_fixuriitem(uri, supplied_port=default_port))

# TODO: merge valid_dn and check_dn
def valid_dn(ldap_dn):
#    if not ldap_dn:
#        return True
    for dn_part in ldap_dn.split(','):
        if not check_dn(dn_part.strip()):
            return False
    return True

def dnproperty(attrname):
    real_attrname = '__%s' % attrname

    def setter(self, value):
        if value and not valid_dn:
            raise ValueError(tr("Invalid dn: %s", value))
        setattr(self, real_attrname, value)

    def getter(self):
        return getattr(self, real_attrname, '')

    setattr(setter, '__name__', '_set%s' % attrname)
    setattr(getter, '__name__', '_get%s' % attrname)

    return property(fset=setter, fget=getter)

