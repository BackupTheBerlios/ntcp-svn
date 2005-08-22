import struct, socket, time, logging, random, sys
import twisted.internet.defer as defer
import twisted.python.failure as failure

from ntcp.punch.PuncherProtocol import PuncherProtocol
from ntcp.punch.ConnectionPunching import ConnectionPunching

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

class Puncher(PuncherProtocol, ConnectionPunching, object):

  """
  Communicates with the Super Node Connection Broker to registre himself
  and to establish a connection with a peer behiend a NAT
  :version: 0.2
  :author: Luca Gaballo
  """
  
  log = logging.getLogger("ntcp")
  
  def __init__(self, reactor, natObj, udpListener=None):
    super(Puncher, self).__init__()
    ConnectionPunching.__init__(self)
    self.deferred = defer.Deferred()
    self.reactor = reactor
    if udpListener != None:
      self.punchListen = udpListener
    else:
      self.startListen()

    self.setNatObj(natObj) # The NAT configuration
    self.initVar()

  def initVar(self):
    """Initialize all variables"""
    self.uri = None
    self.remoteUri = None
    self.requestor = 0 # 1 if I'm the requestor, 0 otherwise
    self.error = 0
    
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
    # UDP listening
    #punchPort = random.randrange(6900, 6999)
    punchPort = 6950
    flag = 1 
    while flag: 
      try:
        self.punchListen = self.reactor.listenUDP(punchPort, self)
        self.log.debug('Hole punching listen on port: %d'%punchPort)
        flag = 0
      except :
        #punchPort = random.randrange(6900, 6999)
        print 'Exception:', sys.exc_info()[0]
        punchPort = 6955
        

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
    # Begin of the keep alive procedure 
    self.rcvKeepAliveResponse()
    
    if not self.deferred.called:
      self.deferred.callback(None)

  def rcvKeepAliveResponse(self):
    """A message from CB broker is received to keep the NAT hole up"""
    #self.log.debug('Received keep alive response...I go to sleep for 20s')
    self.reactor.callLater(20, self.sndKeepAliveRequest)

  def sndKeepAliveRequest(self):
    """Sends the keep alive message"""
    #self.log.debug('I am awake... I send a keep alive msg!')
    self.messageType = 'Keep Alive Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.cbAddress)
  
  def sndConnectionRequest(self, remoteUri=None, remoteAddress=None):
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

    if remoteAddress != None:
        self.toAddress = remoteAddress #Contact directly the remote andpoint
    else:
      if remoteUri == None: 
        d.errback(failure.DefaultException(\
          'You have to specify at least one between remote address and remote URI!'))
        return d
      self.toAddress = self.cbAddress #Connection througth the CB
      
    self.requestor = 1 # I'm the requestor of a TCP connection
    
    listAttr = ()
    # Reload the public address
    self.publicAddr = self.natObj.publicAddr
    # Reload the private address
    self.privateAddr = self.natObj.privateAddr

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
    return d

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
    self.natTraversal()

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
    # Call the NAT traversal TCP method to try to connect
    self.natTraversal()

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

      self.messageType = "Connection Response"   
      self.sendMessage(self.fromAddr, listAttr)

    d = self.natObj.publicAddrDiscovery()
    d.addCallback(discover_succeed)
    d.addErrback(discovery_fail)

     
  def sendMessage(self, toAddr, attributes=()):
    """
    Packs the message and sends it
    """
    # TODO: set timeout
    self._pending[self.tid] = (time.time(), toAddr)
    self.createMessage(attributes) # pack the message
    self.punchListen.write(self.pkt, toAddr)
     
  def rcvErrorResponse(self):
    # Extract the class and number
    error, phrase = self.getErrorCode()
    if error == 420:
      _listUnkAttr = self.getListUnkAttr()
      print (error, phrase, _listUnkAttr)
    else:
      self.log.warning('%s: %s'%(error, phrase))   

    # Calls the clientConnectionFailed function to go back to user
    self.error = 1
    self.clientConnectionFailed(None, '(%s: %s)'%(error, phrase))
