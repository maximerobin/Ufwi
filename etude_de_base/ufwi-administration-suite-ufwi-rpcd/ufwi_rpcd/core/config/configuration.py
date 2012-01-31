"""
Copyright (C) 2009-2011 EdenWall Technologies
Written by Feth AREZKI <farezki AT edenwall.com>
           Romain BIGNON <rbignon AT edenwall.com>

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

from ufwi_rpcd.common.xml_etree import etree as ET
from ufwi_rpcd.backend.exceptions import ConfigError
from ufwi_rpcd.backend.variables_store import VariablesStore

VERSION = '1'

INVALID_SEQUENCE_NUMBER = -5555
SEQUENCE_TAG = 'sequence'

def validateSequenceNumber(sequence_number):
    return isinstance(sequence_number, int) and sequence_number > 0

class Configuration(VariablesStore):

    def __init__(self):
        VariablesStore.__init__(self)
        self.sequence_number = INVALID_SEQUENCE_NUMBER

    def mkXMLTree(self, sequence_number):
        root = VariablesStore.mkXMLTree(self)

        seq = ET.SubElement(root, SEQUENCE_TAG)
        if not validateSequenceNumber(sequence_number):
            raise ConfigError('Trying to write invalid sequence number: %s' % sequence_number)
        seq.text = unicode(sequence_number)
        return root

    def save(self, filename, sequence_number):
        root = self.mkXMLTree(sequence_number)
        return self._save(root, filename)

    def load(self, filename):
        self.sequence_number = INVALID_SEQUENCE_NUMBER
        VariablesStore.load(self, filename)
        if not validateSequenceNumber(self.sequence_number):
            raise ConfigError("Invalid file: the tag %s must define a positive integer (read default or %i )" % (SEQUENCE_TAG, self.sequence_number))

    def parseTag(self, child, key, _type):
        if child.tag == SEQUENCE_TAG:
            if self.sequence_number != INVALID_SEQUENCE_NUMBER:
                raise ConfigError("Invalid file: several %s tags found" % SEQUENCE_TAG)
            self.sequence_number = int(child.text)
        VariablesStore.parseTag(self, child, key, _type)

