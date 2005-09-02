import struct, socket, time, logging, random, sys
import twisted.internet.defer as defer
import twisted.python.failure as failure

from ntcp.punch.PuncherProtocol import PuncherProtocol
from ntcp.punch.ConnectionPunching import ConnectionPunching
from ntcp.connection.Connector import IConnector

# The NAT types: code and decode
NatTypeCod = {
  'None' : 'NONE',
  'Independent' : '000I',
  'AddressDependent' : '00AD',
  'AddressPortDependent' : '0APD',
  'SessionDependent' : '00SD'
   }

NatTypeDec = {
  'NONE' : 'None',
  '000I' : 'Independent',
  '00AD' : 'AddressDependent',
  '0APD' : 'AddressPortDependent',
  '00SD' : 'SessionDependent'
   }

class Puncher(PuncherProtocol, IConnector, object):

  """
  Communicates with the Super Node Connection Broker to registre himself
  and to establish a connection with a peer behiend a NAT
  :version: 0.2
  :author: Luca Gaballo
  """
  
  log = logging.getLogger("ntcp")
  
  def __init__(self, reactor, natObj, udpListener=None):
    """
    Initialises the puncher object to implement
    the hole punching protocol in the endpoint side

    @param reactor: the application's reactor
    @param ntcp.connection.NatConnectivity natObj: the object with NAT information
    @param udpListener: an UDP listener (default None - if None a new one is created)
    """
    super(Puncher, self).__init__()
    # ConnectionPunching.__init__(self)
    self.deferred = defer.Deferred()
    self.d = defer.Deferred()
    self.reactor = reactor
    if udpListener != None:
      self.punchListen = udpListener
    else:
      self.startListen()
    self.setNatObj(natObj) # The NAT configuration
    self.uri = None
    self.remoteUri = None
    self.remoteDelta=0
    self.host = self.remoteUri
    self.port = 0
    self.requestor = 0 # 1 if I'm the requestor, 0 otherwise
    self.registered = 0
    self.error = 0
    self.state = None
    self.c_factory = None
    self.s_factory = None
    self.dedicatedConnector = ()
    self.numConnector = 0
    
    # CB address
    hostname, port = self.p2pConfig.get(\
      'holePunch', 'ConnectionBroker').split(':')
    ip = socket.gethostbyname(hostname)
    self.cbAddress = (ip, int(port))
    
  def setNatObj(self, natObj):
    """Sets the NAT configuration"""
    self.natObj = natObj # The NAT configuration

  def startListen(self):
    """Start to listen on a UDP port"""
    # UDP listening: try to listen on a port
    punchPort = random.randrange(6900, 6999)
    flag = 1 
    while flag:
      # Loop until finds a free port 
      try:
        self.punchListen = self.reactor.listenUDP(punchPort, self)
        self.log.debug('Hole punching listen on port: %d'%punchPort)
        flag = 0
      except :
        print 'Exception:', sys.exc_info()[0]
        punchPort = random.randrange(6900, 6999)
        

  def sndRegistrationRequest(self, uri):
    """
    Sends a registration request to the Connection Broker

    @param string uri : The identifier for registration
    @return void :
    """
    listAttr = ()
    self.publicAddr = (self.natObj.publicIp, 0)
    self.privateAddr = (self.natObj.privateIp, 0)
    self.uri = uri

    # Prepare the message's attributes
    listAttr = listAttr + ((0x0001, uri),)
    listAttr = listAttr + ((0x0002, self.getPortIpList(self.publicAddr)),)
    listAttr = listAttr + ((0x0003, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0004, NatTypeCod[self.natObj.type]),)
    
    self.messageType = 'Registration Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.cbAddress, listAttr)

    return self.deferred

  def rcvRegistrationResponse(self):
    """
    A Connection Broker's registration response is received.
    Start the 'keep alive' mecanism to keep the NAT hole up

    @return void :
    """
    self.registered = 1
    
    # Begin of the keep alive procedure 
    self.rcvKeepAliveResponse()
    
    if not self.deferred.called:
      self.deferred.callback(None)

  def rcvKeepAliveResponse(self):
    """A message from CB broker is received to keep the NAT hole active"""
    #self.log.debug('Received keep alive response...I go to sleep for 20s')
    self.reactor.callLater(20, self.sndKeepAliveRequest)

  def sndKeepAliveRequest(self):
    """Sends the keep alive message"""
    #self.log.debug('I am awake... I send a keep alive msg!')
    listAttr = ()
    # Prepare the message's attributes
    listAttr = listAttr + ((0x0001, self.uri),)

    self.messageType = 'Keep Alive Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.cbAddress, listAttr)
  
  def sndConnectionRequest(self, remoteUri=None, remoteAddress=None):
    """
    Send a connection request to discover and advise the remote user
    behind a NAT for a TCP connection.
    If the remote address is supplied, the request is sent directly
    to remote endpoint, otherwise the CB is contacted.

    @param string uri : The remote node identifier (connection throught CB)
    @param Address remoteAddress : The remote endpoint's address (directly connection)
    @return void :
    """

    self.state = 'connection'
    if remoteAddress != None:
      self.host = self.remoteAddress
      self.toAddress = remoteAddress #Contact directly the remote andpoint
    else:
      if remoteUri == None: 
        d.errback(failure.DefaultException(\
          'You have to specify at least one between remote address and remote URI!'))
        return d
      else: self.host = remoteUri
      self.toAddress = self.cbAddress #Connection througth the CB
      
    self.requestor = 1 # I'm the requestor of a TCP connection
    
    listAttr = ()
    # Reload the public address
    self.publicAddr = self.natObj.publicAddr
    # Reload the private address
    self.privateAddr = self.natObj.privateAddr

    # Prepare the message's attributes
    if remoteUri != None:
      listAttr = listAttr + ((0x0001, remoteUri),)
    if self.uri != None:
      listAttr = listAttr + ((0x1005, self.uri),)
    listAttr = listAttr + ((0x0005, self.getPortIpList(self.publicAddr)),)
    listAttr = listAttr + ((0x0006, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0007, NatTypeCod[self.natObj.type]),)
    
    self.messageType = 'Connection Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.toAddress, listAttr)

    return self.d

  def rcvConnectionResponse(self):
    """
    A connection response is received (from CB or endpoint)
    Now can try to connect

    @return void :
    """
    # Set remote configuration
    self.remotePublicAddress = self.getAddress('PUBLIC-ADDRESSE')
    self.remotePrivateAddress = self.getAddress('PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["NAT-TYPE"]

    # Call the NAT traversal TCP method to try to connect
##     self.connection = ConnectionPunching(punch=self)
##     self.connection.natTraversal(factory=self.c_factory)
    self.getDedicatedConnector().natTraversal(factory=self.c_factory) 

  def rcvConnectionRequest(self):
    """
    A remote user wants to establish a connection.
    We reply to the request and try to connect to
    the requestor endpoint

    @return void :
    """
    self.requestor = 0

    # Set remote configuration
    if "REQUESTOR-USER-ID" in self.avtypeList:
      self.remoteUri = self.avtypeList["REQUESTOR-USER-ID"]    
    self.remotePublicAddress = self.getAddress('REQUESTOR-PUBLIC-ADDRESSE')
    self.remotePrivateAddress = self.getAddress('REQUESTOR-PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["REQUESTOR-NAT-TYPE"]

    # Send a connection response 
    self.sndConnectionResponse()

  def sndConnectionResponse(self):
    """
    Sends a Connection Response Message to the address
    that the Connection Request is received on .
    
    @return void 
    """
    d = defer.Deferred()
          
    def discovery_fail(failure):
      d = defer.Deferred()
      d.errback(failure)
      
    def discover_succeed(publicAddress):
      listAttr = ()
      # Prepare the message's attributes
      # My conf
      self.publicAddr = publicAddress
      self.privateAddr = self.natObj.privateAddr
      if self.uri != None:
        listAttr = listAttr + ((0x0001, self.uri),)
      listAttr = listAttr + ((0x0002, self.getPortIpList(self.publicAddr)),)
      listAttr = listAttr + ((0x0003, self.getPortIpList(self.privateAddr)),)
      listAttr = listAttr + ((0x0004, NatTypeCod[self.natObj.type]),)
      # Requestor conf
      if self.remoteUri != None:
        listAttr = listAttr + ((0x1005, self.remoteUri),)
      listAttr = listAttr + ((0x0005, self.getPortIpList(self.remotePublicAddress)),)
      listAttr = listAttr + ((0x0006, self.getPortIpList(self.remotePrivateAddress)),)
      listAttr = listAttr + ((0x0007, self.remoteNatType),)

      print 'send Connection Response to:', self.fromAddr
      self.messageType = "Connection Response"   
      self.sendMessage(self.fromAddr, listAttr)
      
      # Call the NAT traversal TCP method to try to connect
##     self.connection = ConnectionPunching(punch=self)
##     self.connection.natTraversal(factory=self.s_factory)
      self.getDedicatedConnector().natTraversal(factory=self.s_factory)

      return d

    d = self.natObj.publicAddrDiscovery()
    d.addCallback(discover_succeed)
    d.addErrback(discovery_fail)

    return d
  
# -- Configuration

  def sndConfigurationRequest(self, remoteUri=None, remoteAddress=None):
    """
    Send a configuration request to discover if the remote user is
    behind a NAT.
    If the remote address is supplied, the request is sent directly
    to remote endpoint, otherwise the CB is contacted.

    @param uri : The remote node identifier string (connection throught CB)
    @param remoteAddress : The remote endpoint's address (directly connection)
    @return void :
    """
    self.state = 'configuration'
    self.conf_d = defer.Deferred()
    if remoteAddress != None:
      self.host = self.remoteAddress
      self.toAddress = remoteAddress #Contact directly the remote andpoint
    else:
      if remoteUri == None: 
        d.errback(failure.DefaultException(\
          'You have to specify at least one between remote address and remote URI!'))
        return d
      else: self.host = remoteUri
      self.toAddress = self.cbAddress #Connection througth the CB
          
    listAttr = ()
    # Reload the public address
    self.publicAddr = self.natObj.publicAddr
    # Reload the private address
    self.privateAddr = self.natObj.privateAddr

    # Prepare the message's attributes
    if remoteUri != None:
      listAttr = listAttr + ((0x0001, remoteUri),)
    if self.uri != None:
      listAttr = listAttr + ((0x1005, self.uri),)
    if self.publicAddr != (None, None):
      listAttr = listAttr + ((0x0005, self.getPortIpList(self.publicAddr)),)
    if self.privateAddr != (None, None):
      listAttr = listAttr + ((0x0006, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0007, NatTypeCod[self.natObj.type]),)
    
    self.messageType = 'Configuration Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.toAddress, listAttr)

    return self.conf_d

  def rcvConfigurationResponse(self):
    """
    A configuration response is received (from CB or endpoint)

    @return void :
    """
    # Set remote configuration
    if "PUBLIC-ADDRESSE" in self.avtypeList:   
      self.remotePublicAddress = self.getAddress('PUBLIC-ADDRESSE')
    if "PRIVATE-ADDRESSE" in self.avtypeList:
      self.remotePrivateAddress = self.getAddress('PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["NAT-TYPE"]

    self.natObj.setRemoteNatConf(self.remoteNatType, self.remoteDelta, \
                                 self.remotePrivateAddress, self.remoteNatType)
    self.conf_d.callback(self.remoteNatType)

  def rcvConfigurationRequest(self):
    """
    A remote user wants to know my configuration
    (if I am NAT'ed or not)
    We reply to the request

    @return void :
    """
    # Set remote configuration
    if "REQUESTOR-USER-ID" in self.avtypeList:
      self.remoteUri = self.avtypeList["REQUESTOR-USER-ID"] 
    if "REQUESTOR-PUBLIC-ADDRESSE" in self.avtypeList:   
      self.remotePublicAddress = self.getAddress('REQUESTOR-PUBLIC-ADDRESSE')
    if "REQUESTOR-PRIVATE-ADDRESSE" in self.avtypeList:
      self.remotePrivateAddress = self.getAddress('REQUESTOR-PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["REQUESTOR-NAT-TYPE"]

    # Send a connection response 
    self.sndConfigurationResponse()

  def sndConfigurationResponse(self):
    """
    Sends a configuration Response Message to the address
    that the Connection Request is received on .
    
    @return void 
    """
    d = defer.Deferred()
    
    listAttr = ()
    # Prepare the message's attributes
    # My conf
    self.publicAddr = publicAddress
    self.privateAddr = self.natObj.privateAddr
    if self.uri != None:
      listAttr = listAttr + ((0x0001, self.uri),)
    if self.publicAddr != (None, None):
      listAttr = listAttr + ((0x0002, self.getPortIpList(self.publicAddr)),)
    if self.privateAddr != (None, None):
      listAttr = listAttr + ((0x0003, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0004, NatTypeCod[self.natObj.type]),)
    # Requestor conf
    if self.remoteUri != None:
      listAttr = listAttr + ((0x1005, self.remoteUri),)
    if self.remotePublicAddress != None:
      listAttr = listAttr + ((0x0005, self.getPortIpList(self.remotePublicAddress)),)
    if self.remotePublicAddress != None:
      listAttr = listAttr + ((0x0006, self.getPortIpList(self.remotePrivateAddress)),)
    listAttr = listAttr + ((0x0007, self.remoteNatType),)
    
    print 'send Configuration Response to:', self.fromAddr
    self.messageType = "Configuration Response"   
    self.sendMessage(self.fromAddr, listAttr)

    return d
# -- Configuration (end)

# -- Lookup
  def sndLookupRequest(self, remoteUri=None, remoteAddress=None):
    """
    Send a connection request to discover and advise the remote user
    behind a NAT for a TCP connection.
    If the remote address is supplied, the request is sended directly
    to remote endpoint, otherwise the CB is contacted.

    @param string uri : The remote node identifier (connection throught CB)
    @param Address remoteAddress : The remote endpoint's address (directly connection)
    @return void :
    """
    d = defer.Deferred()
    self.toAddress = self.cbAddress #Connection througth the CB
    
    listAttr = ()
    self.publicAddr = (self.natObj.publicIp, 0)
    self.privateAddr = (self.natObj.privateIp, 0)

    # Prepare the message's attributes
    listAttr = listAttr + ((0x0001, remoteUri),)
    if self.uri != None:
      listAttr = listAttr + ((0x1005, self.uri),)
    listAttr = listAttr + ((0x0005, self.getPortIpList(self.publicAddr)),)
    listAttr = listAttr + ((0x0006, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0007, NatTypeCod[self.natObj.type]),)
    
    self.messageType = 'Lookup Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.toAddress, listAttr)
    return d

  def rcvLookupRequest(self):
    """
    A connection response is received (from CB or endpoint)
    Now can try to connect

    @return void :
    """
    print 'Received Lookup Request'
    # Set remote configuration
    if "REQUESTOR-USER-ID" in self.avtypeList:
      self.remoteUri = self.avtypeList["REQUESTOR-USER-ID"]    
    self.remotePublicAddress = self.getAddress('REQUESTOR-PUBLIC-ADDRESSE')
    self.remotePrivateAddress = self.getAddress('REQUESTOR-PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["REQUESTOR-NAT-TYPE"]

    # Send an Hole Punching message
    self.sndHolePunching()
    
  def rcvLookupResponse(self):
    """
    A connection response is received (from CB or endpoint)
    Now can try to connect

    @return void :
    """
    print 'Received Lookup Response'
    # Set remote configuration
    self.remotePublicAddress = self.getAddress('PUBLIC-ADDRESSE')
    self.remotePrivateAddress = self.getAddress('PRIVATE-ADDRESSE')
    self.remoteNatType = self.avtypeList["NAT-TYPE"]

    # Send an Hole Punching message
    self.sndHolePunching()

  def sndHolePunching(self):
    self.toAddress = self.remotePublicAddress #Hole punching to endpoint
    print 'Received Hole Punching'
        
    self.messageType = 'Hole Punching'
    self.tid = self.getRandomTID()
    self.sendMessage(self.toAddress)

  def rcvHolePunching(self):
    print 'Hole punching: received message from:', self.fromAddr
    
# --
  def sendMessage(self, toAddr, attributes=()):
    """
    Packs the message and sends it

    @param tuple toAddr: the destination address
    @param list attributes: the message's attriubutes
    """
    # TODO: set timeout
    self._pending[self.tid] = (time.time(), toAddr)
    self.createMessage(attributes) # pack the message
    self.punchListen.write(self.pkt, toAddr)
     
  def rcvErrorResponse(self):
    """If an Error Response is received, analises it"""
    # Extract the class and number
    error, phrase = self.getErrorCode()
    if error == 420:
      _listUnkAttr = self.getListUnkAttr()
      print (error, phrase, _listUnkAttr)
    else:
      self.log.warning('%s: %s'%(error, phrase))   

    # Calls the clientConnectionFailed function to go back to user
    self.error = 1
    if self.state == 'configuration':
      if error == 700:
        self.conf_d.callback('Unknown')
      else:
        self.conf_d.errback(failure.DefaultException('%d:%s'%(error, phrase)))
    else:
      self.c_factory.clientConnectionFailed(self, '(%s: %s)'%(error, phrase))
# --

  def getDedicatedConnector(self):
    self.numConnector += 1
    self.connector = ConnectionPunching(punch=self)
    self.dedicatedConnector += (self.connector,)
    return self.dedicatedConnector[self.numConnector-1]
    
    self.connection.natTraversal(factory=self.s_factory) 
    
  
  def setServerFactory(self, factory):
    self.s_factory = factory
    return
  
  def getServerFactory(self):
    return self.s_factory

  def setClientFactory(self, factory):
    self.c_factory = factory
    return

  def getClientFactory(self):
    return self.c_factory
