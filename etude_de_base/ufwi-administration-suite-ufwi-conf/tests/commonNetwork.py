from py import test
from IPy import IP
from nuconf.common.netcfg_rw import deserialize
from nuconf.common.net_objects_rw import NetRW

# {{{ def check_ifaces
def check_ifaces(ifaces):
    """
        Check ifaces is valid
    """
    if type(ifaces) != type(()):
        test.skip("found %s while expecting %s" % (type(ifaces), type({})))

    for eth in ifaces:
        if type(eth) != type(""):
            test.skip("found %s while expecting %s" % (type(eth), type({})))
# }}}
# {{{ def check_netconf
def check_netconf(netconf):
    """
        Check netconf is valid
    """
    if type(netconf) != type ({}):
        test.skip("found %s while expecting %s" % (type(netconf), type({})))

    for keyword in ("name", "network", "service"):
        error = "You must put '%s' in your net configuration" % keyword
        if not netconf.has_key(keyword):
            test.skip(error)

    name_type = type(netconf["name"])
    if name_type != type(""):
        test.skip("examining name, we found %s while expecting %s" %
                  (name_type, type("")))

    network_instance = netconf["network"]
    if not isinstance(network_instance, IP):
        test.skip("examining network, we found %s while expecting %s" %
                  (netconf["network"], "an IP object"))

    service_type = type(netconf["service"])
    if service_type != type(set()):
        test.skip("examining service, we found %s while expecting %s" %
                  (service_type, type(set())))
# }}}
# {{{ def configure_simple_ethernet
def configure_simple_ethernet(blob, serialized, ifaces, netconf):
    """
        Conf should be like :
        ifaces = ('eth2',)
        netconf = {"name"      : "NAME",
                   "network"   : IP("192.168.2.0/24"),
                   "service"   : set(IP("192.168.2.1"),)}
    """
    # Check input
    check_ifaces(ifaces)
    check_netconf(netconf)

    # Let's configure
    netcfg = deserialize(serialized)

    eth1 = netcfg.getInterfaceBySystemName(netconf["iface"])
    netcfg_bondings = set(netcfg.bondings)
    for bonding in netcfg_bondings:
        if eth1 in bonding.ethernets:
            netcfg.removeInterface(bonding)
            break
    netcfg.removeInterface(eth1)

    net = NetRW(
                netconf["name"],
                netconf["network"],
                service_ip_addrs = netconf["service"]
               )
    eth1.addNet(net)

    return (netcfg.serialize(), net)
# }}}
# {{{ def configure_bonding
def configure_bonding(serialized, ifaces, netconf):
    """
        Conf should be like :
        ifaces = ('eth1', 'eth2')
        netconf = {"name"      : "NAME",
                   "network"   : IP("192.168.2.0/24"),
                   "service"   : set(IP("192.168.2.1"),)}
    """
    # Check input
    check_ifaces(ifaces)
    check_netconf(netconf)

    # Let's configure
    netcfg = deserialize(serialized)

    eth1 = netcfg.getInterfaceBySystemName(ifaces[0])
    eth2 = netcfg.getInterfaceBySystemName(ifaces[1])

    netcfg_bondings = set(netcfg.bondings)
    for bonding in netcfg_bondings:
        if eth1 in bonding.ethernets:
            netcfg.removeInterface(bonding)
            break
    netcfg.removeInterface(eth1)

    netcfg_bondings = set(netcfg.bondings)
    for bonding in netcfg_bondings:
        if eth2 in bonding.ethernets:
            netcfg.removeInterface(bonding)
            break
    netcfg.removeInterface(eth2)

    bond0 = netcfg.createBonding('bond0', set((eth1, eth2)))

    # Give an IPv4 configuration to our bonding
    net = NetRW(
                netconf["name"],
                netconf["network"],
                service_ip_addrs = netconf["service"]
               )

    bond0.addNet(net)

    return (netcfg.serialize(), net)
# }}}
# {{{ def configure_vlan
def configure_vlan(serialized, conf):
    """
        Conf should be like :
    """
    # Check configuration
    pass
# }}}

