# Echo server program
import socket
import sys, time
from twisted.internet import reactor
import twisted.internet.defer as defer

import signal, os
import p2pNetwork.testTCP.sniffer as sniffer

class PeerSC:

    def __init__(self):
        self._bind()

    #=================================================================
    def connection(self):
        
        # Echo client program
        RHOST = '10.193.167.111'    # The remote host
        RPORT = 50007              # The same port as used by the server

        # Start to sniff packets
        def _sniffed():
            print 'Packet sniffed'
        
        #d = reactor.callInThread(sniffer.sniff, self)
        #d.addCallback(_sniffed)
        
        # Start timeout and try to connect
        print 'Try to connect...'
##         try:
        #socket.setdefaulttimeout(115)
        self.s.connect((RHOST, RPORT))
##         except KeyboardInterrupt:
##             #self._timeout(1, 1)
##             pass
##         except:
##             print "Connection error:", sys.exc_info()[0], sys.exc_info()[1]
##             #self._timeout(1, 1)

        print 'Try to send data...'
        self.s.send('Hello, world')
        data = self.s.recv(1024)
        self.s.close()
        print 'Received', repr(data)
        #except:
         #   print 'Exception:', sys.exc_info()[0]

    #=================================================================
    def _timeout(self, signum, frame):
        print 'timeout ==> Start listen'
        self.s.close()
        self._bind()
        self.s.listen(1)
        conn, addr = self.s.accept()
        print 'Connected by', addr
        while 1:
            data = conn.recv(1024)
            if not data: break
            conn.send(data)
        #conn.close()
        #s.close()
        #del s

    def _bind(self):
        HOST = '192.168.1.109'    # Symbolic name meaning the local host
        PORT = 50007              # Arbitrary non-privileged port
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((HOST, PORT))
            
    def _sniffed(self, packet):
        print 'Packet sniffed'
        print packet
        print 'SYN:', packet.child().get_SYN()
        print 'SYNn:', packet.child().get_th_seq()
        print 'ACK:', packet.child().get_ACK()
        print 'ACKn:', packet.child().get_th_ack()
        
if __name__ == '__main__':
    p = PeerSC()
    p.connection()

