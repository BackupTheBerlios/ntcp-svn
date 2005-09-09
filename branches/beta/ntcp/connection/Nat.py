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

    

