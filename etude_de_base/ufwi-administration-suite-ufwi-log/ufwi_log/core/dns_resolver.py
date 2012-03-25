import time
import adns

class DNSResolver(object):
    def __init__(self):
        self.adns = adns.init()

    def resolveReverseDNS(self, ip):
        print "reverse dns"
        request = self.adns.submit_reverse(ip, adns.rr.PTR)

        # Wait for ADNS to be ready
        while True:
            try:
                result = request.check()
                break
            except adns.NotReady:
                time.sleep(0.1)


        if len(result[3]) == 0:
            raise Exception('Unable to resolve hostname')

        return result[3][0]
