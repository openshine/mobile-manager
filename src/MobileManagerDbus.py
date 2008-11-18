#!/usr/bin/env python
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

import gobject
import os
import dbus
import dbus.service
import dbus.mainloop.glib
import time
from MobileCapabilities import *

MOBILE_MANAGER_CONTROLLER_PATH="/es/movistar/MobileManager/Manager"
MOBILE_MANAGER_CONTROLLER_URI="es.movistar.MobileManager"
MOBILE_MANAGER_CONTROLLER_INTERFACE_URI=MOBILE_MANAGER_CONTROLLER_URI+".Controller"
MOBILE_MANAGER_DIALER_INTERFACE_URI=MOBILE_MANAGER_CONTROLLER_URI+".Dialer"

MOBILE_MANAGER_DEVICE_PATH="/es/movistar/MobileManager/devices/"
MOBILE_MANAGER_DEVICE_URI="es.movistar.MobileManager"
MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceInfo"
MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceAuth"
MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceState"
MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceXZone"
MOBILE_MANAGER_DEVICE_DEBUG_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceDebug"
MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceSMS"
MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI=MOBILE_MANAGER_DEVICE_URI+".DeviceAddressBook"
MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU=MOBILE_MANAGER_DEVICE_URI+".NoOptionsMenu"

