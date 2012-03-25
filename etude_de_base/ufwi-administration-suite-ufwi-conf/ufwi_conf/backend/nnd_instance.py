from nnd.client import Client as NNDClient

NND_SOCKET = '/var/run/nnd/nnd.socket'

def getclient(logger):
    client = NNDClient(logger=logger)
    client.connect(filename=NND_SOCKET)
    return client

