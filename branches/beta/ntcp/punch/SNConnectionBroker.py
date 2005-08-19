import struct, socket, time, logging

from twisted.internet import reactor
from ntcp.punch.PuncherProtocol import PuncherProtocol

class SNConnectionBroker (PuncherProtocol):

  """
  The Super Node Connection Broker.
  Helps a user to establish a connection with another peer that is behind a NAT.

  :version: 0.2
  :author: Luca Gaballo
  """
  
  logging.basicConfig()
  log = logging.getLogger("CB")
  log.setLevel(logging.DEBUG)
  
  # The IP table with:
  # | id (=primary key) | public IP (=primary key)| private IP | NAT type | 
  peersTable = {}

  def rcvRegistrationRequest(self):
    """
    A Registration Request is received. 

    @return void :
    """
    
    uri = self.avtypeList['USER-ID']
    publAddr = self.fromAddr
    dummy,family,port,ip = struct.unpack( \
                '!cch4s', self.avtypeList['PRIVATE-ADDRESSE'])
    privAddr = (socket.inet_ntoa(ip), port)
    natType = self.avtypeList['NAT-TYPE']
    peerInfo = (uri, publAddr, privAddr, natType)
    self.registrePeer(peerInfo)
    self.printActiveConnection()

    # Reply with a Registration Response
    self.sndRegistrationResponse(publAddr, privAddr)
    
  def sndRegistrationResponse(self, publAddr, privAddr):
    """
    Reply to a registration request

    @return void :
    """
    listAttr = ()
    self.messageType = 'Registration Response'
    listAttr = listAttr + ((0x0002, self.getPortIpList(publAddr)),)
    listAttr = listAttr + ((0x0003, self.getPortIpList(privAddr)),)
    
    self.sendMessage(publAddr, listAttr)

  def rcvKeepAliveRequest(self):
    self.sndKeepAliveResponse()

  def sndKeepAliveResponse(self):
    """Sends the keep alive message"""
    self.messageType = 'Keep Alive Response'
    self.sendMessage(self.fromAddr)

  def rcvConnectionRequest(self):
    """
    A lookup request is received. 

    @return void :
    """
    self.requestor = self.fromAddr

    # Load the peer configuration
    key = self.avtypeList['USER-ID']
    peerInfo = self.getPeerInfo(key)
    if peerInfo == ():
      # TODO: contact other connection broker
      self.sndErrorResponse(((0x0008, '700'),))
      self.log.warn('User not registered!')
      return

    # Sends a Connection request to the other endpoint
    # to get information about it
    self.sndConnectionRequest(peerInfo)
 
  def sndConnectionRequest(self, peerInfo):
    """
    Sends a Connection Request Message to the remote endpoint.
    
    @param peerInfo : the remote endpoint's information
    @return void 
    """
    toAddr = peerInfo[1] # the peer's address
    listAttr = ()
    
    listAttr = listAttr + ((0x1005, self.avtypeList['REQUESTOR-USER-ID']),)
    addr = self.getAddress('REQUESTOR-PUBLIC-ADDRESSE')
    listAttr = listAttr + ((0x0005, self.getPortIpList(addr)),)
    addr = self.getAddress('REQUESTOR-PRIVATE-ADDRESSE')
    listAttr = listAttr + ((0x0006, self.getPortIpList(addr)),)
    listAttr = listAttr + ((0x0007, self.avtypeList['REQUESTOR-NAT-TYPE']),)
    
    self.messageType = "Connection Request"   
    self.sendMessage(toAddr, listAttr)
  
  def rcvConnectionResponse(self):
    """
    Sends a Connection Request Message to the remote endpoint.
    
    @param peerInfo : the remote endpoint's information
    @return void 
    """
    self.sndConnectionResponse()
    
  def sndConnectionResponse(self):
    """
    Sends a lookup response to the puncher.
    
    @return void :
    """ 
    listAttr = ()
    
    listAttr = listAttr + ((0x0001, self.avtypeList['USER-ID']),)
    addr = self.getAddress('PUBLIC-ADDRESSE')
    listAttr = listAttr + ((0x0002, self.getPortIpList(addr)),)
    addr = self.getAddress('PRIVATE-ADDRESSE')
    listAttr = listAttr + ((0x0003, self.getPortIpList(addr)),)
    listAttr = listAttr + ((0x0004, self.avtypeList['NAT-TYPE']),)
    # Requestor conf
    listAttr = listAttr + ((0x1005, self.avtypeList['REQUESTOR-USER-ID']),)
    addr = self.getAddress('REQUESTOR-PUBLIC-ADDRESSE')
    listAttr = listAttr + ((0x0005, self.getPortIpList(addr)),)
    addr = self.getAddress('REQUESTOR-PRIVATE-ADDRESSE')
    listAttr = listAttr + ((0x0006, self.getPortIpList(addr)),)
    listAttr = listAttr + ((0x0007, self.avtypeList['REQUESTOR-NAT-TYPE']),)   

    self.messageType = "Connection Response"    
    self.sendMessage(self.requestor, listAttr)
    
  def printActiveConnection(self):
    """
    Prints the active user registrations

    @return void :
    """
    print '*-----------------------------------------------------------------------*'
    print '* Active connections                                                    *'
    for peer in self.peersTable:
      print "| %12s | %22s | %22s | %4s |" % \
            (peer, self.peersTable[peer][0], \
             self.peersTable[peer][1], \
             self.peersTable[peer][2])                       
    print '*-----------------------------------------------------------------------*'

  def registrePeer(self, (userId, publicIP, privateIp, natInfo)):
    """Records the customer in the customer table"""
    self.peersTable[userId] = (publicIP, privateIp, natInfo)
        
  def getPeerInfo(self, key):
    """Return the client's infos: search by key.
    (id, public address, private address, NAT type)
    
    @param key : the user's uri (the key for the users' table)"""

    l = (key,)
    if key in self.peersTable:
      for i in self.peersTable[key]:
        l = l + (i,)
      return l
    return ()

reactor.listenUDP(6060, SNConnectionBroker())
reactor.run()
