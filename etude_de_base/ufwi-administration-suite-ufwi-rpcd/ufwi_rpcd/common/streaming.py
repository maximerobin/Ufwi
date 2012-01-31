"""
Copyright (C) 2007-2011 EdenWall Technologies
Written by Romain Bignon <romain AT inl.fr>

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

$Id$
"""

import time

VERSION = '3.0rc1'
HELLO = 'streaming %s\n' % VERSION
CONNECT_TIMEOUT = 5.0   # seconds
ACK = 'ack\n'

def parseVersion(hello):
    return hello.strip()[10:]

class UDPacketError(Exception):
    pass

class UDPacket:

    def __init__(self, id='', data=[], error=''):
        self.id = id
        self.timestamp = int(time.time())
        self.data = data
        self.columns = []
        self.error = error

    def serialize(self):

        data = 'ts:%d\n' % int(time.time())
        data += 'id:%s\n' % self.id
        if self.error:
            data += 'error:%s\n' % self.error.replace('\n', '\t')
        if self.columns:
            data += 'columns:%s\n' % '\t'.join(str(s) for s in self.columns)

        data += '\n'
        data += '\t'.join(str(s) for s in self.data)

        return data

    def unSerialize(self, data):

        header = True
        for line in data.split('\n'):

            if header:
                if line == '':
                    header = False
                else:
                    line = line.split(':')
                    key = line[0]
                    value = ':'.join(line[1:])

                    if key == 'ts':
                        self.timestamp = int(value)
                    elif key == 'id':
                        self.id = int(value)
                    elif key == 'columns':
                        self.columns = value.split('\t')
                    elif key == 'error':
                        self.error = value.replace('\t', '\n')
                    else:
                        raise UDPacketError('Unable to parse: incorrect header (%s)' % key)
            else:
                self.data = line.split('\t')

