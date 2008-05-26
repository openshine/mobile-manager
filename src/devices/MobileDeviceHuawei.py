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

from MobileDevice import MobileDevice, AT_COMM_CAPABILITY, X_ZONE_CAPABILITY
from MobileStatus import CARD_TECH_SELECTION_GPRS, CARD_TECH_SELECTION_UMTS
from MobileStatus import CARD_TECH_SELECTION_GRPS_PREFERED, CARD_TECH_SELECTION_UMTS_PREFERED
from MobileStatus import CARD_TECH_SELECTION_AUTO , CARD_DOMAIN_CS, CARD_DOMAIN_PS, CARD_DOMAIN_CS_PS
from MobileStatus import CARD_DOMAIN_ANY, CARD_TECH_UMTS, CARD_TECH_HSPA

class MobileDeviceHuawei(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0x1004,0x12d1), (0x1003,0x12d1), (0x1406,0x12d1)]
        
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
                        if f.startswith("ttyUSB") :
                            ports.append(f)
        ports.sort()
        print ports

        dev = (self.dev_props["usb_device.product_id"],
               self.dev_props["usb_device.vendor_id"])

        if dev == (0x1004,0x12d1) and len(ports) == 4 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[2])
            self.pretty_name = "Huawei"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        elif dev == (0x1003,0x12d1) and len(ports) >= 2 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[1])
            self.pretty_name = "Huawei"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        elif dev == (0x1406,0x12d1) and len(ports) >= 2 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[1])
            self.pretty_name = "Huawei"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def open_device(self):
        MobileDevice.open_device(self)
        
        res = self.send_at_command("AT^PORTSEL=1",  attempt=2)
        if res[2] != "OK" :
            print "error opening huawei device"

        res = self.send_at_command("AT+COPS=3,0",  attempt=2)
        if res[2] != "OK" :
            print "error opening huawei device"

    def is_device_supported(self):
        if self.dev_props.has_key("info.bus"):
            if self.dev_props["info.bus"] ==  "usb_device":
                if self.dev_props.has_key("usb_device.product_id") and self.dev_props.has_key("usb_device.product_id"):
                    dev = (self.dev_props["usb_device.product_id"],
                           self.dev_props["usb_device.vendor_id"])
                    if dev in self.device_list :
                        return True

        return False

    def get_net_info(self):
        tech_in_use, card_mode, card_domain, carrier, carrier_mode = MobileDevice.get_net_info(self)
        if tech_in_use == CARD_TECH_UMTS :
            res = self.send_at_command("AT^SYSINFO",  accept_null_response=False)
            self.dbg_msg ("SYSCFG (HSPA stuff) : %s" % res)
            if res[2] == 'OK' :
                tech = int(res[1][0][-1])
                if tech >= 5 :
                    tech_in_use = CARD_TECH_HSPA
            
        return tech_in_use, card_mode, card_domain, carrier, carrier_mode

    def get_mode_domain(self):
        mode = None
        domain = None
        acqorder = None

        res = self.send_at_command("AT^SYSCFG?",  accept_null_response=False)
        self.dbg_msg ("GET MODE DOMAIN : %s" % res)

        if res[2] == 'OK' :
            pattern = re.compile("\^SYSCFG:(?P<mode>.*),(?P<acqorder>.*),.*,.*,(?P<domain>.*)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                mode = int(matched_res.group("mode"))
                domain = int(matched_res.group("domain"))
                acqorder = int(matched_res.group("acqorder"))

                if mode == 13 and acqorder == 0:
                    real_mode = CARD_TECH_SELECTION_GPRS
                elif mode == 14 and acqorder == 0 :
                    real_mode = CARD_TECH_SELECTION_UMTS
                elif mode == 2 and acqorder == 1 :
                    real_mode = CARD_TECH_SELECTION_GRPS_PREFERED
                elif mode == 2 and acqorder == 2 :
                    real_mode = CARD_TECH_SELECTION_UMTS_PREFERED
                elif mode == 2 and acqorder == 0 :
                    real_mode = CARD_TECH_SELECTION_AUTO
                else:
                    real_mode = None

                if domain == 0:
                    real_domain = CARD_DOMAIN_CS
                elif domain == 1:
                    real_domain = CARD_DOMAIN_PS
                elif domain == 2:
                    real_domain = CARD_DOMAIN_CS_PS
                elif domain == 3:
                    real_domain = CARD_DOMAIN_ANY
                else:
                    real_domain = None
            else:
                return None, None
        else:
            return None, None
                
        return real_mode, real_domain

    def set_mode_domain(self, mode, domain):
        if domain == CARD_DOMAIN_CS:
            real_domain = 0
        elif domain == CARD_DOMAIN_PS:
            real_domain = 1
        elif domain == CARD_DOMAIN_CS_PS :
            real_domain = 2
        elif domain == CARD_DOMAIN_ANY:
            real_domain = 3
        else:
            real_domain = 2
        
        if mode == CARD_TECH_SELECTION_GPRS :
            res = self.send_at_command("AT^SYSCFG=13,0,3FFFFFFF,1,%s" % real_domain)
        elif mode == CARD_TECH_SELECTION_UMTS :
            res = self.send_at_command("AT^SYSCFG=14,0,3FFFFFFF,1,%s" % real_domain)
        elif mode == CARD_TECH_SELECTION_GRPS_PREFERED :
            res = self.send_at_command("AT^SYSCFG=2,1,3FFFFFFF,1,%s" % real_domain)
        elif mode == CARD_TECH_SELECTION_UMTS_PREFERED :
            res = self.send_at_command("AT^SYSCFG=2,2,3FFFFFFF,1,%s" % real_domain)
        elif mode == CARD_TECH_SELECTION_AUTO :
            res = self.send_at_command("AT^SYSCFG=2,0,3FFFFFFF,1,%s" % real_domain)
        else:
            self.dbg_msg ("SET MODE DOMAIN : CRASH")
            return False
        
        if res[2] == 'OK' :
            self.dbg_msg ("SET MODE DOMAIN : %s" % res)
            return True
        else:
            self.dbg_msg ("SET MODE DOMAIN (CRASH) : %s" % res)
            return False
        

    def turn_off(self):
        self.actions_on_reopen_port()
        return MobileDevice.turn_off(self)

    def turn_on(self):
        ret = MobileDevice.turn_on(self)
        
        self.actions_on_reopen_port()
        
        return ret
        
    def actions_on_reopen_port(self):
        
        res = self.send_at_command("AT^PORTSEL=1", attempt=2)
        self.dbg_msg ("PORTSEL : %s" % res)
        if res[2] != "OK" :
            print "error opening huawei device"

        res = self.send_at_command("AT+COPS=3,0", attempt=2)
        self.dbg_msg ("ATCOPS : %s" % res)
        if res[2] != "OK" :
            print "error opening huawei device"

    def get_ussd_cmd_handler(self, fd, at_command, condition, func):
        ret = MobileDevice.get_ussd_cmd_handler(self, fd, at_command, condition, func)
        self.send_at_command("AT^PORTSEL=1")
        return ret
        
    def get_ussd_cmd(self, ussd_cmd, func):
        print "get_USSD_cmd (HUAWEI)"
        self.send_at_command("AT^PORTSEL=0")
        MobileDevice.get_ussd_cmd(self, ussd_cmd, func)
