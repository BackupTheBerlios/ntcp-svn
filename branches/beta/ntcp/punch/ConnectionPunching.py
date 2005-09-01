import struct, socket, time, logging, random, os

from twisted.internet.protocol import Protocol, Factory, ClientFactory
import twisted.internet.defer as defer


class ConnectionPunching(Protocol, ClientFactory):
  """
  This class chooses, in function of the NAT information,
  the methode to use for the connection and implements it.
  If the connection established the twisted methods
  are called to menage the TCP connection
  """
  
  log = logging.getLogger("ntcp")
  
  def __init__(self, _s = None):      
      self.factory = None
      self._super = _s
      self.method = None
      self.connected = 0
      self.attempt = 0
      self.sameLanAttempt = 1
      self.p2pnatAttempt = 1
      self.stunt2Attempt = 1
      self.peerConn = None #  An object implementing IConnector.
  
  def natTraversal(self):
    """
    Chooses the right method for NAT traversal TCP
    """
    print 'natTraversal'
##     self.log.debug('NAT traversal with:')
##     if self.remoteUri != None:
##         self.log.debug('\tURI:\t\t%s'%self.remoteUri)
##     self.log.debug('\tAddress:\t%s:%d'%self.remotePublicAddress)
##     self.log.debug('\tNAT type:\t%s'%self.remoteNatType)
    
    self.attempt = 0
    #self.method = 'stunt2'
    #self.stunt2()
    
    if self.publicAddr[0] == self.remotePublicAddress[0] \
           and self.sameLanAttempt:
        # The two endpoints are in the same LAN
        # but there can be several NATs
        self.method = 'sameLan'
        self.sameLan()
    elif self.remoteNatType == 'None' or self.natObj.type == 'None':
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
          print 'Same LAN: listen on:', self.natObj.privateAddr[1]
          self.transport = None
          self.peerConn = self.reactor.listenTCP(\
              self.natObj.privateAddr[1], self)
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
      self.log.debug('One endpoint is not NATed')
      if self.natObj.type != 'None':
          self.transport = None
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePrivateAddress[0], \
                  self.remotePrivateAddress[1], self)
      else:
          # listen
          print 'One NAT: listen on:', self.natObj.privateAddr[1]
          self.transport = None
          self.peerConn = self.reactor.listenTCP(\
              self.natObj.privateAddr[1], self)
           
  def _oneNat_clientConnectionFailed(self):
      if self.natObj.type != 'None':
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
      self.log.debug('Try to connect with STUNT\#2 method')
      if self.requestor:
          print 'Requestor -> from:', self.privateAddr, \
                'to:', self.remotePublicAddress
          self.transport = None
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePublicAddress[0], \
                  self.remotePublicAddress[1], \
                  self, \
                  bindAddress=self.privateAddr)
      else:
          print 'Contacted -> from:', self.privateAddr, \
                'to:', self.remotePublicAddress[0], self.remotePrivateAddress[1]
          #self.transport = None
          self.peerConn = self.reactor.connectTCP(\
              self.remotePublicAddress[0], \
              self.remotePublicAddress[1], \
              self, \
              timeout = 1, \
              bindAddress = self.privateAddr)

  def stunt2_inv(self):
      self.method = 'stunt2_inv' # Fail: call the next method
      if self.requestor:
          self.requestor = 0
      else:
          self.peerConn.loseConnection()
          self.requestor = 1
      self.stunt2()
          
  def _stunt2_clientConnectionFailed(self):
      if self.requestor:
          if self.attempt < 3:
              # connect
              time.sleep(self.attempt)
              self.attempt = self.attempt + 1
              self.stunt2()
          else:
              if self.method == 'stunt2':
                  self.stunt2_inv()
              elif self.method == 'stunt2_inv':
                  self.attempt = 0
                  self.p2pnat()
      else:
          # listen
          self.log.debug('Listen on %s:%d'%self.natObj.privateAddr)
          self.peerConn = self.reactor.listenTCP(\
              self.natObj.privateAddr[1], self)
          if self.method == 'stunt2':
              self.timeout = self.reactor.callLater(3, self.stunt2_inv)
          elif self.method == 'stunt2_inv':
              self.attempt = 0
              self.timeout = self.reactor.callLater(2, self.p2pnat)

      

  def p2pnat(self):
      try: self.peerConn.loseConnection()
      except: pass
      self.method = 'p2pnat' # Fail: call the next method
      if self.attempt < 1000:
          # connect
          self.attempt = self.attempt + 1
          #self.log.debug('Try to connect with P2PNAT method %d'%self.attempt)
          print 'P2PNAT: From:', self.privateAddr, \
                'to:', self.remotePrivateAddress
          self.peerConn = self.reactor.connectTCP(\
                  self.remotePrivateAddress[0], \
                  self.remotePrivateAddress[1], \
                  self, \
                  bindAddress=self.privateAddr)    

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
      return ConnectionPunching(self)
        
  def clientConnectionFailed(self, connector, reason):
      self.log.debug('[%s]'%reason)
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



