import socket
import sys, time
import signal, os

from twisted.internet import protocol
from twisted.internet import tcp
from twisted.internet import reactor

from impacket import ImpactPacket
from impacket import ImpactDecoder
        
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
    
class Spoofer:
    """Send a spoofed TCP packet
    USAGE: IP-destination dport IP-source sport SYNno ACKno"""

    socketType = socket.SOCK_RAW # Overide socket type.
    addressFamily = socket.AF_INET
    
    def __init__(self):
        self.protocolNum = socket.getprotobyname('tcp')
        self.setACK = 0
        

    #=================================================================
    def fakeConnection(self, argv, argc):

        self.dhost = argv[1]           # The remote host
        self.dport = int(argv[2])      # The same port as used by the server
        self.shost = argv[3]           # The source host
        self.sport = int(argv[4])      # The source port

        if argc >= 6:
            self.SYN = int(argv[5])
        if argc == 7:
            self.setACK = 1
            self.ACK = int(argv[6])

        if platformType == 'win32':
            self.winSpoofing()
        else:
            self.unixSpoofing()
            
    def unixSpoofing(self):
        # Create a new IP packet and set its source and destination addresses.
        ip = ImpactPacket.IP()
        ip.set_ip_src(self.shost)
        ip.set_ip_dst(self.dhost)
        if  self.setACK != 1:
            ip.set_ip_ttl(2)

        # Create a new TCP
        tcp = ImpactPacket.TCP()
        
        # Set the parameters for the connection
        tcp.set_th_sport(self.sport)
        tcp.set_th_dport(self.dport)
        tcp.set_th_seq(self.SYN)
        tcp.set_SYN()
        if  self.setACK == 1:
            tcp.set_th_ack(self.ACK)
            tcp.set_ACK()
                
        # Have the IP packet contain the TCP packet
        ip.contains(tcp)
        # Calculate its checksum.
	tcp.calculate_checksum()
	tcp.auto_checksum = 1
        
        self.s = self.createInternetSocket()
        # Send it to the target host.
	self.s.sendto(ip.get_packet(), (self.dhost, self.dport))

    def winSpoofing(self):
        print "Send packet with netwox..."
##         out = os.popen("netwox530 40 -m %s -p %ld -o %ld -C -q %ld -z -r %ld -E 150 -j 128" \
##                   % (self.dhost, self.dport, self.sport, self.SYN, self.ACK))
        os.system("netwox530 40 -m %s -p %ld -o %ld -C -q %ld -z -r %ld -E 150 -j 128" \
                  % (self.dhost, self.dport, self.sport, self.SYN, self.ACK))
        if out.read() == '':
            print 'Error: packet not sent!'
        else:
            print 'Packet has been sent.'

    def createInternetSocket(self):

        s = socket.socket(self.addressFamily, self.socketType, self.protocolNum)
        s.setblocking(0)
        # enable the sending of tcp headers.
        s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        return s
    

if __name__ == '__main__':
    p = Spoofer()
    p.fakeConnection(sys.argv, len(sys.argv))


