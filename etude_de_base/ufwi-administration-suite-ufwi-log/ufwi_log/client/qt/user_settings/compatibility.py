from sys import exit

from ufwi_rpcd.client import RpcdError
from ufwi_rpcd.common import tr
from ufwi_rpcc_qt.central_window import STANDALONE

SUPPORTED_VERSIONS = ("3.0-1", "3.0-2", "3.0-3")
CLIENT_VERSION = "3.0-3"

class Compatibility:
    def __init__(self, main_window, client):
        self.client = client
        self.main_window = main_window
        self.getVersions()
        self.getFeatures()

    def getVersions(self):
        self.client_version = CLIENT_VERSION
        self._ufwi_logVersion()
        self._reportingVersion()

    def _ufwi_logVersion(self):
        client_attr = {
            'version': self.client_version,
        }
        try:
            server_attr = self.client.call("ufwi_log", "setupClient", client_attr)
        except RpcdError, err:
            try:
                self.ufwi_log_server_version = self.client.call('ufwi_log','getComponentVersion')
            except RpcdError, err:
                self.main_window.error(
                    tr("Log backend not found! Exiting."),
                    dialog=(self.main_window.standalone == STANDALONE))
                exit(1)

                if not self.client.call('acl', 'check', 'ufwi_log', 'table'):
                    exit(1)

                self.main_window.use_edenwall = self.client.call('CORE', 'useEdenWall')
        else:
            self.ufwi_log_server_version = server_attr['version']

    def _reportingVersion(self):
        try:
            self.reporting_server_version = self.client.call('reporting', 'getComponentVersion')
        except RpcdError, err:
                self.main_window.error(
                    tr("Log backend not found! Exiting."),
                    dialog=(self.main_window.standalone == STANDALONE))
                exit(1)


    def getFeatures(self):
        self.input_packet_frag = True
        self.csvexport_all = True
        self.authfail = True
        self.print_enterprise = True
        self.user_id = False

        if self.ufwi_log_server_version < '3.0-3':
            self.user_id = True

        if self.ufwi_log_server_version == "3.0-1":
            self.input_packet_frag = False
            self.csvexport_all = False
            self.authfail = False

        if self.reporting_server_version == "3.0-1":
            self.print_enterprise = False


