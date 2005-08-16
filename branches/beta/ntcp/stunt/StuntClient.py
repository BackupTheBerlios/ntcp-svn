import struct, socket, time, logging, random, os

import twisted.internet.defer as defer
from twisted.internet.protocol import ClientFactory

from ntcp.stunt.StuntProtocol import StuntProtocol

DefaultServers = [
    ('p-maul.rd.francetelecom.fr', 3478),
    ('new-host-2.mmcbill2', 3478),
]

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
    
  def __repr__(self):
    return '<NatType %s>'%(self.type)


NatTypeNone = _NatType('None')
## NatTypeI = _NatType('Independent', _publicIp=publicIp, _privateIp=privateIp)
## NatTypeAD = _NatType('AddressDependent', _publicIp=publicIp, _privateIp=privateIp)
## NatTypeADP = _NatType('AddressPortDependent', _publicIp=publicIp, _privateIp=privateIp)
## NatTypeSD = _NatType('SessionDependent', _publicIp=publicIp, _privateIp=privateIp)

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
    self.tid = self.getRandomTID()
    self._pending[self.tid] = (time.time(), self.serverAddress)
    self.log.debug('sndBindingRequest: message type: %s'%self.messageType)
    self.createMessage()

    return self.deferred
  
  def rcvBindingResponse(self):
    if self.state == '1a':
      self.handleState1a()
    elif self.state == '1b':
      self.handleState1b()
    elif self.state == '2':
      self.handleState2()
    elif self.state == '3':
      self.handleState3()

  def finishedStunt(self):
    pass

  def _resolveStunServers(self):
    # reactor.resolve the hosts!
    for host, port in self.servers:
      d = reactor.resolve(host)
      d.addCallback(lambda x,p=port: self.test1((x, p))) # x=host
      
# ---------------------------------------------------------------
# TEST (1, 2, 3) in STUNT protocol
# ---------------------------------------------------------------

  def test(self, remoteAddress):
    """Test 1 in STUNT"""
    self.sndBindingRequest()
##     self.reactor.connectTCP(remoteAddress[0], remoteAddress[1], \
##                             ClientFactory(self), 30, (self.localIp, self.localPort))

    self.connect(remoteAddress, (self.localIp, self.localPort))


  
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
      self.finishedStunt()
    else:
      self.log.debug('>> Test 2')
      self.state = '2'
      address = (self.serverAddress[0], self.resdict['_altStunAddress'][1])
      self.test(address)    

  def handleState2(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] != self.previousExternalAddress:
      self.delta = self.resdict['externalAddress'][1] - self.previousExternalAddress[1]
      self.natType = _NatType('AddressPortDependent', _publicIp=self.publicIp, _privateIp=self.privateIp, _delta=self.delta)
      self.finishedStunt()
    else:
      self.log.debug('>> Test 3')
      self.state = '3'
      address = self.resdict['_altStunAddress']
      address = (address[0], address[1])
      self.test(address)    

  def handleState3(self):
    #self.transport.loseConnection()
    #self.closeSocket()
    if self.resdict['externalAddress'] != self.previousExternalAddress:
      self.delta = self.resdict['externalAddress'][1] - self.previousExternalAddress[1]
      self.natType = _NatType('AddressDependent', _publicIp=publicIp, _privateIp=privateIp, _delta=self.delta)
      self.finishedStunt()
    else:
      self.natType = _NatType('Independent', _publicIp=self.publicIp, _privateIp=self.privateIp)
      self.finishedStunt()
      
# ---------------------------------------------------------------

      
# ---------------------------------------------------------------
# ---------------------------------------------------------------

  def connect(self, remoteAddress, localAddress):
    #create an INET, STREAMing socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind(localAddress)
    self.log.debug('connect to: %s:%d'%remoteAddress)
    s.connect(remoteAddress)
    #self.connectionMade()
    self._sendMessage(s)

  def _sendMessage(self, s):
    s.send(self.pkt)
    self.recvMessage(s)

  def recvMessage(self, s):
    data = s.recv(65535)
    self.closeSocket(s)
    self.dataReceived(data)

  def closeSocket(self, s):
    s.shutdown(2)
    s.close
  
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
