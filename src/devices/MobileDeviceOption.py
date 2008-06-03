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

from MobileDevice import MobileDevice, MobileDeviceIO, AT_COMM_CAPABILITY, X_ZONE_CAPABILITY
from MobileStatus import CARD_TECH_SELECTION_GPRS, CARD_TECH_SELECTION_UMTS
from MobileStatus import CARD_TECH_SELECTION_GRPS_PREFERED, CARD_TECH_SELECTION_UMTS_PREFERED
from MobileStatus import CARD_TECH_SELECTION_AUTO

class MobileDeviceOption(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0x6000,0xaf0), (0x6100, 0xaf0), (0x6300, 0xaf0)]
        
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
            
            if props.has_key("info.parent") and props["info.parent"] == self.dev_props["info.udi"]:
                if props.has_key("usb.linux.sysfs_path") :
                    files = os.listdir(props["usb.linux.sysfs_path"])
                    for f in files:
                        if f.startswith("ttyUSB"):
                            ports.append(f)
        ports.sort()
        print ports
        
        if len(ports) >= 3 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[2])
            self.set_property("device-icon", "network-wireless")
            self.pretty_name = "Option"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def is_device_supported(self):
        if self.dev_props.has_key("info.bus"):
            if self.dev_props["info.bus"] ==  "usb_device":
                if self.dev_props.has_key("usb_device.product_id") and self.dev_props.has_key("usb_device.product_id"):
                    dev = (self.dev_props["usb_device.product_id"],
                           self.dev_props["usb_device.vendor_id"])
                    if dev in self.device_list :
                        return True

        return False
                
    def get_mode_domain(self):
        card_mode = None
        card_domain = None

        res = self.send_at_command("AT_OPSYS?")
        if res[2] == 'OK' :
            pattern = re.compile("\+OPSYS:\ +(?P<mode>.*),(?P<domain>.*)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                card_mode = int(matched_res.group("mode"))
                card_domain = int(matched_res.group("domain"))
                
        return card_mode, card_domain

    def set_mode_domain(self, mode, domain):
        res = self.send_at_command("AT_OPSYS=%s,%s" % (mode,domain))
        if res[2] == 'OK' :
            self.dbg_msg ("SET MODE DOMAIN : %s" % res)
            return True
        else:
            self.dbg_msg ("SET MODE DOMAIN (CRASH) : %s" % res)
            return False
    
    
    def get_carrier(self):
        res = self.send_at_command("AT+COPS=3,2")
        self.dbg_msg ("CHANGE TO NUMERIC FORMAT : %s" % res)
        
        carrier = MobileDevice.get_carrier(self)
        
        res = self.send_at_command("AT+COPS=3,0")
        self.dbg_msg ("CHANGE TO STRING FORMAT : %s" % res)

        if carrier == "21407" :
            return "movistar"
        else:
            return carrier

    def get_net_info(self):
        tech_in_use = None
        card_mode = None
        card_domain = None
        carrier = None
        carrier_mode = None

        res = self.send_at_command("AT+COPS=3,2")
        self.dbg_msg ("CHANGE TO NUMERIC FORMAT : %s" % res)
        
        res = self.send_at_command("AT+COPS?", accept_null_response=False)
        
        self.dbg_msg ("GET TECH MODE DOMAIN : %s" % res)
        if res[2] == 'OK' :
            tech_in_use = int(res[1][0][-1])
            
            pattern = re.compile('\+COPS:\ +(?P<carrier_selection_mode>\d*),(?P<carrier_format>\d*),"(?P<carrier>.*)"')
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                carrier = matched_res.group("carrier")
                if carrier == "21407" :
                    carrier = "movistar"
                
                carrier_mode = int(matched_res.group("carrier_selection_mode"))

        res = self.send_at_command("AT+COPS=3,0")
        self.dbg_msg ("CHANGE TO STRING FORMAT : %s" % res)

        card_mode, card_domain = self.get_mode_domain()

        

        return tech_in_use, card_mode, card_domain, carrier, carrier_mode
