#!/usr/bin/python2.5

from PyQt4.QtGui import QApplication
from sys import argv, exit, stderr

from ufwi_conf.client.services.dhcp import DhcpFrontend
from ufwi_conf.common.dhcpcfg import DHCPCfg

from mockup import MainWindow, init_qnetobject

if __name__ != '__main__':
    stderr.write("%s is meant to be ran directly\n" % __file__)
    exit(2)

app = QApplication(argv)
client = None

dhcpcfg = DHCPCfg()

init_qnetobject()

backend_values = {
    ("dhcp", "getDhcpConfig"): dhcpcfg.serialize()
}

parent = MainWindow(backend_values)
frontend = DhcpFrontend(client, parent=parent)
frontend.show()
frontend.loaded()
app.exec_()

