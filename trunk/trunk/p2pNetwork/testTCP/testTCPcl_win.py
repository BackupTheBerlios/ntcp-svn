from twisted.internet.protocol import Protocol, ClientFactory, Factory
from twisted.internet import reactor
from twisted.internet import threads
from sys import stdout

import sys
import socket
import time

import p2pNetwork.testTCP.sniff as sniffer
import p2pNetwork.testTCP.udpSniffer as udp_sniffer

class Echo(Protocol):
        
    def dataReceived(self, data = ''):
        stdout.write(data)

    def connectionMade(self):
        print 'Connection Made!' 

class EchoClientFactory(ClientFactory):

    
    def startedConnecting(self, connector):
        print 'Started to connect.'
        self.e = Echo()

    def buildProtocol(self, addr):
        print 'Connected.'
        return self.e
    
    def clientConnectionLost(self, connector, reason):
        print 'Lost connection.  Reason:', reason
        #reactor.stop()
    
    def clientConnectionFailed(self, connector, reason):
        print 'Connection failed. Reason:', reason
        #reactor.stop()



#if __name__ == '__main__':

# Start to listen for UDP connection
udp_obj = udp_sniffer.UDP_factory()   

# Start to sniff packets (run method in thread)
argv = ('', 'eth0', 'tcp port 50007')
print 'Start thread'
reactor.callInThread(sniffer.sniff, argv)
#time.sleep(1)

# Start TCP connection
print 'Start TCP connection'
reactor.connectTCP('10.193.161.57', 50007, EchoClientFactory(), 30, ('192.168.1.234', 50007))
reactor.run()
