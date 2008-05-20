#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#
# Authors : Roberto Majadas <roberto.majadas@openshine.com>
#           Oier Blasco <oierblasco@gmail.com>
#           Alvaro Peña <alvaro.pena@openshine.com>
#
# Copyright (c) 2003-2008, Telefonica Móviles España S.A.U.
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2.1 of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place - Suite 330,
# Boston, MA 02111-1307, USA.
#
from MobileDevice import MobileDevice
import os

class MobileDeviceSerial(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = []

        self.device_port = None
        
        MobileDevice.__init__(self, mcontroller, dev_props)

    def is_device_supported(self):
        
        if self.dev_props.has_key("info.category") :
            if self.dev_props["info.category"] == "serial" :
                if self.dev_props.has_key("serial.device") :
                    dp = self.dev_props["serial.device"]
                    if os.path.basename(dp).startswith("ttyS") :
                        self.device_port = self.dev_props["serial.device"]
                        return True
                    else:
                        return False
        return False

        
    def init_device(self):
        if self.device_port != None:
            self.set_property("data-device", self.dev_props["serial.device"] )
            self.pretty_name = "Serial Port (%s or %s for Win users)" % (os.path.basename( self.dev_props["serial.device"]),
                                                                         "COM%i" % (int( self.dev_props["serial.device"][-1])+1))
            self.set_property("devices-autoconf", True)
            MobileDevice.init_device(self)
            return True
        else:
            return False
        
