#!/usr/bin/python2.5

from PyQt4.QtGui import QApplication
from sys import argv

from ufwi_conf.common.ha_cfg import HAConf
from ufwi_conf.client.system.ha import HAConfigFrontend
from ufwi_conf.client.qt.ufwi_conf_form import NuConfModuleDisabled
from ufwi_conf.client.system.ha import QHAObject

from mockup import MainWindow, init_qnetobject, Client

class TestFrontend(object):
    app = None
    app_exec = False

    def __init__(self):
        if TestFrontend.app is None:
            TestFrontend.app = QApplication(argv)
        mainwindow = MainWindow(self.backend_values())
        frontend = self.frontend(mainwindow)
        frontend.show()
        if not TestFrontend.app_exec:
            TestFrontend.app.exec_()
            TestFrontend.app_exec = True

    def backend_values(self):
        raise NotImplementedError()

    def frontend(self, mainwindow):
        raise NotImplementedError()

class TestHA(TestFrontend):

    def frontend(self, mainwindow):
        client = Client()
        return HAConfigFrontend(client, parent=mainwindow)

class TestHANoBackend(TestHA):
    def backend_values(self):
        return {
        ('ha', "getState"): None
    }

class TestHAWithBackend(TestHA):
    def backend_values(self):
        init_qnetobject()
        serialized_ha_conf = {
            'DATASTRUCTURE_VERSION': 3,
            "ha_type": "PRIMARY",
            "interface_id": "eth0",
            #"interface_id": "268435455",
            "interface_name": "eth0",
            "primary_hostname": "primary",

        }
        QHAObject.getInstance().cfg = HAConf.deserialize(serialized_ha_conf)
        return {
        #('ha', "getState"): ['NOT_REGISTERED', 0, '']
        ('ha', "getState"): ['PRIMARY', 0, '']
    }

if __name__ == '__main__':
    try:
        t = TestHANoBackend()
    except NuConfModuleDisabled:
        pass
    else:
        assert False, "should not load without a backend"

    t = TestHAWithBackend()

