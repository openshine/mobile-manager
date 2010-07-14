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
import gobject
import os
import re
from MobileStatus import *
from MobileCapabilities import *
from MobileManagerDbus import MobileManagerDbusDevice
from messaging import PDU
import MobileManager
import time
import codecs


class MobileDeviceIO():
    def __init__(self, path, actions=None, attempts=1, timeout=2):
        self.path = path
        self.fd = None
        self.attempts = attempts
        self.timeout = timeout
        self.actions = actions

    def open(self):
        self.fd = MobileManager.mdpc.open(self.path)
        print ("Open fd : %s" % self.fd)
        self.flush()
        if self.actions != None:
            self.actions()

    def close(self):
        if self.fd != None :
            print ("Close fd : %s" % MobileManager.mdpc.close(self.fd))
            self.fd = None

    def reopen(self):
        self.flush()
        self.close()
        self.fd = MobileManager.mdpc.open(self.path)
        print ("Open fd : %s" % self.fd)
        self.flush()

        if self.actions != None:
            self.actions()

    def read_c(self):
        c = MobileManager.mdpc.read_c(self.fd)
        return c
        
    def readline(self):
        attempts = 0
        while attempts != self.attempts :
            string = MobileManager.mdpc.read_string(self.fd, self.timeout)
            if string != None:
                return string
            #print "Attempts %s" % attempts
            attempts = attempts + 1
        return None
            
        
    def write(self, string):
        return MobileManager.mdpc.write_string(self.fd, string)

    def fileno(self):
        return self.fd

    def flush(self):
        return MobileManager.mdpc.flush(self.fd)

def hex2bin(str):
    from string import atoi
    bin = ['0000','0001','0010','0011',
           '0100','0101','0110','0111',
           '1000','1001','1010','1011',
           '1100','1101','1110','1111']
    aa = ''
    for i in range(len(str)):
        aa += bin[atoi(str[i],base=16)]
    return aa
            
