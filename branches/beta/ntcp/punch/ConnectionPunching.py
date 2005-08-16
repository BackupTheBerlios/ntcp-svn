import struct, socket, time, logging, random

from twisted.internet.protocol import Protocol, Factory, ClientFactory
import twisted.internet.defer as defer
from twisted.internet import reactor


class ConnectionPunching(Protocol, ClientFactory):
  """
  This class chooses, in function of the NAT information,
  the methode to use for the connection and implements it
  """
  
  def __init__(self, p = None):
      self.factory = None
      self.p = p
  
  def natTraversal(self):
    """
    Chooses the right method for NAT traversal TCP
    """
    self.log.debug('NAT traversal with:')
    self.log.debug('\tURI:\t%s'%self.remoteUri)
    self.log.debug('\tAddress:\t%s:%d'%self.remotePublAddress)
    self.log.debug('\tNAT type:\t%s'%self.remoteNatType)
    
    if self.publicAddr[0] == self.remotePublAddress[0]:
        # The two endpoints are in the same LAN
        # but there can be several NATs
        self.sameLan()

  def sameLan(self):
      if self.requestor:
          # connect
          self.transport = None
          reactor.connectTCP(self.remotePrivAddress[0], self.remotePrivAddress[1], self)
      else:
          # listen
          self.transport = None
          reactor.listenTCP(self.natObj.privateAddr[1], self)

  def setFactory(self, factory):
      self.factory = factory
      
# ---------------------------------------------------------- 
# ----------------------------------------------------------    
  def dataReceived(self, data):
      self.factory.dataReceived(data)
      
  def connectionMade(self):
      self.connectionMade = 1  
      self.p.connectionMade()

  def connectionLost(self, reason):
      self.factory.clientConnectionLost(None, reason)

  def clientConnectionLost(self, connector, reason):
      self.factory.clientConnectionLost(connector, reason)
      
  def startedConnecting(self, connector):
      self.factory.startedConnecting(connector)
    
  def buildProtocol(self, addr):
      self.p = self.factory.buildProtocol(addr)
      return ConnectionPunching(self.p)
    
  def clientConnectionLost(self, connector, reason):
      self.factory.clientConnectionLost(connector, reason)
    
  def clientConnectionFailed(self, connector, reason):
      self.factory.clientConnectionFailed(connector, reason)
