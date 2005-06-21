import sys,random
import logging
import time

import p2pNetwork.discover.stunDiscover as stun
import p2pNetwork.htcp.puncher as punch
import twisted.internet.defer as defer

from twisted.internet import reactor

class Solipsis(object):
    
    def _test(self):

        # The port for the client connection
        port = random.randrange(7000, 7100)
        stunPort = 6999
        
        discovery_deferred = defer.Deferred()
        
        id = ''
        if len(sys.argv) > 1:
            id = sys.argv[1]
        if len(sys.argv) > 2:
            peerURI = sys.argv[2]

        def _registrationMade((transport, puncher)):
            # TODO: reload config
            if len(sys.argv) > 2:
                #puncher.connectByAddress(('127.0.0.1', 7035))
                #p = punch.connectByURI(peerURI, netconf, id, transport, port)
                puncher.connectByURI(peerURI)
                
        def _succeed(address):
            #Discovery succeeded
            self.host, self.port = address
            #self.address = Address(self.host, self.port)
            discovery_deferred.callback((self.host, self.port))
            print "discovevry found address %s:%d" % (self.host, self.port)
            
            stun.printConfiguration()
            #print stun.getConfiguration()
            #print stun.getNATType(), stun.getPrivateAddress(), stun.getPublicAddress()
            netconf = stun.getConfiguration()

            d, puncher = punch.HolePunching(port, reactor, netconf, id)
            d.addCallback(_registrationMade)
            d.addErrback(_fail)
                
            #discovery.connectByAddress(('10.193.167.60', 7079))
            
        
        def _fail(failure):
            # Discovery failed => try next discovery method
            stun.printConfiguration()
            print failure
            

        d = stun.DiscoverAddress(stunPort, reactor)
        d.addCallback(_succeed)
        d.addErrback(_fail)

        
if __name__ == '__main__':
    s = Solipsis()
    s._test()

reactor.run()
