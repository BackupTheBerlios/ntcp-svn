import struct, socket, time, logging, random, os

import twisted.internet.defer as defer
from twisted.internet import threads
from twisted.internet.protocol import Protocol, Factory

from ntcp.stunt.StuntProtocol import StuntProtocol

DefaultServers = [
    ('p-maul.rd.francetelecom.fr', 3478),
    ('new-host-2.mmcbill2', 3478),
]

CHANGE_NONE = struct.pack('!i',0)
CHANGE_PORT = struct.pack('!i',2)
CHANGE_IP = struct.pack('!i',4)
CHANGE_BOTH = struct.pack('!i',6)

class _NatType:
  """The NAT handler"""
  def __init__(self, type, useful=True, blocked=False, 
               _publicIp=None, _privateIp=None, _delta=0):
    
    self.type = type
    self.useful = useful
    self.blocked = blocked
    self.publicIp = _publicIp
    self.privateIp = _privateIp
    self.delta = _delta
    self.filter = None
    
  def __repr__(self):
    return '<NatType %s>'%(self.type)


NatTypeNone = _NatType('None')

class StuntClient(StuntProtocol, object):
  
  log = logging.getLogger("ntcp")

  publicIp = None
  privateIp = None
  delta = 0

  def __init__(self, servers=DefaultServers):
    super(StuntClient, self).__init__()
    self.deferred = defer.Deferred()
    self.localPort = random.randrange(7000, 7100)
    self.localIp = socket.gethostbyname(socket.gethostname())
    self.privateIp = self.localIp
    self.state = '1a'
    self.natType = None
    self.servers = [(socket.gethostbyname(host), port)
                    for host, port in servers]
    self.serverAddress = servers[0]

  def connectionMade(self):
    self.sendMessage()
 
  def parseIfClient(self):
    """
    Control if the response is in the pending request

    @return int : 1 if is an good response, 0 otherwise
    """
    if self.tid in self._pending:
      del self._pending[self.tid]
      return 1
    return 0
  
  def startDiscovery(self):
    self.log.debug('>> Test 1a')
    self.test(self.serverAddress)
    return self.d

  def sndBindingRequest(self):
    self.messageType = 'Binding Request'
    self.sndMessage()

  def sndCaptureRequest(self, attributes=()):
    self.messageType = 'Capture Request'
    self.sndMessage(attributes)
    
  def sndMessage(self, attributes=()):
    self.tid = self.getRandomTID()
    self._pending[self.tid] = (time.time(), self.serverAddress)
    self.log.debug('sndBindingRequest: message type: %s'%self.messageType)
    self.createMessage(attributes)

    return self.deferred

  def finishedStunt(self):
    pass

  def _resolveStunServers(self):
    # reactor.resolve the hosts!
    for host, port in self.servers:
      d = reactor.resolve(host)
      d.addCallback(lambda x,p=port: self.test1((x, p))) # x=host
      
# ---------------------------------------------------------------
# TEST (1, 2, 3) in STUNT protocol:  Binding Behaviour
# ---------------------------------------------------------------

  def test(self, remoteAddress):
    """Test 1 in STUNT"""
    self.sndBindingRequest()
##     self.reactor.connectTCP(remoteAddress[0], remoteAddress[1], \
##                             ClientFactory(self), 30, (self.localIp, self.localPort))

    self.connect(remoteAddress, (self.localIp, self.localPort))
  
  def rcvBindingResponse(self):
    if self.state == '1a':
      self.handleState1a()
    elif self.state == '1b':
      self.handleState1b()
    elif self.state == '2':
      self.handleState2()
    elif self.state == '3':
      self.handleState3()
  
  def handleState1a(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] == (self.localIp, self.localPort):
      self.natType = NatTypeNone
      self.finishedStunt()
    else:
      self.log.debug('>> Test 1b')
      self.state = '1b'
      self.publicIp = self.resdict['externalAddress'][0]
      self.previousExternalAddress = self.resdict['externalAddress']
      time.sleep(1)

      #-----------------------------------------------------------
      #self.test(self.serverAddress) # ==> commented for the test
      self.handleState1b()           # ==> for the test (comment it!!!)
      #-----------------------------------------------------------

  def handleState1b(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] != self.previousExternalAddress:
      self.natType = _NatType('SessionDependent', _publicIp=self.publicIp, _privateIp=self.privateIp)
      #self.startFileringDiscovery()
      self.finishedStunt()
    else:
      self.log.debug('>> Test 2')
      self.state = '2'
      print  self.resdict['_altStunAddress']
      address = (self.serverAddress[0], self.resdict['_altStunAddress'][1])
      self.test(address)    

  def handleState2(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] != self.previousExternalAddress:
      self.delta = self.resdict['externalAddress'][1] - self.previousExternalAddress[1]
      self.natType = _NatType('AddressPortDependent', _publicIp=self.publicIp, _privateIp=self.privateIp, _delta=self.delta)
      #self.startFileringDiscovery()
      self.finishedStunt()
    else:
      self.log.debug('>> Test 3')
      self.state = '3'
      address = self.resdict['_altStunAddress']
      self.test(address)    

  def handleState3(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] != self.previousExternalAddress:
      self.delta = self.resdict['externalAddress'][1] - self.previousExternalAddress[1]
      self.natType = _NatType('AddressDependent', _publicIp=publicIp, _privateIp=privateIp, _delta=self.delta)
      #self.startFileringDiscovery()
      self.finishedStunt()
    else:
      self.natType = _NatType('Independent', _publicIp=self.publicIp, _privateIp=self.privateIp)
      #self.startFileringDiscovery()
      self.finishedStunt()
      
