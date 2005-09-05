import sys, random, time

from twisted.internet.protocol import Protocol, ClientFactory, DatagramProtocol
import twisted.internet.defer as defer
from twisted.internet import reactor

from ntcp.NatConnectivity import NatConnectivity

from ntcp.test.TcpFactory_test import TcpFactory   
from ntcp.test.TcpFactory_test import TcpConnection

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
        self.remote = ' '
        if len(sys.argv) > 1:
            self.uri = sys.argv[1]
        if len(sys.argv) > 2:
            self.remote = sys.argv[2]
            
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal:', failure#.getErrorMessage()
            
        def registrationSucceed(result):
            print 'Registration to the SN Connection Broker has be done'

        def discoverySucceed(result):
            #factory = TcpClientFactory()
            factory = TcpFactory(reactor, self)
            if len(sys.argv) == 2:
                d = self.ntcp.listenTCP(factory=factory, myUri=self.uri).defer
                d.addCallback(registrationSucceed)
                d.addErrback(fail)
            elif len(sys.argv) > 2:
                self.testConnection()
                
# ------------------------------------------------------------------
# For UDP listener
##         # UDP listening
##         punchPort = random.randrange(6900, 6999)
##         flag = 1 
##         while flag: 
##             try:
##                 listener = reactor.listenUDP(punchPort, self)
##                 flag = 0
##             except :
##                 punchPort = random.randrange(6900, 6999)
     
##         print 'Hole punching port: %d'%punchPort
##         # Start to discover the public network address
##         self.ntcp = NatConnectivity(reactor, listener)
# ------------------------------------------------------------------  
        self.ntcp = NatConnectivity(reactor)
        d = self.ntcp.natDiscovery(0)
        # -----------------------------------------------------------  
        # run the nat discovery procedure in a non-bloking mode (0)
        #ntcp.natDiscovery(0)
        # -----------------------------------------------------------
        d.addCallback(discoverySucceed)
        d.addErrback(fail)


    def testConnection(self):
        
        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal TCP:', failure.getErrorMessage()
            
        def succeed(result):
            connector = result
            print 'ccc', connector
            
        def conf_succeed(result):
            if result[0] != None and result[1] != None:
                #factory = TcpClientFactory()
                factory = TcpFactory(reactor)
                # self.remote = ('192.168.1.203', int(self.remote))
                # self.ntcp.connectTCP(remoteAddress=self.remote, factory=factory)
                d = self.ntcp.connectTCP(remoteUri=self.remote, factory=factory, myUri=self.uri)
                d.addCallback(succeed)
                d.addErrback(fail)
                          
        d = self.ntcp.getP2PConfiguration(remoteUri=self.remote)
        d.addCallback(conf_succeed)
        d.addErrback(fail)
        

      
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
        pass
    
    def buildProtocol(self, addr):
        return TcpConnection()
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason


if __name__ == '__main__':
    s = Simulator()
    s.testDiscoveryNat()

reactor.run()
