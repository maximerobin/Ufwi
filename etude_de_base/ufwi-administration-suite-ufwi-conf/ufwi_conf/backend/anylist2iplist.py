"""
This module provides convenience methods to ensure we deal with IPs,
not hostnames.
"""

import re
from IPy import IP
from logging import WARNING

from ufwi_rpcd.backend import RpcdError
from ufwi_rpcd.common.network import \
    IPV4_REGEX_STR, IPV6_REGEX_STR, FQDN_REGEX_STR_PART
from ufwi_rpcd.common.process import ProcessError

from .unix_service import runCommandAndCheck, RunCommandError

TIMEOUT = 30 # seconds

#Old host program (lenny): 'A', recent: 'has address'
V4_DEF = r'(?P<v4def>(A|has address))'
V4_RECORD = r'^(?P<v4host>%s)\s+%s\s+(?P<v4ip>%s)$' % (
    FQDN_REGEX_STR_PART, V4_DEF, IPV4_REGEX_STR
    )

#Old host program (lenny): 'AAAA', recent: 'has address'
V6_DEF = r'(?P<v6def>(AAAA|has IPv6 address))'
V6_RECORD = r'^(?P<v6host>%s)\s+%s\s+(?P<v6ip>%s)$' % (
    FQDN_REGEX_STR_PART, V6_DEF, IPV6_REGEX_STR
    )

RECORD_RE = re.compile('%s|%s' % (V4_RECORD, V6_RECORD), re.IGNORECASE)

class UnresolvableHost(RpcdError):
    """
    This exception to be used internally to this module
    """
    def __init__(self, item):
        self.unresolvable = unicode(item)
        RpcdError.__init__(self, "Unable to resolve '%s'" % unicode(item))

def host2ip(logger, host, dns_ips):
    """
    logger:
        a logger
    host:
        a string/unicode
    dns_ips:
        an iterable of IPs (strings)

    returns a set of all IPy.IP found
    """

    last_index = len(dns_ips) - 1
    for index, dns_ip in enumerate(dns_ips):
        #recent host program:
        #The -t option is used to select the query type. [...]
        #When no query type is specified, host automatically selects an
        #appropriate query type. By default, it looks for A, AAAA, and MX
        #records,[...]

        #older host program is not very different

        command = "host %s %s" % (host, dns_ip)
        all_results = set()
        try:
            child, stdout = runCommandAndCheck(logger, command.split(), timeout=TIMEOUT, env={})
        except (RunCommandError, ProcessError), err:
            logger.writeError(err,
                "Unable to resolve host %s with DNS server %s:" % (host, dns_ip),
                log_level=WARNING)
            if index == last_index:
                raise UnresolvableHost(host)
            continue
        for line in stdout:
            match = RECORD_RE.match(line)
            if not match:
                #nothing found, maybe NS or MX or other field
                continue
            result = match.groupdict()

            #Did we find an ipv4?
            v4ip = result['v4ip']
            if v4ip:
                all_results.add(IP(v4ip))
            else:
                #If we found something, it must be an ipv6, hence assert
                v6ip = result['v6ip']
                assert v6ip, "match gives %s" % repr(result)
                all_results.add(IP(v6ip))
        if all_results:
            break

    if all_results:
        return all_results

    #uh oh, no server could resolve the host
    raise UnresolvableHost(host)

def item2ips(logger, anything, dns_ips):
    """
    logger:
        a logger.
    anything:
        preferably string, numeric or IP.
    dns_ips:
        an iterable of ips as strings.
        Represent DNS servers that can be used.

    returns a set of IPy.IP
    """

    #ensure DNS servers are IPs
    dns_ips = tuple(
            IP(server)
            for server in dns_ips
            )

    try:
        return set((IP(anything),))
    except (ValueError, AttributeError):
        #Exceptions found in IPy.IP
        #host2ip raises relevant exceptions
        return host2ip(logger, anything, dns_ips)

def iterable2ipset(logger, anylist, dns_ips):
    """
    logger:
        a logger.
    anylist:
        a list of strings, IPs, numbers
    dns_ips:
        an iterable of ips as strings.
        Represent DNS servers that can be used.
    """
    result = set()
    for item in anylist:
        result |= item2ips(logger, item, dns_ips)
    return result

