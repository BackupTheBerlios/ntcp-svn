# <copyright>
# Solipsis, a peer-to-peer serverless virtual world.
# Copyright (C) 2002-2005 France Telecom R&D
# 
# This software is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
# 
# This software is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
# 
# You should have received a copy of the GNU Lesser General Public
# License along with this software; if not, write to the Free Software
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA
# </copyright>

import sys

class ConfigData:
    """
    This class holds all configuration values that are settable from
    the user.
    """
    def __init__(self, filename):
        self.var = {}
        self.readConf(filename)
        
    def readConf(self, filename):
        """
        read the configuration from a configuration file
        """
        
        f=open(filename, 'r')
        
        for line in f.readlines():
            if not (line[0] in ('#', ' ', '\n', '\r\n', '[')):
                self.var[(line.split(':', 1)[0]).strip()] = (line.split(':', 1)[1]).strip()
