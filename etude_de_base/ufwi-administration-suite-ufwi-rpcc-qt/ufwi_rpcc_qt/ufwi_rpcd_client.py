
"""
Copyright (C) 2009-2011 EdenWall Technologies

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

from ufwi_rpcd.client import RpcdClientBase
from ufwi_rpcc_qt.streaming import UDPStreamingReceiver
from ufwi_rpcc_qt.async_client import AsyncClient

DEFAULT_STREAMING_PORT = 8080   # udp

class RpcdClient(RpcdClientBase):
    def __init__(self, host=None,
    streaming_port=DEFAULT_STREAMING_PORT,
    **kwargs):

        self.streaming_port = streaming_port
        self._streaming = None
        self.streaming_failed = False
        self._async = None

        RpcdClientBase.__init__(self, host, **kwargs)

    def streaming(self):
        if self._streaming is None and not self.streaming_failed:
            try:
                self._streaming = UDPStreamingReceiver(self)
            except Exception:
                # At first error, disable streaming
                # to avoid similar (duplicate) errors
                self.streaming_failed = True
                raise
        return self._streaming

    def async(self, create=True):
        if self._async:
            return self._async
        if not create:
            return None

        try:
            async_client = self.clone("async_client")
            self._async = AsyncClient(async_client, self)
            return self._async
        except (TypeError, AttributeError):
            raise TypeError('The asynchone class does\'t match the AsyncClientInterface')
        return None

    def logout(self):
        if self._streaming is not None:
            self._streaming.stop()

        if self._async:
            self._async.stop()
            self._async = None

        RpcdClientBase.logout(self)

