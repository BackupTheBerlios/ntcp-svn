import struct, socket, time, logging, random, os

from twisted.internet.protocol import Protocol, Factory, ClientFactory
import twisted.internet.defer as defer
import twisted.python.failure as failure
from twisted.internet import reactor
from twisted.internet import threads

class ConnectionPunching(Protocol, ClientFactory, object):
  """
  This class chooses, in function of the NAT information,
  the methode to use for the connection and implements it.
  If the connection established the twisted methods
  are called to menage the TCP connection
  """
  
  log = logging.getLogger("ntcp")
  
  def __init__(self, punch = None, _s = None):      
      self.factory = None
      self._super = _s
      self.method = None
      self.connected = 0
      self.attempt = 0
      self.sameLanAttempt = 1
      self.p2pnatAttempt = 1
      self.stunt2Attempt = 1
      self.t = 5
      self.peerConn = None #  An object implementing IConnector.
      self.timeout = None
      self.error = 0

      try:
        if punch != None and punch.natObj:
          self.init_puncher_var(punch)
      except: print 'except'

  def init_puncher_var(self, punch):
    if punch != None:
      self.punch = punch
      self.reactor = punch.reactor
      self.cbAddress = punch.cbAddress
      
      self.remoteUri = punch.remoteUri
      self.remotePublicAddress = punch.remotePublicAddress
      self.remotePrivateAddress = punch.remotePrivateAddress
      self.remoteNatType = punch.remoteNatType
      
      #self.remoteUri = punch.remoteUri
      self.publicAddress = punch.natObj.publicAddr
      self.privateAddress = punch.natObj.privateAddr
      self.natType = punch.natObj.type

      self.requestor = punch.requestor
      self.d = punch.d
      self.d_conn = punch.d_conn
      self.error = punch.error
  
  def natTraversal(self, factory=None):
    """
    Chooses the right method for NAT traversal TCP
    """
    if factory != None:
      self.factory = factory
    
    self.attempt = 0
    
    self.stunt1()
    if self.publicAddress[0] == self.remotePublicAddress[0] \
           and self.sameLanAttempt:
        # The two endpoints are in the same LAN
        # but there can be several NATs
        self.method = 'sameLan'
        self.sameLan()
    elif self.natType == 'None' or self.remoteNatType == 'None':
        self.oneNat()            
    else:
        self.method = 'stunt2'
        self.stunt2()

  def setFactory(self, factory):
      self.factory = factory
  def getFactory(self):
      return self.factory
  
# ----------------------------------------------------------
# Methods implementation
# ----------------------------------------------------------

# ----------------------------------------------------------
  def sameLan(self):
      """
      This method is called when the peers are in the same LAN.
      Multiple layers of NATs can be present in the same LAN
      and this method could fail if the peers are behind
      different internal NATs.
      """
      self.log.debug('Endpoints in the same LAN:')
      self.log.debug('try to connect with private address')
      if self.requestor:
          self.transport = None
          print 'Same LAN: Try to connect...'
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePrivateAddress[0], \
                  self.remotePrivateAddress[1], self)
          self.log.debug('ppp:%s'%self.peerConn)
      else:
          # listen
          print 'Same LAN: listen on:', self.privateAddress[1]
          self.transport = None
          self.peerConn = self.reactor.listenTCP(\
              self.privateAddress[1], self)
          self.sameLanAttempt = 0
          self.timeout = self.reactor.callLater(\
              6, self._sameLan_clientConnectionFailed)
          
  def _sameLan_clientConnectionFailed(self):
      if self.requestor:
          if self.attempt <= 3:
              # connect
              time.sleep(self.attempt)
              self.attempt = self.attempt + 1
              self.sameLan()
          else:
              self.sameLanAttempt = 0
              self.natTraversal()
      else:
          # listen
          self.natTraversal()

  def oneNat(self):
      """
      """
      #self.log.debug('One endpoint is not NATed')
      print 'One endpoint is not NATed'
      if self.natType != 'None':
          self.transport = None
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePrivateAddress[0], \
                  self.remotePrivateAddress[1], self)
      else:
          # listen
          print 'One NAT: listen on:', self.privateAddress[1]
          self.transport = None
          self.peerConn = self.reactor.listenTCP(\
              self.privateAddress[1], self)
           
  def _oneNat_clientConnectionFailed(self):
      if self.natType != 'None':
          if self.attempt <= 3:
              # connect
              time.sleep(self.attempt)
              self.attempt = self.attempt + 1
              self.oneNat()
          else:
              self.stunt2()
      else:
          # listen
          pass

  def stunt2(self):
      #self.log.debug('Try to connect with STUNT\#2 method')
      #print 'Try to connect with STUNT2 method'
      if self.requestor:
        # Here I try just several client connection
        print 'STUNT2:Requestor -> from:', self.privateAddress, \
              'to:', self.remotePublicAddress
        
        self.transport = None
        self.peerConn = self.reactor.connectTCP(\
                  self.remotePublicAddress[0], \
                  self.remotePublicAddress[1], \
                  self, \
                  timeout = 1, \
                  bindAddress=self.privateAddress)
        
        # Try several connect for t seconds
        if self.method == 'stunt2' and self.timeout == None:
          self.timeout = reactor.callLater(self.t, self.stopConnect)
        elif self.method == 'stunt2_inv' and self.timeout == None:
          self.timeout = reactor.callLater(self.t, self.stopConnect)
          
      else:
        # Here I try with an initial client connection
        # that fail --> try to listen
        print 'STUNT2:Contacted -> from:', self.privateAddress, \
              'to:', self.remotePublicAddress[0], self.remotePrivateAddress[1]
        # self.transport = None
        self.peerConn = self.reactor.connectTCP(\
              self.remotePublicAddress[0], \
              self.remotePublicAddress[1], \
              self, \
              timeout = 1, \
              bindAddress = self.privateAddress)
    
  def stunt2_inv(self):
      self.method = 'stunt2_inv' # Fail: call the next method
      self.timeout = None
      if self.requestor:
          self.requestor = 0
      else:
          self.peerConn.loseConnection()
          self.requestor = 1
      self.stunt2()
          
  def _stunt2_clientConnectionFailed(self):
    # If exist, stop timeout
