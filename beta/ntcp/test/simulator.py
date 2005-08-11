import sys, random

import twisted.internet.defer as defer
from twisted.internet import reactor

from ntcp.connection.NATConnectivity import NATConnectivity 

class Simulator(object):
    """
    A simulator of an application that uses
    the NAT traversal for TCP connection
    """
    
    d = defer.Deferred()
    
    def testDiscoveryNat(self):
        """
        Discover the NAT presence, type and mapping with STUN/STUNT mudule.
        Register to the Super Node Connection Broker.
        Start an TCP communication with the other endpoint.
        """
       
        self.uri = ' '
        self.remoteUri = ' '
        if len(sys.argv) > 1:
            self.uri = sys.argv[1]
        if len(sys.argv) > 2:
            self.remoteUri = sys.argv[2]
            
        def succeed(result):
            print 'Registration to the SN Connection Broker has be done'
            if len(sys.argv) > 2:
                self.testConnection()
        
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal TCP:', failure#.getErrorMessage()
      

        # Start to discover the public network address
        self.ntcp = NATConnectivity(reactor)
        d = self.ntcp.natDiscovery(self.uri)
        d.addCallback(succeed)
        d.addErrback(fail)

    def testConnection(self):
        

        def succeed(result):
            pass
        
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal TCP:', failure#.getErrorMessage()
      

        # Start to discover the public network address
        remoteAddress = ('10.193.167.246', 7101)
        localPort = random.randrange(7000, 7100)
        d = self.ntcp.forceConnection(remoteUri=self.remoteUri, localPort=localPort)
        d.addCallback(succeed)
        d.addErrback(fail)
        
        
if __name__ == '__main__':
    s = Simulator()
    s.testDiscoveryNat()

reactor.run()
