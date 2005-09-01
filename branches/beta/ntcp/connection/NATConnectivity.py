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
    
  def holePunching(self, uri):
    """
    """
    self._puncher.sndLookupRequest(remoteUri=uri)

  def setFactory(self, factory):
    """Sets a factory for TCP connection

    @param factory - a twisted.internet.protocol.*Factory instance 
    """
    self._puncher.setFactory(factory)
  def getFactory(self):
    """Gets the TCP factory
    
    @return: factory - a twisted.internet.protocol.ServerFactory instance
    """
    return self._puncher.getFactory()
  
  def listenTCP(self, port=0, factory=None, backlog=5, interface='',  uri=None):
    """Make a registration to CB and listen for incoming connection request

    @param port: a port number on which to listen, default to 0 (any) (only default implemented)
    @param factory: a twisted.internet.protocol.ServerFactory instance 
    @param backlog: size of the listen queue (not implemented)
    @param interface: the hostname to bind to, defaults to '' (all) (not implemented)
    @param uri: the user's URI for registration to Connection Broker
    return: void
    """
    d = defer.Deferred()
    #self._puncher = Puncher(self.reactor, self, self.udpListener)
    
    if factory != None:
      # Sets the factory for TCP connection
      self.setFactory(factory)

    d = self._puncher.sndRegistrationRequest(uri)
    return d
    
  def connectTCP(self, host=None, remoteUri=None, \
                 port=0, factory=None, \
                 timeout=30, bindAddress=None, \
                 myUri=None):
    """
    Force a connection with another user through NATs
    helped by the ConnectionBroker.
    It needs at least one between 'host' and 'remoteUri'

    @param host: a host name, default None
    @param remoteUri : The remote endpoint's uri, default None
    @param port: a port number, default to 0 (any)
    @param factory: a twisted.internet.protocol.ClientFactory instance 
    @param timeout: number of seconds to wait before assuming the connection has failed.  (not implemented)
    @param bindAddress: a (host, port) tuple of local address to bind to, or None. (not implemented)
    @param myUri : The uri for future incoming connection request

    @return :  An object implementing IConnector.
    This connector will call various callbacks on the factory
    when a connection is made,failed, or lost
    - see ClientFactory docs for details.
    """
    d = defer.Deferred()
    d_conn = defer.Deferred()
    
    if self._puncher == None:
      self._puncher = Puncher(self.reactor, self)

    if self.getFactory() == None and factory == None:
      # Error
      d.errback(failure.DefaultException('You have to specify a factory'))
    elif factory != None:
      self.setFactory(factory)

    def fail(failure):
      """ Error in NAT Traversal TCP """
      print 'ERROR in NAT Traversal (registration):', failure.getErrorMessage()
  
    def connection_succeed(result):
      print 'connection succeed:', result
      d_conn.callback(result)
      
    def connection_fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      
    def discovery_fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      
    def discover_succeed(publicAddress):
      self.publicAddr = publicAddress
      if self.publicAddr != None:
        d = defer.Deferred()
        d = self._puncher.sndConnectionRequest(remoteUri, host)
        d.addCallback(connection_succeed)
        d.addErrback(connection_fail)

        print self._puncher.peerConn
      else:
        self.d.errback('The NAT doesn\'t allow inbound TCP connection')

    def registrationSucceed(result):
      print 'Registration to the SN Connection Broker has be done'
    
      # Discovery external address
      d = self.publicAddrDiscovery(port)
      d.addCallback(discover_succeed)
      d.addErrback(discovery_fail)
      
    # Registration to Connection Broker for incoming connection
    if myUri != None:
      d = self._puncher.sndRegistrationRequest(myUri)
      d.addCallback(registrationSucceed)
      d.addErrback(fail)
    else:
      d = self.publicAddrDiscovery(port)
      d.addCallback(discover_succeed)
      d.addErrback(discovery_fail)
      
    return d_conn
