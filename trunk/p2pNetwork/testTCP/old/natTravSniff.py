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

class Broker(Protocol):

    def __init__(self):

        # Start to sniff packets
        # run method in thread and get result as defer.Deferred
        #reactor.callInThread(sniffer.sniff, self)
        pass

    #=================================================================
    def fakeConnection(self, argv, argc):
        
        dhost = '10.193.167.50'    # The remote host
        dport = 50007              # The same port as used by the server
        
        shost = '10.193.161.93'    # The source host
        sport = 50007              # The source port

        dhost = argv[1]           # The remote host
        dport = int(argv[2])           # The same port as used by the server
        sport = dport             # The source port
        shost = argv[3]           # The source host

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
        #self._bind()

        # Calculate its checksum.
	tcp.calculate_checksum()
	tcp.auto_checksum = 1

        # Send it to the target host.
	self.s.sendto(ip.get_packet(), (dhost, dport))

    def connection(self):
        RHOST = '10.193.161.93'    # The remote host
        RPORT = 50007              # The same port as used by the server

        self._bind()
        
        # Start timeout and try to connect
        print 'Try to connect...'
        time.sleep(1)
        self.s.connect((RHOST, RPORT))
        print 'connection made'

    def _sniffed(self, packet):
            print 'Packet sniffed'
            print packet
            print 'SYNn:', packet.child().get_th_seq()
            print 'SYN:', packet.child().get_SYN()
            print 'ACK:', packet.child().get_ACK()
            print 'ACKn:', packet.child().get_th_ack()

if __name__ == '__main__':
    b = Broker()
    b.fakeConnection(sys.argv, len(sys.argv))


