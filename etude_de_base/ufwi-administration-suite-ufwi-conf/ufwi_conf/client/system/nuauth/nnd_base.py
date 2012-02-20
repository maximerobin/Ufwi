from PyQt4.QtCore import QObject, SIGNAL
from PyQt4.QtGui import QDialog

from ufwi_conf.common.user_dir.base import AD, LDAP, EDIRECTORY

def bindbutton(button, callback):
    QObject.connect(button, SIGNAL("clicked()"), callback)

def bindlineedit(lineedit, callback):
    # textEdited => triggered only by human interaction
    QObject.connect(lineedit, SIGNAL("textEdited(QString)"), callback)

def infer_bind_dn(login_or_bind_dn, user_base_dn):
    return u"cn=%s,%s" % (login_or_bind_dn, unicode(user_base_dn))

def infer_login(bind_dn):
    index = bind_dn.find(',')
    if index > -1 and len(bind_dn) > 4:
        return bind_dn[3:index]
    return bind_dn

def infer_user_base_dn(realm):
    realm = unicode(realm).strip().lower()
    dc_parts = realm.split('.')
    return "cn=users,dc=%s" % ",dc=".join(dc_parts)

def pretty_bind_dn(bind_dn, user_base_dn):
    login = infer_login(bind_dn)
    if infer_bind_dn(login, user_base_dn) == bind_dn:
        return login
    return bind_dn


_DEFAULT_USER_FILTER = {
        AD: "sAMAccountName=%%s",
        LDAP: "(&(uid=%%s)(objectClass=posixAccount))",
        EDIRECTORY: "(&(uid=%%s)(objectClass=Person))",
    }
_DEFAULT_USER_MEMBER_ATTR = {
        AD: "memberOf",
    }
_DEFAULT_GROUP_ATTR_NAME = {
        AD: "cn",
        LDAP: "cn",
        EDIRECTORY: "dn",
    }
_DEFAULT_GROUP_ENUM_FILTER = {
        AD: "objectClass=group",
        EDIRECTORY: "(objectClass=groupOfNames)",
    }
_DEFAULT_GROUP_FILTER = {
        AD: "cn=%%s",
        LDAP: "objectClass=posixGroup",
        EDIRECTORY: "(objectClass=groupOfNames)",
    }
_DEFAULT_GROUP_MEMBER_ATTR = {
        LDAP: "memberUid",
        EDIRECTORY: "securityEquals",
    }

DEFAULT_PARAMS = {
    "group_attr_name": _DEFAULT_GROUP_ATTR_NAME,
    "group_base_dn": {},
    "group_enum_filter": _DEFAULT_GROUP_ENUM_FILTER,
    "group_filter": _DEFAULT_GROUP_FILTER,
    "group_member_attr": _DEFAULT_GROUP_MEMBER_ATTR,
    "user_base_dn": {},
    "user_filter": _DEFAULT_USER_FILTER,
    "user_member_attr": _DEFAULT_USER_MEMBER_ATTR,
}

_NOTFOUNDDICT = {}

def get_default_param(param, type_):
    return DEFAULT_PARAMS.get(param, _NOTFOUNDDICT).get(type_, "")

SHOW_CONTROLS = {
    "Always": """
        user_base_dn
        group_base_dn
        user_filter
        """.split(),
    AD: """
        group_enum_filter
        user_member_attr
        """.split(),
    LDAP: """
        group_attr_name
        group_base_dn
        group_filter
        group_member_attr
        user_base_dn
        """.split(),
    EDIRECTORY: """
        group_member_attr
        """.split(),
}


class NndDialog(QDialog):
    """
    Derived class must also inherit of a Qt designer widget
    """
    def __init__(self, nnd_widget, conf, title="", name=""):
        QDialog.__init__(self)
        self.nnd_widget = nnd_widget
        self.name = name
        self.conf = conf
        self.setupUi(self)
        self.setWindowTitle(title)
        self.bindsignals(nnd_widget)

    def bindsignals(self, widget):
        pass

