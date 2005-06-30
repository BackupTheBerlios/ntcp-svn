from twisted.internet.protocol import DatagramProtocol
from twisted.internet import reactor
import p2pNetwork.testTCP.spoof as spoof

import ConfigParser

class UDP_factory(DatagramProtocol):
  """An UDP service to allow a TCP connection:
   - Hole punching to connect in UDP to the other peer
   - Forces the ack number in a TCP response packet sent via UDP hole"""

  def __init__(self):
    self.sp = spoof.Spoofer()
    print 'Start to listen'
    reactor.listenUDP(9999, self)
    self.receivedSYN = 0
    self.sentSYN = 0

    self.withSpoofing = 0

    # Load configuration
    config = ConfigParser.ConfigParser()
    config.read("test.conf")
    
    self.myIP=config.get('myConf', 'myIP')
    self.myPort=int(config.get('myConf', 'myPort'))
    self.peerIP=config.get('peer', 'peerIP')
    self.peerPort=int(config.get('peer', 'peerPort'))
    self.CBIP=config.get('CB', 'CBIP')
    self.CBPort=int(config.get('CB', 'CBPort'))
    self.udpPort=int(config.get('UDPhole', 'udpPort'))
    
  
  def datagramReceived(self, data, (host, port)):
    """Listen for the peer's SYN
    If it has the SYN and the ACK send the TCP simulated response"""
    
    print "received %r from %s:%d\n" % (data, host, port)
    if data == '':
      print 'Hole made'
      return
    else:
      print 'SYN received (from %s:%d):\t\t'%(host, port), data
      self.receivedSYN = 1
      self.peerSYN=int(data)+1
      self.fakeConnection()

  def punchHole(self):
    """To punch an hole in the NAT for UDP communication with the peer"""
    # Send void packet to punch an hole
    if self.withSpoofing == 0:
      host = self.peerIP
      port = self.udpPort
      
      print "Punch hole...(%s:%d)"%(host, port)
      self.transport.write("", (host, port))
    

  def send_SYN_to_ConnectionBroker(self, syn):
    """Sends the SYN number of my connect()ion to:
    - the other peer for TCP connction without spoofing
    - the connection broker for spoofing"""
    
    # Send SYN to connection broker via UDP protocol
    if self.withSpoofing == 1:
      host = self.CBIP
      port = self.CBPort
    else:
      host = self.peerIP
      port = self.udpPort
    
    print "Send SYN to peer(%s:%d):\t"%(host, port), syn
    self.sentSYN = 1
    self.SYN=int(syn)
    #reactor.listenUDP(50007, self)
    if self.withSpoofing == 1:
      self.transport.write("%ld:%d:%d"%(self.SYN, self.peerPort, self.myPort), (host, port))
    else:
      self.transport.write("%ld"%self.SYN, (host, port))
      
    self.fakeConnection()

  def fakeConnection(self):
    """Sends the SYNACK packet to the other peer
    Optional: sends a SYNACK to himself for a unidirectional
    simulated TCP connection"""

##     if self.sentSYN and not self.receivedSYN:
##       dhost = self.peerIP
##       dport = self.peerPort
##       shost = self.myIP
##       sport = self.myPort
##       argv = ('', dhost, '%ld'%dport, shost, '%ld'%sport, '%ld'%self.SYN)
##       argc = len(argv)
##       print 'Send SYN', self.SYN, 'to%s:%d %s:%d'%(dhost, dport, shost, sport)
##       self.sp.fakeConnection(argv, argc)
    
    #print 'Fake connection:', self.sentSYN, self.receivedSYN, '\n'
    if self.sentSYN and self.receivedSYN:
      dhost = self.peerIP
      dport = self.peerPort
      shost = self.myIP
      sport = self.myPort
      argv = ('', dhost, '%ld'%dport, shost, '%ld'%sport, '%ld'%self.SYN, '%ld'%self.peerSYN)
      argc = len(argv)
      print 'Send SYN-ACK', self.SYN, self.peerSYN, 'to%s:%d %s:%d'%(dhost, dport, shost, sport)
      #self.sp.fakeConnection(argv, argc)

      # -----------------------------------------
      # Auto send SYNACK
##       dhost = '10.193.161.57'
##       dport = 50007
##       shost = '10.193.167.86'
##       sport = 50007
##       self.SYN = self.ACK - 1
##       self.ACK = self.SYN + 1
##       argv = ('', dhost, '%d'%dport, shost, '%ld'%self.SYN, '%ld'%self.ACK)
##       argc = len(argv)
##       self.sp.fakeConnection(argv, argc)
      # -----------------------------------------

