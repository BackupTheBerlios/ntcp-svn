import logging, random, time

import twisted.internet.defer as defer
from twisted.internet import threads
import twisted.python.failure as failure

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
  It discovers the NAT information (type and mapping)
  :version: 0.2
  :author: Luca Gaballo
  """
  log = logging.getLogger("ntcp")
  
  def __init__(self):
    # The nat configuration
    self.type = None
    self.delta = None
    self.publicIP = None
    self.publicPort = None
    self.publicAddr = (self.publicIP, self.publicPort)
    self.privateIp = None
    self.privatePort = None
    self.privateAddr = (self.privateIp, self.privatePort)

  def natDiscovery(self, bloking = 1):
    """
    Discover NAT presence and information about.

    @param bloking: if 0 makes NAT discovery in non bloking mode (default 1)
    @return void :
    """
    if bloking:
      return self._natDiscoveryDefer()
    else:
      return self._natDiscoveryThread()

  def _natDiscoveryDefer(self):
    """Makes NAT discovery in bloking mode

    @return defer: 
    """
    d = defer.Deferred()
    d2 = defer.Deferred()
   
    def succeed(natConfig):
      """The STUN/STUNT discovery has be done."""
      self.setNatConf(natConfig)
      self.printNatConf()
      d2.callback((self.publicIp, 0))
      return d2
              
    def fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      
    # Start to discover the public network address and NAT configuration
    d = stunt.NatDiscovery(self.reactor)
    d.addCallback(succeed)
    d.addErrback(fail) 

    return d2

  def _natDiscoveryThread(self):
    """Makes NAT discovery in non-bloking mode
    start the discovery process in a thread

    @return void:
    """
    d = defer.Deferred()
   
    def succeed(natConfig):
      """The STUN/STUNT discovery has be done."""
      print "STUNT discovery found address!"
      self.setNatConf(natConfig)
      self.printNatConf()
              
    def fail(failure):
      print "STUNT failed:", failure.getErrorMessage()
      
    # Start to discover the public network address and NAT configuration
    self.reactor.callInThread(stunt.NatDiscovery, self.reactor, self)
    
  def publicAddrDiscovery(self, localPort=0):
    """
    Discover the mapping for the tuple (int IP, int port, ext IP, ext port)
    
    @param int localPort : The connection local port (default any)
    @return tuple publicAddress : The previewed mapped address on the NAT
    """
    d = defer.Deferred()
    d2 = defer.Deferred()
    
    if localPort == 0:
      localPort = random.randrange(49152, 65535)

    # Set the private address too
    self.privatePort = localPort
    self.privateAddr = (self.privateIp, self.privatePort)

    def discovery_fail(failure):
      d = defer.Deferred()
      d.errback(failure)
        
    def discover_succeed(publicAddress):
      print 'Address and Port discovered', publicAddress
      self.publicIp = publicAddress[0]
      # Discover the public address (from NAT config)
      if self.type == 'Independent':
        self.publicPort = publicAddress[1] - 1

      if self.type == 'AddressDependent':
        self.publicPort = publicAddress[1] - 1 + self.delta
        
      if self.type == 'AddressPortDependent':
        self.publicPort = publicAddress[1] - 1 + self.delta
        
      if self.type == 'SessionDependent':
        self.publicPort = publicAddress[1] - 1 + self.delta
        
      publicAddr = (self.publicIp, self.publicPort)

      d2.callback(publicAddr)

    if self.type == 'None':
      d2.callback((self.publicIp, localPort))
    else:      
      d = stunt.AddressDiscover(self.reactor, localPort+1)
      d.addCallback(discover_succeed)
      d.addErrback(discovery_fail)

    return d2
      

  def setNatConf(self, natConfig):
    """
    Sets the NAT's configuration

    @param NatConf : the NAT configuration tuple 
    @return void :
    """
    self.type = natConfig.type 
    self.delta = natConfig.delta
    self.publicIp = natConfig.publicIp
    self.privateIp = natConfig.privateIp

    # Upload the NAT configuration link in puncher
    self._puncher.setNatObj(self)

  def printNatConf(self):
    """
    Prints the NAT's configuration
    
    @return void :
    """
    print "*------------------------------------------------------*"
    print "NTCP Configuration:\n"
    print "\t", configurationText[1], "\t", self.type
    print "\t", configurationText[2], "\t", self.privateIp
    print "\t", configurationText[3], "\t", self.publicIp
    print "\t", configurationText[4], "\t", self.delta
    print "*------------------------------------------------------*"
    

class NatConnectivity(NAT, object):

  """
  Interface with the application.
  Discover NAT information (type and mapping) and force a connection
  through NATs with the Super Node Connection Broker's help
  or by a directly UDP connection with the remote endpoint.
  """
  
  logging.basicConfig()
  log = logging.getLogger("ntcp")
  log.setLevel(logging.DEBUG)

  def __init__(self, reactor, udpListener=None):
    super(NatConnectivity, self).__init__()
    self.reactor = reactor
    self._puncher = None # the puncher to establish the connection
    self.udpListener = udpListener # A listener for UDP communication
    self._puncher = Puncher(self.reactor, self, self.udpListener)

  def datagramReceived(self, message, fromAddr):
    """A link to the internal datagramReceived function"""
    self._puncher.datagramReceived(message, fromAddr)

  def registrationToCB(self, uri, factory=None):
    """Make a registration to CB

    @param uri: the user's URI
    @param factory: the factory to menage a TCP connection (default=None)
    """
    d = defer.Deferred()
    #self._puncher = Puncher(self.reactor, self, self.udpListener)
    
    if factory != None:
      # Sets the factory for TCP connection
      self.setFactory(factory)

    d = self._puncher.sndRegistrationRequest(uri)
    return d
    
  def holePunching(self, uri):
    """
    """
    self._puncher.sndLookupRequest(remoteUri=uri)

  def connectTCP(self, remoteUri=None, remoteAddress=None,\
                 factory=None, localPort=0):
    """
    Force a connection with another user through NATs
    helped by the ConnectionBroker

    @param string remoteUri : The remote endpoint's uri
    @param tuple remoteAddress : The remote endpoint's address
    @param CliantFactory factory : The TCP Client factory
    @param int localPort : The local port for TCP connection (default any)
    @return void :
    """
    d = defer.Deferred()
    
    if self._puncher == None:
      self._puncher = Puncher(self.reactor, self)

    if self.getFactory() == None and factory == None:
      # Error
      d.errback(failure.DefaultException('You have to specify a factory'))
    elif factory != None:
      self.setFactory(factory)
      
    def discovery_fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      
    def discover_succeed(publicAddress):
      self.publicAddr = publicAddress
      if self.publicAddr != None:
        d = self._puncher.sndConnectionRequest(remoteUri, remoteAddress)
      else:
        self.d.errback('The NAT doesn\'t allow inbound TCP connection')
      
    d = self.publicAddrDiscovery(localPort)
    d.addCallback(discover_succeed)
    d.addErrback(discovery_fail)

  def setFactory(self, factory):
    """Sets a factory for TCP connection"""
    self._puncher.setFactory(factory)
  def getFactory(self):
    """Gets the TCP factory"""
    return self._puncher.getFactory()
