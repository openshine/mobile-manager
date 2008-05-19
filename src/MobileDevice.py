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
import MobileManager


class MobileDeviceIO():
    def __init__(self, path, attempts=1, timeout=2):
        self.path = path
        self.fd = MobileManager.mdpc.open(path)
        self.attempts = attempts
        self.timeout = timeout

    def close(self):
        if self.fd != None :
            MobileManager.mdpc.close(self.fd)
            self.fd = None

    def reopen(self):
        self.flush()
        self.close()
        self.fd = MobileManager.mdpc.open(self.path)
        self.flush()
        
    def readline(self):
        attempts = 0
        while attempts != self.attempts :
            string = MobileManager.mdpc.read_string(self.fd, self.timeout)
            if string != None:
                return string
            print "Attempts %s" % attempts
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
        
        self.data_device = ''
        self.conf_device = ''
        self.velocity = "57600"
        self.hardware_flow_control = False
        self.hardware_error_control = False
        self.hardware_compress = False
        self.devices_autoconf = False

        self.multiport = False

        self.pretty_name = ''
        self.priority = "0"


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
                                      "carrier_selection_mode" : None}

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
            if self.data_port != self.conf_port and self.conf_port != '' :
                return True
            else:
                return False
        elif property.name == 'pretty-name':
            if self.pretty_name != '' :
                return self.pretty_name
            else:
                return self.dev_props["info.product"]
        elif property.name == 'priority':
            return self.priority
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
        elif property.name == 'priority':
            self.priority = value
        else:
            raise AttributeError, 'unknown property %s' % property.name

        self.save_conf()

    def set_debug_func(self, func):
        self.external_debug_func = func

    def dbg_msg (self, str):
        if self.external_debug_func != None :
             self.external_debug_func (str)
        else:
            print str

    def connect_dbus(self):
        self.dbus_device = MobileManagerDbusDevice(self , self.mcontroller.bname,
                                                   os.path.basename(self.dev_props["info.udi"]))
        self.dbus_device_path = str(self.dbus_device)
        
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

    def status_polling(self):
        
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

        self.dbg_msg ("----------------------> END poll round %s" % self.poll_round)
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
            self.serial = MobileDeviceIO(conf_port)
            
            self.status_polling_timeout_id = gobject.timeout_add(3000, self.status_polling)
        
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
                    self.actions_on_reopen_port()
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
                self.actions_on_reopen_port()
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
            self.actions_on_reopen_port()
            if  accept_null_response == False:
                return self.send_at_command(str, attempt - 1, accept_null_response=False)
            else:
                return self.send_at_command(str, attempt - 1)
        
        return result
        
        

    def send_at_command_old (self, str, attempt=6, accept_null_response=True):
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
                    break
            else:
                if attempt == 0:
                    return None
                else:
                    print "reopening and resending command %s" % str
                    self.serial.reopen()
                    self.actions_on_reopen_port()
                    if  accept_null_response == False:
                        ret = self.send_at_command(str, attempt - 1, accept_null_response=False)
                        if ret[0] == 'OK' and ret[-1] == 'OK' :
                            print "double OK case!!"
                            return [str, [] ,'OK']
                        return ret
                    else:
                        ret = self.send_at_command(str, attempt - 1)
                        if ret[0] == 'OK' and ret[-1] == 'OK' :
                            print "double OK case!!"
                            return [str, [] ,'OK']
                        return ret

        result = [tt_res[0],tt_res[1:-1],tt_res[-1]]
        print ">TTRES = %s" % result

        #This response is for some especial cases in options cards
        if tt_res[0] == 'OK' and tt_res[-1] == 'OK' :
            print "double OK case!!"
            return [str, [] ,'OK']

        if accept_null_response == False:
            if len(result[1]) == 0 and result[0] == "OK" :
                if attempt == 0:
                    return result
                print "Reopening and resending , the response is ok but there isn't echo (%s, attempt=%s)" % (result, attempt)
                self.serial.reopen()
                self.actions_on_reopen_port()
                ret = self.send_at_command(str, attempt - 1, accept_null_response=False)
                if ret[0] == 'OK' and ret[-1] == 'OK' :
                    print "double OK case!!"
                    return [str, [] ,'OK']
                return ret

        if result[0] != str :
            if attempt == 0:
                return result
            print "Reopening and resending , wrong echo command field  (%s, attempt=%s)" % (result, attempt)
            self.serial.reopen()
            self.actions_on_reopen_port()
            ret = self.send_at_command(str, attempt - 1)
            if ret[0] == 'OK' and ret[-1] == 'OK' :
                print "double OK case!!"
                return [str, [] ,'OK']
            return ret
        
        return result

    def actions_on_reopen_port(self):
        pass

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
        if res[2] == 'OK':
            return True
        else:
            return False

    @pin_status_required (PIN_STATUS_READY)
    def set_pin(self, old_pin, new_pin):
        res = self.send_at_command('AT+CPWD="SC", "%s", "%s"'  % (old_pin, new_pin))
        self.dbg_msg ("SET PIN : %s" % res) 
        if res[2] == 'OK' :
            return True
        else:
            return False
    
    @pin_status_required (PIN_STATUS_READY)
    def set_pin_active(self, pin, active=True):
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

    @pin_status_required (PIN_STATUS_READY)
    def is_pin_active(self):
        if self.cached_status_values["is_pin_active"] != None:
            return self.cached_status_values["is_pin_active"]
        
        res = self.send_at_command('AT+CLCK="SC",2', accept_null_response=False)
        self.dbg_msg ("IS PIN ACTIVE : %s" % res)
        
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
                    
    @pin_status_required (PIN_STATUS_WAITING_PUK)
    def send_puk (self, puk, pin):
        res = self.send_at_command('AT+CPIN="%s", "%s"'  % (puk, pin))
        self.dbg_msg ("SEND PUK : %s" % res) 
        if res[2] == 'OK':
            return True
        else:
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
                return None
                
        elif res[2].startswith("+CME ERROR:"):
            if res[2].find("SIM not inserted") != -1 :
                self.dbg_msg("PIN STATUS : ERROR Sim not inserted")
                return PIN_STATUS_NO_SIM
            if res[2].find("SIM failure") != -1 :
                self.dbg_msg("PIN STATUS : ERROR Sim failure")
                return PIN_STATUS_SIM_FAILURE

        return None

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=0)  
    def get_signal(self):
        res = self.send_at_command('AT+CSQ', accept_null_response=False)
        self.dbg_msg ("GET SIGNAL : %s" % res)
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
        
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error="NO CARRIER")
    def get_carrier(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("GET CARRIER : %s" % res)
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

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=-1)
    def get_carrier_selection_mode(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("GET CARRIER SELECTION : %s" % res)
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
        

    def turn_on(self):        
        res = self.send_at_command('AT+CFUN=1')
        self.dbg_msg ("TURN ON : %s" % res)
        if res[2] == 'OK':
            self.card_is_on = True
            return True
        else:
            return False
        
    def turn_off(self):
        res = self.send_at_command('AT+CFUN=0')
        self.dbg_msg ("TURN OFF : %s" % res)
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


    def get_net_info(self):
        tech_in_use = None
        card_mode = None
        card_domain = None
        carrier = None
        carrier_mode = None
        
        res = self.send_at_command("AT+COPS?", accept_null_response=False)
        
        self.dbg_msg ("GET TECH MODE DOMAIN : %s" % res)
        if res[2] == 'OK' :
            tech_in_use = int(res[1][0][-1])
            
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
        

    def get_mode_domain(self):
        card_mode = None
        card_domain = None

        return card_mode, card_domain

    def set_mode_domain(self, mode, domain):
        print "set_mode_domain"
        return True

    def get_card_info(self):
        res = self.send_at_command('ATI')
        self.dbg_msg ("GET CARD INFO : %s" % res)
        if res[2] == 'OK' :
            return res[1]
        else:
            return []

    def __get_carrier_list_from_raw(self, raw) :
        print "__get_carrier_list_from_raw in"
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

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=None)
    def get_carrier_list(self, func):
        self.send_at_command_async('AT+COPS=?', self.__get_carrier_list_from_raw, func)

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def set_carrier(self, carrier_id, tech):
        res = self.send_at_command('AT+COPS=1,2,"%s",%s' % ( carrier_id, tech ))
        self.dbg_msg ("SET CARRIER : %s" % res)
        res2 = self.send_at_command('AT+COPS=3,0')
        self.dbg_msg ("SET CARRIER 2 : %s" % res2)

        if res == None:
            return False
        
        if res[2] != 'OK' :
            return False
        else:
            return True

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def set_carrier_auto_selection(self):
        res = self.send_at_command('AT+COPS=0')
        print res
        if res[2] == "OK":
            return True
        else:
            return False

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_carrier_auto(self):
        res = self.send_at_command('AT+COPS?',  accept_null_response=False)
        self.dbg_msg ("IS CARRIER AUTO ? : %s" % res)

        if res[2] == 'OK':
            pattern = re.compile("\+COPS:\ +(?P<mode>\d+)")
            matched_res = pattern.match(res[1][0])
            if matched_res != None:
                if matched_res.group("mode") == "0" :
                    return True
                else:
                    return False
        return False
    
    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_attached(self):
        res = self.send_at_command('AT+CGREG?', accept_null_response=False)
        self.dbg_msg ("IS ATTACHED ? : %s" % res)
        if res[2] == 'OK':
            pattern = re.compile("\+CGREG:.*,(?P<state>\d+)")
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

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=0)
    def get_attach_state(self):
        res = self.send_at_command('AT+CGREG?', accept_null_response=False)
        self.dbg_msg ("GET ATTACH STATE : %s" % res)
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

    @pin_status_required (PIN_STATUS_READY, ret_value_on_error=False)
    def is_roaming(self):
        res = self.send_at_command('AT+CGREG?',  accept_null_response=False)
        self.dbg_msg ("IS ROAMING ? : %s" % res)
        if res[2] == 'OK':
            pattern = re.compile("\+CGREG:.*,(?P<state>\d+)")
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
        

    def start_polling(self):
        print "start polling"
        #self.pause_polling_necesary = False

    def stop_polling(self):
        print "stop polling"
        #self.pause_polling_necesary = True

gobject.type_register(MobileDevice)
 
