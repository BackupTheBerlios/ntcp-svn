import struct, socket, time, logging, random
import twisted.internet.defer as defer

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
  
  def __init__(self, reactor):
    super(Puncher, self).__init__()
    self.deferred = defer.Deferred()
    self.reactor = reactor

    self.requestor = None
    
    hostname, port = self.p2pConfig.get('holePunch', 'ConnectionBroker').split(':')
    ip = socket.gethostbyname(hostname)
    self.server = (ip, int(port))
    #self.server = ('127.0.0.1', int(port))
    
    punchPort = int(self.p2pConfig.get('holePunch', 'punchPort'))
    punchPort = random.randrange(6900, 6999)
    flag = 1 
    while flag: 
      try:
        self.listening = self.reactor.listenUDP(punchPort, self)
        flag = 0
      except :
        print 'excepttioooonnn'
        punchPort = random.randrange(6900, 6999)
        

  def sndRegistrationRequest(self, uri, natConf):
    """
    Sends a registration request to the SN Connection Broker

    @param string uri : The identifier for registration
    @param NAT natConf : The NAT configuration
    @return void :
    """
    
    listAttr = ()
    self.publicAddr = (natConf.publicIp, 0)
    self.privateAddr = (natConf.privateIp, 0)
    self.uri = uri
    
    listAttr = listAttr + ((0x0001, uri),)
    listAttr = listAttr + ((0x0002, self.getPortIpList(self.publicAddr)),)
    listAttr = listAttr + ((0x0003, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0004, NatTypeCod[natConf.type]),)
    
    self.messageType = 'Registration Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.server, listAttr)

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
    self.log.debug('Received keep alive response...I go to sleep for 20s')
    self.reactor.callLater(20, self.sndKeepAliveRequest)

  def sndKeepAliveRequest(self):
    """Sends the keep alive message"""
    self.log.debug('I am awake... I send a keep alive msg!')
    self.messageType = 'Keep Alive Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.server)
  
  def sndLookupRequest(self, remoteUri, natConf):
    """
    Send a lookup request to discover and advise the remote user
    behind a NAT for a TCP connection

    @param string uri : The remote node identifier
    @return void :
    """
    self.remoteUri = remoteUri
    self.requestor = 1
    
    listAttr = ()
    self.publicAddr = natConf.publicAddr
    
    listAttr = listAttr + ((0x0001, remoteUri),)
    listAttr = listAttr + ((0x1005, self.uri),)
    listAttr = listAttr + ((0x0005, self.getPortIpList(self.publicAddr)),)
    listAttr = listAttr + ((0x0006, self.getPortIpList(self.privateAddr)),)
    listAttr = listAttr + ((0x0004, NatTypeCod[natConf.type]),)
    
    self.messageType = 'Lookup Request'
    self.tid = self.getRandomTID()
    self.sendMessage(self.server, listAttr)

  def rcvLookupResponse(self):
    """
    The SN-Connection Broker answer to a lookup request

    @param NAT dstNatConf : The remote endpoint NAT configuration
    @return void :
    """

    dummy,family,port,addr = struct.unpack( \
                '!ccH4s', self.avtypeList["PUBLIC-ADDRESSE"])
    self.remotePublAddress = (socket.inet_ntoa(addr), port)
    dummy,family,port,addr = struct.unpack( \
                '!ccH4s', self.avtypeList["PRIVATE-ADDRESSE"])
    self.remotePrivAddress = (socket.inet_ntoa(addr), port)
    self.remoteNatType = self.avtypeList["NAT-TYPE"]

    # Call the NAT traversal TCP method
    self.natTraversal()

  def rcvConnectionRequest(self):
    """
    A remote user wants to establish a connection.
    Sarts the connection through NATs procedure

    @param string uri : The remote endpoint identifier
    @param NAT requestorNatConf : The remote endpoint NAT configuration
    @return void :
    """
    self.requestor = 0

    self.remoteUri = self.avtypeList["REQUESTOR-USER-ID"]
    dummy,family,port,addr = struct.unpack( \
                '!ccH4s', self.avtypeList["REQUESTOR-PUBLIC-ADDRESSE"])
    self.remotePublAddress = (socket.inet_ntoa(addr), port)
    
    dummy,family,port,addr = struct.unpack( \
                    '!ccH4s', self.avtypeList["REQUESTOR-PRIVATE-ADDRESSE"])
    self.remotePrivAddress = (socket.inet_ntoa(addr), port)
    self.remoteNatType = self.avtypeList["NAT-TYPE"]

    # Call the NAT traversal TCP method
    self.natTraversal()
      
  def sendMessage(self, toAddr, attributes=()):
    """
    Sets some variables before send the message
    """
    # TODO: set timeout
    self._pending[self.tid] = (time.time(), toAddr)
    self.createMessage(attributes)
    self.transport.write(self.pkt, toAddr)

    
