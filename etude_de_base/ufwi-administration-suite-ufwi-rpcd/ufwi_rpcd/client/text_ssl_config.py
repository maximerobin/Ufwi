from ufwi_rpcd.common.logger import Logger
from .ssl_config import ClientSSLConfig

class TextClientSSLConfig(ClientSSLConfig, Logger):
    def __init__(self):
        ClientSSLConfig.__init__(self)
        Logger.__init__(self, "ssl")

    def sslInfo(self, info):
        info.logInto(self)

