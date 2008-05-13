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

class MobileDeviceUSB(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = []
        self.device_port = None
        
        MobileDevice.__init__(self, mcontroller, dev_props)

    def is_device_supported(self):
        
        if self.dev_props.has_key("info.bus") :
            if self.dev_props["info.bus"] == "usb_device" :
                acm_ok = False
                serial_ok = False
        
                devices = self.hal_manager.GetAllDevices()
                for device in devices :
                    device_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", device)
                    try:
                        props = device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
                    except:
                        return False
                    if props.has_key("info.parent") and props["info.parent"] == self.dev_props["info.udi"]:
                        if props.has_key("info.linux.driver") :
                            if props["info.linux.driver"] == "cdc_acm" :
                                acm_ok = True

                            # Sometimes hal create a child under this hal-node with the serial device
                            # It's necesary search in the posibles childs, looking for serial device
                            for dev in devices :
                                dev_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", dev)
                                p = dev_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
                                if p.has_key("info.parent") and p["info.parent"] == props["info.udi"]:
                                    if p.has_key("info.category") :
                                        if p["info.category"] == "serial":
                                            serial_ok = True
                                            self.device_port = p["serial.device"]
                                    
                        if props.has_key("info.category") :
                            if props["info.category"] == "serial":
                                serial_ok = True
                                self.device_port = props["serial.device"]

                if acm_ok and serial_ok :
                    return True
                else:
                    return False
            else:
                return False
        else:
            return False
        
    def init_device(self):
        if self.device_port != None:
            self.set_property("data-device", self.device_port)
            self.set_property("devices-autoconf", True)
            MobileDevice.init_device(self)
            return True
        else:
            return False
        
