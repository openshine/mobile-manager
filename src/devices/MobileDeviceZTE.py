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

from MobileDevice import MobileDevice
from MobileStatus import *
from MobileCapabilities import *
from MobileManager import MobileDeviceIO

class MobileDeviceZTE(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY, SMS_CAPABILITY, ADDRESSBOOK_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0x1,0x19d2), (0x66,0x19d2), (0x124, 0x19d2) ]
        
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

        self.set_property("device-icon", "network-wireless")

        dev = (self.dev_props["usb_device.product_id"],
               self.dev_props["usb_device.vendor_id"])
        
        if len(ports) == 4 :
            if dev == (0x66,0x19d2) or dev == (0x124, 0x19d2):
                self.set_property("data-device", "/dev/%s" % ports[3])
                self.set_property("conf-device", "/dev/%s" % ports[1])
            else:
                self.set_property("data-device", "/dev/%s" % ports[0])
                self.set_property("conf-device", "/dev/%s" % ports[2])
            self.pretty_name = "ZTE"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def is_device_supported(self):
        if self.dev_props.has_key("info.subsystem"):
            if self.dev_props["info.subsystem"] ==  "usb_device":
                if self.dev_props.has_key("usb_device.product_id") and self.dev_props.has_key("usb_device.product_id"):
                    dev = (self.dev_props["usb_device.product_id"],
                           self.dev_props["usb_device.vendor_id"])
                    if dev in self.device_list :
                        return True

        return False

    def get_mode_domain(self):
        mode = None
        domain = None
        acqorder = None

        res = self.send_at_command("AT+ZCSPS?",  accept_null_response=False)
        self.dbg_msg ("GET DOMAIN : %s" % res)

        if res[2] == 'OK' :
            pattern = re.compile("\+ZCSPS:\ +(?P<domain>\d*)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                 domain = int(matched_res.group("domain"))
                 
                 if domain == 0:
                     real_domain = CARD_DOMAIN_CS
                 elif domain == 1:
                     real_domain = CARD_DOMAIN_PS
                 elif domain == 2:
                     real_domain = CARD_DOMAIN_CS_PS
                 else:
                     real_domain = CARD_DOMAIN_ANY
        else:
            return None, None

        res = self.send_at_command("AT+ZSNT?",  accept_null_response=False)
        self.dbg_msg ("GET MODE : %s" % res)

        if res[2] == 'OK' :
            pattern = re.compile("\+ZSNT:\ +(?P<cm_mode>\d*),(?P<net_sel_mode>\d*),(?P<acqorder>\d*)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                cm_mode = int(matched_res.group("cm_mode"))
                net_sel_mode = int(matched_res.group("net_sel_mode"))
                acqorder = int(matched_res.group("acqorder"))

                if cm_mode == 0 and acqorder == 0:
                    real_mode = CARD_TECH_SELECTION_AUTO
                elif cm_mode == 2:
                    real_mode = CARD_TECH_SELECTION_UMTS
                elif cm_mode == 1:
                    real_mode = CARD_TECH_SELECTION_GPRS
                elif cm_mode == 0 and acqorder == 2:
                    real_mode = CARD_TECH_SELECTION_UMTS_PREFERED
                elif cm_mode == 0 and acqorder == 1:
                    real_mode = CARD_TECH_SELECTION_UMTS_PREFERED
                else:
                    real_mode = None
        else:
            return None, None
        
        return  real_mode, real_domain

    def set_mode_domain(self, mode, domain):
        if domain == CARD_DOMAIN_CS:
            real_domain = 0
        elif domain == CARD_DOMAIN_PS:
            real_domain = 1
        elif domain == CARD_DOMAIN_CS_PS :
            real_domain = 2
        else:
            self.dbg_msg ("SET DOMAIN : (CRASH)")
            return False
        
        res =  self.send_at_command("AT+ZCSPS=%s" % real_domain)
        if res[2] == 'OK' :
            self.dbg_msg ("SET DOMAIN : %s" % res)
        else:
            self.dbg_msg ("SET DOMAIN (CRASH) : %s" % res)
            return False
        
        if mode == CARD_TECH_SELECTION_GPRS :
            res = self.send_at_command("AT+ZSNT=1,0,0")
        elif mode == CARD_TECH_SELECTION_UMTS :
            res = self.send_at_command("AT+ZSNT=2,0,0")
        elif mode == CARD_TECH_SELECTION_GRPS_PREFERED :
            res = self.send_at_command("AT+ZSNT=0,0,1")
        elif mode == CARD_TECH_SELECTION_UMTS_PREFERED :
            res = self.send_at_command("AT+ZSNT=0,0,2")
        elif mode == CARD_TECH_SELECTION_AUTO :
            res = self.send_at_command("AT+ZSNT=0,0,0")
        else:
            self.dbg_msg ("SET MODE : CRASH")
            return False
        
        if res[2] == 'OK' :
            self.dbg_msg ("SET MODE : %s" % res)
            MobileDevice.set_mode_domain(self, mode, domain)
            return True
        else:
            self.dbg_msg ("SET MODE (CRASH) : %s" % res)
            return False

    def get_card_info(self):
        self.dbg_msg ("GET CARD INFO (ZTE STYLE)" )
        
        self.serial.write("ATI\r")
        attempts = 5
        
        info = []
        
        res = self.serial.readline()
        while attempts != 0 :
            if res == "OK" :
                break
            elif res == None :
                attempts = attempts - 1
            
            info.append(res)
            res = self.serial.readline()
        
        return info

    def get_net_info(self):
        tech_in_use = None
        card_mode = None
        card_domain = None
        carrier = None
        carrier_mode = None
        
        res = self.send_at_command("AT+COPS?", accept_null_response=False)
        
        self.dbg_msg ("GET TECH MODE DOMAIN : %s" % res)
        try:
            if res[2] == 'OK' :
                try :
                    tech_in_use = int(res[1][0][-1])
                except:
                    tech_in_user = 2

                pattern = re.compile('\+COPS:\ +(?P<carrier_selection_mode>\d*),(?P<carrier_format>\d*),"(?P<carrier>.*)",')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("carrier_format") != "0" :
                        res = self.send_at_command("AT+COPS=3,0")
                        self.dbg_msg ("ATCOPS : %s" % res)
                        if res[2] != "OK" :
                            self.dbg_msg ("error changing to correct format")
                        return self.get_net_info()

                    carrier = matched_res.group("carrier")
                    carrier_mode = int(matched_res.group("carrier_selection_mode"))
                
            card_mode, card_domain = self.get_mode_domain()

            return tech_in_use, card_mode, card_domain, carrier, carrier_mode
        except:
            self.dbg_msg ("GET TECH MODE DOMAIN (except): %s" % res)
            return tech_in_use, card_mode, card_domain, carrier, carrier_mode

    def get_sim_id(self):
        if self.sim_id != None :
            self.dbg_msg ("SIM ID (cached) : %s" % self.sim_id)
            return self.sim_id

        cimi = None
        
        self.serial.write("AT+CIMI\r")
        attempts = 5
        
        res = self.serial.readline()
        while attempts != 0 :
            if res == "OK" :
                break
            elif "CIMI" in res:
                res = self.serial.readline()
                continue
            elif cimi == None and res != None and len(res)>0:
                cimi = res
            elif res == None :
                attempts = attempts - 1
            
            res = self.serial.readline()
        
        if res == 'OK' :
            self.dbg_msg ("GET SIM ID (ZTE STYLE)" )
            self.dbg_msg ("* SIM ID : %s" % cimi)
            return cimi
        else:
            self.dbg_msg ("GET SIM ID (ZTE STYLE)" )
            self.dbg_msg ("* SIM ID (ZTE STYLE) : (error)")
            return None

    def send_at_pdu_command_to_device(self, sms):
        self.serial.flush()
        self.serial.write("AT+CMGS=" + str(sms[0]) + "\r")
        
    def get_unread_smss(self):
        self.dbg_msg("* GET UNREAD SMS INIT (ZTE style) ....")
        ret_value = ["AT+CMGL=0", [], "OK"]
        
        self.serial.write("AT+CMGL=0\r")
        self.dbg_msg ("Send (ZTE style) : AT+CMGL=0")
        
        attempts = 5
        res = self.serial.readline()
        while attempts != 0 :
            self.dbg_msg ("Recv (ZTE style) : %s" % res)
            
            if len(res) > 0 :
                break
            elif res == None :
                attempts = attempts - 1
                
            res = self.serial.readline()
        
        attempts = 5
        res = self.serial.readline()
        while attempts != 0 :
            self.dbg_msg ("Recv (ZTE style) : %s" % res)
            
            if res == "OK" :
                break
            elif "ERROR" in res :
                ret_value[2]="ERROR"
                break
            elif len(res):
                ret_value[1].append(res)
            elif res == None :
                attempts = attempts - 1

            res = self.serial.readline()
        
        self.dbg_msg("* GET UNREAD SMS END (ZTE style) : %s " % ret_value)
        return ret_value


    def actions_on_open_port(self):
        ret = MobileDevice.actions_on_open_port(self)
        if ret == False :
            return False
        
        dev = (self.dev_props["usb_device.product_id"],
               self.dev_props["usb_device.vendor_id"])

        self.serial.write("AT+CPMS?\r")
        self.dbg_msg ("Send : AT+CPMS?")
        attempts = 5
        res = self.serial.readline()
        while attempts != 0 :
            self.dbg_msg ("Recv : %s" % res)
            
            if res == "OK" :
                break
            elif res == None :
                attempts = attempts - 1

            res = self.serial.readline()

        if res != "OK" :
            self.dbg_msg ("ACTIONS ON OPEN PORT END FAILED--------")
            return False
