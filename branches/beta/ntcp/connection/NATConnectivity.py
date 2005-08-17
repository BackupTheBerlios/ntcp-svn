import logging, random

import twisted.internet.defer as defer

from ntcp.punch.Puncher import Puncher
import ntcp.stunt.StuntDiscovery as stunt

configurationText = ['NAT presence ', \
                     'NAT type     ', \
                     'My private IP', \
                     'My public IP ', \
                     'Binding delta'] 

class NAT:

  """
  It's a NAT mirror. It has all the information about a NAT (if there is one).
  It discevers the NAT information (type and mapping)
  :version: 0.2
  :author: Luca Gaballo
  """
  log = logging.getLogger("ntcp")
  
  def __init__(self):
    self.d = defer.Deferred()
    # The nat configuration
    self.type = None
    self.delta = None
    self.publicIP = None
    self.publicPort = None
    self.publicAddr = (self.publicIP, self.publicPort)
    self.privateIp = None
    self.privatePort = None
    self.privateAddr = (self.privateIp, self.privatePort)

  def natDiscovery(self, uri='xxx'):
    """
    Discover NAT presence and information about.
    In case of NAT presence it registers himself to his SN Connection Broker

    @return void :
    """
    d = self.d

    def registrationMade(result):
      """ Registration to the SN Connection Broker has be done """
      if not d.called:
        d.callback()

    def registrationFail(failure):
      """ Fail in registration to the Super Node """
      self.log.error(' in registration to CB: %s'%failure.getErrorMessage())
   
    def succeed(natConfig):
      """
      The STUN/STUNT discovery has be done.
      Registration to the SN Connection Broker
      """
      self.log.debug(natConfig)
      self.setNatConf(natConfig)
      self.printNatConf()

      # Registration to the Connection Broker
      self.puncher = Puncher(self.reactor, self.factory, self)
      d = self.puncher.sndRegistrationRequest(uri)
      d.addCallback(registrationMade)
      d.addErrback(registrationFail)

              
    def fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      return d
      
    # Start to discover the public network address and NAT configuration
    d = stunt.NatDiscovery(self.reactor)
    d.addCallback(succeed)
    d.addErrback(fail)   

    return d

  def publicAddrDiscovery(self, localPort=0):
    """
    Discover the mapping for the tuple (int IP, int port, ext IP, ext port)
    
    @param int localPort : The connection local port (default any)
    @return tuple publicAddress : The previewed mapped address on the NAT
    """
#    @param tuple remoteAddr : The connection's remote address (IP, port)

    if localPort == 0:
      localPort = random.randrange(49152, 65535)

    # Set the private address too
    self.privatePort = localPort
    self.privateAddr = (self.privateIp, self.privatePort)

    # Discover the public address (from NAT config)
    if self.type == 'Independent':
      self.publicPort = localPort
      self.publicAddr = (self.publicIp, localPort)
      return self.publicAddr
    if self.type == 'AddressDependent':
      self.publicPort = localPort
      self.publicAddr = (self.publicIp, localPort)
      return self.publicAddr
    if self.type == 'AddressPortDependent':
      self.publicPort = localPort
      self.publicAddr = (self.publicIp, localPort)
      return self.publicAddr
    if self.type == 'SessionDependent':
      return None


  def setNatConf(self, natConfig):
    """
    sets the NAT's configuration

    @param NatConf : the NAT configuration tuple 
    @return void :
    """
    self.type = natConfig.type 
    self.delta = natConfig.delta
    self.publicIp = natConfig.publicIp
    self.privateIp = natConfig.privateIp

  def printNatConf(self):
    """
    Prints the NAT's configuration
    
    @return void :
    """
    print "\n*------------------------------------------------------*"
    print "Configuration:\n"
    print "\t", configurationText[1], "\t", self.type
    print "\t", configurationText[2], "\t", self.privateIp
    print "\t", configurationText[3], "\t", self.publicIp
    print "*------------------------------------------------------*"
    



class NatConnectivity(NAT, object):

  """
  Interface with the application. Discover NAT information (type and mapping) and force a connection through NATs with the Super Node Connection Broker's help.
  :version:
  :author:
  """
  
  logging.basicConfig()
  log = logging.getLogger("ntcp")
  log.setLevel(logging.DEBUG)

  def __init__(self, reactor, factory):
    super(NatConnectivity, self).__init__()
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


