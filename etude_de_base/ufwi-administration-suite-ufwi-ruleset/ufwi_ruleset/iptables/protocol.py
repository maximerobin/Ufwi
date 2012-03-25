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

from ufwi_rpcd.backend import tr
from ufwi_ruleset.forward.protocol import ProtocolIGMP, ProtocolLayer4
from ufwi_ruleset.iptables import IptablesError
from ufwi_ruleset.iptables.arguments import Arguments

def formatProtocol(protocol, chain):
    if protocol.layer3 in ("ipv4", "ipv6"):
        # Layer 3 protocol
        return Arguments()

    # Layer 4 protocol
    args = Arguments('-p', protocol.layer4)
    if protocol.layer4 in (u"tcp", u"udp"):
        if protocol.sport:
            args += Arguments('--sport', unicode(protocol.sport))
        else:
            args += Arguments('--sport', '1:65535')
        if protocol.dport:
            args += Arguments('--dport', unicode(protocol.dport))
        else:
            args += Arguments('--dport', '1:65535')
        if (protocol.layer4 == u"tcp") and (chain != "INPUT"):
            # First TCP packet must be a SYN
            args += Arguments('--syn')
        args += Arguments('-m', 'state', '--state', 'NEW')
    elif protocol.layer4 == u"icmp":
        if protocol.type is not None:
            text = unicode(protocol.type)
            if protocol.code is not None:
                text += u"/%s" % protocol.code
            args += Arguments(u'--icmp-type', text)
    elif protocol.layer4 == u"icmpv6":
        if protocol.type is not None:
            text = unicode(protocol.type)
            if protocol.code is not None:
                text += u"/%s" % protocol.code
            args += Arguments(u'--icmpv6-type', text)
    elif isinstance(protocol, (ProtocolIGMP, ProtocolLayer4)):
        # no extra parameter
        pass
    else:
        raise IptablesError(tr('The "%s" layer 4 protocol is not supported'), protocol.layer4)
    return args

