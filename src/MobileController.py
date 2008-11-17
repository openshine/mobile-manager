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
import gobject
import dbus
if getattr(dbus, "version", (0,0,0)) >= (0,41,0):
    import dbus.glib

from MobileStatus import CARD_STATUS_DETECTED, CARD_STATUS_CONFIGURED
from MobileCapabilities import AT_COMM_CAPABILITY
from MobileDialWvdial import MobileDialWvdial
from MobileManager.MobileManagerDbus import MobileManagerDbusController

DeviceDrivers = ["Huawei", "Option", "Nozomi", "Novatel", "Sierra", "ZTE", "Bluetooth", "USB", "Serial"]

class MobileController(gobject.GObject):

    __gsignals__ = { 'active-dev-card-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_INT,)) ,
                     'active-dev-tech-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_INT,)) ,
                     'active-dev-mode-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_INT,)) ,
                     'active-dev-domain-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                           (gobject.TYPE_INT,)) ,
                     'active-dev-signal-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                          (gobject.TYPE_INT,)) ,
                     'active-dev-pin-act-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                            (gobject.TYPE_BOOLEAN,)) ,
                     'active-dev-roaming-status-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                           (gobject.TYPE_BOOLEAN,)) ,
                     'active-dev-carrier-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                     (gobject.TYPE_STRING,)) ,
                     'active-dev-sms-received' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                     (gobject.TYPE_INT,)) ,
                     'active-dev-sms-spool-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                     (gobject.TYPE_INT,)) ,
                     'active-dev-carrier-sm-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                               (gobject.TYPE_INT,)) ,
                     'active-dev-x-zone-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                               (gobject.TYPE_STRING,)) ,

                     'dev-card-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-tech-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-mode-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                         (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-domain-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                           (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-signal-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                          (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-pin-act-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                            (gobject.TYPE_STRING, gobject.TYPE_BOOLEAN,)) ,
                     'dev-roaming-status-changed': (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                           (gobject.TYPE_STRING, gobject.TYPE_BOOLEAN,)) ,
                     'dev-carrier-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                     (gobject.TYPE_STRING, gobject.TYPE_STRING,)) ,
                     'dev-sms-received' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                     (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-sms-spool-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     'dev-carrier-sm-status-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                               (gobject.TYPE_STRING, gobject.TYPE_INT,)) ,
                     
                     'added-device' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                         (gobject.TYPE_STRING,)) ,
                     'removed-device' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                         (gobject.TYPE_STRING,)) ,
                     'supported-device-detected' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                    (gobject.TYPE_STRING,)) ,
                     
                     'active-device-changed' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,
                                                    (gobject.TYPE_STRING,)) ,
                     
                     }
                     
    def __init__(self, bname=None):
        gobject.GObject.__init__(self)

        #Hal Support inicialization
        self.dbus = dbus.SystemBus()
        self.bname = bname
        self.hal_manager_obj = self.dbus.get_object("org.freedesktop.Hal", "/org/freedesktop/Hal/Manager")
        self.hal_manager = dbus.Interface(self.hal_manager_obj, "org.freedesktop.Hal.Manager")
        
        #Signals
        self.hal_manager.connect_to_signal("DeviceAdded", self.__plug_device_cb)
        self.hal_manager.connect_to_signal("DeviceRemoved", self.__unplug_device_cb)

        self.available_devices = []
        self.__procesing_devices = []

        self.dialer = MobileDialWvdial(self)

        if bname != None:
            MobileManagerDbusController(bus_name=bname, mcontroller=self)
        
        
        self.__first_time_hardware_detection()

    def __first_time_hardware_detection(self):
        #Import available drivers
        
        for x in DeviceDrivers :
            exec("from MobileDevice%s import MobileDevice%s" % (x,x))
        
        devices = self.hal_manager.GetAllDevices()
        for device in devices :
            device_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", device)
            dev_props = device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
            for driver in DeviceDrivers:
                exec ("d = MobileDevice%s(self, dev_props)" % driver)
                if d.is_device_supported() == True:
                    d.connect_dbus()
                    self.available_devices.append([d.get_property("priority"), False, d.dev_props["info.udi"], d])
                    break

        self.available_devices.sort()
        self.available_devices.reverse()
        

        for dev in self.get_available_devices() :
            if dev.init_device() != True:
                print "Error in init_device of %s" % dev
            else:
                dev.open_device()
                    
        print self.available_devices
        
    def __real_add_device_cb(self, device):
        print "real add device %s" % str(device)
        if device.init_device() == True :
            if len(self.available_devices)>0 :
                i=0
                for x in self.available_devices :
                    if int(x[0]) < int(device.get_property("priority")) :
                        break
                    i = i + 1
                device.connect_dbus()
                self.available_devices.insert(i, [device.get_property("priority"),
                                                  False, device.dev_props["info.udi"], device])
            else:
                device.connect_dbus()
                self.available_devices.append([device.get_property("priority"),
                                              False, device.dev_props["info.udi"], device])

            print self.available_devices    
            device.open_device()
            try:
                self.__procesing_devices.remove(device.dev_props["info.udi"])
            except:
                print "device not in procesing list"
            self.emit('added-device', device.dev_props["info.udi"])
            return False
        else:
            return True

    def __real_plug_device_cb(self, udi):
        if udi in self.__procesing_devices :
            return False
        
        for x in self.available_devices :
            if x[2] == udi :
                return False
            
        #Import available drivers
        for x in DeviceDrivers :
            exec("from MobileDevice%s import MobileDevice%s" % (x,x))
        
        device_dbus_obj = self.dbus.get_object("org.freedesktop.Hal", udi)
        try:
            dev_props = device_dbus_obj.GetAllProperties(dbus_interface="org.freedesktop.Hal.Device")
        except:
            return False
            
        for driver in DeviceDrivers:
            
            exec ("d = MobileDevice%s(self, dev_props)" % driver)
            if d.is_device_supported() == True:
                print "device supported %s" % udi
                self.__procesing_devices.append(udi)
                self.emit('supported-device-detected', d.dev_props["info.udi"])
                self.emit('dev-card-status-changed', d.dev_props["info.udi"], CARD_STATUS_DETECTED)
                d.cached_status_values["card_status"] = CARD_STATUS_DETECTED
                gobject.timeout_add(5000, self.__real_add_device_cb, d)

        return False

    def __plug_device_cb(self, udi):
        gobject.timeout_add(3000, self.__real_plug_device_cb, udi)

    def __unplug_device_cb(self, udi):
        for x in self.available_devices :
            if x[2] == udi :
                dev_id = x[3].dbus_device.__dbus_object_path__
                x[3].close_device()
                x[3].disconnect_dbus()
                self.available_devices.remove(x)
                self.emit('removed-device', dev_id)                   
                return

    def get_active_device(self):
        if len(self.available_devices) > 0 :
            for x in self.available_devices :
                if x[1] == True:
                    return x[3]
            self.available_devices[0][1] == True
            return self.available_devices[0][3]
        else:
            return None
        
    def set_active_device(self, udi):
        for x in self.available_devices :
            x[1] = False
        
        if udi == None:
             self.emit('active-device-changed', None)
             return
        
        for x in self.available_devices :
            if x[2] == udi:
                x[1] = True
                self.emit('active-device-changed', udi)
                x[3].emit_status_signals()
                return
        self.emit('active-device-changed', None)

    def get_available_devices(self):
        ret = []
        for x in self.available_devices :
            ret.append(x[3])
        return ret

    def get_available_at_devices(self):
        ret = []
        for x in self.available_devices :
            if AT_COMM_CAPABILITY in x[3].capabilities :
                ret.append(x[3])
        return ret

    def get_available_not_at_devices(self):
        ret = []
        for x in self.available_devices :
            if AT_COMM_CAPABILITY not in x[3].capabilities :
                ret.append(x[3])
        return ret
    
gobject.type_register(MobileController)
    

        
