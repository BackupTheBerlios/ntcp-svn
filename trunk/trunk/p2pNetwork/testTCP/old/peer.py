from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.internet import reactor
from sys import stdout

import socket

class Echo(Protocol):
        
    def dataReceived(self, data = ''):
        stdout.write(data)

    def connectionMade(self):
        print 'connection Made' 

class EchoClientFactory(ClientFactory):

    
    def startedConnecting(self, connector):
        print 'Started to connect.'
        self.e = Echo()
    
    def buildProtocol(self, addr):
        print 'Connected.'
        return self.e
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason

factory = Factory()
factory.protocol = EchoServer

dhost = '10.193.161.93'    # The remote host
dport = 50007              # The same port as used by the server

shost = '192.168.1.109'    # The source host
sport = 50007              # The source port

sck = reactor.connectTCP(dhost, dport, EchoClientFactory(), 30, (shost, sport))
reactor.run()