class MobileDevice(gobject.GObject) :

    __gproperties__ = {
        'data-device' : (gobject.TYPE_STRING, 'data device',
                         'string that represents the data device',
                         '', gobject.PARAM_READWRITE),
        'conf-device' : (gobject.TYPE_STRING, 'device',
                         'string that represents the conf device',
                         '', gobject.PARAM_READWRITE),
        'velocity' : (gobject.TYPE_STRING, 'velocity',
                      'int that represents the conf device',
                      "57600", gobject.PARAM_READWRITE),
        'hardware-flow-control' : (gobject.TYPE_BOOLEAN, 'hardware flow control',
                                   'boolean that represents the harware flow control',
                                   False, gobject.PARAM_READWRITE),
        'hardware-error-control' : (gobject.TYPE_BOOLEAN, 'hardware error control',
                                    'boolean that represents the hardware error control',
                                    False, gobject.PARAM_READWRITE),
        'hardware-compress' : (gobject.TYPE_BOOLEAN, 'hardware compress',
                              'string that represents the hardware compress',
                              False, gobject.PARAM_READWRITE),
        'devices-autoconf' : (gobject.TYPE_BOOLEAN, 'devices autoconf',
                              'boolean that represents if the driver has port autodetection',
                              False, gobject.PARAM_READWRITE),
        'device-conf-file' : (gobject.TYPE_STRING, 'device conf file',
                              'string that represents the device conf file',
                              '', gobject.PARAM_READABLE),
        'multiport-device' : (gobject.TYPE_BOOLEAN, 'multiport device',
                              'boolean that represents if is available a second port for conf the device diferent than data port',
                              False, gobject.PARAM_READABLE),
        
        'pretty-name' : (gobject.TYPE_STRING, 'pretty name',
                         'string that represents the pretty name of the device',
                         '', gobject.PARAM_READABLE),
        'priority' : (gobject.TYPE_STRING, 'priority',
                      'int that represents the priority to use the device over other devices',
                      '0', gobject.PARAM_READWRITE),
        'device-icon' : (gobject.TYPE_STRING, 'device icon',
                         'string that represents the icon of the device',
                         '', gobject.PARAM_READWRITE),
        
        'smsc-number' : (gobject.TYPE_STRING, 'smsc-number',
                         'string that represents the smsc number',
                         '', gobject.PARAM_READABLE),
        }
    
    def __init__ (self, mcontroller, dev_props) :
        gobject.GObject.__init__(self)
        self.poll_round = 0
        self.polling_flag = False
        
        self.dbus = mcontroller.dbus
        self.hal_manager = mcontroller.hal_manager
        self.mcontroller = mcontroller
        self.dev_props = dev_props

        self.serial = None

        self.pdu = PDU()
        
        self.data_device = ''
        self.conf_device = ''
        self.velocity = "57600"
        self.hardware_flow_control = False
        self.hardware_error_control = False
        self.hardware_compress = False
        self.devices_autoconf = False

        self.multiport = False

        self.pretty_name = ''
        self.device_icon = ''
        self.priority = "0"
        self.smsc_number = ''
        self.sim_id = None

        self.using_data_device=False

        path_device_conf = os.path.join("/etc", "MobileManager/", "Devices/")
        os.system ("mkdir -p %s" % path_device_conf)

        device_conf_file = os.path.join(path_device_conf,
                                        os.path.basename(dev_props["info.udi"]))
        
        self.device_conf_file = device_conf_file
        if not os.path.exists(os.path.dirname(device_conf_file)) :
            os.system ("mkdir -p %s" % os.path.dirname(device_conf_file))

        self.exists_conf = self.load_conf()

        #Status Polling Stuff

        self.status_polling_timeout_id = None
        self.cached_status_values = { "card_status" : None,
                                      "tech" : None,
                                      "mode" : None,
                                      "domain" : None,
                                      "signal_level" : None,
                                      "is_pin_active" : None,
                                      "is_roaming" : None,
                                      "carrier_name" : None,
                                      "carrier_selection_mode" : None,
                                      "ab_size" : None}

        self.external_debug_func = None
        self.card_is_on = None
        self.pause_polling_necesary = False
        self.x_zone_support = None

        self.dbus_device = None
        self.dbus_device_path = None

        if X_ZONE_CAPABILITY not in self.capabilities :
            self.x_zone_support = False


    def do_get_property(self, property):
        if property.name == 'data-device': 
            return self.data_device
        elif property.name == 'conf-device':
            return self.conf_device
        elif property.name == 'velocity':
            return self.velocity
        elif property.name == 'hardware-flow-control':
            return self.hardware_flow_control
        elif property.name == 'hardware-error-control':
            return self.hardware_error_control
        elif property.name == 'hardware-compress':
            return self.hardware_compress
        elif property.name == 'devices-autoconf':
            return self.devices_autoconf
        elif property.name == 'device-conf-file':
            return self.device_conf_file
        elif property.name == 'multiport-device':
            if self.data_device != self.conf_device and self.conf_device != '' :
                return True
            else:
                return False
        elif property.name == 'pretty-name':
            if self.pretty_name != '' :
                return self.pretty_name
            else:
                return self.dev_props["info.product"]
        elif property.name == 'device-icon':
            return self.device_icon
        
        elif property.name == 'priority':
            return self.priority
        elif property.name == 'smsc-number' :
            return self.smsc_number
        else:
            raise AttributeError, 'unknown property %s' % property.name

    def do_set_property(self, property, value):
        if property.name == 'data-device': 
            self.data_device = value
        elif property.name == 'conf-device':
            self.conf_device = value
        elif property.name == 'velocity':
            self.velocity = value
        elif property.name == 'hardware-flow-control':
            self.hardware_flow_control = value
        elif property.name == 'hardware-error-control':
            self.hardware_error_control = value
        elif property.name == 'hardware-compress':
            self.hardware_compress = value
        elif property.name == 'devices-autoconf':
            self.devices_autoconf = value
        elif property.name == 'device-conf-file':
            return
        elif property.name == 'multiport-device' :
            return
        elif property.name == 'pretty-name' :
            return
        elif property.name == 'device-icon':
            self.device_icon = value
        elif property.name == 'priority':
            self.priority = value
        elif property.name == 'smsc-number':
            self.smsc_number = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

        self.save_conf()

    def __upower_actions (self):
        try:
            import dbus
            bus = dbus.SystemBus()
            proxy = bus.get_object('org.freedesktop.UPower', '/org/freedesktop/UPower')
            iface = dbus.Interface(proxy, 'org.freedesktop.UPower')
            
            iface.connect_to_signal("Sleeping", self.__upower_sleeping_cb)
            iface.connect_to_signal("Resuming", self.__upower_resuming_cb)
        except:
            print "May be UPower is not present!"

    def __upower_sleeping_cb(self):
        print "%s ---> To Sleep" % self
        self.stop_polling()

    def __upower_resuming_cb(self):
        print "%s ---> Resuming" % self
        self.start_polling()

    def set_debug_func(self, func):
        self.external_debug_func = func

    def dbg_msg (self, str):
        if self.external_debug_func != None :
             self.external_debug_func (str)
        else:
            MobileManager.log.debug(str)

    def connect_dbus(self):
        self.dbus_device = MobileManagerDbusDevice(self , self.mcontroller.bname,
                                                   os.path.basename(self.dev_props["info.udi"]))
        self.dbus_device_path = str(self.dbus_device)
        self.__upower_actions()
        
    def disconnect_dbus(self):
        print "disconnecting "
        self.dbus_device.disconnect_dbus()
        print "disconnected"
        

    def is_device_supported(self):
        return False

    def init_device(self):
        #Initialization of devices, usefull for pre-configure ports or other stuff
        if MobileManager.AT_COMM_CAPABILITY in self.capabilities :
            self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], CARD_STATUS_CONFIGURED)
            self.cached_status_values["card_status"] = CARD_STATUS_CONFIGURED
        
        return True

    def load_conf(self):
        device_conf_file = self.get_property("device-conf-file")
        
        if not os.path.exists(device_conf_file) :
            return False

        f = open (device_conf_file)
        lines = f.readlines()
        f.close()

        data_dev_patt = re.compile("^data_device +(?P<value>/dev/\W+)")
        conf_dev_patt = re.compile("^conf_device +(?P<value>/dev/\W+)")
        vel_patt = re.compile("^velocity +(?P<value>[0-9]+)")
        hfc_patt = re.compile("^hardware_flow_control +(?P<value>[01])")
        hec_patt = re.compile("^hardware_error_control +(?P<value>[01])")
        hc_patt = re.compile("^hardware_compress +(?P<value>[01])")
        priority_patt = re.compile("^priority +(?P<value>[0-9]+)")
        smsc_patt = re.compile("^smsc_number +(?P<value>[0-9]+)")
        
        for line in lines :
            if not line.startswith("#") :
                if data_dev_patt.match(line) != None:
                    value = data_dev_patt.match(line).group("value")
                    self.set_property("data-device", value)
                elif conf_dev_patt.match(line) != None:
                    value = conf_dev_patt.match(line).group("value")
                    self.set_property("conf-device", value)
                elif vel_patt.match(line) != None:
                    value = vel_patt.match(line).group("value")
                    self.set_property("velocity", value)
                elif hfc_patt.match(line) != None:
                    value = hfc_patt.match(line).group("value")
                    self.set_property("hardware-flow-control", bool(int(value)))
                elif hec_patt.match(line) != None:
                    value = hec_patt.match(line).group("value")
                    self.set_property("hardware-error-control", bool(int(value)))
                elif hc_patt.match(line) != None:
                    value = hc_patt.match(line).group("value")
                    self.set_property("hardware-compress", bool(int(value)))
                elif priority_patt.match(line) != None:
                    value = priority_patt.match(line).group("value")
                    self.set_property("priority", value)
                elif smsc_patt.match(line) != None:
                    value = priority_patt.match(line).group("value")
                    self.set_property("smsc-number", value)

        return True
            
    def save_conf(self):
        device_conf_file = self.get_property("device-conf-file")
        f = open (device_conf_file, 'w+')
        if self.get_property("devices-autoconf") == False:
            data_device = self.get_property("data-device")
            conf_device = self.get_property("conf-device")
            if len(data_device) > 0 :
                f.write("data_device %s\n" % data_device)
            if len(conf_device) > 0 :
                f.write("conf_device %s\n" % conf_device)
                
        f.write("velocity %s\n" % self.get_property("velocity"))
        f.write("hardware_flow_control %s\n" % int(self.get_property("hardware-flow-control")))
        f.write("hardware_error_control %s\n" % int(self.get_property("hardware-error-control")))
        f.write("hardware_compress %s\n" % int(self.get_property("hardware-compress")))
        f.write("priority %s\n" % self.get_property("priority"))
        f.write("smsc %s\n" % self.get_property("smsc-number"))
        f.close()

    # Decorators (pin_status_required)
    def pin_status_required(status, ret_value_on_error=False):
        def wrap (f):
            def _f(self, *args, **kw):
                if self.polling_flag == True :
                    return f(self, *args, **kw)
                else:
                    if self.pin_status() == status :
                        return f(self, *args, **kw)
                    else:
                        print "Pin Status Required : %s" % status
                        return ret_value_on_error
            return _f
        return wrap

    def __real_status_polling(self):
        
        self.dbg_msg ("----------------------> INIT poll round %s" % self.poll_round)

        if self.pause_polling_necesary == True :
            self.dbg_msg ("Pause Polling") 
            return True

        card_status = None
        tech = None
        mode = None
        domain = None
        signal_level = None
        is_pin_active = None
        is_roaming = None
        carrier_name = None
        carrier_selection_mode = None

        card_status = self.get_card_status()

        if card_status > CARD_STATUS_CONFIGURED :
            if card_status == CARD_STATUS_NO_SIM :
                print "NO SIM , NO PIN"

        if card_status >= CARD_STATUS_READY :
            self.polling_flag = True

            is_pin_active = self.is_pin_active()
            tech ,mode , domain, carrier_name, carrier_selection_mode = self.get_net_info()
            signal_level = self.get_signal()
            x_zone = self.get_x_zone()
            if x_zone == None:
                self.mcontroller.emit('active-dev-x-zone-changed', None)
            else:
                self.mcontroller.emit('active-dev-x-zone-changed', x_zone)

            self.polling_flag = False

        if self.cached_status_values["card_status"] != card_status :
            self.cached_status_values["card_status"] = card_status
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-card-status-changed', card_status)
                self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)
            else:
                self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)

        if self.cached_status_values["is_pin_active"] != is_pin_active :
            self.cached_status_values["is_pin_active"] = is_pin_active
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-pin-act-status-changed' , is_pin_active)
                self.mcontroller.emit('dev-pin-act-status-changed' , self.dev_props["info.udi"], is_pin_active)
            else:
                self.mcontroller.emit('dev-pin-act-status-changed' , self.dev_props["info.udi"], is_pin_active)

        if card_status >= CARD_STATUS_READY :
            if self.cached_status_values["tech"] != tech :
                self.cached_status_values["tech"] = tech
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-tech-status-changed', tech)
                    self.mcontroller.emit('dev-tech-status-changed', self.dev_props["info.udi"], tech)
                else:
                    self.mcontroller.emit('dev-tech-status-changed', self.dev_props["info.udi"], tech)

            if self.cached_status_values["mode"] != mode :
                if mode != None:
                    self.cached_status_values["mode"] = mode
                    if self.__is_active_device():
                        self.mcontroller.emit('active-dev-mode-status-changed', mode)
                        self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], mode)
                    else:
                        self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], mode)

            if self.cached_status_values["domain"] != domain :
                self.cached_status_values["domain"] = domain
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-domain-status-changed', domain)
                    self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], domain)
                else:
                    self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], domain)

            if self.cached_status_values["signal_level"] != signal_level :
                self.cached_status_values["signal_level"] = signal_level
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-signal-status-changed', signal_level)
                    self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)
                else:
                    self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)

            if self.cached_status_values["carrier_name"] != carrier_name :
                self.cached_status_values["carrier_name"] = carrier_name
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-carrier-changed', carrier_name)
                    self.mcontroller.emit('dev-carrier-changed', self.dev_props["info.udi"], carrier_name)
                else:
                    self.mcontroller.emit('dev-carrier-changed', self.dev_props["info.udi"], carrier_name)

            if self.cached_status_values["carrier_selection_mode"] != carrier_selection_mode :
                self.cached_status_values["carrier_selection_mode"] = carrier_selection_mode
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-carrier-sm-status-changed', carrier_selection_mode)
                    self.mcontroller.emit('dev-carrier-sm-status-changed', self.dev_props["info.udi"], carrier_selection_mode)
                else:
                    self.mcontroller.emit('dev-carrier-sm-status-changed', self.dev_props["info.udi"], carrier_selection_mode)

            self.sms_poll()
            self.verify_concat_sms_spool()

        self.dbg_msg ("----------------------> END poll round %s" % self.poll_round)
        self.poll_round = self.poll_round + 1
        return True
        
    def status_polling(self):
        try:
            return self.__real_status_polling()
        except:
            self.dbg_msg ("----------------------> END poll round %s (poll exception) " % self.poll_round)
            self.poll_round = self.poll_round + 1
            return True

    def emit_status_signals(self):
        if not MobileManager.AT_COMM_CAPABILITY in self.capabilities :
            return
        
        if self.cached_status_values["card_status"] != None :
            card_status = self.cached_status_values["card_status"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-card-status-changed', card_status)
                self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)
            else:
                self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)

        if self.cached_status_values["is_pin_active"] != None :
            is_pin_active = self.cached_status_values["is_pin_active"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-pin-act-status-changed' , is_pin_active)
                self.mcontroller.emit('dev-pin-act-status-changed' , self.dev_props["info.udi"], is_pin_active)
            else:
                self.mcontroller.emit('dev-pin-act-status-changed' , self.dev_props["info.udi"], is_pin_active)

        if self.cached_status_values["tech"] != None :
            tech = self.cached_status_values["tech"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-tech-status-changed', tech)
                self.mcontroller.emit('dev-tech-status-changed', self.dev_props["info.udi"], tech)
            else:
                self.mcontroller.emit('dev-tech-status-changed', self.dev_props["info.udi"], tech)
                 
        if self.cached_status_values["mode"] != None :
            mode = self.cached_status_values["mode"] 
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-mode-status-changed', mode)
                self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], mode)
            else:
                self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], mode)
                 
        if self.cached_status_values["domain"] != None :
            domain = self.cached_status_values["domain"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-domain-status-changed', domain)
                self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], domain)
            else:
                self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], domain)

        if self.cached_status_values["signal_level"] != None :
            signal_level = self.cached_status_values["signal_level"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-signal-status-changed', signal_level)
                self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)
            else:
                self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)

        if self.cached_status_values["carrier_name"] != None :
            carrier_name = self.cached_status_values["carrier_name"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-carrier-changed', carrier_name)
                self.mcontroller.emit('dev-carrier-changed', self.dev_props["info.udi"], carrier_name)
            else:
                self.mcontroller.emit('dev-carrier-changed', self.dev_props["info.udi"], carrier_name)
           
        if self.cached_status_values["carrier_selection_mode"] != None :
            carrier_selection_mode = self.cached_status_values["carrier_selection_mode"]
            if self.__is_active_device():
                self.mcontroller.emit('active-dev-carrier-sm-status-changed', carrier_selection_mode)
                self.mcontroller.emit('dev-carrier-sm-status-changed', self.dev_props["info.udi"], carrier_selection_mode)
            else:
                self.mcontroller.emit('dev-carrier-sm-status-changed', self.dev_props["info.udi"], carrier_selection_mode)

        if self.cached_status_values["is_roaming"] != None :
            is_roaming = self.cached_status_values["is_roaming"]
            if self.__is_active_device() :
                self.mcontroller.emit('active-dev-roaming-status-changed', is_roaming)
                self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], is_roaming)
            else:
                self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], is_roaming)
                        
    def __is_active_device(self):
        if self.mcontroller.get_active_device() == self :
            return True
        else:
            return False
        
    def get_card_status(self):
        
        if not self.is_on() :
            return CARD_STATUS_OFF

        if self.cached_status_values["card_status"] == CARD_STATUS_READY :
            self.polling_flag = True
            attach = self.get_attach_state()
            self.polling_flag = False
        
            if attach == 5 :
                if self.cached_status_values["is_roaming"] != True :
                    self.cached_status_values["is_roaming"] = True
                    if self.__is_active_device() :
                        self.mcontroller.emit('active-dev-roaming-status-changed', True)
                        self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], True)
                    else:
                        self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], True)
                        
            elif attach == 1 :
                if self.cached_status_values["is_roaming"] != False :
                    self.cached_status_values["is_roaming"] = False
                    if self.__is_active_device() :
                        self.mcontroller.emit('active-dev-roaming-status-changed', False)
                        self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], False)
                    else:
                        self.mcontroller.emit('dev-roaming-status-changed', self.dev_props["info.udi"], False)
                
            else:
                return CARD_STATUS_ATTACHING
        
            return CARD_STATUS_READY

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

        if pin_status !=  PIN_STATUS_READY :
            return CARD_STATUS_ERROR

        self.polling_flag = True
        attach = self.get_attach_state()
        self.polling_flag = False
        
        if attach == 5 :
            if self.cached_status_values["is_roaming"] != True :
                self.cached_status_values["is_roaming"] = True
                self.mcontroller.emit('active-dev-roaming-status-changed', True)
        elif attach == 1 :
            if self.cached_status_values["is_roaming"] != False :
                self.cached_status_values["is_roaming"] = False
                self.mcontroller.emit('active-dev-roaming-status-changed', False)
        else:
            return CARD_STATUS_ATTACHING
        
        return CARD_STATUS_READY
            
    
    def open_device(self):
        if AT_COMM_CAPABILITY in self.capabilities :
            conf_port = self.get_property("conf-device")
            self.serial = MobileDeviceIO(conf_port, self.actions_on_open_port)
            self.serial.open()
            
            self.status_polling_timeout_id = gobject.timeout_add(5000, self.status_polling)
        
    def close_device(self):
        if AT_COMM_CAPABILITY in self.capabilities :
            if self.status_polling_timeout_id != None:
                gobject.source_remove(self.status_polling_timeout_id)
        if self.serial != None :
            self.serial.close()

    def send_at_command (self, str, attempt=5, accept_null_response=True):
        if self.serial == None :
            return
        
        self.serial.flush()
        
        try:
            self.serial.write(str + "\r")
        except:
            print "CRASH ON WRITE"
        
        tt_res = []
        while True:
            res = self.serial.readline()
            if res != None:
                if len(res.strip("\r\n")) > 0:
                    tt_res.append(res.strip("\r\n"))
                if res.startswith("OK") or res.startswith("ERROR") or res.startswith("+CME ERROR"):
                    #Remove double OK Case
                    if "OK" in tt_res:
                        tt_res_tmp = []
                        for x in tt_res :
                            if x != "OK" :
                                tt_res_tmp.append(x)
                        
                        if len(tt_res_tmp) == 1 :
                            if tt_res_tmp[0].startswith("+") :
                                tt_res_tmp = [str, tt_res_tmp[0], 'OK']
                            else:
                                tt_res_tmp.append("")
                                tt_res_tmp.append("OK")
                        elif len(tt_res_tmp)>1 :
                            tt_res_tmp.append("OK")
                        else:
                            tt_res_tmp = [str, "", "OK"]
                            
                        tt_res = tt_res_tmp
                    break
            else:
                if attempt == 0:
                    return None
                else:
                    print "reopening and resending command %s" % str
                    self.serial.reopen()
                    if  accept_null_response == False:
                        return self.send_at_command(str, attempt - 1, accept_null_response=False)
                    else:
                        return self.send_at_command(str, attempt - 1)
        
        result = [tt_res[0],tt_res[1:-1],tt_res[-1]]

        if accept_null_response == False:
            if len(result[1]) == 0 and result[0] == "OK" :
                if attempt == 0:
                    return result
                print "Reopening and resending , the response is ok but there isn't echo (%s, attempt=%s)" % (result, attempt)
                self.serial.reopen()
                return self.send_at_command(str, attempt - 1, accept_null_response=False)
        else:
            if len(result[1]) == 0 and result[0] == "OK" :            
                if result[0] != str :
                    result[0] = str
                print "Accept null response , return value %s" % result
                return result
                

        if result[0] != str :
            if attempt == 0:
                return result
            print "Reopening and resending , wrong echo command field  (%s, attempt=%s)" % (result, attempt)
            self.serial.reopen()
            if  accept_null_response == False:
                return self.send_at_command(str, attempt - 1, accept_null_response=False)
            else:
                return self.send_at_command(str, attempt - 1)
        
        return result

    def actions_on_open_port(self):
        if MobileManager.AT_COMM_CAPABILITY not in self.capabilities :
            return True
        
        self.dbg_msg ("ACTIONS ON OPEN PORT INIT --------")    

        if self.get_using_data_device() == False :
            io = MobileDeviceIO(self.get_property("data-device"))
            io.open()

            io.write("AT\r")
            self.dbg_msg ("Send to DATA PORT : AT")
            attempts = 2
            res = io.readline()
            while attempts != 0 :
                self.dbg_msg ("Recv from DATA PORT : %s" % res)

                if res == "OK" :
                    break
                elif res == None :
                    attempts = attempts - 1

                res = io.readline()

            if res != "OK" :
                io.close()
                
                io = MobileDeviceIO(self.get_property("data-device"))
                io.open()

                io.write("AT\r")
                self.dbg_msg ("Send to DATA PORT (2nd): AT")
                attempts = 2
                attempts_msg = 2
                
                res = io.readline()
                while attempts != 0 and attempts_msg != 0 :
                    self.dbg_msg ("Recv from DATA PORT (2nd) : %s" % res)

                    if res == "OK" :
                        break
                    elif res !="OK" and res != None:
                        attempts_msg = attempts_msg - 1
                    elif res == None :
                        attempts = attempts - 1

                res = io.readline()
                io.close()
                if res == None :
                    self.dbg_msg ("ACTIONS ON OPEN PORT END FAILED--------")
                    return False
                else:
                    return True

            io.close()
        
        return True

    def __at_async_handler(self, fd, condition, at_command, get_info_from_raw, func):
        print "__at_async_handler in"
        
        tt_res = [at_command]
        while True :
            res = self.serial.readline()
            gobject.main_context_default ().iteration ()
            if len(res.strip("\r\n")) > 0:
                tt_res.append(res.strip("\r\n"))
            if res.startswith("OK") or res.startswith("ERROR") or res.startswith("+CME ERROR"):
                break

        result = [tt_res[0],tt_res[1:-1],tt_res[-1]]
        func(get_info_from_raw(result))

        print "__at_async_handler out"
        self.pause_polling_necesary = False
        return False

    def send_at_command_async (self, str, get_info_from_raw, func):
        if self.serial == None :
            return

        
        self.pause_polling_necesary = True
        self.serial.flush()
        self.serial.write(str + "\r")
        at_command = self.serial.readline()
        gobject.io_add_watch(self.serial.fileno(), gobject.IO_IN, self.__at_async_handler, at_command, get_info_from_raw, func)
        

    @pin_status_required (PIN_STATUS_WAITING_PIN)
    def send_pin (self, pin):
        res = self.send_at_command('AT+CPIN="%s"' % pin)
        self.dbg_msg ("SEND PIN : %s" % res)
        try:
            if res[2] == 'OK':
                return True
            else:
                return False
        except:
            self.dbg_msg ("SEND PIN (excpt): %s" % res)
            return False

    @pin_status_required (PIN_STATUS_READY)
    def set_pin(self, old_pin, new_pin):
        res = self.send_at_command('AT+CPWD="SC", "%s", "%s"'  % (old_pin, new_pin))
        self.dbg_msg ("SET PIN : %s" % res)
        try:
            if res[2] == 'OK' :
                return True
            else:
                return False
        except:
            self.dbg_msg ("SET PIN (excpt): %s" % res)
            return False
    
    @pin_status_required (PIN_STATUS_READY)
    def set_pin_active(self, pin, active=True):
        try:
            if active == True:
                res = self.send_at_command('AT+CLCK="SC",1,"%s"' % pin)
                self.dbg_msg ("SET PIN ACTIVE TRUE : %s" % res) 
                if res[2] == 'OK':
                    emit_signal = False
                    if self.cached_status_values["is_pin_active"] != True :
                        emit_signal = True
                    self.cached_status_values["is_pin_active"] = True
                    if emit_signal == True:
                        self.mcontroller.emit('active-dev-pin-act-status-changed' , True)
                    return True
                else:
                    return False
            else:
                res = self.send_at_command('AT+CLCK="SC",0,"%s"' % pin)
                self.dbg_msg ("SET PIN ACTIVE FALSE : %s" % res) 
                if res[2] == 'OK':
                    emit_signal = False
                    if self.cached_status_values["is_pin_active"] != False :
                        emit_signal = True
                    self.cached_status_values["is_pin_active"] = False
                    if emit_signal == True:
                        self.mcontroller.emit('active-dev-pin-act-status-changed' , False)
                    return True
                else:
                    return False
        except:
            self.dbg_msg ("SET PIN ACTIVE (excpt) : %s" % res)
            return False

    @pin_status_required (PIN_STATUS_READY)
    def is_pin_active(self):
        if self.cached_status_values["is_pin_active"] != None:
            return self.cached_status_values["is_pin_active"]
        
        res = self.send_at_command('AT+CLCK="SC",2', accept_null_response=False)
        self.dbg_msg ("IS PIN ACTIVE : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CLCK:\ +(?P<active>[01])")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("active") == "1" :
                        self.cached_status_values["is_pin_active"] = True
                        return True
                    else:
                        self.cached_status_values["is_pin_active"] = False
                        return False
                else:
                    print "Response Not Mached !"
                    print "res -> (%s)" % res
                    return None
        except:
            self.dbg_msg ("IS PIN ACTIVE (except): %s" % res)
            return None
                    
    @pin_status_required (PIN_STATUS_WAITING_PUK)
    def send_puk (self, puk, pin):
        res = self.send_at_command('AT+CPIN="%s", "%s"'  % (puk, pin))
        self.dbg_msg ("SEND PUK : %s" % res)
        try:
            if res[2] == 'OK':
                return True
            else:
                return False
        except:
            self.dbg_msg ("SEND PUK (except): %s" % res)
            return False

    def pin_status(self):
        res = self.send_at_command('AT+CPIN?', accept_null_response=False)
        if res[2] == 'OK' :
            pattern = re.compile("\+CPIN: (?P<msg>.+)")
            print res
            matched_res = pattern.match(res[1][0])
            if matched_res != None :
                msg = matched_res.group("msg")
                if msg == "READY":
                    return PIN_STATUS_READY
                if msg == "SIM PIN":
                    return PIN_STATUS_WAITING_PIN
                if msg ==  "SIM PUK":
                    return PIN_STATUS_WAITING_PUK
            else:
                print "Response Not Mached !"
                print "res -> (%s)" % res
                return PIN_STATUS_NO_SIM
                
        elif res[2].startswith("+CME ERROR:"):
            if res[2].find("SIM not inserted") != -1 :
                self.dbg_msg("PIN STATUS : ERROR Sim not inserted")
                return PIN_STATUS_NO_SIM
            if res[2].find("SIM failure") != -1 :
                self.dbg_msg("PIN STATUS : ERROR Sim failure")
                return PIN_STATUS_SIM_FAILURE

        return PIN_STATUS_NO_SIM

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=0)  
    def get_signal(self):
        res = self.send_at_command('AT+CSQ', accept_null_response=False)
        self.dbg_msg ("GET SIGNAL : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile('\+CSQ:\ +(?P<signal>\d{1,2})')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    return int(matched_res.group("signal"))
                else:
                    return 0
            else:
                print "Response Not Mached !"
                print "res -> (%s)" % res
                return 0
        except:
            self.dbg_msg ("GET SIGNAL (excpt) : %s" % res)
            return 0
        
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error="NO CARRIER")
    def get_carrier(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("GET CARRIER : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile('\+COPS:\ +\d*,\d*,"(?P<carrier>.*)"')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    return matched_res.group("carrier")
                else:
                    return "NO CARRIER"
            else:
                print "Response Not Mached !"
                print "res -> (%s)" % res
                return "NO CARRIER"
        except:
            self.dbg_msg ("GET CARRIER (excpt) : %s" % res)
            return "NO CARRIER"

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=-1)
    def get_carrier_selection_mode(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("GET CARRIER SELECTION : %s" % res)
        try:
            if res[2] == 'OK' :
                pattern = re.compile('\+COPS:\ +(?P<mode>\d*),')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    return int(matched_res.group("mode"))
                else:
                    return -1
            else:
                print "Response Not Mached !"
                print "res -> (%s)" % res
                return -1  
        except:
            self.dbg_msg ("GET CARRIER SELECTION (except): %s" % res)
            return -1

    def is_on(self):
        if self.card_is_on != None :
            return self.card_is_on
        
        res = self.send_at_command('AT+CFUN?', accept_null_response=False)
        self.dbg_msg ("IS ON : %s" % res)

        try:
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
        except:
            self.dbg_msg ("IS ON (except): %s" % res)
            return False

    def turn_on(self):        
        res = self.send_at_command('AT+CFUN=1')
        self.dbg_msg ("TURN ON : %s" % res)
        try:
            if res[2] == 'OK':
                self.card_is_on = True
                return True
            else:
                return False
        except:
            self.dbg_msg ("TURN ON (except): %s" % res)
            return False
        
    def turn_off(self):
        if MobileManager.AT_COMM_CAPABILITY not in self.capabilities:
            return True
        
        res = self.send_at_command('AT+CFUN=0')
        self.dbg_msg ("TURN OFF : %s" % res)
        try:
            if res[2] == 'OK':
                self.card_is_on = False
                card_status = CARD_STATUS_OFF
                signal_level = 99
                self.cached_status_values["card_status"] = CARD_STATUS_OFF
                if self.__is_active_device():
                    self.mcontroller.emit('active-dev-card-status-changed', card_status)
                    self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)
                    self.mcontroller.emit('active-dev-signal-status-changed', signal_level)
                    self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)
                else:
                    self.mcontroller.emit('dev-card-status-changed', self.dev_props["info.udi"], card_status)
                    self.mcontroller.emit('dev-signal-status-changed', self.dev_props["info.udi"], signal_level)

                self.cached_status_values = { "card_status" : None,
                                              "tech" : None,
                                              "mode" : None,
                                              "domain" : None,
                                              "signal_level" : None,
                                              "is_pin_active" : None,
                                              "is_roaming" : None,
                                              "carrier_name" : None,
                                              "carrier_selection_mode" : None}
                return True
            else:
                return False
        except:
            self.dbg_msg ("TURN OFF (except) : %s" % res)
            return False

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

                pattern = re.compile('\+COPS:\ +(?P<carrier_selection_mode>\d*),(?P<carrier_format>\d*),"(?P<carrier>.*)"')
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
        
    def get_mode_domain(self):
        card_mode = None
        card_domain = None

        return card_mode, card_domain

    def set_mode_domain(self, mode, domain):  
        m = int(mode)
        d = int(domain)
        
        self.dbg_msg ("EMITING SINGNALS MODE-DOMAIN (%s,%s)" % (m, d))
        self.cached_status_values["domain"] = d
        if self.__is_active_device():
            self.mcontroller.emit('active-dev-domain-status-changed', d)
            self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], d)
        else:
            self.mcontroller.emit('dev-domain-status-changed', self.dev_props["info.udi"], d)
                 
        self.cached_status_values["mode"] = m
        if self.__is_active_device():
            self.mcontroller.emit('active-dev-mode-status-changed', m)
            self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], m)
        else:
            self.mcontroller.emit('dev-mode-status-changed', self.dev_props["info.udi"], m)
        
        return True

    def get_card_info(self):
        res = self.send_at_command('ATI')
        self.dbg_msg ("GET CARD INFO : %s" % res)
        try:
            if res[2] == 'OK' :
                return res[1]
            else:
                return []
        except:
            self.dbg_msg ("GET CARD INFO (except): %s" % res)
            return []

    def get_carrier_list_from_raw(self, raw) :
        print "__get_carrier_list_from_raw in"
        try:
            if raw[2] == 'OK':
                pattern = re.compile("\+COPS:\ +(?P<list>.*),,(?P<supported_modes>\(.*\)),(?P<supported_formats>\(.*\))")
                matched_res = pattern.match(raw[1][0])
                if matched_res != None :
                    exec ('dict = {"carrier_list" : [%s] , "supported_modes" : %s, "supported_formats" : %s}'
                          % (matched_res.group("list"), matched_res.group("supported_modes"), matched_res.group("supported_formats")))
                    print "__get_carrier_list_from_raw out"
                    return dict
                else:
                    return None
            else:
                return None
        except:
            return None

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=None)
    def get_carrier_list(self, func):
        self.send_at_command_async('AT+COPS=?', self.get_carrier_list_from_raw, func)

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def set_carrier(self, carrier_id, tech):
        res = self.send_at_command('AT+COPS=1,2,"%s",%s' % ( carrier_id, tech ))
        self.dbg_msg ("SET CARRIER : %s" % res)
        res2 = self.send_at_command('AT+COPS=3,0')
        self.dbg_msg ("SET CARRIER 2 : %s" % res2)

        try:
            if res == None:
                return False

            if res[2] != 'OK' :
                return False
            else:
                return True
        except:
            return False

    def get_ussd_cmd_handler(self, fd, condition, at_command, func):
        self.dbg_msg("__get_ussd_cmd_hadler in")
        tt_res = [at_command]

        attempts = 2
        
        while True :
            res = self.serial.readline()
            print "ussd ----> %s\n" % res
            gobject.main_context_default ().iteration()

            if res == None :
                if attempts == 0 :
                    tt_res.append("No service available")
                    tt_res.append("OK")
                    break
                attempts = attempts - 1
                continue
            
            if len(res.strip("\r\n")) > 0:
                if res.startswith("+CUSD:"):
                    pattern = re.compile(".*,+(?P<value>.*),")
                    try:
                        matched_res = pattern.match(res)
                        value = matched_res.group("value")
                        tt_res.append(value.strip('"'))
                    except:
                        tt_res.append("Service error")
                    tt_res.append("OK")
                    break
                else:
                    continue
            else:
                continue
        
        result = [tt_res[0],tt_res[1:-1],tt_res[-1]]
        func(result)

        self.dbg_msg("__get_ussd_cmd_hadler out")
        self.pause_polling_necesary = False
        return False

    def get_ussd_cmd_handler_gsm7(self, fd, condition, at_command, func):
        self.dbg_msg("__get_ussd_cmd_hadler_gsm7 in")
        tt_res = [at_command]

        attempts = 2
        
        while True :
            res = self.serial.readline()
            print "ussd ----> %s\n" % res
            gobject.main_context_default ().iteration()

            if res == None :
                if attempts == 0 :
                    tt_res.append("No service available")
                    tt_res.append("OK")
                    break
                attempts = attempts - 1
                continue
            
            if len(res.strip("\r\n")) > 0:
                if res.startswith("+CUSD:"):
                    pattern = re.compile(".*,+(?P<value>.*),")
                    try:
                        matched_res = pattern.match(res)
                        value = matched_res.group("value")
                        tt_res.append(self.from_gsm7(value.strip('"')))
                    except:
                        tt_res.append("Service error")

                    tt_res.append("OK")
                    break
                else:
                    continue
            else:
                continue
        
        result = [tt_res[0],tt_res[1:-1],tt_res[-1]]
        func(result)

        self.dbg_msg("__get_ussd_cmd_hadler_gsm7 out")
        self.pause_polling_necesary = False
        return False

    def get_ussd_cmd(self, cmd, func):
        ussd_cmd = 'AT+CUSD=1,"%s",15' % cmd
        res = self.send_at_command(ussd_cmd)
        self.dbg_msg ("GET USSD : %s" % res)
        
        if res[2] == 'OK':
            self.pause_polling_necesary = True
            self.serial.flush()
            gobject.io_add_watch(self.serial.fileno(), gobject.IO_IN,
                                 self.get_ussd_cmd_handler,  ussd_cmd, func)
        else:
            ussd_cmd = 'AT+CUSD=1,"%s",15' % self.to_gsm7(cmd)
            res = self.send_at_command(ussd_cmd)
            self.dbg_msg ("GET USSD : %s" % res)
            
            if res[2] == 'OK':
                self.pause_polling_necesary = True
                self.serial.flush()
                gobject.io_add_watch(self.serial.fileno(), gobject.IO_IN,
                                     self.get_ussd_cmd_handler_gsm7,  ussd_cmd, func)
            else:
                func([ussd_cmd,[], "ERROR"])

    def to_gsm7(self, message):
        import MobileManager.messaging.gsm0338
        pdu = ""
        txt = message.encode("gsm0338")

        tl = len(txt)
        txt += '\x00'
        msgl = len(txt) * 7 / 8
        op = [-1] * msgl
        c = shift = 0

        for n in range(msgl):
            if shift == 6:
                c += 1

            shift = n % 7
            lb = ord(txt[c]) >> shift
            hb = (ord(txt[c+1]) << (7-shift) & 255)
            op[n] = lb + hb
            c += 1
        pdu = ''.join([chr(x) for x in op])
        ret_pdu = ''.join(["%02x" % ord(n) for n in pdu])
        return ret_pdu

    def from_gsm7(self, message, limit=0x00):
        import MobileManager.messaging.gsm0338

        count = last = 0
        result = []

        for i in range(0, len(message), 2):
            byte = int(message[i:i+2], 16)
            mask = 0x7F >> count
            out = ((byte & mask) << count) + last
            last = byte >> (7 - count)
            result.append(chr(out))

            if limit and (len(result) >= limit):
                break

            if count == 6:
                result.append(chr(last))
                last = 0

            count = (count + 1) % 7

        return ''.join(result)

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error="")
    def get_msisdn(self):
        res = self.send_at_command('AT+CSIM=18,"00A40804047F106F40"', accept_null_response=False)
        
        self.dbg_msg ("LOOKING MSISDN FILE : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile('\+CSIM:.*4,\"(?P<file>.+)\"')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("file").startswith("61") or matched_res.group("file") == "9000" :
                        res2 = self.send_at_command('AT+CSIM=10,"00B2010400"', accept_null_response=False)
                        self.dbg_msg ("LOOKING THE MSISDN REG : %s" % res2)
                        try:
                            if res2[2] == 'OK':
                                pattern = re.compile('\+CSIM:.*,\"(?P<file>.+)\"')
                                self.dbg_msg("LOOKING TYPE IN MSISDN FILE (step 2) : %s" % res2)
                                matched_res = pattern.match(res2[1][0])
                                if matched_res != None:
                                    response = matched_res.group("file")
                                    code = '70' + response.split("70",1)[1][:10]
                                    ret = ''
                                    for i in [1,0,3,2,5,4,7,6,9,8,11] :
                                        ret = ret + str(code[i])
                                    return ret
                                else:
                                    self.dbg_msg ("LOOKING TYPE IN MSISDN FILE (not msisdn): %s" % res2)
                                    return ""
                            else:
                                self.dbg_msg (" LOOKING THE MSISDN REG (not msisdn) : %s" % res)
                                return ""
                        except:
                            self.dbg_msg ("LOOKING THE MSISDN REG (except): %s" % res2)
                            return ""
                            
                    else:
                        self.dbg_msg ("LOOKING MSISDN FILE (not file) : %s" % res)
                        return ""
            else:
                self.dbg_msg ("LOOKING MSISDN FILE (error) : %s" % res)
                return ""
        except:
            self.dbg_msg ("GET MSISDN (except) : %s" % res)
            return ""


    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def set_carrier_auto_selection(self):
        res = self.send_at_command('AT+COPS=0')
        print res
        try:
            if res[2] == "OK":
                return True
            else:
                return False
        except:
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_carrier_auto(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("IS CARRIER AUTO ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+COPS:\ +(?P<mode>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("mode") == "0" :
                        return True
                    else:
                        return False
            return False
        except:
            return False

    def get_attach_info_by_cgreg(self):
        res = self.send_at_command('AT+CGREG?', accept_null_response=False)
        self.dbg_msg ("CGREG INFO : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CGREG:.*,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "1" or  matched_res.group("state") == "5":
                        return int(matched_res.group("state"))
                    else:
                        return 0
                else:
                    return 0
            else:
                return 0
        except:
            self.dbg_msg ("CGREG INFO (except): %s" % res)
            return 0
    
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_attached(self):
        res = self.send_at_command('AT+CREG?', accept_null_response=False)
        self.dbg_msg ("IS ATTACHED ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CREG:.*,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "1" or  matched_res.group("state") == "5":
                        return True
                    else:
                        ret = self.get_attach_info_by_cgreg()
                        if ret == 1 or ret == 5 :
                            return True
                        return False
                else:
                    ret = self.get_attach_info_by_cgreg()
                    if ret == 1 or ret == 5 :
                        return True
                    return False
            else:
                ret = self.get_attach_info_by_cgreg()
                if ret == 1 or ret == 5 :
                    return True
                return False
        except:
            self.dbg_msg ("IS ATTACHED ? (except): %s" % res)
            ret = self.get_attach_info_by_cgreg()
            if ret == 1 or ret == 5 :
                return True
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=0)
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
                        return self.get_attach_info_by_cgreg()
                else:
                    return self.get_attach_info_by_cgreg()
            else:
                return self.get_attach_info_by_cgreg()
        except:
            self.dbg_msg ("GET ATTACH STATE (except): %s" % res)
            return self.get_attach_info_by_cgreg()

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_roaming(self):
        res = self.send_at_command('AT+CREG?',  accept_null_response=False)
        self.dbg_msg ("IS ROAMING ? : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CREG:.*,(?P<state>\d+)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("state") == "5" :
                        return True
                    else:
                        ret = self.get_attach_info_by_cgreg()
                        if ret == 5 :
                            return True
                        return False
                else:
                    ret = self.get_attach_info_by_cgreg()
                    if ret == 5 :
                        return True
                    return False
            else:
                ret = self.get_attach_info_by_cgreg()
                if ret == 5 :
                    return True
                return False
        except:
            self.dbg_msg ("IS ROAMING ? (excepet): %s" % res)
            ret = self.get_attach_info_by_cgreg()
            if ret == 5 :
                return True
            return False
    
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=None)
    def get_x_zone(self):
        if self.x_zone_support == False:
            return None
        elif self.x_zone_support == None:
            res = self.send_at_command('AT+CRSM=176,28472,0,0,5',  accept_null_response=False)
            self.dbg_msg ("GET X ZONE : %s" % res)
            if res[2] != 'OK' :
                self.x_zone_support = False
                return None
            
            if res[2] == 'OK':
                pattern = re.compile('\+CRSM:.*"(?P<code>.*)"')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    code = matched_res.group("code")
                    bin_code = hex2bin(code)
                    if bin_code.startswith("11111111") :
                        if bin_code.endswith("00111100"):
                            self.x_zone_support = False
                            return None
                        else:
                            self.x_zone_support = True
                            res_zone = self.send_at_command('AT+CRSM=176,28486,0,0,17', accept_null_response=False)
                            self.dbg_msg ("GET X ZONE : %s" % res_zone)
                            if res_zone[2] == 'OK':
                                 zone_pattern = re.compile('\+CRSM:.*"(?P<code>.*)"')
                                 zone_matched_res = zone_pattern.match(res_zone[1][0])
                                 if zone_matched_res != None:
                                     code = zone_matched_res.group("code")
                                     code = code[2:]
                                     while True:
                                         if code[-2:] == "FF":
                                             code = code[:-2]
                                             if code == "":
                                                 return None
                                         else:
                                             return code
                            else:
                                return None
                            
                    elif bin_code.startswith("10011110") :
                        if bin_code[16:24] == "00011001" :
                            self.x_zone_support = False
                            return None
                        else:
                            self.x_zone_support = True
                            res_zone = self.send_at_command('AT+CRSM=176,28486,0,0,17', accept_null_response=False)
                            self.dbg_msg ("GET X ZONE : %s" % res_zone)
                            if res_zone[2] == 'OK':
                                 zone_pattern = re.compile('\+CRSM:.*"(?P<code>.*)"')
                                 zone_matched_res = zone_pattern.match(res_zone[1][0])
                                 if zone_matched_res != None:
                                     code = zone_matched_res.group("code")
                                     code = code[2:]
                                     while True:
                                         if code[-2:] == "FF":
                                             code = code[:-2]
                                             if code == "":
                                                 return None
                                         else:
                                             return code
                            else:
                                return None
                    else:
                        return None
                else:
                    return None
        else:
            res_zone = self.send_at_command('AT+CRSM=176,28486,0,0,17',  accept_null_response=False)
            self.dbg_msg ("GET X ZONE : %s" % res_zone)
            if res_zone[2] == 'OK':
                zone_pattern = re.compile('\+CRSM:.*"(?P<code>.*)"')
                zone_matched_res = zone_pattern.match(res_zone[1][0])
                if zone_matched_res != None:
                    code = zone_matched_res.group("code")
                    code = code[2:]
                    while True:
                        if code[-2:] == "FF":
                            code = code[:-2]
                            if code == "":
                                return None
                        else:
                            return code
                else:
                    return None
            else:
                return None

        return None

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=None)
    def get_sim_id(self):
        if self.sim_id != None :
            self.dbg_msg ("SIM ID (cached) : %s" % self.sim_id)
            return self.sim_id

        res = self.send_at_command('AT+CIMI')
        self.dbg_msg ("GET SIM ID : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile('\+CIMI:\ +(?P<cimi>.+)')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    cimi = matched_res.group("cimi")
                    self.dbg_msg ("* SIM ID : %s" % cimi)
                    return cimi
                else:
                    pattern = re.compile('^(?P<cimi>\d+)$')
                    matched_res = pattern.match(res[1][0])
                    if matched_res != None:
                        cimi = matched_res.group("cimi")
                        self.dbg_msg ("* SIM ID : %s" % cimi)
                        return cimi
                    else:
                        return None
            else:
                return None
        except:
            self.dbg_msg ("SMS SIM ID (except): %s" % res)
            return None

    def verify_concat_sms_spool(self):
        self.dbg_msg("VERIFING CONCAT SPOOL")
        if self.sim_id == None :
            return

        tmp_sms_spool = os.path.join("/var", "spool/", "MobileManager/", self.sim_id, ".tmp/")
        sms_list = os.listdir(tmp_sms_spool)

        for sms_dir in sms_list :
            self.dbg_msg("* Verifing sms_id (%s)" % sms_dir)
            sms_item_list = os.listdir(os.path.join(tmp_sms_spool, sms_dir))
            item_completed = True
            
            for item in sms_item_list :
                statinfo = os.stat(os.path.join(tmp_sms_spool, sms_dir, item))
                if statinfo.st_size == 0 :
                    item_completed = False
                    break
            
            if item_completed == False:
                self.dbg_msg("* sms_id (%s) Not completed , waiting for more parts" % sms_dir)
                st_info = os.stat(os.path.join(tmp_sms_spool, sms_dir))
                if time.time() - st_info.st_ctime > 24*60*60 :
                    self.dbg_msg("* Removed : %s" % os.path.join(tmp_sms_spool, sms_dir))
                    os.system("rm -fr %s" % os.path.join(tmp_sms_spool, sms_dir))
                    
                continue
            else:
                self.dbg_msg("* sms_id (%s) completed" % sms_dir)
                sms_spool_path = os.path.join("/var", "spool/", "MobileManager/", self.sim_id)
                sms_files = os.listdir(sms_spool_path + "/received")
                ids = []
                
                for sms_id in sms_files:
                    try:
                        i = int(sms_id)
                        ids.append(i)
                    except:
                        self.dbg_msg ("wrong sms filename")
                
                ids.sort()
                last_id = 0
                
                if len(ids) > 0:
                    last_id = ids[-1]

                
                concat_sms_list = os.listdir(os.path.join(tmp_sms_spool, sms_dir))
                concat_ids = []
                
                for csms_id in concat_sms_list:
                    try:
                        i = int(csms_id)
                        concat_ids.append(i)
                    except:
                        self.dbg_msg ("wrong concat sms filename")
                
                concat_ids.sort()
                concat_sms_sorted_paths = ""

                for csms_id in concat_ids:
                    concat_sms_sorted_paths = concat_sms_sorted_paths + os.path.join(tmp_sms_spool, sms_dir, str(csms_id)) + " "
                    os.system("cp %s %s" % (os.path.join(tmp_sms_spool, sms_dir, str(csms_id)),
                                            os.path.join("/tmp", os.path.basename(os.path.join(tmp_sms_spool, sms_dir, str(csms_id))))))

                new_id = last_id + 1
                
                self.dbg_msg("* Coping data to received id (%s)" % new_id)
                os.system("cat %s > %s" % (concat_sms_sorted_paths,
                                             os.path.join(sms_spool_path,"received",str(new_id))))
                
                self.dbg_msg("* Removing concat sms (%s)" % sms_dir)
                os.system("rm -fr %s" % os.path.join(tmp_sms_spool, sms_dir))

                if self.__is_active_device() :
                    self.mcontroller.emit('active-dev-sms-received', new_id)
                self.mcontroller.emit('dev-sms-received', self.dev_props["info.udi"], new_id)

        self.dbg_msg("VERIFING CONCAT SPOOL END")


    def get_unread_smss(self):
        res = self.send_at_command('AT+CMGL=0')
        self.dbg_msg("* GET UNREAD SMS : %s" % res)
        return res

    def sms_poll(self):
        self.dbg_msg("SMS POOL")
        
        if self.sim_id == None :
            sim_id = self.get_sim_id()
            if sim_id != None:
                self.sim_id = sim_id
            else:
                return

        sms_spool_path = os.path.join("/var", "spool/", "MobileManager/", self.sim_id)
        self.dbg_msg( "* spool path = %s" % sms_spool_path)

        if os.path.exists(sms_spool_path) == False :
            os.system ("mkdir -p %s" % sms_spool_path)

        if os.path.exists(sms_spool_path + "/sended" ) == False :
            os.system ("mkdir -p %s" % sms_spool_path + "/sended")

        if os.path.exists(sms_spool_path + "/received" ) == False :
            os.system ("mkdir -p %s" % sms_spool_path + "/received")

        if os.path.exists(sms_spool_path + "/draft" ) == False :
            os.system ("mkdir -p %s" % sms_spool_path + "/draft")

        if os.path.exists(sms_spool_path + "/.tmp" ) == False :
            os.system ("mkdir -p %s" % sms_spool_path + "/.tmp")


        res = self.send_at_command('AT+CPMS="SM","SM","SM"')
        self.dbg_msg ("* SMS READ MODE : %s" % res)
        try:
            if res[2] != 'OK':
                return
        except:
            self.dbg_msg ("* SMS READ MODE (except): %s" % res)
            return

        res = self.send_at_command('AT+CMGF=0')
        self.dbg_msg ("* SMS PDU MODE : %s" % res)
        try:
            if res[2] != 'OK':
                return
        except:
            self.dbg_msg ("* SMS PDU MODE (except): %s" % res)
            return

        res = self.get_unread_smss()
        try:
            if res[2] != 'OK':
                return
            else:
                
                if len(res[1]) == 1 :
                    self.dbg_msg("SMS POOL END")
                    return
                
                sms_files = os.listdir(sms_spool_path + "/received")
                ids = []
                
                for sms_id in sms_files:
                    try:
                        i = int(sms_id)
                        ids.append(i)
                    except:
                        self.dbg_msg ("wrong sms filename")
                
                ids.sort()
                last_id = 0
                
                if len(ids) > 0:
                    last_id = ids[-1]

                for i in range(0, len(res[1]), 2) :
                    pattern = re.compile("\+CMGL:.*(?P<id>\d+),")
                    matched_res = pattern.match(res[1][i])
                    if matched_res != None:
                        sms_id = matched_res.group("id")
                        
                        try:
                            sms_decoded = self.pdu.decode_pdu(res[1][i+1])
                            print "~~~~~~~~~~~~~~~~~~~~"
                            print sms_decoded
                            print "~~~~~~~~~~~~~~~~~~~~"
                            
                            if sms_decoded[5] == 0:
                                new_id = last_id + 1
                                sms_fd = codecs.open(sms_spool_path + "/received/" + str(new_id), "w", encoding="utf-8")

                                sms_fd.write("0|%s|%s|%s\n%s" %
                                             (sms_decoded[0],
                                              sms_decoded[3],
                                              sms_decoded[1],
                                              sms_decoded[2]))

                                sms_fd.close()
                                self.sms_delete(sms_id)
                                self.dbg_msg("* Saved sms (%s)" % new_id)
                                if self.__is_active_device() :
                                    self.mcontroller.emit('active-dev-sms-received', new_id)
                                self.mcontroller.emit('dev-sms-received', self.dev_props["info.udi"], new_id)
                                last_id = last_id + 1
                            else:
                                if os.path.exists(sms_spool_path + "/.tmp/" + str(sms_decoded[4])) == False:
                                    print "* creating dir %s" % sms_spool_path + "/.tmp/" + str(sms_decoded[4])
                                    os.system ("mkdir -p %s" % sms_spool_path + "/.tmp/" + str(sms_decoded[4]))
                                for i in range(1, sms_decoded[5] + 1) :
                                    print "* touching %s" % sms_spool_path + "/.tmp/" + str(sms_decoded[4]) + "/" + str(i)
                                    os.system ("touch %s" % sms_spool_path + "/.tmp/"
                                               + str(sms_decoded[4]) + "/"
                                               + str(i))

                                sms_fd = codecs.open(sms_spool_path + "/.tmp/"
                                              + str(sms_decoded[4]) + "/"
                                              + str(sms_decoded[6])
                                              , "w", encoding="utf-8")
                                
                                if sms_decoded[6] == 1 :
                                    sms_fd.write("0|%s|%s|%s\n%s" %
                                                 (sms_decoded[0],
                                                  sms_decoded[3],
                                                  sms_decoded[1],
                                                  sms_decoded[2]))
                                else:
                                    sms_fd.write(sms_decoded[2])

                                sms_fd.close()
                                self.sms_delete(sms_id)
                                
                        except:
                            self.dbg_msg ("* WRONG SMS DECODE")
                    else:
                        self.dbg_msg ("* WRONG SMS")
                    
        except:
            self.dbg_msg ("* GET UNREAD SMS (except): %s" % res)
            return
        
        self.dbg_msg("SMS POOL END")
        
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_delete(self, index):
        res = self.send_at_command('AT+CMGD=%s' % index)
        self.dbg_msg ("SMS DELETE : %s" % res)
        try:
            if res[2] == 'OK':
                return True
            else:
                return False
        except:
            self.dbg_msg ("SMS DELETE (except): %s" % res)
            return False       

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=[])
    def sms_list_spool(self, spoolname):
        if self.sim_id == None:
            return []
        
        spool_path = os.path.join("/var", "spool/",
                                       "MobileManager/", self.sim_id,
                                       spoolname)
        sms_files = os.listdir(spool_path)
        if len(sms_files) == 0 :
            return []

        ids = []
        for sms_id in sms_files:
            try:
                i = int(sms_id)
                ids.append(i)
            except:
                self.dbg_msg ("wrong sms filename")
        ids.sort()

        ret = []
        
        for sms_id in ids:
            fd = codecs.open(os.path.join(spool_path,str(sms_id)), "r", encoding="utf-8")
            header = fd.readline()
            header = header.strip("\n")
            header = header.split("|")
            fd.close()
            ret.append([sms_id, int(header[0]), header[1],
                        time.mktime(time.strptime(header[3],"%y/%m/%d %H:%M:%S"))])

        return ret

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=(0,1,"",0,""))
    def sms_get_spool_item(self, spoolname, index):
        if self.sim_id == None:
            return 0, 1, "", 0, ""
        
        spool_path = os.path.join("/var", "spool/",
                                       "MobileManager/", self.sim_id,
                                       spoolname,str(index))

        if os.path.exists(spool_path) :
            fd = codecs.open(os.path.join(spool_path), "r", encoding="utf-8")
            header = fd.readline()
            header = header.strip("\n")
            header = header.split("|")
            print header
            sms_text = ""
            for line in fd:
                sms_text = sms_text + line
                
            fd.close()
            sms_time = time.mktime(time.strptime(header[3], "%y/%m/%d %H:%M:%S"))

            return index, int(header[0]), header[1], sms_time, sms_text
        else:
            return 0, 1, "", 0, ""

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_mark_item(self, spoolname, index, readed):
        if self.sim_id == None:
            return False
        
        spool_path = os.path.join("/var", "spool/",
                                  "MobileManager/", self.sim_id,
                                  spoolname,str(index))

        if os.path.exists(spool_path) :
            fd = codecs.open(os.path.join(spool_path), "r", encoding="utf-8")
            lines = fd.readlines()
            lines[0] = str(int(readed)) + lines[0][1:-1]
            fd.close()
            os.system("rm %s" % os.path.join(spool_path))
            
            fd = codecs.open(os.path.join(spool_path), "w", encoding="utf-8")
            num_lines = len(lines)
            count_lines = 0
            for line in lines:
                count_lines = count_lines + 1
                if count_lines == num_lines:
                    fd.write(line)
                else:
                    fd.write(line + "\n")
            fd.close()

            spool_id=None
            if spoolname == "received" :
                spool_id = 0
            elif spoolname == "sended" :
                spool_id = 1
            else:
                spool_id = 2
            
            if self.__is_active_device() :
                self.mcontroller.emit('active-dev-sms-spool-changed', spool_id)
            self.mcontroller.emit('dev-sms-spool-changed', self.dev_props["info.udi"], spool_id)
            
            return True
        else:
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_delete_spool_item(self, spoolname, index):
        if self.sim_id == None:
            return False
        
        spool_path = os.path.join("/var", "spool/",
                                  "MobileManager/", self.sim_id,
                                  spoolname,str(index))

        if os.path.exists(spool_path):
            os.system("rm %s" % os.path.join(spool_path))
            spool_id=None
            if spoolname == "received" :
                spool_id = 0
            elif spoolname == "sended" :
                spool_id = 1
            else:
                spool_id = 2
            
            if self.__is_active_device() :
                self.mcontroller.emit('active-dev-sms-spool-changed', spool_id)
            self.mcontroller.emit('dev-sms-spool-changed', self.dev_props["info.udi"], spool_id)
            return True
        else:
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_set_spool_item(self, spoolname, number, text):
        if self.sim_id == None:
            return False
        
        spool_path = os.path.join("/var", "spool/",
                                  "MobileManager/", self.sim_id,
                                  spoolname)

        sms_files = os.listdir(spool_path)

        ids = []    
        for sms_id in sms_files:
            try:
                i = int(sms_id)
                ids.append(i)
            except:
                self.dbg_msg ("wrong sms filename")

        ids.sort()
        last_id = 0

        if len(ids) > 0:
            last_id = ids[-1]

        new_id = last_id + 1
        fd = codecs.open(spool_path + "/" + str(new_id), "w", encoding="utf-8")
        fd.write("1|%s|0|%s\n" % (number, time.strftime("%y/%m/%d %H:%M:%S", time.localtime())))
        fd.write(text)
        fd.close()
        spool_id=None
        if spoolname == "received" :
            spool_id = 0
        elif spoolname == "sended" :
            spool_id = 1
        else:
            spool_id = 2
            
        if self.__is_active_device() :
            self.mcontroller.emit('active-dev-sms-spool-changed', spool_id)
        self.mcontroller.emit('dev-sms-spool-changed', self.dev_props["info.udi"], spool_id)
        
        return True

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_edit_draft(self, index, number, text):
        if self.sim_id == None:
            return False
        
        spool_path = os.path.join("/var", "spool/",
                                  "MobileManager/", self.sim_id,
                                  "draft",str(index))

        if os.path.exists(spool_path) :
            os.system("rm %s" % os.path.join(spool_path))
            fd = codecs.open(os.path.join(spool_path), "w", encoding="utf-8")
            fd.write("0|%s|0|%s\n" % (number, time.strftime("%y/%m/%d %H:%M:%S", time.localtime())))
            fd.write(text)
            fd.close()
            
            spool_id=2            
            if self.__is_active_device() :
                self.mcontroller.emit('active-dev-sms-spool-changed', spool_id)
            self.mcontroller.emit('dev-sms-spool-changed', self.dev_props["info.udi"], spool_id)
            return True
        else:
            return False
        

    def sms_get_smsc (self):
        return self.get_property("smsc-number")

    
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_send(self, number, smsc, text, request_status=False):
        init_time = time.time()
        sms_list = self.pdu.encode_pdu(number, text, smsc, request_status)

        # Set PDU MODE
        res = self.send_at_command('AT+CMGF=0', accept_null_response=False)
        self.dbg_msg ("SET PDU MODE : %s" % res)
        try:
            if res[2] != 'OK':
                return False
        except:
            self.dbg_msg ("SET PDU MODE (excpt): %s" % res)
            return False

        # Send Message
        if self.__send_sms_at_commands(sms_list) == True:
            self.sms_set_spool_item("sended", number, text)
            end_time = time.time()
            self.dbg_msg("SMS TIME : %s" % (init_time - end_time))
            return True
        else:
            return False


    def send_at_pdu_command_to_device(self, sms):
        self.serial.flush()
        self.serial.write("AT+CMGS=" + str(sms[0]) + "\r")
        self.serial.readline()

    def __send_pdu_to_device(self, sms) :
        self.send_at_pdu_command_to_device(sms)
        
        c = ""
        while c != ">":
            c = self.serial.read_c()
            if c == "" :
                self.dbg_msg("__send_sms_at_commands error")
                return False
        self.serial.read_c()
        
        pdu_to_send = sms[1] + chr(26)
        
        time.sleep(1)
        
        for pdu_c in pdu_to_send :
            self.serial.write(pdu_c)
            r_pdu_c = self.serial.read_c()
            
            if r_pdu_c == "\r" :
                self.dbg_msg("PDU sended")
                break
                
            if r_pdu_c != pdu_c :
                self.dbg_msg("ups !!! r_pdu_c (%s) != pdu_c (%s)" % (ord(r_pdu_c),ord(pdu_c)))
            else:
                #print "char[%s]=%s" % (i, pdu_c)
                #i = i + 1
                pass

    def __send_sms_at_commands(self, sms_list):
        if self.serial == None :
            return False
        
        self.serial.flush()

        for sms in sms_list:
            resend_attepts = 3
            timeout = 5 

            self.__send_pdu_to_device(sms)
            
            while True :
                if resend_attepts == 0 :
                    self.dbg_msg("PDU -> ERROR")
                    self.dbg_msg("PDU NO MORE TRIES")
                    return False
                
                if timeout == 0 :
                    self.dbg_msg("PDU -> TIMEOUT")
                    return False
                    
                ret = self.serial.readline()
                if ret == None:
                    self.dbg_msg("PDU -> TIMEOUT (retry in 0.3s)")
                    time.sleep(0.3)
                    timeout = timeout - 1
                    continue
                
                if "OK" in ret :
                    self.dbg_msg("PDU -> OK")
                    break
                elif "ERROR" in ret:
                    self.dbg_msg("PDU -> ERROR")
                    self.dbg_msg("PDU SLEEP")
                    time.sleep(3)
                    self.serial.flush()
                    self.dbg_msg("PDU RESEND ")
                    resend_attepts = resend_attepts - 1
                    self.__send_pdu_to_device(pdu_to_send)
                    self.dbg_msg("PDU RESENDED ")
                    continue
                
            self.dbg_msg("PDU SLEEP")
            time.sleep(1)

        return True
    
    def sms_set_smsc(self, smsc):
        self.set_property("smsc-number", smsc)

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def sms_ab_add(self, name, number):
        item_type = None
        if number.startswith("+") :
            item_type = 145
        else:
            item_type = 129
        
        res = self.send_at_command('AT+CPBW=,"%s",%s,"%s"' % (number, item_type, name)
                                   , accept_null_response=False)
        self.dbg_msg ("ADD ITEM TO BOOKMARK : %s" % res)
        try:
            if res[2] == 'OK':
                return True
            else:
                return False
        except:
            self.dbg_msg ("ADD ITEM TO BOOKMARK (excpt): %s" % res)
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)   
    def sms_ab_del(self, index):
        res = self.send_at_command('AT+CPBW=%s' % index
                                   , accept_null_response=False)
        self.dbg_msg ("DEL BOOKMARK ITEM : %s" % res)
        try:
            if res[2] == 'OK':
                return True
            else:
                return False
        except:
            self.dbg_msg ("DEL BOOKMARK ITEM (excpt): %s" % res)
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=[])   
    def sms_ab_find(self, pattern):
        res = self.send_at_command('AT+CPBF="%s"' % pattern
                                   , accept_null_response=False)
        self.dbg_msg ("FIND BOOKMARK ITEM : %s" % res)
        try:
            if res[2] == 'OK':
                ab_list = []
                for item in res[1]:
                    pattern =  re.compile("\+CPBF:.*(?P<id>\d+),\"(?P<number>.+)\",(?P<i_type>\d+),\"(?P<name>.+)\"")
                    matched_res = pattern.match(item)
                    if matched_res != None:
                        cid = matched_res.group("id")
                        name = matched_res.group("name")
                        number = matched_res.group("number")
                        ab_list.append([cid, name, number])
                    else:
                        self.dbg_msg ("FIND ADDRESSBOOK LIST (not matched): %s" % res)
                    
                return ab_list
            else:
                return []
        except:
            self.dbg_msg ("FIND BOOKMARK ITEM (excpt): %s" % res)
            return []
        
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=(0, "", ""))   
    def sms_ab_get(self, index):
        res = self.send_at_command('AT+CPBR=%s' % index
                                   , accept_null_response=False)
        self.dbg_msg ("GET BOOKMARK ITEM : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CPBR:.*(?P<id>\d+),\"(?P<number>.+)\",(?P<i_type>\d+),\"(?P<name>.+)\"")
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    i_type = matched_res.group("i_type")
                    name = matched_res.group("name")
                    number = matched_res.group("number")
                    
                    name = name.decode("latin-1")
                    return int(i_type), name, number
                else:
                    self.dbg_msg ("GET BOOKMARK ITEM (not matched): %s" % res)
                    return 0, "", ""
            else:
                return 0, "", ""
        except:
            self.dbg_msg ("GET BOOKMARK ITEM (excpt): %s" % res)
            return 0, "", ""

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=0)
    def sms_ab_get_size(self):
        try:
            if self.cached_status_values["ab_size"] != None :
                return self.cached_status_values["ab_size"]
        except:
            pass
        
        res = self.send_at_command('AT+CPBR=?'
                                   , accept_null_response=False)
        self.dbg_msg ("GET ADDRESSBOOK INFO : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile("\+CPBR:.*\((?P<leni>\d+)-(?P<lene>\d+)\)")
                matched_res = pattern.match(res[1][0])
                if matched_res != None :
                    self.cached_status_values["ab_size"] = int(matched_res.group("lene"))

                    if self.cached_status_values["ab_size"] > 250 :
                        self.cached_status_values["ab_size"] = 250

                    return self.cached_status_values["ab_size"]
                else:
                    self.dbg_msg ("GET ADDRESSBOOK INFO (not match) : %s" % res)
                    return 0
            else:
                return 0
        except:
            self.dbg_msg ("GET ADDRESSBOOK INFO (except) : %s" % res)
            return 0


    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=[])
    def sms_ab_list(self):
        res = self.send_at_command('AT+CPBS="SM"'
                                   , accept_null_response=False)

        if res[2] != 'OK':
            self.dbg_msg ("ENABLE ADDRESSBOOK NOT OK")
            return []
            
        ab_size = self.sms_ab_get_size()
        if ab_size == 0 :
            self.dbg_msg ("GET ADDRESSBOOK LIST (not ab_size available)")
            return []
        
        ab_list = []
        
        for x in range(1,ab_size+1):
            index, name, number = self.sms_ab_get(x)
            if index != 0 :
                ab_list.append([index, name, number])
                
        return ab_list

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=[])
    def sms_ab_list_old(self):
        ab_size = self.sms_ab_get_size()
        if ab_size == 0 :
            self.dbg_msg ("GET ADDRESSBOOK LIST (not ab_size available)")
            return []

        res = self.send_at_command('AT+CPBR=1,%s' % ab_size
                                   , accept_null_response=False)

        self.dbg_msg ("GET ADDRESSBOOK LIST : %s" % res)
        try:
            ab_list = []
            if res[2] == 'OK':
                for item in res[1]:
                    pattern =  re.compile("\+CPBR:.*(?P<id>\d+),\"(?P<number>.+)\",(?P<i_type>\d+),\"(?P<name>.+)\"")
                    matched_res = pattern.match(item)
                    if matched_res != None:
                        cid = matched_res.group("id")
                        name = matched_res.group("name")
                        number = matched_res.group("number")
                        ab_list.append([int(cid), name.decode("latin-1"), number])
                    else:
                         self.dbg_msg ("GET ADDRESSBOOK LIST (not matched): %s" % res)
                    
                return ab_list
            else:
                return []
        except:
            self.dbg_msg ("GET ADDRESSBOOK LIST (except) : %s" % res)
            return []

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=True)
    def is_postpaid(self):
        res = self.send_at_command('AT+CSIM=18,"00A40804047F436F02"', accept_null_response=False)
        
        self.dbg_msg ("LOOKING POSTPAID FILE : %s" % res)
        try:
            if res[2] == 'OK':
                pattern = re.compile('\+CSIM:.*4,\"(?P<file>.+)\"')
                matched_res = pattern.match(res[1][0])
                if matched_res != None:
                    if matched_res.group("file").startswith("61") or matched_res.group("file") == "9000" :
                        res2 = self.send_at_command('AT+CSIM=10,"00B0000001"', accept_null_response=False)
                        self.dbg_msg ("LOOKING TYPE IN POSTPAID FILE : %s" % res2)
                        try:
                            if res2[2] == 'OK':
                                pattern = re.compile('\+CSIM:.*,\"(?P<file>.+)\"')
                                self.dbg_msg("LOOKING TYPE IN POSTPAID FILE (step 2) : %s" % res2)
                                matched_res = pattern.match(res2[1][0])
                                if matched_res != None:
                                    if matched_res.group("file").endswith("9000") :
                                        if int(matched_res.group("file")[1]) == 0 :
                                            self.dbg_msg ("---> PREPAID")
                                            return False
                                        else:
                                            self.dbg_msg ("---> POSTPAID")
                                            return True
                                    else:
                                        self.dbg_msg ("LOOKING TYPE IN POSTPAID FILE (not type): %s" % res2)
                                        return True
                                else:
                                    self.dbg_msg ("LOOKING TYPE IN POSTPAID FILE (not type): %s" % res2)
                                    return True
                        except:
                            self.dbg_msg ("LOOKING TYPE IN POSTPAID FILE (except): %s" % res2)
                            return True
                            
                    elif matched_res.group("file") == "6A82" :
                        #FIXME Add support for old sim cards
                        self.dbg_msg ("OLD SIM CARD , return TRUE by default")
                        return True
                    else:
                        self.dbg_msg (" LOOKING POSTPAID FILE (not file) : %s" % res)
                        return True
            else:
                self.dbg_msg ("LOOKING POSTPAID FILE (error) : %s" % res)
                return True
        except:
            self.dbg_msg ("IS POSTPAID (except) : %s" % res)
            return True
    
    def start_polling(self):
        print "start polling"
        self.pause_polling_necesary = False

    def stop_polling(self):
        print "stop polling"
        self.pause_polling_necesary = True

    def set_using_data_device(self, value):
        self.using_data_device=value

    def get_using_data_device(self):
        return self.using_data_device
    

gobject.type_register(MobileDevice)
 
