from twisted.internet.protocol import Protocol, Factory
from twisted.internet import reactor
from sys import stdout

class EchoServer(Protocol):

    def dataReceived(self, data):
        stdout.write(data)

    def connectionMade(self):
        print 'Server Connection made'
	print self.transport.getHost()
	print self.transport.getPeer()
        self.transport.write("An apple a day keeps the doctor away\r\n")

# Next lines are magic:
factory = Factory()
factory.protocol = EchoServer

reactor.listenTCP(8007, factory)
reactor.run()
