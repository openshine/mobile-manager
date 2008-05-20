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
import dbus.glib

from MobileDial import MobileDial


PPP_MANAGER_OBJECT_PATH ="/es/tid/em/PPPManager"
PPP_MANAGER_SERVICE_NAME="es.tid.em.PPPManager"
PPP_MANAGER_INTERFACE_NAME ="es.tid.em.IPPPManager"

PPP_CONNECT_SIGNAL ="connected_signal"
PPP_DISCONNECT_SINGAL ="disconnected_signal"
PPP_CONNECTING_SIGNAL ="connecting_signal"
PPP_DISCONNECTING_SIGNAL ="disconnecting_signal"

PPP_PARAM_DEVICE_PORT_KEY ="DEVICE_PORT"
PPP_PARAM_DEVICE_SPEED_KEY ="DEVICE_SPEED"
PPP_PARAM_COMPRESSION_KEY = "COMPRESION" 
PPP_PARAM_FLOW_CONTROL_KEY = "FLOW_CONTROL"
PPP_PARAM_ERROR_CONTROL_KEY = "ERROR_CONTROL" 


class MobileDialPPP(MobileDial):

    def __init__(self, mcontroller):
        self.bus = dbus.SystemBus()
        self.proxy_obj = self.bus.get_object(PPP_MANAGER_SERVICE_NAME, PPP_MANAGER_OBJECT_PATH)
        self.ppp_manager = dbus.Interface(self.proxy_obj, PPP_MANAGER_INTERFACE_NAME)

        self.bus.add_signal_receiver(self.__connected_cb,"connected_signal",PPP_MANAGER_INTERFACE_NAME,PPP_MANAGER_SERVICE_NAME,PPP_MANAGER_OBJECT_PATH)
        self.bus.add_signal_receiver(self.__disconnected_cb,"disconnected_signal",PPP_MANAGER_INTERFACE_NAME,PPP_MANAGER_SERVICE_NAME,PPP_MANAGER_OBJECT_PATH)
        self.bus.add_signal_receiver(self.__connecting_cb,"connecting_signal",PPP_MANAGER_INTERFACE_NAME,PPP_MANAGER_SERVICE_NAME,PPP_MANAGER_OBJECT_PATH)
        self.bus.add_signal_receiver(self.__disconnecting_cb,"disconnecting_signal",PPP_MANAGER_INTERFACE_NAME,PPP_MANAGER_SERVICE_NAME,PPP_MANAGER_OBJECT_PATH)
        self.bus.add_signal_receiver(self.__ppp_stats_cb,"pppstats_signal",PPP_MANAGER_INTERFACE_NAME,PPP_MANAGER_SERVICE_NAME,PPP_MANAGER_OBJECT_PATH)
         
        MobileDial.__init__(self, mcontroller)

    def start(self, parameters):
        print "PPP start"
        self.dev = self.mcontroller.get_active_device()
        if self.dev == None :
            print "ERROR IN PPP START"
            return
        
        parameters[PPP_PARAM_DEVICE_PORT_KEY] = str(self.dev.get_property("data-device"))
        parameters[PPP_PARAM_DEVICE_SPEED_KEY] = str(self.dev.get_property("velocity"))
        
        if self.dev.get_property("hardware-flow-control") :
            parameters[PPP_PARAM_FLOW_CONTROL_KEY] = "YES"
        else:
            parameters[PPP_PARAM_FLOW_CONTROL_KEY] = "NO"

        if self.dev.get_property("hardware-error-control") :
            parameters[PPP_PARAM_ERROR_CONTROL_KEY] = "YES"
        else:
            parameters[PPP_PARAM_ERROR_CONTROL_KEY] = "NO"
            
        if self.dev.get_property("hardware-compress") :
            parameters[PPP_PARAM_COMPRESSION_KEY] = "YES"
        else:
            parameters[PPP_PARAM_COMPRESSION_KEY] = "NO"

        print parameters
        
        self.ppp_manager.start(parameters)
        

    def stop(self):
        print "PPP Stop"
        self.ppp_manager.stop(reply_handler=self.__async_ingnore_result,
                              error_handler=self.__async_ingnore_error)

    def status(self, r_handler_func=None, e_handler_func=None):
        print "PPP status"
        if r_handler_func == None :
            return self.ppp_manager.status()
        else:
            self.ppp_manager.status(reply_handler=r_handler_func, error_handler=e_handler_func)

    def __connected_cb(self):
        print "MobileDialPPP emit connected"
        self.emit('connected')

    def __connecting_cb(self):
        print "MobileDialPPP emit connecting"
        self.emit('connecting')

    def __disconnected_cb(self):
        print "MobileDialPPP emit disconnected"
        self.emit('disconnected')

    def __disconnecting_cb(self):
        print "MobileDialPPP emit disconnecting"
        self.emit('disconnecting')

    def __ppp_stats_cb(self, recived_bytes ,sent_bytes, interval_time):
        self.emit("pppstats_signal", recived_bytes, sent_bytes, interval_time)

    def __async_ingnore_result(self,data=None):
        pass
    
    def __async_ingnore_error(self,e=None):
        pass
    
