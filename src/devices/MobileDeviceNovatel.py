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
from MobileStatus import *

class MobileDeviceNovatel(MobileDevice):
    def __init__(self, mcontroller, dev_props):
        self.capabilities = [AT_COMM_CAPABILITY, X_ZONE_CAPABILITY]
        
        #Device list with tuplas representating the device (product_id, vendor_id)
        self.device_list = [(0x4400,0x1410)]
        
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
        print ports
        
        if len(ports) >= 3 :
            self.set_property("data-device", "/dev/%s" % ports[0])
            self.set_property("conf-device", "/dev/%s" % ports[1])
            self.set_property("device-icon", "network-wireless")
            self.pretty_name = "Novatel"
            self.set_property("devices-autoconf", True)
            if not self.exists_conf :
                self.set_property("priority", "50")
            MobileDevice.init_device(self)
            return True
        else:
            return False

    def actions_on_open_port(self):
        io = MobileDeviceIO(self.get_property("data-device"))
        io.open()
        
        io.write("AT$NWDMAT=1\r")
        self.dbg_msg ("Send to DATA PORT : AT$NWDMAT=1")
        attempts = 5
        res = io.readline()
        while attempts != 0 :
            self.dbg_msg ("Recv to DATA PORT: %s" % res)
            
            if res == "OK" :
                break
            elif res == None :
                attempts = attempts - 1

            res = io.readline()

        if res != "OK" :
            self.dbg_msg ("ACTIONS ON OPEN PORT END FAILED--------")
            io.close()
            return False

        io.close()
        
        ret = MobileDevice.actions_on_open_port(self)
        
        if ret == False :
            return False
        
        self.serial.write("AT\r")
        self.dbg_msg ("Send : AT")
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

        self.dbg_msg ("ACTIONS ON OPEN PORT END --------")
        return True

    def get_card_status(self):
        pin_status = self.pin_status()
        if pin_status == None:
            return CARD_STATUS_ERROR

        if pin_status == PIN_STATUS_NO_SIM :
            return CARD_STATUS_NO_SIM

        if pin_status == PIN_STATUS_SIM_FAILURE :
            return CARD_STATUS_NO_SIM

        if pin_status == PIN_STATUS_WAITING_PIN :	
            return CARD_STATUS_PIN_REQUIRED

        if pin_status == PIN_STATUS_WAITING_PUK:
            return CARD_STATUS_PUK_REQUIRED

        return MobileDevice.get_card_status(self)


    def get_net_info(self):
        tech_in_use, card_mode, card_domain, carrier, carrier_mode = MobileDevice.get_net_info(self)
        if tech_in_use == CARD_TECH_UMTS :
            res = self.send_at_command("AT$CNTI=0",  accept_null_response=False)
            self.dbg_msg ("AT$CNTI=0 (HSPA stuff) : %s" % res)
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

        res = self.send_at_command('AT$NWRAT?',  accept_null_response=False)
        self.dbg_msg ("GET DOMAIN ($NWRAT?) : %s" % res)

        if res[2] == 'OK':
            pattern = re.compile("\$NWRAT:\ +(?P<mode>\d+),+(?P<domain>\d+)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                if matched_res.group("domain") == "0" :
                    domain = CARD_DOMAIN_CS
                elif matched_res.group("domain") == "1" :
                    domain = CARD_DOMAIN_PS
                elif matched_res.group("domain") == "2" :
                    domain = CARD_DOMAIN_CS_PS
                else:
                    domain = CARD_DOMAIN_ANY

                if matched_res.group("mode") == "0" :
                    mode = CARD_TECH_SELECTION_AUTO
                elif matched_res.group("mode") == "2" :
                    mode = CARD_TECH_SELECTION_UMTS
                elif matched_res.group("mode") == "1" :
                    mode = CARD_TECH_SELECTION_GPRS
        
        if domain != None and mode != None :
            return mode, domain
        else:
            self.dbg_msg ("GET MODE DOMAIN FAILED")
            return None, None

    def set_mode_domain(self, mode, domain):
        rmode = None
        rdomain = None
        
        if mode == CARD_TECH_SELECTION_GPRS :
            rmode = "1"
        elif mode == CARD_TECH_SELECTION_UMTS :
            rmode = "2"
        elif mode == CARD_TECH_SELECTION_GRPS_PREFERED :
            rmode = "1"
        elif mode == CARD_TECH_SELECTION_UMTS_PREFERED :
            rmode = "2"
        elif mode == CARD_TECH_SELECTION_AUTO :
            rmode = "0"
        else:
            rmode = "0"

        if domain == CARD_DOMAIN_CS:
            rdomain = "0"
        elif domain == CARD_DOMAIN_PS:
            rdomain = "1"
        elif domain == CARD_DOMAIN_CS_PS :
            rdomain = "2"
        elif domain == CARD_DOMAIN_ANY:
            rdomain = "2"
        else:
            rdomain = "2"

        res = self.send_at_command("AT$NWRAT=%s,%s" % (rmode, rdomain))
        self.dbg_msg ("SET DOMAIN : %s" % res)
        
    def get_carrier_list_from_raw(self, raw):
        print "__get_carrier_list_from_raw in"
        try:
            print "-----> raw : %s" % raw
            
            if raw[2] == 'OK':
                carrier_list = "" 
                pattern = re.compile("\+COPS:\ +(?P<list>.*)")
                for line in raw[1] :
                    matched_res = pattern.match(line)
                    if matched_res != None :
                        if carrier_list == "" :
                            carrier_list = matched_res.group("list")
                        else:
                            carrier_list = carrier_list + "," + matched_res.group("list")
                        
                exec ('dict = {"carrier_list" : [%s] , "supported_modes" : %s, "supported_formats" : %s}'
                      % (carrier_list, "(0,1,2,3,4)", "(0,1,2)"))
                print "__get_carrier_list_from_raw out"
                
                return dict
            else:
                return None
            
        except:
            return None
            
