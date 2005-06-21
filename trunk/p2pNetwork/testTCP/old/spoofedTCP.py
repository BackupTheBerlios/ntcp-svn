import socket, fcntl
from twisted.internet import protocol, base
from twisted.internet import tcp
from twisted.internet.protocol import Protocol
from twisted.internet import udp
from twisted.internet import reactor

import impacket # library from http://oss.coresecurity.com/projects/impacket.html
from impacket import ImpactDecoder,ImpactPacket

from twisted.python.runtime import platformType
if platformType == 'win32':
    from errno import WSAEWOULDBLOCK as EWOULDBLOCK
    from errno import WSAEINTR as EINTR
    from errno import WSAEMSGSIZE as EMSGSIZE
    from errno import WSAECONNREFUSED as ECONNREFUSED
    from errno import WSAECONNRESET
    from errno import EAGAIN
elif platformType != 'java':
    from errno import EWOULDBLOCK, EINTR, EMSGSIZE, ECONNREFUSED, EAGAIN
	
	
class Sniffer(Protocol):

    def __init__(self):
        self.fake_addr = None
        self.dest = "127.0.0.1"
        self.port = 9999

    def setFakeSrc(self, addr):
        """Set the fake address from which packets should appear to come."""
        self.fake_addr = addr
	        
    def startProtocol(self):
        print "starting Echo"

    
    def dataReceived(self, data):
        """data is a IP packet object from Impacket."""
        ip = data
        tcp = ip.child()
        if tcp.get_uh_dport() == 9999:
            src = ip.get_ip_src()
            
            #print "host = %s" % (host,)
            print "tcp src = %s" % (src,)
            print "received: %s" % (tcp,)
            
            if self.fake_addr and src == "128.98.3.63":
                # Fake the src address and resend the packet
                ip.set_ip_src(self.fake_addr)
                print "resending with src = %s\n" % (ip.get_ip_src(),)
                #self.transport.write(ip.get_packet(), (self.dest,self.port))

class RawTCP(tcp.Port):
    """Raw tcp port."""
    
    __implements__ = tcp.Port.__implements__
    
    socketType = socket.SOCK_RAW # Overide socket type.
    addressFamily = socket.AF_INET
    
    def __init__(self, *args, **kw):
        tcp.Port.__init__(self,*args,**kw)
	        
        self.protocolNum = socket.getprotobyname('TCP')
        print self.protocolNum
        self.decoder = ImpactDecoder.IPDecoder()
	    
    def createInternetSocket(self):
        print 'createInternetSocket'
        s = base.BasePort.createInternetSocket(self)
        if platformType == "posix":
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return s
	
    def doRead(self):
        """Called when my socket is ready for reading."""
        print 'Read something!!!'
        try:
            if platformType == "posix":
                numAccepts = self.numberAccepts
            else:
                # win32 event loop breaks if we do more than one accept()
                # in an iteration of the event loop.
                numAccepts = 1
            for i in range(numAccepts):
                # we need this so we can deal with a factory's buildProtocol
                # calling our loseConnection
                if self.disconnecting:
                    return
                try:
                    skt, addr = self.socket.accept()
                except socket.error, e:
                    if e.args[0] in (EWOULDBLOCK, EAGAIN):
                        self.numberAccepts = i
                        break
                    elif e.args[0] == EPERM:
                        continue
                    raise

                protocol = self.factory.buildProtocol(self._buildAddr(addr))
                if protocol is None:
                    skt.close()
                    continue
                s = self.sessionno
                self.sessionno = s+1
                transport = self.transport(skt, protocol, addr, self, s)
                transport = self._preMakeConnection(transport)
                protocol.makeConnection(transport)
            else:
                self.numberAccepts = self.numberAccepts+20
        except:
            # Note that in TLS mode, this will possibly catch SSL.Errors
            # raised by self.socket.accept()
            #
            # There is no "except SSL.Error:" above because SSL may be
            # None if there is no SSL support.  In any case, all the
            # "except SSL.Error:" suite would probably do is log.deferr()
            # and return, so handling it here works just as well.
            log.deferr()




        
##         read = 0
##         while read < self.maxThroughput:
##             try:
##                 data, addr = self.socket.recvfrom(self.maxPacketSize)
##                 read += len(data)
##                 ip = self.decoder.decode(data)
##                 if isinstance(ip.child(),ImpactPacket.TCP) and \
##                        ip.child().get_uh_dport() == self.port:                
##                     self.protocol.dataReceived(ip, addr)
##             except socket.error, se:
##                 no = se.args[0]
##                 if no in (EAGAIN, EINTR, EWOULDBLOCK):
##                     return
##                 if (no == ECONNREFUSED) or (platformType == "win32" and no == WSAECONNRESET):
##                     # XXX for the moment we don't deal with connection refused
##                     # in non-connected UDP sockets.
##                     pass
##                 else:
##                     raise
## 	##            except:
## 	##                log.deferr()
	
sniff = Sniffer()
sniff.setFakeSrc("127.0.0.1")

reactor.listenWith(RawTCP, factory=sniff, port=9999, interface='', reactor=reactor)
reactor.run()
