import struct, socket, time, logging, random
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

    self.natObj = natObj # The NAT configuration
    self.requestor = 0 # 1 if I'm the requestor, 0 otherwise
    self.error = 0

    # CB address
    hostname, port = self.p2pConfig.get('holePunch', 'ConnectionBroker').split(':')
    ip = socket.gethostbyname(hostname)
    self.cbAddress = (ip, int(port))

  def startListen():
    """Start to listen on a UDP port"""
    # UDP listening
    punchPort = random.randrange(6900, 6999)
    flag = 1 
    while flag: 
      try:
        self.log.debug('Hole punching port: %d'%punchPort)
        self.punchListen = self.reactor.listenUDP(punchPort, self)
        flag = 0
      except :
        punchPort = random.randrange(6900, 6999)
        

  def sndRegistrationRequest(self, uri):
    """
    Sends a registration request to the SN Connection Broker

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
    A registration response is received by the SN-Connection Broker

    @return void :
    """
    # Begin of the keep alive procedure 
    self.rcvKeepAliveResponse()
    
    if not self.deferred.called:
      self.deferred.callback(None)

  def rcvKeepAliveResponse(self):
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
    behind a NAT for a TCP connection

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

    # TODO: remove obligatory URI
    if remoteUri == None:
      remoteUri = 'xxxx'
    self.remoteUri = remoteUri

    print self.publicAddr
    listAttr = listAttr + ((0x0001, remoteUri),)
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
    A connection response is received
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
    We reply to the request and try to connect to it

    @return void :
    """
    self.requestor = 0

    # Set remote configuration
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
      listAttr = listAttr + ((0x0001, self.uri),)
      listAttr = listAttr + ((0x0002, self.getPortIpList(self.publicAddr)),)
      listAttr = listAttr + ((0x0003, self.getPortIpList(self.privateAddr)),)
      listAttr = listAttr + ((0x0004, NatTypeCod[self.natObj.type]),)
      # Requestor conf
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
