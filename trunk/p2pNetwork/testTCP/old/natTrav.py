# Echo server program
import socket
import sys, time
from twisted.internet import reactor
from twisted.internet import threads
import twisted.internet.defer as defer

import signal, os
import p2pNetwork.testTCP.sniffer as sniffer

class PeerSC:

    def __init__(self):
        self._bind()

    #=================================================================
    def connection(self):
        
        # Echo client program
        RHOST = '10.193.161.32'    # The remote host
        RPORT = 50007              # The same port as used by the server

        # Start to sniff packets
        # run method in thread and get result as defer.Deferred

        reactor.callInThread(sniffer.sniff, self)
        #d = threads.deferToThread(sniffer.sniff)
        #d.addCallback(_sniffed)
        
        # Start timeout and try to connect
        print 'Try to connect...'
        time.sleep(2)
        try:
            self.s.connect((RHOST, RPORT))
        except:
            print 'Exception: do nothing'
               
    def connectionMade():
        time.sleep(2)
        print 'Try to send'
        self.s.send('Hello, world')
        
        time.sleep(2)
        print 'Try to listen'
        data = self.s.recv(1024)
        self.s.close()
        print 'Received', repr(data)

    def _bind(self):
        HOST = '192.168.1.109'    # Symbolic name meaning the local host
        PORT = 50007              # Arbitrary non-privileged port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        #self.s.bind((HOST, PORT))

    def _sniffed(self, packet):
            print 'Packet sniffed'
            print packet
            print packet.child().get_th_dport()
            print 'SYNn:', packet.child().get_th_seq()
            print 'SYN:', packet.child().get_SYN()
            print 'ACK:', packet.child().get_ACK()
            print 'ACKn:', packet.child().get_th_ack()

if __name__ == '__main__':
    p = PeerSC()
    p.connection()

