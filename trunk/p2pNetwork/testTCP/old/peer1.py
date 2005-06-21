# Echo server program
import socket
import sys, time
from twisted.internet import reactor
from twisted.internet.protocol import Protocol, ClientFactory
from twisted.internet import threads
import twisted.internet.defer as defer

import signal, os
import p2pNetwork.testTCP.sniffer as sniffer
from impacket import ImpactPacket
from impacket import ImpactDecoder

class PeerSC(Protocol):

    def __init__(self):

        # Start to sniff packets
        # run method in thread and get result as defer.Deferred
        #reactor.callInThread(sniffer.sniff, self)
        pass

    #=================================================================
    def fakeConnection(self, argv, argc):
        
        dhost = argv[1]           # The remote host
        dport = int(argv[2])      # The same port as used by the server
        sport = dport             # The source port
        shost = argv[3]           # The source host

        if argc >= 5:
            SYN = int(argv[4])
        if argc == 6:
            ACK = int(argv[5])
            
        # Create a new IP packet and set its source and destination addresses.
        ip = ImpactPacket.IP()
        ip.set_ip_src(shost)
        ip.set_ip_dst(dhost)

        # Create a new TCP
        tcp = ImpactPacket.TCP()
        
        # Set the parameters for the connection
        tcp.set_th_sport(sport)
        tcp.set_th_dport(dport)
        tcp.set_th_seq(SYN)
        tcp.set_SYN()
        if argc == 6:
            tcp.set_th_ack(ACK)
            tcp.set_ACK()
        
        
        # Have the IP packet contain the TCP packet
        ip.contains(tcp)

        # Open a raw socket. Special permissions are usually required.
        protocol_num = socket.getprotobyname('tcp')
        self.s = socket.socket(socket.AF_INET, socket.SOCK_RAW, protocol_num)
        self.s.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)

        # Calculate its checksum.
	tcp.calculate_checksum()
	tcp.auto_checksum = 1

        # Send it to the target host.
	self.s.sendto(ip.get_packet(), (dhost, dport))

        # Instantiate an IP packets decoder.
        # As all the packets include their IP header, that decoder only is enough.
        decoder = ImpactDecoder.IPDecoder()

        while 1:
            packet = self.s.recvfrom(4096)[0]
            # Packet received. Decode and display it.
            packet = decoder.decode(packet)
            print 'source:', packet.get_ip_src()
            #print packet.get_ip_src(), packet.child().get_th_sport()
            if isinstance(packet.child(),ImpactPacket.TCP)  and \
                   packet.child().get_th_sport() > 50000:
                self._sniffed(packet)

## -- Server --
##         self._bind(shost)

##         while 1:
## 	#if s in select.select([s],[],[],1)[0]:
## 	   #reply = self.s.recvfrom(2000)[0]
##            data = self.s.recv(1024)
##            print "Received:", data

##            print 'listen'
##            self.stcp.listen(1)
##            conn, addr = self.stcp.accept()
##            print 'Connected by', addr
##            while 1:
##                data = conn.recv(1024)
##                if not data: break
##                conn.send(data)

           
	   # Use ImpactDecoder to reconstruct the packet hierarchy.
	   #rip = ImpactDecoder.IPDecoder().decode(reply)
	   # Extract the ICMP packet from its container (the IP packet).
	   #rtcp = rip.child()

           #print "Message from:", rip.get_ip_src(), rtcp.get_th_sport()


    def connection(self):
        RHOST = '10.193.161.93'    # The remote host
        RPORT = 50007              # The same port as used by the server

        self._bind()
        
        # Start timeout and try to connect
        print 'Try to connect...'
        time.sleep(1)
        self.s.connect((RHOST, RPORT))
        print 'connection made'

    def _bind(self, shost):
        HOST = shost    # Symbolic name meaning the local host
        PORT = 50007              # Arbitrary non-privileged port
        self.stcp = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        #self.stcp.setsockopt(socket.IPPROTO_IP, socket.IP_HDRINCL, 1)
        self.stcp.bind((HOST, PORT))
        
    def _sniffed(self, packet):
        print 'Packet sniffed'
        print packet
        print 'SYN:', packet.child().get_SYN()
        print 'SYNn:', packet.child().get_th_seq()
        print 'ACK:', packet.child().get_ACK()
        print 'ACKn:', packet.child().get_th_ack()

if __name__ == '__main__':
    p = PeerSC()
    p.fakeConnection(sys.argv, len(sys.argv))