# ---------------------------------------------------------------

# ---------------------------------------------------------------
# TEST (1, 2, 3) in STUNT protocol: Endpoint Filtering Behaviour 
# ---------------------------------------------------------------

  def startFileringDiscovery(self):
    attributes = ()
    self.localPort = random.randrange(7000, 7100)
    self.log.debug('>> Filter: Test 2')
    attributes = attributes + ((0x0003, CHANGE_BOTH),)
    self.state = 'f2' # It doesn't try test 1
    self.filterTest(self.serverAddress, attributes)
  
  def filterTest(self, remoteAddress, attributes = ()):
    """Test 1 in STUNT"""
    self.sndCaptureRequest(attributes)
    self.connect(remoteAddress, (self.localIp, self.localPort))
      
  def rcvCaptureResponse(self):
    if self.state == 'f1':
      self.handleFState1()
    elif self.state == 'f2':
      self.handleFState2()
    elif self.state == 'f3':
      self.handleFState3()

  def handleFState2(self):
    attributes = ()
    if self.receivedSYN == 0:
      self.log.debug('>> Filter: Test 3')
      self.state = 'f3'
      attributes = attributes + ((0x0003, CHANGE_PORT),)
      self.localPort = random.randrange(7000, 7100)
      self.filterTest(self.serverAddress, attributes)    
    else:
      self.natType.filter = 'EndpointIndependent'
      self.finishedStunt()

  def handleFState3(self):
    if self.receivedSYN == 0:
      self.natType.filter = 'EndpointAddressDependent'
      self.finishedStunt()
    else:
      self.natType.filter = 'EndpointAddressPortDependent'
      self.finishedStunt()
      
# ---------------------------------------------------------------
      
# ---------------------------------------------------------------
# ---------------------------------------------------------------

  def connect(self, remoteAddress, localAddress):
    #create an INET, STREAMing socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(localAddress)
    self.s = s
    self.log.debug('connect to: %s:%d'%remoteAddress)
    s.connect(remoteAddress)
    #self.connectionMade()
    self._sendMessage(s)

  def _sendMessage(self, s):
    self.log.debug('Send message')
    s.send(self.pkt)
    if self.state == '1a' or self.state == '1b' \
           or self.state == '2' or self.state == '3': 
      self.recvMessage(s)
    if self.state == 'f1' or self.state == 'f2' or self.state == 'f3':
      d = threads.deferToThread(self.listen, s)
      d.addCallback(self.synReceived)
      d.addErrback(self.error)
      d.setTimeout(5, self.synNotReceived, s)
      
      #self.reactor.callLater(5, self.synNotReceived)

      return d

  def recvMessage(self, s):
    data = s.recv(65535)
    self.closeSocket(s)
    self.dataReceived(data)

  def listen(self, s):
    #self.reactor.callLater(5, self.timeout, s)
    #self.reactor.callInThread(self.timeout, s)
##     self.s = s
##     d = threads.deferToThread(self.timeout)
##     d.addCallback(self.synNotReceived)
    #self.closeSocket(s)
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((self.localIp, self.localPort))
    s.listen(1)
    conn, addr = s.accept()
    conn.close()
    self.closeSocket(s)
    print 'closed'

    return (conn, addr)
        
  def closeSocket(self, s):
    s.shutdown(2)
    s.close

  def synReceived(self, (s, addr)):
    self.closeSocket(s)
    self.log.debug('synReceived')
    if addr != '127.0.0.1' and addr != self.localIp:
      self.log.debug('synReceived')
      self.receivedSYN = 1
      self.rcvCaptureResponse()
    
  def synNotReceived(self, args, sock):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.connect((self.localIp, self.localPort))
    self.closeSocket(s)
    self.closeSocket(sock)
    
    self.log.debug('synNotReceived')
    self.receivedSYN = 0
    #self.closeSocket(self.s)
    self.rcvCaptureResponse()

  def error(self, reason):
    pass
# ---------------------------------------------------------------
# ---------------------------------------------------------------


##########################################################
##
## Binding Behaviour
##
##                               /\
##              +--------+      /  \ N    +--------+
##              | Test 1 |---->/Addr\---->| Test 1 |
##              +--------+     \Same/     +--------+
##                              \? /          |
##                               \/           |
##                                | Y         |
##                                V           V
##                  /\         No NAT         /\
##                 /  \                      /  \
##              N /Bind\     +--------+   Y /Bind\
##    NB=ADP <----\Same/<----| Test 2 |<----\Same/
##                 \? /      +--------+      \? /
##                  \/                        \/
##                   | Y                       | N
##                   |                         V
##                   V            /\         NB=SD
##               +--------+      /  \ N
##               | Test 3 |---->/Bind\----> NB=AD
##               +--------+     \Same/
##                               \? /
##                                \/
##                                 | Y
##                                 |
##                                 V
##                               NB=I
##
##########################################################
        
##########################################################
##
## Endpoint Filtering Behaviour
##
##                               /\
##              +--------+      /  \ N    +--------+
##              | Test 1 |---->/Recv\---->| Test 2 |
##              +--------+     \ SYN/     +--------+
##                              \? /          |
##                               \/           |
##                                | Y         |
##                                V           |
##                              EF=O         /\
##                 /\                       /  \
##              Y /  \      +--------+   N /Recv\
##    EF=AD <----/Recv\<----| Test 3 |<----\ SYN/
##               \ SYN/     +--------+      \? /
##                \? /                       \/
##                 \/                         | Y
##                 | N                        V
##                 V                        EF=I
##               EF=ADP
##
##
##########################################################
