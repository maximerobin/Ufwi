++++++++++++++++++
NuFace backend API
++++++++++++++++++

Resources
=========

Create base objects (ruleset and networks) for our examples:

>>> from nuface.forward.client import createLocalClient
>>> from nuface.forward.mockup import Ruleset
>>> from nuface.forward.resource import Resources, InterfaceResource, NetworkResource, HostResource
>>> local_client = createLocalClient()
>>> ruleset = Ruleset(local_client)
>>> networks = Resources(ruleset)

Create an interface
-------------------

>>> eth0 = InterfaceResource(networks, {'id': u'eth0', 'name': u'eth0'})
>>> networks._create(eth0)
>>> unicode(eth0)
u'The "eth0" interface'
>>> eth0
<InterfaceResource id='eth0'>
>>> eth0.getAddressTypes()
set([u'interface', u'IPv4', u'IPv6'])

Create an IPv4 network
----------------------

>>> from IPy import IP
>>> lan = NetworkResource(eth0, {'id': u'LAN', 'address': '192.168.1.0/24'})
>>> eth0._create(lan)
>>> unicode(lan)
u'The "LAN" network (192.168.1.0/24)'
>>> lan
<NetworkResource id='LAN'>

Create an IPv4 host
-------------------

>>> host = HostResource(lan, {'id': u'bart', 'address': '192.168.1.19'})
>>> lan._create(host)
>>> unicode(host)
u'The "bart" host (192.168.1.19)'
>>> host
<HostResource id='bart'>
>>> host.getAddressTypes()
set([u'IPv4'])

XML export
----------

>>> from nucentral.common.xml_etree import etree, indent
>>> from StringIO import StringIO
>>> xml = etree.Element("ruleset")
>>> output = StringIO()
>>> node = eth0.exportXML(xml)
>>> doc = etree.ElementTree(xml)
>>> indent(xml)
>>> doc.write(output)
>>> print output.getvalue()
<ruleset>
   <interface id="eth0" name="eth0">
      <network address="192.168.1.0/24" id="LAN">
         <host address="192.168.1.19" id="bart" />
      </network>
   </interface>
</ruleset>
<BLANKLINE>

Delete a resource
-----------------

Current resource tree:

>>> def dumpTree(parent, depth=0):
...    if depth:
...       prefix = u"+" + "-" * depth + u"> "
...    else:
...       prefix = u''
...    for resource in parent.getChildren():
...       print prefix + unicode(resource)
...       dumpTree(resource, depth + 1)
...
>>> dumpTree(networks)
The "eth0" interface
+-> The "LAN" network (192.168.1.0/24)
+--> The "bart" host (192.168.1.19)

Delete the host "bart":

>>> networks.delete(u'bart')
>>> dumpTree(networks)
The "eth0" interface
+-> The "LAN" network (192.168.1.0/24)

Modify a resource
-----------------

>>> networks.modifyObject(lan, {'id': u'My LAN', 'address': '10.4.5.0/24'}, False)
>>> dumpTree(networks)
The "eth0" interface
+-> The "My LAN" network (10.4.5.0/24)


Protocols
=========

Create base objects (ruleset and protocols) for our examples:

>>> from nuface.forward.protocol import Protocols
>>> ruleset = Ruleset(local_client)
>>> protocols = Protocols(ruleset)

Create a TCP protocol
---------------------

>>> protocols.createObject({'id': u'http', 'layer4': 'tcp', 'sport': '1024:65535', 'dport': '80'}, False)
>>> http = protocols[u'http']
>>> unicode(http)
u'The protocol "http"'
>>> http
<ProtocolTcp id='http'>
>>> http.sport
<PortInterval 1024:65535>

Create an UDP protocol
----------------------

>>> protocols.createObject({'id': u'dns', 'layer4': 'udp', 'dport': '53'}, False)
>>> dns = protocols[u'dns']
>>> unicode(dns)
u'The protocol "dns"'
>>> dns
<ProtocolUdp id='dns'>

Create an ICMP protocol
-----------------------

>>> protocols.createObject({'id': u'ping', 'layer4': 'icmp', 'type': 8}, False)
>>> ping = protocols[u'ping']
>>> unicode(ping)
u'The protocol "ping"'
>>> ping
<ProtocolIcmp id='ping'>

Test XML export
---------------

>>> from nucentral.common.xml_etree import etree, indent
>>> from StringIO import StringIO
>>> xml = etree.Element("ruleset")
>>> output = StringIO()
>>> node = protocols.exportXML(xml)
>>> doc = etree.ElementTree(xml)
>>> indent(xml)
>>> doc.write(output)
>>> print output.getvalue()
<ruleset>
   <protocols>
      <udp dport="53">dns</udp>
      <tcp dport="80" sport="1024:65535">http</tcp>
      <icmp type="8">ping</icmp>
   </protocols>
</ruleset>
<BLANKLINE>

Delete a protocol
-----------------

>>> protocols.delete(u'ping')
>>> from pprint import pprint
>>> pprint(protocols.values())
[<ProtocolTcp id='http'>, <ProtocolUdp id='dns'>]

Modify a protocol
-----------------

>>> http = protocols[u'http']
>>> protocols.modifyObject(http, {'id': u'https', 'dport': '443'}, False)
>>> pprint(protocols.values())
[<ProtocolTcp id='https'>, <ProtocolUdp id='dns'>]

