from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.internet import reactor
from sys import stdout

import socket

class Echo(Protocol):
        
    def dataReceived(self, data = ''):
        stdout.write(data)

        # set SO_REUSEADDR (if available on this platform)
        if hasattr(socket, 'SOL_SOCKET') and hasattr(socket, 'SO_REUSEADDR'):
            print 'set SO_REUSEADDR in ', self.transport.socket
            self.transport.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            print 'SO_REUSEADDR setted'

            self.startListen()

    def startListen(self):
        #self.port = self.transport.getHost().port
        
        #print self.transport.socket


        #self.transport.loseConnection()

        print 'Try to listen on 8007'
        reactor.listenTCP(8007, factory)
        print 'listen'
        

class EchoClientFactory(ClientFactory):

    
    def startedConnecting(self, connector):
        print 'Started to connect.'
        self.e = Echo()
    
    def buildProtocol(self, addr):
        print 'Connected.'
        return self.e
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        #self.e.startListen()
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        #reactor.connectTCP('10.193.167.111', 8007, self)

class EchoServer(Protocol):
    
    def dataReceived(self, data):
        stdout.write(data)
    
    def connectionMade(self):
        print 'Server Connection made'
        self.transport.write("An apple a day keeps the doctor away\r\n")

# Next lines are magic:
factory = Factory()
factory.protocol = EchoServer

#reactor.connectTCP('10.193.163.246', 8007, EchoClientFactory())
sck = reactor.connectTCP('10.193.163.246', 8007, EchoClientFactory(), 30, ('192.168.1.101', 8007))
reactor.run()

## if __name__ == '__main__':
##     s = Echo()
##     s._test()
