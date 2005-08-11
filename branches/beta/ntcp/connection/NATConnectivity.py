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

  def __init__(self, reactor):
    super(NATConnectivity, self).__init__()
    self.reactor = reactor

  def forceConnection(self, remoteUri=None, remoteAddr=None, localPort=0):
    """
    Force a connection with another user
    through NATs helped by the SN-ConnectionBroker

    @param string peerUri : The remote endpoint's uri
    @return void :
    """
    publicAddr = self.publicAddrDiscovery(localPort)
    self.log.debug('The previwed publicAddress mapped by NAT is: %s:%d'%publicAddr)

    if publicAddr != None:
      self.puncher.sndLookupRequest(remoteUri, self)

    return self.d


