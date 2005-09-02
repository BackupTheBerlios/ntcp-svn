import logging, random, time

import twisted.internet.defer as defer
from twisted.internet import threads
import twisted.python.failure as failure

from ntcp.connection.Nat import NatManager
from ntcp.punch.Puncher import Puncher

class NtcpFactory:
    def __init__(self, d):
        self.defer = d
    def stopListening(self):
        pass

class NatConnectivity(NatManager, object):

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
        self.udpListener = udpListener # A listener for UDP communication
        self._puncher = Puncher(self.reactor, self, self.udpListener) # the puncher to establish the connection

    def datagramReceived(self, message, fromAddr):
        """A link to the internal datagramReceived function"""
        self._puncher.datagramReceived(message, fromAddr)
    
    def holePunching(self, uri):
        """
        """
        self._puncher.sndLookupRequest(remoteUri=uri)

    def setServerFactory(self, factory):
        """Sets a factory for TCP connection
        @param factory - a twisted.internet.protocol.*Factory instance 
        """
        self._puncher.setServerFactory(factory)
        self._puncher.s_factory = factory
        
    def getFactory(self):
        """Gets the TCP factory
        @return: factory - a twisted.internet.protocol.ServerFactory instance
        """
        return self._puncher.getFactory()

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
 
    def listenTCP(self, port=0, factory=None, backlog=5, interface='',  myUri=None):
        """Make a registration to CB and listen for incoming connection request
        
        @param port: a port number on which to listen, default to 0 (any) (only default implemented)
        @param factory: a twisted.internet.protocol.ServerFactory instance 
        @param backlog: size of the listen queue (not implemented)
        @param interface: the hostname to bind to, defaults to '' (all) (not implemented)
        @param myUri: the user's URI for registration to Connection Broker
        return: void
        """
        d = defer.Deferred()
        # self._puncher = Puncher(self.reactor, self, self.udpListener)
    
        if factory != None:
            # Sets the factory for TCP connection
            self.setServerFactory(factory)

        d = self._puncher.sndRegistrationRequest(myUri)
        return NtcpFactory(d)
    
    def connectTCP(self, \
                   host=None, \
                   port=None, \
                   remoteUri=None, \
                   factory=None, \
                   timeout=30, \
                   bindAddress=None, \
                   myUri=None):
        """
        Force a connection with another user through NATs
        helped by the ConnectionBroker.
        It needs at least one between (host, port) and 'remoteUri'
        
        @param host: a host name, default None
        @param port: a port number, the UDP remote port (it's mandatory if host is present)
        @param remoteUri : The remote endpoint's uri, default None
        @param factory: a twisted.internet.protocol.ClientFactory instance 
        @param timeout: number of seconds to wait before assuming the connection has failed.  (not implemented)
        @param bindAddress: a (host, port) tuple of local address to bind to, or None.
        @param myUri : The uri for future incoming connection request
        
        @return :  An object implementing IConnector.
        This connector will call various callbacks on the factory
        when a connection is made,failed, or lost
        - see ClientFactory docs for details.
        """
        d = defer.Deferred()
        d_conn = defer.Deferred()
        
        if host == None:
            remoteAddress = None
        else:
            remoteAddress = (host, port)
            
        localPort = 0 # any
        if bindAddress != None:
            localPort = bindAddress[1]
            
        if self._puncher == None:
            self._puncher = Puncher(self.reactor, self)

        if self._puncher.getClientFactory() == None and factory == None:
            # Error
            d.errback(failure.DefaultException('You have to specify a factory'))
        elif factory != None:
            self._puncher.setClientFactory(factory)
            self._puncher.c_factory = factory

        def fail(failure):
            """ Error in NAT Traversal TCP """
            print 'ERROR in NAT Traversal (registration):', failure#.getErrorMessage()

        def connection_succeed(result):
            print 'connection succeed:', result
            d_conn.callback(result)

        def connection_fail(failure):
            print 'connection fail', failure
            d = defer.Deferred()
            d.errback(failure)

        def discovery_fail(failure):
            d = defer.Deferred()
            d.errback(failure)

        def discovery_succeed(publicAddress):
            self.publicAddr = publicAddress
            print 'Address discovered:', publicAddress
            if self.publicAddr != None:
                d = defer.Deferred()
                d = self._puncher.sndConnectionRequest(remoteUri, remoteAddress)
                d.addCallback(connection_succeed)
                d.addErrback(connection_fail)
            else:
                self.d.errback('The NAT doesn\'t allow inbound TCP connection')

        def registrationSucceed(result):
            print 'Registration to the SN Connection Broker has be done'
            
            # Discovery external address
            d = self.publicAddrDiscovery(localPort)
            d.addCallback(discovery_succeed)
            d.addErrback(discovery_fail)
            
        # Registration to Connection Broker for incoming connection
        if myUri != None and not self._puncher.registered:
            print 'register...'
            d = self._puncher.sndRegistrationRequest(myUri)
            d.addCallback(registrationSucceed)
            d.addErrback(fail)
        else:
            d = self.publicAddrDiscovery(localPort)
            d.addCallback(discovery_succeed)
            d.addErrback(discovery_fail)
            
        return d_conn

    def getP2PConfiguration(self, \
                            host=None, \
                            port=None, \
                            remoteUri=None):
        """
        Gets the local and remote NAT type.
        It requires at least one between parameters (host, port) and remoteUri

        @param host: a host name, default None
        @param port: a port number, the UDP remote port (it's mandatory if host is present)
        @param remoteUri : The remote endpoint's uri, default None
        @return: defer the callback result is (local NAT type, remote NAT type)
        """
        
        d = defer.Deferred()
        if host == None:
            remoteAddress = None
        else:
            remoteAddress = (host, port)

        def fail(failure):
            """ Error in NTCP"""
            print 'ERROR in NTCP (get configuration):', failure.getErrorMessage()
            return None
        
        def discoveryConfigurationSucceed(remote):
            # Returns the result
            if remote == 'Unknown':
                d.callback((self.type, None))
            else:
                d.callback((self.type, self.remoteNat.type))

        def discoverySucceed(result):
            # Asks for remote NAT configuration
            d = defer.Deferred()
            d = self._puncher.sndConfigurationRequest(\
                remoteUri, remoteAddress)
            d.addCallback(discoveryConfigurationSucceed)
            d.addErrback(fail)
            
        
        if self.discover == 0:
            # Discover local NAT configuration
            d = defer.Deferred()
            d = self.natDiscovery()
            d.addCallback(discoverySucceed)
            d.addErrback(fail)
        else:
            discoverySucceed(None)

        return d

    def getlocalNatConf(self):
        return self.localNat
