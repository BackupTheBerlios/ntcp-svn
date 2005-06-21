# Echo server program
import socket
import sys, time
from twisted.internet import reactor

import signal, os

class PeerSC:

    def __init__(self):
        self._binxd()

    #================================================================
    def connection(self):
        
        # Echo client program
        RHOST = '10.193.161.90'    # The remote host
        RPORT = 50007              # The same port as used by the server

        print 'Try to connect...'
        try:
            #socket.setdefaulttimeout(115)
            # Set TTL
            self.s.setsockopt(socket.IPPROTO_IP, socket.IP_TTL, 2)
            self.s.connect((RHOST, RPORT))
        except KeyboardInterrupt, ConnectionRefused:
            print "Connection error:", sys.exc_info()[0], sys.exc_info()[1]
            self._timeout(1, 1)
            self.s.close()
            del self.s
            pass
        except:
            print "Connection error:", sys.exc_info()[0], sys.exc_info()[1]
            self._timeout(1, 1)
            self.s.close()
            del self.s

        print 'Try to send data...'
        self.s.send('Hello, world')
        data = self.s.recv(1024)
        self.s.close()
        del self.s
        print 'Received', repr(data)
        #except:
         #   print 'Exception:', sys.exc_info()[0]

    #=================================================================
    def _timeout(self, signum, frame):
        print 'timeout ==> Start listen'
        #self.s.close()
        #self._bind()
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
        #self.s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.s.bind((HOST, PORT))
    
if __name__ == '__main__':
    p = PeerSC()
    p.connection()

