from twisted.internet.protocol import Protocol, ClientFactory, DatagramProtocol
from twisted.internet import reactor

      
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

    def connectionLost(self, reason):
        print 'Lost connection.  Reason:', reason

class TcpClientFactory(ClientFactory):
    
    def startedConnecting(self, connector):
        pass
    
    def buildProtocol(self, addr):
        return TcpConnection()
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