class MobileManagerDbusController(dbus.service.Object):
    def __init__(self, bus_name, path=MOBILE_MANAGER_CONTROLLER_PATH, mcontroller=None):
        self.mcontroller = mcontroller
        self.mcontroller.connect("active-dev-card-status-changed", self.__active_dev_card_status_changed_cb)
        self.mcontroller.connect("active-dev-tech-status-changed", self.__active_dev_tech_status_changed_cb)
        self.mcontroller.connect("active-dev-mode-status-changed", self.__active_dev_mode_status_changed_cb)
        self.mcontroller.connect("active-dev-domain-status-changed", self.__active_dev_domain_status_changed_cb)
        self.mcontroller.connect("active-dev-signal-status-changed", self.__active_dev_signal_status_changed_cb)
        self.mcontroller.connect("active-dev-pin-act-status-changed", self.__active_dev_pin_act_status_changed_cb)
        self.mcontroller.connect("active-dev-roaming-status-changed", self.__active_dev_roaming_status_changed_cb)
        self.mcontroller.connect("active-dev-carrier-changed", self.__active_dev_carrier_changed_cb)
        self.mcontroller.connect("active-dev-sms-received", self.__active_dev_sms_received_cb)
        self.mcontroller.connect("active-dev-sms-spool-changed", self.__active_dev_sms_spool_changed_cb)
        self.mcontroller.connect("active-dev-carrier-sm-status-changed", self.__active_dev_carrier_sm_status_changed_cb)
        self.mcontroller.connect("active-dev-x-zone-changed", self.__active_dev_x_zone_changed_cb)
        self.mcontroller.connect("dev-card-status-changed", self.__dev_card_status_changed_cb)
        self.mcontroller.connect("dev-tech-status-changed", self.__dev_tech_status_changed_cb)
        self.mcontroller.connect("dev-mode-status-changed", self.__dev_mode_status_changed_cb)
        self.mcontroller.connect("dev-domain-status-changed", self.__dev_domain_status_changed_cb)
        self.mcontroller.connect("dev-signal-status-changed", self.__dev_signal_status_changed_cb)
        self.mcontroller.connect("dev-pin-act-status-changed", self.__dev_pin_act_status_changed_cb)
        self.mcontroller.connect("dev-roaming-status-changed", self.__dev_roaming_status_changed_cb)
        self.mcontroller.connect("dev-carrier-changed", self.__dev_carrier_changed_cb)
        self.mcontroller.connect("dev-sms-received", self.__dev_sms_received_cb)
        self.mcontroller.connect("dev-sms-spool-changed", self.__dev_sms_spool_changed_cb)
        self.mcontroller.connect("dev-carrier-sm-status-changed", self.__dev_carrier_sm_status_changed_cb)
        self.mcontroller.connect("added-device", self.__added_device_cb)
        self.mcontroller.connect("removed-device", self.__removed_device_cb)
        self.mcontroller.connect("supported-device-detected", self.__supported_device_detected_cb)
        self.mcontroller.connect("active-device-changed", self.__active_device_changed_cb)

        self.mcontroller.dialer.connect("connected", self.__dialer_connected_cb)
        self.mcontroller.dialer.connect("disconnected", self.__dialer_disconnected_cb)
        self.mcontroller.dialer.connect("connecting", self.__dialer_connecting_cb)
        self.mcontroller.dialer.connect("disconnecting", self.__dialer_disconnecting_cb)
        self.mcontroller.dialer.connect("pppstats_signal", self.__dialer_ppp_stats_cb)

        dbus.service.Object.__init__(self, bus_name, path)

    #Exported Methods
    
    @dbus.service.method(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         in_signature='', out_signature='ao')
    def GetAvailableDevices(self):
        ret = []
        devices_list =  self.mcontroller.get_available_devices()
        for x in devices_list :
            ret.append(x.dbus_device.__dbus_object_path__)
            
        return ret

    @dbus.service.method(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         in_signature='s', out_signature='o')
    def FromDevIdGetObject(self, dev_id):
        return self.__FromDevIdGetObject(dev_id)
    
    def __FromDevIdGetObject(self, dev_id):
        devices_list =  self.mcontroller.get_available_devices()
        for x in devices_list:
            if dev_id in x.dev_props["info.udi"] :
                return x.dbus_device.__dbus_object_path__
        return ''

    @dbus.service.method(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetActiveDevice(self):
        device = self.mcontroller.get_active_device()
        if device != None :
            return device.dbus_device.__dbus_object_path__
        else:
            return ""

    @dbus.service.method(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         in_signature='s', out_signature='b')
    def SetActiveDevice(self, device_obj_path):
        devices_list =  self.mcontroller.get_available_devices()
        for x in devices_list:
            if os.path.basename(device_obj_path) in x.dev_props["info.udi"] :
                self.mcontroller.set_active_device(x.dev_props["info.udi"])
                return True
        return False

    #MController signals wrapper

    def __active_dev_card_status_changed_cb(self,mcontroller, status):
        self.ActiveDevCardStatusChanged(status)
        
    def __active_dev_tech_status_changed_cb(self,mcontroller, status):
        self.ActiveDevTechStatusChanged(status)
        
    def __active_dev_mode_status_changed_cb(self,mcontroller, status):
        self.ActiveDevModeStatusChanged(status)
        
    def __active_dev_domain_status_changed_cb(self,mcontroller, status):
        self.ActiveDevDomainStatusChanged(status)
        
    def __active_dev_signal_status_changed_cb(self,mcontroller, status):
        self.ActiveDevSignalStatusChanged(status)
        
    def __active_dev_pin_act_status_changed_cb(self,mcontroller, status):
        self.ActiveDevPinActStatusChanged(status)
        
    def __active_dev_roaming_status_changed_cb(self,mcontroller, status):
        self.ActiveDevRoamingActStatusChanged(status)
        
    def __active_dev_carrier_changed_cb(self,mcontroller, carrier_name):
        self.ActiveDevCarrierChanged(carrier_name)
        
    def __active_dev_carrier_sm_status_changed_cb(self,mcontroller, status):
        self.ActiveDevCarrierSmStatusChanged(status)

    def __active_dev_sms_received_cb(self,mcontroller, index):
        self.ActiveDevSmsReceived(index)

    def __active_dev_sms_spool_changed_cb(self,mcontroller, index):
        self.ActiveDevSmsSpoolChanged(index)

    def __active_dev_x_zone_changed_cb(self,mcontroller, xzone_name):
        if xzone_name != None :
            self.ActiveDevXZoneChanged(xzone_name)
        
    def __dev_card_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevCardStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_tech_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevTechStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_mode_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevModeStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_domain_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevDomainStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_signal_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevSignalStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_pin_act_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevPinActStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_roaming_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevRoamingActStatusChanged(self.__FromDevIdGetObject(dev_id), status)
        
    def __dev_carrier_changed_cb(self,mcontroller, dev_id, carrier_name):
        self.DevCarrierChanged(self.__FromDevIdGetObject(dev_id), carrier_name)
        
    def __dev_carrier_sm_status_changed_cb(self,mcontroller, dev_id, status):
        self.DevCarrierSmStatusChanged(self.__FromDevIdGetObject(dev_id), status)

    def __dev_sms_received_cb(self,mcontroller, dev_id, index):
        self.DevSmsReceived(self.__FromDevIdGetObject(dev_id), index)

    def __dev_sms_spool_changed_cb(self,mcontroller, dev_id, index):
        self.DevSmsSpoolChanged(self.__FromDevIdGetObject(dev_id), index)
                              
    def __added_device_cb(self,mcontroller, dev_id):
        self.AddedDevice(self.__FromDevIdGetObject(dev_id))
        
    def __removed_device_cb(self,mcontroller, dev_id):
        self.RemovedDevice(dev_id)

    def __supported_device_detected_cb(self, mcontroller, dev_id):
        print "Supported Device in MobileManagerDbus"
        self.SupportedDeviceDetected(dev_id)
        
    def __active_device_changed_cb(self,mcontroller, dev_id):
        device = self.__FromDevIdGetObject(dev_id)
        print device
        self.ActiveDeviceChanged(device)

    def __dialer_connected_cb (self, dialer):
        self.Connected()

    def __dialer_connecting_cb(self, dialer):
        self.Connecting()
        
    def __dialer_disconnected_cb (self, dialer):
        self.Disconnected()

    def __dialer_disconnecting_cb(self, dialer):
        self.Disconnecting()

    def __dialer_ppp_stats_cb(self, dialer, rb, tb, it):
        self.Stats(rb, tb, it)
            
    #Exported Signals

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevCardStatusChanged(self, status):
        pass
    
    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevTechStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevModeStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevDomainStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevSignalStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='b')
    def ActiveDevPinActStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='b')
    def ActiveDevRoamingActStatusChanged(self, status):
        pass
    
    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def ActiveDevCarrierChanged(self, carrier_name):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevCarrierSmStatusChanged(self, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevSmsReceived(self, index):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='i')
    def ActiveDevSmsSpoolChanged(self, type):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def ActiveDevXZoneChanged(self, xzone_name):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevCardStatusChanged(self, device, status):
        pass
    
    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevTechStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevModeStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevDomainStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevSignalStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='sb')
    def DevPinActStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='sb')
    def DevRoamingActStatusChanged(self, device, status):
        pass
    
    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='ss')
    def DevCarrierChanged(self, device, carrier_name):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevCarrierSmStatusChanged(self, device, status):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevSmsReceived(self, device, index):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='si')
    def DevSmsSpoolChanged(self, device, index):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='ss')
    def DevXZoneChanged(self, device, xzone_name):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def AddedDevice(self, device):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def RemovedDevice(self, device):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def SupportedDeviceDetected(self, device):
        pass

    @dbus.service.signal(MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,
                         signature='s')
    def ActiveDeviceChanged(self, device):
        pass

    @dbus.service.method(MOBILE_MANAGER_DIALER_INTERFACE_URI,
                         in_signature='sssbsss')    
    def Start(self, username, password, apn, auto_dns,
              primary_dns, secundary_dns, dns_suffixes):
        self.mcontroller.dialer.start(username, password, apn, auto_dns,
                                      primary_dns, secundary_dns, dns_suffixes)

    @dbus.service.method(MOBILE_MANAGER_DIALER_INTERFACE_URI)    
    def Stop(self):
        self.mcontroller.dialer.stop()

    @dbus.service.method(MOBILE_MANAGER_DIALER_INTERFACE_URI,
                        in_signature='', out_signature='i')
    def Status(self):
        return self.mcontroller.dialer.status()

    @dbus.service.signal(MOBILE_MANAGER_DIALER_INTERFACE_URI)    
    def Connecting(self):
        pass
    
    @dbus.service.signal(MOBILE_MANAGER_DIALER_INTERFACE_URI)
    def Connected(self):
        pass

    @dbus.service.signal(MOBILE_MANAGER_DIALER_INTERFACE_URI)
    def Disconnecting(self):
        pass

    @dbus.service.signal(MOBILE_MANAGER_DIALER_INTERFACE_URI)
    def Disconnected(self):
        pass

    @dbus.service.signal(MOBILE_MANAGER_DIALER_INTERFACE_URI,
                         signature='iid' )
    def Stats(self, recived_bytes, sent_bytes, interval_time):
        pass

