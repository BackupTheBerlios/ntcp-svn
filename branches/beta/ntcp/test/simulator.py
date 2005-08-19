import sys, random, time

from twisted.internet.protocol import Protocol, ClientFactory, DatagramProtocol
import twisted.internet.defer as defer
from twisted.internet import reactor

from ntcp.connection.NATConnectivity import NatConnectivity 

class Simulator(DatagramProtocol, object):
    """
    A simulator of an application that uses
    the NAT traversal for TCP connection
    """
    
    d = defer.Deferred()

    
    def datagramReceived(self, message, fromAddr):
        self.ntcp.datagramReceived(message, fromAddr)
    
    def testDiscoveryNat(self):
        """
        Discover the NAT presence, type and mapping with STUN/STUNT mudule.
        Register to the Super Node Connection Broker.
        Start an TCP communication with the other endpoint.
        """
       
        d = defer.Deferred()
        self.uri = ' '
        self.remoteUri = ' '
        if len(sys.argv) > 1:
            self.uri = sys.argv[1]
        if len(sys.argv) > 2:
            self.remote = sys.argv[2]
            
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal:', failure#.getErrorMessage()
            
        def registrationSucceed(result):
            print 'Registration to the SN Connection Broker has be done'
            if len(sys.argv) > 2:
                self.testConnection()

        def discoverySucceed(result):
            factory = TcpClientFactory()
            d = self.ntcp.registrationToCB(self.uri, factory)
            d.addCallback(registrationSucceed)
            d.addErrback(fail)
        
        # UDP listening
        punchPort = random.randrange(6900, 6999)
        flag = 1 
        while flag: 
            try:
                listener = reactor.listenUDP(punchPort, self)
                flag = 0
            except :
                punchPort = random.randrange(6900, 6999)
     
        print 'Hole punching port: %d'%punchPort
        # Start to discover the public network address
        self.ntcp = NatConnectivity(reactor, listener)
        d = self.ntcp.natDiscovery()
        d.addCallback(discoverySucceed)
        d.addErrback(fail)


    def testConnection(self):
        
        def succeed(result):
            pass
        
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal TCP:', failure.getErrorMessage()
      
        factory = TcpClientFactory()
        self.remote = ('192.168.1.203', int(self.remote))
        self.ntcp.connectTCP(remoteAddress=self.remote, factory=factory)
        #d = self.ntcp.connectTCP(remoteUri=self.remote, factory=factory)
        #d.addCallback(succeed)
        #d.addErrback(fail)

      
class TcpConnection(Protocol):
    """
    All the Twisted functions for a TCP connection (c/s) 
    """
    
    def dataReceived(self, data):
        print 'Data received'
        print data

    def connectionMade(self):
        print 'Connection Made...write data...'
        self.transport.write("An apple a day keeps the doctor away\r\n") 
        

class TcpClientFactory(ClientFactory):
    
    def startedConnecting(self, connector):
        print 'Started to connect.'
    
    def buildProtocol(self, addr):
        print 'Connected.'
        return TcpConnection()
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason


if __name__ == '__main__':
    s = Simulator()
    s.testDiscoveryNat()

reactor.run()