##     try: self.timeout.cancel()
##     except: pass
      
    if self.requestor:
      if self.attempt < self.t * 100:
        # connect
        time.sleep(self.attempt)
        self.attempt = self.attempt + 1
        self.stunt2()
      else:
        # If exist, stop timeout
        try: self.timeout.cancel()
        except: pass
        if self.method == 'stunt2':
          self.stunt2_inv()
        elif self.method == 'stunt2_inv':
          self.attempt = 0
          self.p2pnat()
    else:
      # listen
      self.log.debug('Listen on %s:%d'%self.privateAddress)
      self.peerConn = self.reactor.listenTCP(\
              self.privateAddress[1], self)
      if self.method == 'stunt2':
        self.timeout = self.reactor.callLater(self.t, self.stunt2_inv)
      elif self.method == 'stunt2_inv':
        self.attempt = 0
        self.timeout = self.reactor.callLater(self.t, self.p2pnat)

  def stopConnect(self):
    self.attempt = self.t * 10000
      
  def p2pnat(self):
      try: self.peerConn.loseConnection()
      except: pass
      self.method = 'p2pnat' # Fail: call the next method
      if self.attempt < self.t * 10:
          # connect
          self.attempt = self.attempt + 1
          #self.log.debug('Try to connect with P2PNAT method %d'%self.attempt)
          print 'P2PNAT: From:', self.privateAddress, \
                'to:', self.remotePublicAddress
          delay = random.random()
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePublicAddress[0], \
                  self.remotePublicAddress[1], \
                  self, \
                  timeout = 1+delay, \
                  bindAddress=self.privateAddress)   
          # Try several connect for t seconds
          if self.attempt == 1:
            self.timeout = reactor.callLater(self.t, self.stopConnect)
      else:
        #self.ntcp_fail()
        self.stunt1()

  def stunt1(self):
    """Try with spoofing"""
    import ntcp.punch.UdpSniffy as udp_sniffer
    import ntcp.punch.rawsniff as sniffer

    # Start to listen for UDP communication
    udp_obj = udp_sniffer.UDP_factory(self)
                                      
    # Start to sniff packets (run method in thread)
    argv = ('', 'eth0', 'tcp port %d'%self.privateAddress[1])
    #reactor.callInThread(sniffer.sniff(argv, udp_obj))
    threads.deferToThread(sniffer.sniff(argv, udp_obj))
    print 'connect'
    self.reactor.connectTCP(\
                  self.remotePublicAddress[0], \
                  self.remotePublicAddress[1], \
                  self, \
                  timeout = 30, \
                  bindAddress=self.privateAddress)
    



  def ntcp_fail(self):
    print 'NTCP: failed to connect with:', self.remotePublicAddress
    self.factory.clientConnectionFailed(self.punch, \
                                        'NTCP: failed to connect with: %s:%d'%self.remotePublicAddress)
##     print self
##     self._super.d_conn.errback(failure.DefaultException('NTCP: failed to connect with: %s:%d'%self.remotePublicAddress))

# ----------------------------------------------------------




# ----------------------------------------------------------
# Wrapping of the twisted.internet.protocol classes
# ----------------------------------------------------------    
  def dataReceived(self, data):
    self._super.protocol.dataReceived(data)
      
  def connectionMade(self):
    self.connected = 1
    # If exist, stop timeout
    try:
      self._super.timeout.cancel()
    except:
      pass
    
    self._super.d.callback(self._super.peerConn)
    
    self._super.protocol.transport = self.transport
    self._super.protocol.connectionMade()
    
  def connectionLost(self, reason):
    #self.factory.clientConnectionLost(None, reason)
    self._super.factory.clientConnectionLost(None, reason)
    
  def startedConnecting(self, connector):
    self.factory.startedConnecting(connector)
    
  def buildProtocol(self, addr):
    self.protocol = self.factory.buildProtocol(addr)
    return ConnectionPunching(self, _s=self)
        
  def clientConnectionFailed(self, connector, reason):
    #print '%s'%reason
    if self.connected == 0 and not self.error:
      if self.method == 'sameLan':
        self._sameLan_clientConnectionFailed()
      elif self.method == 'stunt2':
        self._stunt2_clientConnectionFailed()
      elif self.method == 'stunt2_inv':
        self._stunt2_clientConnectionFailed()
      elif self.method == 'p2pnat':
        self.p2pnat()
    else:
      self.factory.clientConnectionFailed(connector, reason)



