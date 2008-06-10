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
import MobileManager.ui
import gtk
import gtk.glade
import os
import re
import dbus
import dbus.glib
import gettext

from MobileManager.MobileManagerDbus import MOBILE_MANAGER_CONTROLLER_PATH,MOBILE_MANAGER_CONTROLLER_URI,MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,MOBILE_MANAGER_DEVICE_PATH,MOBILE_MANAGER_DEVICE_URI,MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI

VELOCITY = [9600, 14400, 19200, 38400, 56000, 57600, 115200]

GETTEXT_DOMAIN="mobile-manager"

class MobileDeviceConfWidget(gtk.HBox):

    def __init__(self):
        gtk.HBox.__init__(self)

        MobileManager.ui.init_i18n()
        
        main_ui_filename = os.path.join(MobileManager.ui.mobilemanager_glade_path, "mm_devices_conf.glade")
        widgets = self.__get_glade_widgets(main_ui_filename)
        self.xml = gtk.glade.XML(main_ui_filename,"mm_device_conf_widget")

        for widget in widgets :
            exec ('self.%s = self.xml.get_widget("%s")' % (widget.strip("mm_") ,widget))
            
        self.dbus = None
        self.mm_manager_obj = None
        self.mcontroller = None
        if self.__init_bus() == False:
            return        
        

        self.at_op_button = MobileManager.ui.MobileATOptionsButton()
        self.at_op_button.set_no_show_all(True)
        self.at_op_button_vbox.add(self.at_op_button)
        self.at_op_button.set_label(_("Options"))

        self.devs_liststore = gtk.ListStore(str, str, gtk.gdk.Pixbuf)
        self.devs_combobox.set_model(self.devs_liststore)

        cell = gtk.CellRendererPixbuf()
        self.devs_combobox.pack_start(cell, False)
        self.devs_combobox.add_attribute(cell, 'pixbuf', 2)
        
        cell = gtk.CellRendererText()
        self.devs_combobox.pack_start(cell, False)
        self.devs_combobox.add_attribute(cell, 'text', 0)


        self.v_liststore = gtk.ListStore(str)
        self.velocity_combobox.set_model(self.v_liststore)

        for x in VELOCITY :
             self.v_liststore.append([x])

        self.__init_fields()

        self.last_not_at_device = None

        self.handlers = []
        
        self.handlers.append([self.devs_combobox,
                              self.devs_combobox.connect("changed", self.__devs_combobox_cb, None)])
        self.handlers.append([self.velocity_combobox,
                              self.velocity_combobox.connect("changed", self.__velocity_combobox_cb, None)])
        self.handlers.append([self.hfc_checkbutton,
                              self.hfc_checkbutton.connect("toggled", self.__hfc_checkbutton_cb, None)])
        self.handlers.append([self.hec_checkbutton,
                              self.hec_checkbutton.connect("toggled", self.__hec_checkbutton_cb, None)])
        self.handlers.append([self.hc_checkbutton,
                              self.hc_checkbutton.connect("toggled", self.__hc_checkbutton_cb, None)])

        self.mcontroller.connect_to_signal("AddedDevice", self.__AddedDevice_cb)
        self.mcontroller.connect_to_signal("RemovedDevice", self.__RemovedDevice_cb)
        self.mcontroller.connect_to_signal("ActiveDeviceChanged", self.__ActiveDeviceChanged_cb)
        self.mcontroller.connect_to_signal("ActiveDevCardStatusChanged", self.__ActiveDevCardStatusChanged_cb)

        self.add(self.device_conf_widget)

        self.no_dev_label.set_no_show_all(True)
        self.devs_combobox.set_no_show_all(True)
        self.device_configuration_vbox.set_no_show_all(True)
        
        self.show()


    def __init_bus(self):
        try:
            self.dbus = dbus.SystemBus()
            
            self.mm_manager_obj = self.dbus.get_object(MOBILE_MANAGER_CONTROLLER_URI,
                                                       MOBILE_MANAGER_CONTROLLER_PATH)
            self.mcontroller = dbus.Interface(self.mm_manager_obj,
                                              MOBILE_MANAGER_CONTROLLER_INTERFACE_URI)
            return True
        except:
            print "Not dbus connection available"
            return False
        
    def __get_device_info_from_path(self, dev_path):
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   dev_path)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        return dev_info

    def __get_device_auth_from_path(self, dev_path):
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   dev_path)
        dev_auth = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI)
        return dev_auth

    def __get_device_state_from_path(self, dev_path):
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   dev_path)
        dev_auth = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI)
        return dev_auth
            
    def __get_glade_widgets(self, f):
        fd = open(f)
        pattern = re.compile(".*id=\"(?P<widget>mm_.*)\"")
        lines = fd.readlines()
        fd.close()
        widgets = []
        
        for line in lines :
            matched_res = pattern.match(line)
            if matched_res != None :
                widgets.append(matched_res.group("widget"))
                
        return widgets

    def __init_fields(self):
        devs_list = self.mcontroller.GetAvailableDevices()
        icontheme = gtk.icon_theme_get_default()
        
        for dev_path in devs_list :
            dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                       dev_path)
            dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
            device_icon = dev_info.GetDeviceIcon()
            pixbuf = None
            
            if device_icon != "" :
                pixbuf = icontheme.load_icon(device_icon, 16, 0)
                
            self.devs_liststore.append([dev_info.GetPrettyName(), dev_path, pixbuf])
        print len(devs_list)
        if len(devs_list) > 0 :
            active_dev = self.mcontroller.GetActiveDevice()
            index = devs_list.index(active_dev)
            self.devs_combobox.set_active(index)
            self.__reset_info_fields()
        else:
            self.no_dev_label.show()
            self.devs_combobox.hide()
            self.device_configuration_vbox.hide()

    def __AddedDevice_cb(self, device):
        for x in self.handlers:
            x[0].handler_block(x[1])

        self.devs_liststore.clear()
        active_dev = self.mcontroller.GetActiveDevice()
        
        devs_list = self.mcontroller.GetAvailableDevices()
        for dev_path in devs_list :
            dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                       dev_path)
            dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
            icontheme = gtk.icon_theme_get_default()
            device_icon = dev_info.GetDeviceIcon()
            pixbuf = None
            
            if device_icon != "" :
                pixbuf = icontheme.load_icon(device_icon, 16, 0)
            
            self.devs_liststore.append([dev_info.GetPrettyName(), dev_path, pixbuf])

        index = devs_list.index(active_dev)
        self.devs_combobox.set_active(index)

        self.__reset_info_fields()

        for x in self.handlers:
            x[0].handler_unblock(x[1])

    
    def __RemovedDevice_cb(self, device):
        for x in self.handlers:
            x[0].handler_block(x[1])

        self.devs_liststore.clear()
        active_dev = self.mcontroller.GetActiveDevice()
        
        devs_list = self.mcontroller.GetAvailableDevices()
        for dev_path in devs_list :
            dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                       dev_path)
            dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
            icontheme = gtk.icon_theme_get_default()
            device_icon = dev_info.GetDeviceIcon()
            pixbuf = None
            
            if device_icon != "" :
                pixbuf = icontheme.load_icon(device_icon, 16, 0)
            
            self.devs_liststore.append([dev_info.GetPrettyName(), dev_path, pixbuf])

        if active_dev != "" :
            index = devs_list.index(active_dev)
            self.devs_combobox.set_active(index)

        self.__reset_info_fields()

        for x in self.handlers:
            x[0].handler_unblock(x[1])

    def __ActiveDeviceChanged_cb(self, device):
        dev_path = self.mcontroller.GetActiveDevice()
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   dev_path)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI) :
            self.at_op_button.hide()
        else:
            self.at_op_button.show()

    def __ActiveDevCardStatusChanged_cb(self, status):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        dev_auth = self.__get_device_auth_from_path(dev_path)
        
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI) :
            return
                
        status = dev_auth.PINStatus()
        
        if status == MobileManager.PIN_STATUS_READY :
            self.at_op_button.show()
        else:
            self.at_op_button.hide()

    def __devs_combobox_cb(self, widget, data):
        active_dev_num = self.devs_combobox.get_active()
        if active_dev_num == -1 :
            self.device_configuration_vbox.hide()
            return

        tmp_iter = self.devs_liststore.get_iter(active_dev_num)
        row_udi = self.devs_liststore.get_value(tmp_iter, 1)

        self.mcontroller.SetActiveDevice(row_udi)
        for x in self.handlers:
            x[0].handler_block(x[1])
        self.__reset_info_fields ()
        for x in self.handlers:
            x[0].handler_unblock(x[1])
        


    def __reset_info_fields (self):
        active_dev = self.mcontroller.GetActiveDevice()
        if active_dev == "":
            self.no_dev_label.show()
            self.devs_combobox.hide()
            self.device_configuration_vbox.hide()
            return
        else:
            self.no_dev_label.hide()
            self.devs_combobox.show()
            self.device_configuration_vbox.show()
        
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   active_dev)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        
        self.device_label.set_text(dev_info.GetDataDevicePath())
        self.velocity_combobox.set_active(VELOCITY.index(dev_info.GetVelocity()))
        self.hfc_checkbutton.set_active(dev_info.GetHardwareFlowControl())
        self.hec_checkbutton.set_active(dev_info.GetHardwareErrorControl())
        self.hc_checkbutton.set_active(dev_info.GetHardwareCompress())

    def __velocity_combobox_cb(self, widget, data):
        active_dev = self.mcontroller.GetActiveDevice()
        if active_dev == None:
            return
        
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   active_dev)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        dev_info.SetVelocity(VELOCITY[widget.get_active()])

    def __hfc_checkbutton_cb(self, widget, data):
        active_dev = self.mcontroller.GetActiveDevice()
        if active_dev == None:
            return
        
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   active_dev)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        dev_info.SetHardwareFlowControl(widget.get_active())
            

    def __hec_checkbutton_cb(self, widget, data):
        active_dev = self.mcontroller.GetActiveDevice()
        if active_dev == None:
            return
        
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   active_dev)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        dev_info.SetHardwareErrorControl(widget.get_active())
            
    def __hc_checkbutton_cb(self, widget, data):
        active_dev = self.mcontroller.GetActiveDevice()
        if active_dev == None:
            return
        
        dev = self.dbus.get_object(MOBILE_MANAGER_DEVICE_URI,
                                   active_dev)
        dev_info = dbus.Interface(dev, MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI)
        dev_info.SetHardwareCompress(widget.get_active())
                   
def main():
    gtk.main()
    return

if __name__ == "__main__":
    mcontroller = MobileManager.MobileController()
    mdcw = MobileDeviceConfWidget(mcontroller)

    win = gtk.Window()
    win.add(mdcw)
    win.show()
    
    main()
