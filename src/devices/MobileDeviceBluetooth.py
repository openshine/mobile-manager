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

class MobileDeviceBluetooth(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = []
        
        MobileDevice.__init__(self, mcontroller, dev_props)
        
    def is_device_supported(self):
        
        if self.dev_props.has_key("info.capabilities") :
            if self.dev_props["info.capabilities"][0] == "bluetooth_hci" :
                devices = self.mcontroller.get_available_devices()
                for dev in devices:
                    data_dev = dev.get_property("data-device")
                    if "rfcomm" in data_dev :
                        hci = data_dev.replace("/dev/rfcomm","hci")
                        if hci in  self.dev_props["linux.sysfs_path"] :
                            print "Bluetooth device already present in mcontroller"
                            return False
                return True
            else:
                return False
        else:
            return False

    def init_device(self):
        print 0
        port = "/dev/rfcomm%s" % os.path.basename(self.dev_props["linux.sysfs_path"]).strip("hci")
        
        parent_dev_dbus_obj =  self.dbus.get_object("org.freedesktop.Hal", self.dev_props["info.parent"])
        try:
            parent_props = parent_dev_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
        except:
            print "init error in Bluetooth device"
            self.set_property("data-device", port)
            self.set_property("devices-autoconf", True)
            MobileDevice.init_device(self)
            return True

        if parent_props.has_key("info.subsystem") :
            if parent_props["info.subsystem"] == "usb_device" :
                if parent_props.has_key("info.product") :
                    self.pretty_name = parent_props["info.product"]
                    if self.pretty_name == "Bluetooth Host Controller Interface":
                        self.pretty_name = "Bluetooth"
                    
        
        self.set_property("data-device", port)
        self.set_property("devices-autoconf", True)
        self.set_property("device-icon", "stock_bluetooth")

        MobileDevice.init_device(self)
        
        return True
        

        
