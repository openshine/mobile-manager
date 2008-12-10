#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#
# Authors : Roberto Majadas <roberto.majadas@openshine.com>
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

from MobileDevice import MobileDevice, AT_COMM_CAPABILITY, X_ZONE_CAPABILITY
from MobileStatus import CARD_TECH_SELECTION_GPRS, CARD_TECH_SELECTION_UMTS
from MobileStatus import CARD_TECH_SELECTION_GRPS_PREFERED, CARD_TECH_SELECTION_UMTS_PREFERED
from MobileStatus import CARD_TECH_SELECTION_AUTO , CARD_DOMAIN_CS, CARD_DOMAIN_PS, CARD_DOMAIN_CS_PS
from MobileStatus import CARD_DOMAIN_ANY, CARD_TECH_UMTS, CARD_TECH_HSPA, CARD_TECH_HSDPA, CARD_TECH_HSUPA
from MobileManager import MobileDeviceIO


class MobileDeviceSierra(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0x6855,0x1199), (0x6890,0x1199)]
        
        MobileDevice.__init__(self, mcontroller, dev_props)

    def is_device_supported(self):
        if self.dev_props.has_key("info.subsystem"):
            if self.dev_props["info.subsystem"] ==  "usb_device":
                if self.dev_props.has_key("usb_device.product_id") and self.dev_props.has_key("usb_device.product_id"):
                    dev = (self.dev_props["usb_device.product_id"],
                           self.dev_props["usb_device.vendor_id"])
                    if dev in self.device_list :
                        return True

        return False

    def init_device(self) :
        ports = []
        devices =  self.hal_manager.GetAllDevices()

        device_udi = self.dev_props["info.udi"]
        
        for device in devices :
            device_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", device)
            try:
                props = device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
            except:
                return False

            device_tmp = props["info.udi"]
            
            if device_tmp.startswith(device_udi):
                if props.has_key("serial.device") :
                    ports.append(os.path.basename(props["serial.device"]))
            
        ports.sort()

        dev = (self.dev_props["usb_device.product_id"],
               self.dev_props["usb_device.vendor_id"])
        
        if len(ports) >= 3 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            if dev == (0x6890,0x1199) :
                self.set_property("conf-device", "/dev/%s" % ports[3])
            else:
                self.set_property("conf-device", "/dev/%s" % ports[2])

            print "data ------------> %s" % self.get_property("data-device")
            print "conf ------------> %s" % self.get_property("conf-device")

            self.set_property("device-icon", "network-wireless")
            self.pretty_name = "Sierra"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def get_attach_state(self):
        res = self.send_at_command('AT+CGREG?', accept_null_response=False)
        self.dbg_msg ("GET ATTACH STATE : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CGREG:\ +\d+,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "1" or  matched_res.group("state") == "5":
                        return int(matched_res.group("state"))
                else:
                    return 0
            else:
                return 0
        except:
            self.dbg_msg ("GET ATTACH STATE (except): %s" % res)
            return 0

    def is_attached(self):
        res = self.send_at_command('AT+CGREG?', accept_null_response=False)
        self.dbg_msg ("IS ATTACHED ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CGREG:\ +\d+,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "1" or  matched_res.group("state") == "5":
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False
        except:
            self.dbg_msg ("IS ATTACHED ? (except): %s" % res)
            return False

    def is_roaming(self):
        res = self.send_at_command('AT+CGREG?',  accept_null_response=False)
        self.dbg_msg ("IS ROAMING ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CGREG:\ +\d+,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "5" :
                        return True
                    else:
                        return False
                else:
                    return False
            else:
                return False
        except:
            self.dbg_msg ("IS ROAMING ? (excepet): %s" % res)
            return False

    def get_net_info(self):
        tech_in_use, card_mode, card_domain, carrier, carrier_mode = MobileDevice.get_net_info(self)
        if tech_in_use == CARD_TECH_UMTS :
            res = self.send_at_command("AT*CNTI=0",  accept_null_response=False)
            self.dbg_msg ("AT*CNTI=0 (HSPA stuff) : %s" % res)
            tech = res[1][0]
            
            if res[2] == 'OK' :
                if "HSDPA" in tech :
                    tech_in_use == CARD_TECH_HSDPA
                elif "HSUPA" in tech :
                    tech_in_use = CARD_TECH_HSUPA
                    
        return tech_in_use, card_mode, card_domain, carrier, carrier_mode

    def get_mode_domain(self):
        mode = None
        domain = None

        res = self.send_at_command('AT!SELMODE?',  accept_null_response=False)
        self.dbg_msg ("GET DOMAIN : %s" % res)
 
        if res[2] == 'OK':
            pattern = re.compile("\!SELMODE:\ +(?P<domain>\d+)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                if matched_res.group("domain") == "00" :
                    domain = CARD_DOMAIN_CS
                elif matched_res.group("domain") == "01" :
                    domain = CARD_DOMAIN_PS
                elif matched_res.group("domain") == "02" :
                    domain = CARD_DOMAIN_CS_PS
                else:
                    domain = CARD_DOMAIN_ANY

        res = self.send_at_command('AT!SELRAT?',  accept_null_response=False)
        self.dbg_msg ("GET MODE : %s" % res)
 
        if res[2] == 'OK':
            pattern = re.compile("\!SELRAT:\ +(?P<mode>\d+)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                if matched_res.group("mode") == "00" :
                    mode = CARD_TECH_SELECTION_AUTO
                elif matched_res.group("mode") == "01" :
                    mode = CARD_TECH_SELECTION_UMTS
                elif matched_res.group("mode") == "02" :
                    mode = CARD_TECH_SELECTION_GPRS
                elif matched_res.group("mode") == "03" :
                    mode = CARD_TECH_SELECTION_UMTS_PREFERED
                elif matched_res.group("mode") == "04" :
                    mode = CARD_TECH_SELECTION_GRPS_PREFERED

        if domain != None and mode != None :
            return mode, domain
        else:
            self.dbg_msg ("GET MODE DOMAIN FAILED")
            return None, None

    def set_mode_domain(self, mode, domain):
        if mode == CARD_TECH_SELECTION_GPRS :
            res = self.send_at_command("AT!SELRAT=02")
        elif mode == CARD_TECH_SELECTION_UMTS :
            res = self.send_at_command("AT!SELRAT=01")
        elif mode == CARD_TECH_SELECTION_GRPS_PREFERED :
            res = self.send_at_command("AT!SELRAT=04")
        elif mode == CARD_TECH_SELECTION_UMTS_PREFERED :
            res = self.send_at_command("AT!SELRAT=03")
        elif mode == CARD_TECH_SELECTION_AUTO :
            res = self.send_at_command("AT!SELRAT=00")
        else:
            self.dbg_msg ("SET MODE DOMAIN : CRASH")
            return False

        self.dbg_msg ("SET MODE : %s" % res)

        if domain == CARD_DOMAIN_CS:
            real_domain = 00
        elif domain == CARD_DOMAIN_PS:
            real_domain = 01
        elif domain == CARD_DOMAIN_CS_PS :
            real_domain = 02
        elif domain == CARD_DOMAIN_ANY:
            real_domain = 02
        else:
            real_domain = 02

        res = self.send_at_command("AT!SELMODE=%s" % real_domain)
        self.dbg_msg ("SET DOMAIN : %s" % res)

    def is_on(self):
        if self.card_is_on != None :
            return self.card_is_on
        
        res = self.send_at_command('AT+CFUN?', accept_null_response=False)
        self.dbg_msg ("IS ON : %s" % res)

        if res[2] == 'OK' :
            pattern = re.compile('\+CFUN:\ +(?P<is_on>\d*)')
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                self.card_is_on =  bool(int(matched_res.group("is_on")))
                return bool(int(matched_res.group("is_on")))
            else:
                return False
        else:
            print "Response Not Mached !"
            print "res -> (%s)" % res
            return False

