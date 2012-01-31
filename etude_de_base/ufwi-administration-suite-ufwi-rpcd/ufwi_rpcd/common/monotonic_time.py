
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

import platform

if platform.system() not in ('Windows', 'Darwin'):
    from ctypes import Structure, c_long, CDLL, c_int, POINTER, byref
    from ctypes.util import find_library

    if platform.system() == 'FreeBSD':
        CLOCK_MONOTONIC = 4
    else:
        CLOCK_MONOTONIC = 1

    class timespec(Structure):
        _fields_ = [
            ('tv_sec', c_long),
            ('tv_nsec', c_long)
        ]

    librt_filename = find_library('rt')
    if not librt_filename:
        # On Debian Lenny (Python 2.5.2), find_library() is unable
        # to locate /lib/librt.so.1
        librt_filename = 'librt.so.1'
    librt = CDLL(librt_filename)
    _clock_gettime = librt.clock_gettime
    _clock_gettime.argtypes = (c_int, POINTER(timespec))

    def monotonic_time():
        """
        Clock that cannot be set and represents monotonic time since some
        unspecified starting point. The unit is a second.
        """
        t = timespec()
        _clock_gettime(CLOCK_MONOTONIC, byref(t))
        return t.tv_sec + t.tv_nsec / 1e9
else:
    try:
        from win32api import GetTickCount
        def monotonic_time():
            return GetTickCount / 1000.0
    except ImportError:
        from time import time as monotonic_time

