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

class Nat:
  def __init__(self, type, delta=None, publicAddress=None, privateAddress=None):
    self.type = NatTypeDec[type]
    self.delta = delta
    self.publicAddress = publicAddress
    self.privateAddress = privateAddress
    

class NatManager:
  """
  It's a NAT mirror. It has all the information about a NAT (if there is one).
  It discovers the NAT information (type and mapping)
  :version: 0.2
  :author: Luca Gaballo
  """
  log = logging.getLogger("ntcp")
  
  def __init__(self):
    # The nat configuration
    self.discover = 0
    self.type = None
    self.delta = None
    # TODO: delete publicIP, publicPort, privateIP, privatePort
    self.publicIP = None
    self.publicPort = None
    self.publicAddr = (self.publicIP, self.publicPort)
    self.privateIp = None
    self.privatePort = None
    self.privateAddr = (self.privateIp, self.privatePort)

    self.localNat = Nat('NONE')
    self.remoteNat = None

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
      self.setNatConf(natConfig)
      self.printNatConf()
      d.callback(None)
              
    def fail(failure):
      print "STUNT failed:", failure.getErrorMessage()
      
    # Start to discover the public network address and NAT configuration
    self.reactor.callInThread(stunt.NatDiscovery, self.reactor, succeed)
    return d
    
  def publicAddrDiscovery(self, localPort=0):
    """
    Discover the mapping for the tuple (int IP, int port, ext IP, ext port)
    
    @param int localPort : The connection local port (default any)
    @return tuple publicAddress : The previewed mapped address on the NAT
    """
    d = defer.Deferred()
    d2 = defer.Deferred()

    print 'initial port:', localPort
    if localPort == 0:
      localPort = random.randrange(49152, 65535)
      
    print 'selected port:', localPort

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
    self.discover = 1
    self.type = natConfig.type 
    self.delta = natConfig.delta
    self.publicIp = natConfig.publicIp
    self.privateIp = natConfig.privateIp
    self.publicAddr = (natConfig.publicIp, 0)
    self.privateAddr = (natConfig.privateIp, 0)
    
    self.localNat = Nat(NatTypeCod[self.type], self.delta, self.publicAddr, self.privateAddr)

    # Upload the NAT configuration link in puncher
    self._puncher.setNatObj(self)

  def setRemoteNatConf(self, type, delta, publicAddress, privateAddress):
    """
    Sets the remote NAT's configuration

    @return void :
    """
    self.remoteNat = Nat(type, delta, publicAddress, privateAddress)
    
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
