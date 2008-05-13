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


VELOCITY = ["9600","14400","19200","38400","56000","57600","115200"]

class MobileDeviceConfWidget(gtk.HBox):

    def __init__(self, mcontroller):
        gtk.HBox.__init__(self)
        
        main_ui_filename = os.path.join(MobileManager.ui.mobilemanager_glade_path, "mm_devices_conf.glade")
        widgets = self.__get_glade_widgets(main_ui_filename)
        self.xml = gtk.glade.XML(main_ui_filename,"mm_device_conf_widget")

        for widget in widgets :
            exec ('self.%s = self.xml.get_widget("%s")' % (widget.strip("mm_") ,widget))
            
        self.mcontroller = mcontroller

        self.at_op_button = MobileManager.ui.MobileATOptionsButton(mcontroller)
        self.at_op_button_vbox.add(self.at_op_button)
        self.at_op_button.set_label(_("Options"))

        self.od_liststore = gtk.ListStore(str, str)
        self.od_combobox.set_model(self.od_liststore)
        cell = gtk.CellRendererText()
        self.od_combobox.pack_start(cell, True)
        self.od_combobox.add_attribute(cell, 'text', 0)

        self.v_liststore = gtk.ListStore(str)
        self.velocity_combobox.set_model(self.v_liststore)

        for x in VELOCITY :
             self.v_liststore.append([x])

        self.last_not_at_device = None

        self.handlers = []
        
        self.handlers.append([self.imc_radiobutton,
                              self.imc_radiobutton.connect("toggled", self.__imc_radiobutton_cb, None)])
        self.handlers.append([self.od_radiobutton,
                              self.od_radiobutton.connect("toggled", self.__od_radiobutton_cb, None)])
        self.handlers.append([self.od_combobox,
                              self.od_combobox.connect("changed", self.__od_combobox_cb, None)])
        self.handlers.append([self.velocity_combobox,
                              self.velocity_combobox.connect("changed", self.__velocity_combobox_cb, None)])
        self.handlers.append([self.hfc_checkbutton,
                              self.hfc_checkbutton.connect("toggled", self.__hfc_checkbutton_cb, None)])
        self.handlers.append([self.hec_checkbutton,
                              self.hec_checkbutton.connect("toggled", self.__hec_checkbutton_cb, None)])
        self.handlers.append([self.hc_checkbutton,
                              self.hc_checkbutton.connect("toggled", self.__hc_checkbutton_cb, None)])

        self.active_dev_hd = self.mcontroller.connect("active-device-changed", self.__active_device_changed_cb)

        self.add(self.device_conf_widget)
        self.show()
        self.at_op_button.set_no_show_all(True)
        self.at_op_button.hide()

            
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

    def __active_device_changed_cb(self, mcontroller, udi):
        print "MOBILEDEVICECONF (__active_device_changed_cb) init"
        for x in self.handlers:
            x[0].handler_block(x[1])

        active_dev = self.mcontroller.get_active_device()
        print "MOBILEDEVICECONF (__active_device_changed_cb) dev = %s" % str(active_dev)
        print "MOBILEDEVICECONF (__active_device_changed_cb) 1"
        if active_dev == None:
            print "MOBILEDEVICECONF (__active_device_changed_cb) 2"
            self.device_configuration_vbox.hide()
            self.imc_radiobutton.set_active(True)
            self.od_combobox.set_sensitive(False)
            self.imc_label.set_text(_("Not device available"))
            not_at_devs = self.mcontroller.get_available_not_at_devices()
            self.od_liststore.clear()
            
            for dev in not_at_devs:
                self.od_liststore.append([dev.get_property("pretty-name"), dev.dev_props["info.udi"]])
            if len(not_at_devs) > 0:
                self.od_combobox.set_active(0)
            print "MOBILEDEVICECONF (__active_device_changed_cb) 3"
            
        else:
            if MobileManager.AT_COMM_CAPABILITY in active_dev.capabilities :
                print "MOBILEDEVICECONF (__active_device_changed_cb) 4"
                self.imc_radiobutton.set_active(True)
                self.od_combobox.set_sensitive(False)
                self.imc_label.set_text(active_dev.get_property("pretty-name"))

                not_at_devs = self.mcontroller.get_available_not_at_devices()
                self.od_liststore.clear()

                i = 0
                default_dev = 0
                for dev in not_at_devs:
                    self.od_liststore.append([dev.get_property("pretty-name"), dev.dev_props["info.udi"]])
                    if dev.dev_props["info.udi"] == self.last_not_at_device :
                        default_dev = i
                    i = i + 1
                if len(not_at_devs) > 0:
                    self.od_combobox.set_active(default_dev)
                print "MOBILEDEVICECONF (__active_device_changed_cb) 5"
                    
            else:
                print "MOBILEDEVICECONF (__active_device_changed_cb) 6"
                self.last_not_at_device = active_dev.dev_props["info.udi"]
                self.od_radiobutton.set_active(True)
                self.od_combobox.set_sensitive(True)
                at_devs = self.mcontroller.get_available_at_devices()
                if len(at_devs) == 0:
                    self.imc_label.set_text(_("Not device available"))
                else:
                    self.imc_label.set_text(at_devs[0].get_property("pretty-name"))

                not_at_devs = self.mcontroller.get_available_not_at_devices()
                self.od_liststore.clear()

                i = 0
                default_dev = 0
                for dev in not_at_devs:
                    self.od_liststore.append([dev.get_property("pretty-name"), dev.dev_props["info.udi"]])
                    if dev.dev_props["info.udi"] == udi :
                        default_dev = i
                    i = i + 1
                if len(not_at_devs) > 0:
                    self.od_combobox.set_active(default_dev)
                print "MOBILEDEVICECONF (__active_device_changed_cb) 7"
            
            print "MOBILEDEVICECONF (__active_device_changed_cb) 8"
            print "MOBILEDEVICECONF (__active_device_changed_cb) dev = %s" % str(active_dev)
            print "MOBILEDEVICECONF (__active_device_changed_cb) %s" % active_dev.get_property("data-device")
            self.device_label.set_text(active_dev.get_property("data-device"))
            self.velocity_combobox.set_active(VELOCITY.index(active_dev.get_property("velocity")))
            self.hfc_checkbutton.set_active(active_dev.get_property("hardware-flow-control"))
            self.hec_checkbutton.set_active(active_dev.get_property("hardware-error-control"))
            self.hc_checkbutton.set_active(active_dev.get_property("hardware-compress"))
            self.device_configuration_vbox.show()

            at_devs = self.mcontroller.get_available_at_devices()
            if len(at_devs) > 0 :
                self.at_op_button.show()
            else:
                self.at_op_button.hide()
            print "MOBILEDEVICECONF (__active_device_changed_cb) 9"

        for x in self.handlers:
            x[0].handler_unblock(x[1])
            
        print "MOBILEDEVICECONF (__active_device_changed_cb) END"
        

    def __imc_radiobutton_cb(self, widget, data):
        if widget.get_active() == False:
            return

        if self.mcontroller.dialer.status() ==  MobileManager.PPP_STATUS_CONNECTED:
            self.mcontroller.dialer.stop()
        
        self.od_combobox.set_sensitive(False)

        at_devs = self.mcontroller.get_available_at_devices()
        if len(at_devs) == 0:
            self.imc_label.set_text(_("Not device available"))
            self.at_op_button.hide()
            self.mcontroller.set_active_device(None)
        else:
            self.imc_label.set_text(at_devs[0].get_property("pretty-name"))
            self.at_op_button.show()
            self.mcontroller.set_active_device(at_devs[0].dev_props["info.udi"])
            if not at_devs[0].is_on() :
                at_devs[0].turn_on()

    def __od_radiobutton_cb(self, widget, data):
        if widget.get_active() == False:
            return
        
        if self.mcontroller.dialer.status() ==  MobileManager.PPP_STATUS_CONNECTED:
            self.mcontroller.dialer.stop()
        
        at_devs = self.mcontroller.get_available_at_devices()
        for at_dev in at_devs :
            at_dev.turn_off()
        
        self.at_op_button.set_sensitive(False)
        self.od_combobox.set_sensitive(True)
        active_dev_num = self.od_combobox.get_active()
        if active_dev_num == -1 :
            if len(self.mcontroller.get_available_not_at_devices()) > 0 :
                self.od_combobox.set_active(0)
            else:
                self.mcontroller.set_active_device(None)
                return
                
        self.__od_combobox_cb(self.od_combobox, None)

    def __od_combobox_cb(self, widget, data):
        active_dev_num = self.od_combobox.get_active()
        if active_dev_num == -1 :
            self.device_configuration_vbox.hide()
            return

        if self.mcontroller.dialer.status() ==  MobileManager.PPP_STATUS_CONNECTED:
            self.mcontroller.dialer.stop()
        
        tmp_iter = self.od_liststore.get_iter(active_dev_num)
        row_udi = self.od_liststore.get_value(tmp_iter, 1)

        dev = None

        for x in self.mcontroller.get_available_not_at_devices() :
            if x.dev_props["info.udi"] == row_udi :
                dev = x
                break

        if dev == None:
            return

        self.mcontroller.set_active_device(dev.dev_props["info.udi"])

    def __velocity_combobox_cb(self, widget, data):
        dev = self.mcontroller.get_active_device()
        if dev != None:
            dev.set_property("velocity", VELOCITY[widget.get_active()])

    def __hfc_checkbutton_cb(self, widget, data):
        dev = self.mcontroller.get_active_device()
        if dev != None:
            dev.set_property("hardware-flow-control", widget.get_active())
            

    def __hec_checkbutton_cb(self, widget, data):
        dev = self.mcontroller.get_active_device()
        if dev != None:
            dev.set_property("hardware-error-control", widget.get_active())
            
    def __hc_checkbutton_cb(self, widget, data):
        dev = self.mcontroller.get_active_device()
        if dev != None:
            dev.set_property("hardware-compress", widget.get_active())      
                   
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
