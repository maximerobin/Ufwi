from logging import getLogger

from ufwi_rpcd.client.error import RpcdError
from ufwi_rpcc_qt.keepalive import KeepAlive
from ufwi_conf.client.system.network import QNetObject
from ufwi_conf.common.netcfg_rw import deserialize

logger = getLogger('root')

class Client(object):

    def __init__(self):
        self._async = Async()
    def clone(self, name):
        return self

    def async(self):
        return self._async

class Async(object):
    def call(self, component, call, *args, **kwargs):
        callback = kwargs.get('callback')
        assert callback is not None, "supply callback"
        errback = kwargs.get('errback')
        assert errback is not None, "supply errback"

class MainWindow(object):
    def __init__(self, backend_values):
        self.backend_values = backend_values
        self.client = Client()
        self.keep_alive = KeepAlive(self)

    def noop(self, *args, **kwargs):
        pass

    def init_call(self, *call):
        if call in self.backend_values:
            return self.backend_values[call]
        raise RpcdError("calling error", "unregistered call:%s" % unicode(call))

    readonly = False

    def __getattr__(self, attrname):
        if attrname == 'debug':
            return True
        for item in ('info error warning critical'.split()):
            if attrname == item:
                return getattr(logger, item)
        logger.info("called mainwindow.%s" % attrname)

        return self.noop

a_netconfig = {'DATASTRUCTURE_VERSION': 1,
 'bondings': {},
 'ethernets': {'0': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth7',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth7',
                     'unique_id': 805306378,
                     'user_label': 'eth7',
                     'vlans': {}},
               '1': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth6',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth6',
                     'unique_id': 805306377,
                     'user_label': 'eth6',
                     'vlans': {}},
               '2': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth8',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth8',
                     'unique_id': 805306379,
                     'user_label': 'eth8',
                     'vlans': {}},
               '3': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth9',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth9',
                     'unique_id': 805306380,
                     'user_label': 'eth9',
                     'vlans': {}},
               '4': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth5',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth5',
                     'unique_id': 805306382,
                     'user_label': 'eth5',
                     'vlans': {}},
               '5': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth2',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth2',
                     'unique_id': 805306383,
                     'user_label': 'eth2',
                     'vlans': {}},
               '6': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth0',
                     'mac_address': '',
                     'nets': {'0': {'label': '172.16.0.0/16',
                                    'primary_ip_addrs': {'__type__': 'set'},
                                    'secondary_ip_addrs': {'__type__': 'set'},
                                    'service_ip_addrs': {'0': {'IP': '172.16.1.21',
                                                               '__type__': 'IP'},
                                                         '__type__': 'set'},
                                    'string_desc': '172.16.0.0/16',
                                    'unique_id': 268435455}},
                     'reserved_for_ha': False,
                     'routes': {'0': {'dst': '0.0.0.0/0',
                                      'router': '172.16.0.1',
                                      'unique_id': 536870911}},
                     'system_name': 'eth0',
                     'unique_id': 805306384,
                     'user_label': 'eth0',
                     'vlans': {}},
               '7': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth3',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth3',
                     'unique_id': 805306385,
                     'user_label': 'eth3',
                     'vlans': {}},
               '8': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth4',
                     'mac_address': '',
                     'nets': {},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth4',
                     'unique_id': 805306386,
                     'user_label': 'eth4',
                     'vlans': {}},
               '9': {'aggregated': False,
                     'eth_auto': True,
                     'hard_label': 'eth1',
                     'mac_address': '',
                     'nets': {'0': {'label': '192.168.1.0/24',
                                    'primary_ip_addrs': {'__type__': 'set'},
                                    'secondary_ip_addrs': {'__type__': 'set'},
                                    'service_ip_addrs': {'0': {'IP': '192.168.1.1',
                                                               '__type__': 'IP'},
                                                         '__type__': 'set'},
                                    'string_desc': '192.168.1.0/24',
                                    'unique_id': 268435456}},
                     'reserved_for_ha': False,
                     'routes': {},
                     'system_name': 'eth1',
                     'unique_id': 805306381,
                     'user_label': 'eth1',
                     'vlans': {}}},
 'vlans': {}
 }

def init_qnetobject():
    q_netobject = QNetObject.getInstance()
    q_netobject.cfg = deserialize(a_netconfig)

