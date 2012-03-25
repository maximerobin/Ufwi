#!/usr/bin/python

from sys import argv, exit, stderr
from PyQt4.QtGui import QApplication

if __name__ != '__main__':
    stderr.write("%s is meant to be ran directly\n" % __file__)
    exit(2)

app = QApplication(argv)

try:
    from ufwi_conf.client.system.nuauth.user_dir import NuauthFrontEnd
    from ufwi_conf.common.user_dir import NuauthCfg
    from ufwi_conf.client.tests.mockup import MainWindow, init_qnetobject
except ImportError:
    stderr.write(
        """ImportError. Probably a PYTHONPATH problem.
I personnaly cd into edenwall's src/ and use
% PYTHONPATH=ufwi_rpcd:ufwi_conf ufwi_conf/ufwi_conf/client/tests/test_nuauth.py

"""
        )
    raise

client = None

nuauthcfg = NuauthCfg()

init_qnetobject()

config = {'DATASTRUCTURE_VERSION': 4,
 '__type__': 'ufwi_conf.common.user_dir.base.NuauthCfg',
 'auth': {'DATASTRUCTURE_VERSION': 1,
          '__type__': 'ufwi_conf.common.user_dir.base.SameAsOrgAuth'},
 'org': {'DATASTRUCTURE_VERSION': 1,
         '__type__': 'ufwi_conf.common.user_dir.base.NndOrg',
         'default_domain': 'toto',
         'domains': {'__type__': 'dict',
                     'toto': {'DATASTRUCTURE_VERSION': 2,
                              '__type__': 'ufwi_conf.common.user_dir.base.NndDomain',
                              'group_attr_name': 'cn',
                              'group_base_dn': 'cn=users,dc=otgo',
                              'group_enum_filter': 'objectClass=group3',
                              'group_filter': 'cn=%%s',
                              'group_member_attr': '',
                              'label': 'toto',
                              'realm': 'otgo',
                              'servers': {'0': {'DATASTRUCTURE_VERSION': 2,
                                                '__type__': 'ufwi_conf.common.user_dir.base.NndServer',
                                                'bind_dn': '',
                                                'bind_pw': '',
                                                'ca_cert': '',
                                                'checkcert': False,
                                                'group_attr_name': '',
                                                'group_base_dn': '',
                                                'group_enum_filter': '',
                                                'group_filter': '',
                                                'group_member_attr': '',
                                                'label': 'sdsq',
                                                'ldapuri': 'ldap://dqsd:389',
                                                'tls': False,
                                                'user_attr_name': '',
                                                'user_base_dn': 'sss',
                                                'user_filter': '',
                                                'user_member_attr': ''},
                                          '__type__': 'list'},
                              'type_': 'AD',
                              'user_attr_name': '',
                              'user_base_dn': 'cn=users,dc=otgo',
                              'user_filter': 'sAMAccountName=%%s',
                              'user_member_attr': 'memberOf'}}}
        }
backend_values = {
    ("nuauth", "getNuauthConfig"):  config, #nuauthcfg.serialize(),
    ("nuauth", "availableModules"): {
        'auth': ['RADIUS', 'KERBEROS', 'KERBEROS_AD', 'SAME', 'NOT CONFIGURED'],
        'group': ['LDAP', 'AD', 'NND', 'NOT CONFIGURED']
    }
}

parent = MainWindow(backend_values)
frontend = NuauthFrontEnd(client, parent=parent)
frontend.setMinimumWidth(800)
frontend.setMinimumHeight(500)
frontend.show()
app.exec_()

app = QApplication(argv)

app.exec_()

