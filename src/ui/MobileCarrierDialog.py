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
import os
import gobject
import gtk
import gtk.glade

import dbus
import dbus.glib

import time

from MobileManager.MobileManagerDbus import MOBILE_MANAGER_CONTROLLER_PATH,MOBILE_MANAGER_CONTROLLER_URI,MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,MOBILE_MANAGER_DEVICE_PATH,MOBILE_MANAGER_DEVICE_URI,MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI

class MobileCarrierSelectorDialog:

    def __init__(self):
        self.dbus = None
        self.mm_manager_obj = None
        self.mcontroller = None
        if self.__init_bus() == False:
            return 
        
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        dev_auth = self.__get_device_auth_from_path(dev_path)
        dev_state = self.__get_device_state_from_path(dev_path)
        
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI) :
            return
        
        status = dev_auth.PINStatus()
        if not status == MobileManager.PIN_STATUS_READY :
            return 

        
        main_ui_filename =  os.path.join(MobileManager.ui.mobilemanager_glade_path, "mm_carrier_dialog.glade")
        self.widget_tree = gtk.glade.XML(main_ui_filename,"carrier_selection_dialog")
        self.dialog = self.widget_tree.get_widget("carrier_selection_dialog")

        self.carrier_combobox = self.widget_tree.get_widget("carrier_combobox")
        self.carrier_combobox_hbox = self.widget_tree.get_widget("carrier_combobox_hbox")
        self.carrier_scan_progressbar = self.widget_tree.get_widget("carrier_scan_progressbar")
        
        self.carrier_combobox_changed_id = self.carrier_combobox.connect("changed",self.__carrier_combobox_cb, None)

        cell = gtk.CellRendererPixbuf()
        self.carrier_combobox.pack_start(cell, False)
        self.carrier_combobox.add_attribute(cell, "stock_id",0)
       
        cell = gtk.CellRendererText()
        self.carrier_combobox.pack_start(cell, False)
        self.carrier_combobox.add_attribute(cell, 'text', 1)     
  
        self.refresh_button = self.widget_tree.get_widget("refresh_button")
        self.refresh_button.connect("clicked",self.__refresh_button_cb, None)

        self.ok_button = self.widget_tree.get_widget("ok_button")
        self.ok_button.connect("clicked",self.__ok_button_cb, None)
        
        self.cancel_button = self.widget_tree.get_widget("cancel_button")
        self.cancel_button.connect("clicked",self.__cancel_button_cb, None)

        self.timer = gobject.timeout_add (100, self.__progress_timeout_cb, None)
        
        self.carrier_combobox_hbox.show()
        self.carrier_scan_progressbar.hide()

        self.reg_attempts = 0

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
        
    def __progress_timeout_cb(self, data):
        self.carrier_scan_progressbar.pulse()
        return True

    def run(self, refresh=True):
        refresh_at_start = refresh
        
        while True :
            self.dialog.show()
            if refresh_at_start == True :
                self.refresh_button.emit("clicked")
                refresh_at_start = False
            
            res = self.dialog.run()

            print "Mobile Carrier Dialog res --> %s" % res 

            if res == 0 :
                #clicked refresh button
                continue
            
            if res != gtk.RESPONSE_OK:
                self.dialog.hide()
                return False
            else:
                res = self.__select_carrier()
                if res == True :
                    self.carrier_combobox_hbox.hide()
                    self.carrier_scan_progressbar.set_text(_("Attaching to network"))
                    self.carrier_scan_progressbar.show()
                    self.ok_button.set_sensitive(False)
                    self.cancel_button.set_sensitive(False)
                    self.refresh_button.set_sensitive(False)

                    self.reg_attempts = 10
                    gobject.timeout_add (1500, self.__registering_timeout_cb, None)
                    
                else:
                    dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                    dlg.set_icon_name("phone")
                    dlg.set_markup(_("<b>Network selection failure</b>"))
                    dlg.format_secondary_markup(_("The network selection has failed. Try again or select other carrier."))
                    dlg.run()
                    dlg.destroy()
                    continue
                
                return True

    def __registering_timeout_cb(self, data):
        print "registering timeout <<<----------"
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state = self.__get_device_state_from_path(dev_path)
        
        if dev_state.IsAttached() == True:
            self.dialog.hide()
            return False
        else:
            if self.reg_attempts == 0:
                self.carrier_combobox_hbox.show()
                self.carrier_scan_progressbar.hide()
                self.cancel_button.set_sensitive(True)
                self.refresh_button.set_sensitive(True)
                model =  self.carrier_combobox.get_model()
                if len(model) > 0 :
                    self.ok_button.set_sensitive(True)
                else:
                    self.ok_button.set_sensitive(False)
                    
                self.run(refresh=False)
                return False
            else:
                self.reg_attempts = self.reg_attempts - 1
                return True
            
            
    def __select_carrier(self):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state = self.__get_device_state_from_path(dev_path)

        model = self.carrier_combobox.get_model()
        act_iter = self.carrier_combobox.get_active_iter()
        if act_iter != None :
            res = dev_state.SetCarrier(int(model.get_value(act_iter, 3)),
                                       int(model.get_value(act_iter, 4)))
            if res == True :
                return True
            else:
                return False
        return False
            

    def __refresh_button_cb (self, widget, data):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state = self.__get_device_state_from_path(dev_path)
        
        self.carrier_combobox_hbox.hide()
        self.carrier_scan_progressbar.set_text(_("Scanning carriers"))
        self.carrier_scan_progressbar.show()
        self.ok_button.set_sensitive(False)
        self.cancel_button.set_sensitive(False)
        self.refresh_button.set_sensitive(False)

        mainloop =  gobject.MainLoop(is_running=True)
        context = mainloop.get_context()
        t1 = time.time()
        while time.time() - t1 < 2 :
            context.iteration()
        
        dev_state.GetCarrierList(reply_handler=self.__update_carrier_list,
                                 error_handler=self.__timeout_error,
                                 timeout=2000000)
    
    def __get_carrier_list_again(self, data):
	print "__get_carrier_list_again"
        mainloop =  gobject.MainLoop(is_running=True)
        context = mainloop.get_context()
	context.iteration()
        dev_path = self.mcontroller.GetActiveDevice()
	context.iteration()
        dev_state = self.__get_device_state_from_path(dev_path)
        context.iteration()
        dev_state.GetCarrierList(reply_handler=self.__update_carrier_list,
                                 error_handler=self.__timeout_error,
                                 timeout=2000000)
	return False
    
    def __timeout_error(self, e):
	print "get_carrier_list_timeout"
        gobject.timeout_add (20000, self.__get_carrier_list_again, None)
        return True    

    def __update_carrier_list(self, carrierlist, supported_modes, supported_formats):
        carrier_list = carrierlist
        
        model = gtk.ListStore(str,str,str,str,str)
        for x in carrier_list:
            record = list(x)
            if record[0] == 1 or record[0] == 2:
                record.pop(0)
                record.insert(0,gtk.STOCK_YES)
            else:
                record.pop(0)
                record.insert(0,gtk.STOCK_NO)

            if record[4] == 2:
                record[1] = record [1] + " (3G)"
            else:
                record[1] = record [1] + " (2G)"
            
            print record
            model.append(record)

        self.carrier_combobox.set_model(model)
        self.cancel_button.set_sensitive(True)
        self.refresh_button.set_sensitive(True)
        self.carrier_combobox_hbox.show()
        self.carrier_scan_progressbar.hide()
        if len(model) > 0 :
            self.carrier_combobox.set_active(0)
            self.ok_button.set_sensitive(True)
        else:
            self.ok_button.set_sensitive(False)
            

    def __carrier_combobox_cb(self, widget, data):
        carrier_num = widget.get_active()
        if carrier_num <0 :
            self.ok_button.set_sensitive(False)

        model = widget.get_model()
        tmp_iter = model.get_iter(carrier_num)
        value = model.get_value(tmp_iter, 0)
        

    def __cancel_button_cb(self, widget, data):
        gobject.source_remove(self.timer)
        self.timer = 0
        self.dialog.hide()
        

    def __ok_button_cb(self, widget, data):
        print "OK"

    
    
