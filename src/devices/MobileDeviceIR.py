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

class MobileDeviceIR(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = []
        
        MobileDevice.__init__(self, mcontroller, dev_props)

    def is_device_supported(self):
        
        if self.dev_props.has_key("info.capabilities") :
            if self.dev_props["info.capabilities"][0] == "bluetooth_hci" :
                return True
            else:
                return False
        else:
            return False
        

        
