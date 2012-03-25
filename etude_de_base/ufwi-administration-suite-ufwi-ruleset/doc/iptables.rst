ICMPv6 and --state INVALID
==========================

NuFace doesn't drop INVALID packets on ICMPv6 because it breaks IPv6
connectivity. Local link multicast ICMPv6 packets are detected as INVALID by
-m state --state INVALID.

Fixed in Linux 2.6.29:

 * http://bugzilla.netfilter.org/show_bug.cgi?id=567
 * http://git.kernel.org/?p=linux/kernel/git/torvalds/linux-2.6.git;a=commit;h=3f9007135c1dc896db9a9e35920aafc65b157230


INPUT chain, invalid packets and --syn
======================================

If the default decision of the INPUT chain is DROP, existing connections will
be dropped after a firewall reboot. Clients will have to wait the TCP
timeout (5 minutes by default) to be noticed.

NuFace doesn't filter invalid packets nor the TCP SYN flag (--syn) in the INPUT
chain to avoid this issue.


TCP and UDP port 0
==================

TCP port 0 and UDP port 0 are reserved and must not be used on the Internet.
That's why it's not possible in NuFace to create a protocol with port 0. If the
source or destination port is not specified, NuFace uses --sport 1:65535 or
--dport 1:65535.

