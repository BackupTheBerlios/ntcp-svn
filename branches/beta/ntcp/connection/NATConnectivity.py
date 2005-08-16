import logging

import twisted.internet.defer as defer

from ntcp.connection.NAT import NAT
from ntcp.punch.Puncher import Puncher

class NATConnectivity(NAT, object):

  """
  Interface with the application. Discover NAT information (type and mapping) and force a connection through NATs with the Super Node Connection Broker's help.
  :version:
  :author:
  """
  
  logging.basicConfig()
  log = logging.getLogger("ntcp")
  log.setLevel(logging.DEBUG)

  def __init__(self, reactor, factory):
    super(NATConnectivity, self).__init__()
    self.reactor = reactor
    self.factory = factory

  def connectTCP(self, remoteUri,  factory=None, localPort=0, remoteAddr=None):
    """
    Force a connection with another user
    through NATs helped by the SN-ConnectionBroker

    @param string remoteUri : The remote endpoint's uri
    @param CliantFactory factory : The TCP Client factory
    @return void :
    """
    if factory != None:
      self.factory = factory
      
    self.publicAddr = self.publicAddrDiscovery(localPort)
    self.log.debug('The previwed publicAddress mapped by NAT is: %s:%d'%self.publicAddr)

    if self.publicAddr != None:
      self.puncher.sndLookupRequest(remoteUri, factory)

    return self.d


