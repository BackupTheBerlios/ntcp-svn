import sys
import string
from threading import Thread
import socket
import struct

import pcapy
from pcapy import findalldevs, open_live
import impacket
from impacket.ImpactDecoder import EthDecoder, LinuxSLLDecoder

class DecoderThread(Thread):
    """A thread to sniff packets on my machine,
    read the SYN number and send it to the peer"""
    
    def __init__(self, pcapObj, udp_obj):
        self.udp_obj = udp_obj
        # Query the type of the link and instantiate a decoder accordingly.
        datalink = pcapObj.datalink()
        if pcapy.DLT_EN10MB == datalink:
            self.decoder = EthDecoder()
        elif pcapy.DLT_LINUX_SLL == datalink:
            self.decoder = LinuxSLLDecoder()
        else:
            raise Exception("Datalink type not supported: " % datalink)

        self.pcap = pcapObj
        Thread.__init__(self)

    def run(self):
        # Sniff ad infinitum.
        # PacketHandler shall be invoked by pcap for every packet.
        self.pcap.loop(0, self.packetHandler)

    def packetHandler(self, hdr, data):
        # Use the ImpactDecoder to turn the rawpacket into a hierarchy
        # of ImpactPacket instances.
        # Display the packet in human-readable form.
        print self.decoder.decode(data)
        print 'Try to send SYN...'
        syn = struct.unpack('!L', data[4:8])[0]
        self.udp_obj.send_SYN_to_ConnectionBroker(syn)
        #self.stop()


def getInterface():
    # Grab a list of interfaces that pcap is able to listen on.
    # The current user will be able to listen from all returned interfaces,
    # using open_live to open them.
    ifs = findalldevs()
    print 'interface:', ifs
    # No interfaces available, abort.
    if 0 == len(ifs):
        print "You don't have enough permissions to open any interface on this system."
        sys.exit(1)

    # Only one interface available, use it.
    elif 1 == len(ifs):
        print 'Only one interface present, defaulting to it.'
        return ifs[0]

    # Listen always on eth0
    return ifs[0]

    # Ask the user to choose an interface from the list.
    count = 0
    for iface in ifs:
        print '%i - %s' % (count, iface)
        count += 1
    idx = int(raw_input('Please select an interface: '))

    return ifs[idx]

def sniff(argv, udp_obj):

    # Create the hole for UDP communication
    udp_obj.punchHole()
  
    sys.argv = argv
    if len(sys.argv) < 3:
        print 'usage: sniff.py <interface> <expr>'
        sys.exit(0)
    
    dev = getInterface()
  
    # Open interface for catpuring.
    p = open_live(dev, 1500, 0, 100)
    
    # Set the BPF filter. See tcpdump(3).
    filter = ' '.join(sys.argv[2:])
    p.setfilter(filter)
    
    print "Listening on %s: net=%s, mask=%s, linktype=%d" % (dev, p.getnet(), p.getmask(), p.datalink())
  
    # Start sniffing thread and finish main thread.
    DecoderThread(p, udp_obj).start()
