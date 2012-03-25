from IPy import IP
from logging import getLogger

from ufwi_conf.backend.anylist2iplist import iterable2ipset

def test_pureips():
    logger = getLogger("root")
    testcase = tuple(IP(item) for item in "0 192.168.9.12 227.90.1.2 aa:bb:cc::dd".split())
    ns_ips = ("192.168.33.2",)
    result = iterable2ipset(logger, testcase, ns_ips)
    assert len(result) == len(testcase)
    assert all(isinstance(item, IP) for item in result)

def test_purenames():
    logger = getLogger("root")
    testcase = "google.com edenwall.com yahoo.de".split()
    ns_ips = ("192.168.33.2",)
    result = iterable2ipset(logger, testcase, ns_ips)
    #cannot assert about len when we give names
    assert all(isinstance(item, IP) for item in result)

def test_mixed():
    logger = getLogger("root")
    testcase = "google.com 192.168.242.10 edenwall.com 88.6.4.2 yahoo.de".split()
    ns_ips = ("192.168.33.2",)
    result = iterable2ipset(logger, testcase, ns_ips)
    #cannot assert about len when we give names
    assert all(isinstance(item, IP) for item in result)

