import struct, socket, time, logging, random
import twisted.internet.defer as defer


class ConnectionPunching:
  """
  This class chooses, in function of the NAT information,
  the methode to use for the connection and implements it
  """
  
  def __init__(self):
      pass
  
  
  
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
          # listen
          pass
      else:
          # connect
          pass
      
