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
import os
import re
import gobject

from MobileDevice import MobileDevice, MobileDeviceIO
from MobileStatus import * 
from MobileCapabilities import *

from MobileDeviceOption import MobileDeviceOption

class MobileDeviceNozomi(MobileDeviceOption):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY, SMS_CAPABILITY, ADDRESSBOOK_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0xc, 0x1931)]
        
        MobileDevice.__init__(self, mcontroller, dev_props)


    def init_device(self) :
        ports = []
        devices =  self.hal_manager.GetAllDevices()
        for device in devices :
            device_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", device)
            try:
                props = device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
            except:
                return False
            
            if props.has_key("info.linux.driver") and props["info.linux.driver"] == "nozomi":
                if props.has_key("linux.sysfs_path") :
                    files = os.listdir(props["linux.sysfs_path"] + "/tty")
                    for f in files:
                        if f.startswith("noz"):
                            ports.append(f)
        ports.sort()
        print ports
        
        if len(ports) >= 3 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[2])
            self.set_property("device-icon", "network-wireless")
            self.pretty_name = "Option Nozomi"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def is_device_supported(self):
        if self.dev_props.has_key("info.linux.driver"):
            if self.dev_props["info.linux.driver"] ==  "nozomi":
                if self.dev_props.has_key("pci.product_id") and self.dev_props.has_key("pci.product_id"):
                    dev = (self.dev_props["pci.product_id"],
                           self.dev_props["pci.vendor_id"])
                    if dev in self.device_list :
                        return True

        return False
