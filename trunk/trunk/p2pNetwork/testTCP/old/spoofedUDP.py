import socket, fcntl
from twisted.internet import protocol
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
	
    
class Echo(protocol.DatagramProtocol):

    def __init__(self):
        self.fake_addr = None
        self.dest = "127.0.0.1"
        self.port = 9999
        
    def setFakeSrc(self, addr):
        """Set the fake address from which packets should appear to come."""
        self.fake_addr = addr
        
    def startProtocol(self):
        print "starting Echo"
        
    def datagramReceived(self, data, (host, port)):
        """data is a IP packet object from Impacket."""
        ip = data
        udp = ip.child()
        if udp.get_uh_dport() == 9999:
            src = ip.get_ip_src()
            
            print "host = %s" % (host,)
            print "udp src = %s" % (src,)
            print "received: %s" % (udp,)
            
            if self.fake_addr and src == "128.98.3.63":
                # Fake the src address and resend the packet
                ip.set_ip_src(self.fake_addr)
                print "resending with src = %s\n" % (ip.get_ip_src(),)
                self.transport.write(ip.get_packet(), (self.dest,self.port))

class RawUDPPort(udp.Port):
    """Raw udp port."""
    
    __implements__ = udp.Port.__implements__

    socketType = socket.SOCK_RAW # Overide socket type.
    addressFamily = socket.AF_INET
    
    def __init__(self, *args, **kw):
        udp.Port.__init__(self,*args,**kw)
        
        self.protocolNum = socket.getprotobyname('udp')
        self.decoder = ImpactDecoder.IPDecoder()
        
    def createInternetSocket(self):
        s = socket.socket(self.addressFamily, self.socketType, self.protocolNum)
        s.setblocking(0)
        # enable the sending of udp headers.
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        if fcntl and hasattr(fcntl, 'FD_CLOEXEC'):
            old = fcntl.fcntl(s.fileno(), fcntl.F_GETFD)
            fcntl.fcntl(s.fileno(), fcntl.F_SETFD, old | fcntl.FD_CLOEXEC)
            return s
	
    def doRead(self):
        """Called when my socket is ready for reading."""
        read = 0
        while read < self.maxThroughput:
            try:
                data, addr = self.socket.recvfrom(self.maxPacketSize)
                read += len(data)
                ip = self.decoder.decode(data)
                if isinstance(ip.child(),ImpactPacket.UDP) and \
                       ip.child().get_uh_dport() == self.port:                
                    self.protocol.datagramReceived(ip, addr)
            except socket.error, se:
                no = se.args[0]
                if no in (EAGAIN, EINTR, EWOULDBLOCK):
                    return
                if (no == ECONNREFUSED) or (platformType == "win32" and no == WSAECONNRESET):
                    # XXX for the moment we don't deal with connection 	refused
                    # in non-connected UDP sockets.
                    pass
                else:
                    raise
	##            except:
	##                log.deferr()
	
echo = Echo()
echo.setFakeSrc("127.0.0.1")

reactor.listenWith(RawUDPPort, proto=echo, port=9999, interface="localhost", reactor=reactor)
reactor.run()
