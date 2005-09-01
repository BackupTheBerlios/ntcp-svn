import logging
import twisted.internet.defer as defer

import ntcp.stunt.StuntClient as stunt

stun_section = {
    'servers': ('stun_servers', str, ""),
}

class _NatDiscover(stunt.StuntClient):
    
    log = logging.getLogger("ntcp")
    
    def __init__(self, reactor, *args, **kargs):
        stunt.StuntClient.__init__(self, *args, **kargs)
        self.reactor = reactor

    def Run(self):
        self.d = defer.Deferred()
        #self.reactor.callLater(0, self.startDiscovery)
        self.d = self.startDiscovery()
        return self.d

    def _Failed(self):
        self.d.errback(Exception("no response from servers %s" % self.servers))

    def Timeout(self):
        self._finished = True
        self.listening.stopListening()
        self._Failed()

    def finishedStunt(self):
        self.log.debug('NatDiscovery finished')
        if not self.d.called:
            self.d.callback(self.natType)
            
    def _finishedPortDiscovery(self, address):
        self.log.debug('Port Discovery finished')
        if not self.d.called:
            self.d.callback(address)


def NatDiscovery(reactor, succeed=None):
    d = defer.Deferred()
    discovery = _NatDiscover(reactor)

    # Start listening
    d = discovery.Run()

    if succeed == None: return d
    else:
        # We are in a non-bloking mode
        succeed(discovery.natType)

def AddressDiscover(reactor, port):
    d = defer.Deferred()
    discovery = _NatDiscover(reactor)

    # Start listening
    return discovery.portDiscovery(port)

