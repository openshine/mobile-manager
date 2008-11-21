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
from MobileStatus import *
from MobileCapabilities import *
import os
import re

class MobileDeviceUSB(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY, SMS_CAPABILITY, ADDRESSBOOK_CAPABILITY, NO_OPTIONS_MENU]
        self.device_port = None
        
        MobileDevice.__init__(self, mcontroller, dev_props)

    def is_device_supported(self):
        
        if self.dev_props.has_key("info.subsystem") :
            if self.dev_props["info.subsystem"] == "usb_device" :
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
            self.set_property("conf-device", self.device_port)
            self.set_property("devices-autoconf", True)
            self.set_property("device-icon", "stock_cell-phone")
            MobileDevice.init_device(self)
            return True
        else:
            return False
    
    def is_on(self):
        if self.card_is_on == None:
            self.card_is_on = True

        return self.card_is_on

    def turn_on(self):
        self.card_is_on = True
        return True

    def turn_off(self):
        self.card_is_on = False
        return False

    def get_attach_state(self):
        res = self.send_at_command('AT+CREG?', accept_null_response=False)
        self.dbg_msg ("GET ATTACH STATE : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CREG:.*,(?P<state>\d+)")
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

    
    def sms_poll(self):
        if self.sim_id == None :
            sim_id = self.get_sim_id()
            if sim_id != None:
                self.sim_id = sim_id
        return

    def verify_concat_sms_spool(self):
        pass
    
    def get_mode_domain(self):
        mode = None
        domain = None

        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("GET MODE DOMAIN (USB) ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+COPS:\ +(?P<data>.+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    list = matched_res.group("data").split(',')
                    if len(list) == 4 :
                        if list[3] == "2" :
                            mode = CARD_TECH_SELECTION_UMTS
                        else:
                            mode = CARD_TECH_SELECTION_GPRS
                    else:
                        self.dbg_msg ("GET MODE DOMAIN (USB) (AT+COPS not return TECH)) : %s" % res)
                        mode = CARD_TECH_SELECTION_AUTO
            return mode, CARD_DOMAIN_ANY
        except:
            self.dbg_msg ("GET MODE DOMAIN (except) : %s" % res)
            return CARD_TECH_SELECTION_AUTO, CARD_DOMAIN_ANY

    def set_mode_domain(self):
        return True
    
    
