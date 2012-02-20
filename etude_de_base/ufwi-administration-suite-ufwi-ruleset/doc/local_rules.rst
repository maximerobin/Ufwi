+++++++++++++++++++++++++++++
NuFace: Locale iptables rules
+++++++++++++++++++++++++++++

It's possible to define your own iptables and ip6tables rules using
/var/lib/nuface3/local_rules_ipv4.d/ and /var/lib/nuface3/local_rules_ipv6.d/
directories.

Filename format is "TABLE*.rules" (pre) or "TABLE*.rules.post" (post),
where "*" means "any string" and TABLE is one of the Netfilter table:

 - filter: INPUT, OUTPUT, FORWARD
 - nat: PREROUTING, POSTROUTING, OUTPUT
 - mangle: PREROUTING, INPUT, FORWARD, OUTPUT, POSTROUTING

Examples of complete filenames:

  /var/lib/nuface3/local_rules_ipv4.d/nat-masquerading.rules
  /var/lib/nuface3/local_rules_ipv6.d/filter_https.rules

File format is iptables-restore: it's like calling iptables but without the
"iptables " prefix. Example, to get this rules before any other NuFace rules: ::

   iptables -A OUTPUT -p tcp --dport 80 -d 192.168.0.4 -j ACCEPT
   iptables -A OUTPUT -p tcp --dport 8080 -d 192.168.0.5 -j ACCEPT

Create the file /var/lib/nuface3/local_rules_ipv4.d/filter_http.rules: ::

   -A OUTPUT -p tcp --dport 80 -d 192.168.0.4 -j ACCEPT
   -A OUTPUT -p tcp --dport 8080 -d 192.168.0.5 -j ACCEPT

