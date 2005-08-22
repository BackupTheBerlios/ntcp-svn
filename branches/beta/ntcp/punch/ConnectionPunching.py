import struct, socket, time, logging, random

from twisted.internet.protocol import Protocol, Factory, ClientFactory
import twisted.internet.defer as defer
from twisted.internet import reactor


class ConnectionPunching(Protocol, ClientFactory):
  """
  This class chooses, in function of the NAT information,
  the methode to use for the connection and implements it
  """
  
  log = logging.getLogger("ntcp")
  
  def __init__(self, _s = None):
      self.factory = None
      self._super = _s
      self.connected = 0
      self.attempt = 0
      self.sameLanAttempt = 1
  
  def natTraversal(self):
    """
    Chooses the right method for NAT traversal TCP
    """
    self.log.debug('NAT traversal with:')
    if self.remoteUri != None:
        self.log.debug('\tURI:\t\t%s'%self.remoteUri)
    self.log.debug('\tAddress:\t%s:%d'%self.remotePublicAddress)
    self.log.debug('\tNAT type:\t%s'%self.remoteNatType)
    
    if self.publicAddr[0] == self.remotePublicAddress[0] and self.sameLanAttempt:
        # The two endpoints are in the same LAN
        # but there can be several NATs
        self.sameLan()
    else:
        self.log.debug('Other method to be implemented')

  def setFactory(self, factory):
      self.factory = factory
  def getFactory(self):
      return self.factory     
# ----------------------------------------------------------
# Methods implementation
# ----------------------------------------------------------

# ----------------------------------------------------------
  def sameLan(self):
      self.log.debug('Endpoints in the same LAN:')
      self.log.debug('try to connect with private address')
      if self.requestor:
          if self.attempt <= 3:
              # connect
              time.sleep(self.attempt)
              self.attempt = self.attempt + 1
              self.transport = None
              print 'Same LAN: Try to connect to:', \
                    self.remotePrivateAddress[0], self.remotePrivateAddress[1]
              self.peerConn = reactor.connectTCP(\
                  self.remotePrivateAddress[0], self.remotePrivateAddress[1], self)
          else:
              self.sameLanAttempt = 0
              self.natTraversal()
      else:
          # listen
          print 'Same LAN: listen on:', self.natObj.privateAddr[1]
          self.transport = None
          self.peerConn = reactor.listenTCP(self.natObj.privateAddr[1], self)
          

# ----------------------------------------------------------




# ----------------------------------------------------------
# Wrapping of the twisted.internet.protocol classes
# ----------------------------------------------------------    
  def dataReceived(self, data):
      self._super.protocol.dataReceived(data)
      
  def connectionMade(self):
      self.connected = 1
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
      if self.connected == 0 and not self.error:
          # The connection never started
          self.natTraversal()
      else:
          self.factory.clientConnectionFailed(connector, reason)