class MobileManagerDbusDevice(dbus.service.Object):
    def __init__(self, device, bname, dev_id):
        self.device = device
        self.dev_id = dev_id
        self.bname = bname
        self.carrier_list = None
        self.carrier_last_check = 0
        self.ussd_result = ""
        
        dbus.service.Object.__init__(self, bname, MOBILE_MANAGER_DEVICE_PATH + dev_id)

    def disconnect_dbus(self):
        self.remove_from_connection(path = MOBILE_MANAGER_DEVICE_PATH + self.dev_id)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='as')
    def GetCapabilities(self):
        ret = [MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI]
        if AT_COMM_CAPABILITY in self.device.capabilities :
            ret.append(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI)
            ret.append(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI)

        if X_ZONE_CAPABILITY in self.device.capabilities :
            ret.append(MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI)

        if SMS_CAPABILITY in self.device.capabilities :
            ret.append(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI)

        if ADDRESSBOOK_CAPABILITY in self.device.capabilities :
            ret.append(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI)

        if NO_OPTIONS_MENU in self.device.capabilities :
            ret.append(MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU)

        return ret
    
    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='s', out_signature='b')
    def HasCapability(self, capability):
        if capability == MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI :
            if AT_COMM_CAPABILITY in self.device.capabilities :
                return True
            else:
                return False
        elif capability == MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI:
            if AT_COMM_CAPABILITY in self.device.capabilities :
                return True
            else:
                return False
        elif capability == MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI:
            if X_ZONE_CAPABILITY in self.device.capabilities :
                return True
            else:
                return False
        elif capability == MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI:
            return True
        elif capability == MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI :
            if SMS_CAPABILITY in self.device.capabilities :
                return True
            else:
                return False
        elif capability == MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI :
            if ADDRESSBOOK_CAPABILITY in self.device.capabilities :
                return True
            else:
                return False
        elif capability == MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU :
            if NO_OPTIONS_MENU in self.device.capabilities :
                return True
            else:
                return False
        else:
            return False

    @dbus.service.method(MOBILE_MANAGER_DEVICE_DEBUG_INTERFACE_URI,
                         in_signature='s', out_signature='sass')
    def SendAtCommand(self, at_command):
        ret = self.device.send_at_command(at_command)
        
        if len(ret[1])==0:
            return ret[0], [""], ret[2]
        else:
            return ret[0], ret[1], ret[2]

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetDataDevicePath(self):
        return self.device.get_property("data-device")

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetConfDevicePath(self):
        return self.device.get_property("conf-device")

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def GetVelocity(self):
        return int(self.device.get_property("velocity"))

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='i', out_signature='')
    def SetVelocity(self, velocity):
         self.device.set_property("velocity", str(velocity))

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def GetHardwareFlowControl(self):
        return self.device.get_property('hardware-flow-control')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='b', out_signature='')
    def SetHardwareFlowControl(self, value):
        self.device.set_property('hardware-flow-control', value)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def GetHardwareErrorControl(self):
        return self.device.get_property('hardware-error-control')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='b', out_signature='')
    def SetHardwareErrorControl(self, value):
        self.device.set_property('hardware-error-control', value)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def GetHardwareCompress(self):
        return self.device.get_property('hardware-compress')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='b', out_signature='')
    def SetHardwareCompress(self, value):
        self.device.set_property('hardware-compress', value)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetPrettyName(self):
        return self.device.get_property('pretty-name')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetDeviceIcon(self):
        return self.device.get_property('device-icon')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def GetPriority(self):
        return int(self.device.get_property('priority'))

    @dbus.service.method(MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsMultiPortDevice(self):
        return self.device.get_property('multiport-device')

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='s', out_signature='b')
    def SendPIN(self, pin):
        return self.device.send_pin(pin)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='ss', out_signature='b')
    def SetPIN(self, old_pin, new_pin):
        return self.device.set_pin(old_pin, new_pin)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='sb', out_signature='b')
    def SetPINActive(self, pin, active):
        return self.device.set_pin_active(pin, active)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsPINActive(self):
        return self.device.is_pin_active()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def PINStatus(self):
        return self.device.pin_status()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,
                         in_signature='ss', out_signature='b')
    def SendPUK(self, puk, pin):
        return self.device.send_puk(puk, pin)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='')
    def EmitStatusSignals(self):
        self.device.emit_status_signals()
        

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def GetSingal(self):
        return self.device.get_signal()

    def __update_carrier_list(self, data):
        self.carrier_last_check = time.time()
	if type(data["supported_formats"]) == int :
            data["supported_formats"] = [data["supported_formats"]]
        self.carrier_list = data

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='a(isssi)aiai')
    def GetCarrierList(self):
        delta = time.time() - self.carrier_last_check
        if delta < 180 :
            print "Carrier Delta : %s" % delta
            carrier_list = self.carrier_list
            return carrier_list["carrier_list"], carrier_list["supported_modes"], carrier_list["supported_formats"]
        
        self.device.get_carrier_list(self.__update_carrier_list)
        
        mainloop =  gobject.MainLoop(is_running=True)
        context = mainloop.get_context()
        while self.device.pause_polling_necesary == True :
            context.iteration()
        carrier_list = self.carrier_list
        print carrier_list
        return carrier_list["carrier_list"], carrier_list["supported_modes"], carrier_list["supported_formats"]

    def __check_ussd_cmd(self, data):
        if len(data) == 3 :
            if data[2] == "OK" :
                self.ussd_result = data[1][0]
            else:
                self.ussd_result = ""
        else:
            self.ussd_result = ""
        
    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='s', out_signature='s')
    def GetUSSDCmd(self, ussd_cmd):
        self.device.get_ussd_cmd(ussd_cmd, self.__check_ussd_cmd)

        mainloop = gobject.MainLoop(is_running=True)
        context = mainloop.get_context()
        while self.device.pause_polling_necesary == True :
            context.iteration()

        if self.ussd_result != "" :
            ret = self.ussd_result
        else:
            ret = ""
        self.ussd_result = ""

        return ret

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetCarrier(self):
        return self.device.get_carrier()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsOn(self):
        return self.device.is_on()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def TurnOn(self):
        return self.device.turn_on()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def TurnOff(self):
        return self.device.turn_off()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='iiisi')
    def GetNetInfo(self):
        return  self.device.get_net_info()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='ii')
    def GetModeDomain(self):
        return self.device.get_mode_domain()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='ii', out_signature='b')
    def SetModeDomain(self, mode, domain):
        return self.device.set_mode_domain(mode, domain)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='as')
    def GetCardInfo(self):
        return self.device.get_card_info()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def GetCardStatus(self):
        return self.device.get_card_status()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='ii', out_signature='b')
    def SetCarrier(self, carrier_id, tech):
        return self.device.set_carrier(carrier_id, tech)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def SetCarrierAutoSelection(self):
        return self.device.set_carrier_auto_selection()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsCarrierAuto(self):
        return self.device.is_carrier_auto()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsAttached(self):
        return  self.device.is_attached()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='i')
    def GetAttachState(self):
        return self.device.get_attach_state()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,
                         in_signature='', out_signature='b')
    def IsRoaming(self):
        return self.device.is_roaming()

    @dbus.service.method(MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI,
                         in_signature='', out_signature='s')
    def GetXZone(self):
        x_zone = self.device.get_x_zone()
        if x_zone != None :
            return x_zone
        else:
            return ''

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='', out_signature='a(ubsd)')
    def ListReceived(self):
        return self.device.sms_list_spool("received")

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='', out_signature='a(ubsd)')
    def ListSended(self):
        return self.device.sms_list_spool("sended")
        pass

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='', out_signature='a(ubsd)')
    def ListDrafts(self):
        return self.device.sms_list_spool("draft")
        pass

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def DeleteReceived(self, index):
        return self.device.sms_delete_spool_item("received", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def DeleteSended(self, index):
        return self.device.sms_delete_spool_item("sended", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def DeleteDraft(self, index):
        return self.device.sms_delete_spool_item("draft", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='ubsds')
    def GetReceived(self, index):
        return self.device.sms_get_spool_item("received", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='ubsds')
    def GetSended(self, index):
        return self.device.sms_get_spool_item("sended", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='ubsds')
    def GetDraft(self, index):
        return self.device.sms_get_spool_item("draft", index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='ss', out_signature='b')
    def SetDraft(self, number, text):
        return self.device.sms_set_spool_item("draft", number, text)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='uss', out_signature='b')
    def EditDraft(self, index, number, text):
        return self.device.sms_edit_draft(index, number, text)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def MarkReceivedReaded(self, index):
        return self.device.sms_mark_item("received", index, True)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def MarkReceivedUnReaded(self, index):
        return self.device.sms_mark_item("received", index, False)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def MarkSendedReaded(self, index):
        return self.device.sms_mark_item("sended", index, True)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def MarkSendededUnReaded(self, index):
        return self.device.sms_mark_item("sended", index, False)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_SMS_INTERFACE_URI,
                         in_signature='sss', out_signature='u')
    def Send(self, number, smsc, text):
        if self.device.sms_send(number, smsc, text) == True :
            return True
        else:
            return False
    
    @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
                         in_signature='', out_signature='a(uss)')
    def ListContacts(self):
        return self.device.sms_ab_list()
    
    @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
                         in_signature='ss', out_signature='b')
    def Add(self, name, number):
        return self.device.sms_ab_add(name, number)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
                         in_signature='u', out_signature='b')
    def Delete(self, index):
        return self.device.sms_ab_del(index)

    ## @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
    ##                      in_signature='s', out_signature='a(uss)')
    ## def FindContact(self, pattern):
    ##     return self.device.sms_ab_find(pattern)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
                         in_signature='u', out_signature='(uss)')
    def Get(self, index):
        return self.device.sms_ab_get(index)

    @dbus.service.method(MOBILE_MANAGER_DEVICE_ADDRESSBOOK_INTERFACE_URI,
                         in_signature='', out_signature='u')
    def GetSize(self):
        return self.device.sms_ab_get_size()

    
    
if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    name = dbus.service.BusName(MOBILE_MANAGER_CONTROLLER_URI, dbus.SystemBus())

    controller = DbusController(bus_name=name)

    mainloop = gobject.MainLoop()
    mainloop.run()
