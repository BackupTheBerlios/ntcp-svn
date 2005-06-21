from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.internet import reactor
from sys import stdout

import socket

class Echo(Protocol):

    def dataReceived(self, data):
        stdout.write(data)

class EchoClientFactory(ClientFactory):

    def startedConnecting(self, connector):
        print 'Started to connect.'

    def buildProtocol(self, addr):
        print 'Connected.'
        return Echo()

    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason

    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        #reactor.connectTCP('10.193.161.71', 8007, self)

class EchoServer(Protocol):

    def dataReceived(self, data):
        stdout.write(data)

    def connectionMade(self):
        print 'Server Connection made'
        self.transport.write("An apple a day keeps the doctor away\r\n")

	if hasattr(socket, 'SOL_SOCKET') and hasattr(socket, 'SO_REUSEADDR'):
            print 'set SO_REUSEADDR in ', self.transport.socket
            self.transport.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
	    print 'SO_REUSEADDR setted'



	self.transport.loseConnection()
        self.transport.socket.shutdown(1)
 	#self.transport.socket.close()
        
#	try:
#		self.transport.socket.shutdown(1)
#        	self.transport.socket.close()
#	except:
#		print 'Error catch'
#	reactor.stop()
#	return

        reactor.connectTCP('10.193.167.101', 8007, \
                           EchoClientFactory(), 5, ('10.193.161.65', 8007))

    def connectionLost(self, reason):
        print 'Connection lost', reason


# Next lines are magic:
factory = Factory()
factory.protocol = EchoServer


#reactor.connectTCP('10.193.163.246', 8007, EchoClientFactory())
#reactor.connectTCP('10.193.161.71', 50338, EchoClientFactory())
#reactor.connectTCP('10.193.161.71', 8007, EchoClientFactory())
reactor.listenTCP(8007, factory)
reactor.run()
