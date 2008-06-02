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
import dbus
import dbus.glib

from MobileManager.MobileManagerDbus import MOBILE_MANAGER_CONTROLLER_PATH,MOBILE_MANAGER_CONTROLLER_URI,MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,MOBILE_MANAGER_DEVICE_PATH,MOBILE_MANAGER_DEVICE_URI,MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI

def is_valid_pin(pin):
    try:
        int(pin)
    except:
        return False
    
    if len(pin) >3 and len(pin) <9:
        return True
    else:
        return False


class MobilePukDialog:
    def __init__(self):
        self.dbus = None
        self.mm_manager_obj = None
        self.mcontroller = None
        if self.__init_bus() == False:
            return
        
        main_ui_filename = os.path.join(MobileManager.ui.mobilemanager_glade_path ,"mm_puk_dialog.glade")
        MobileManager.ui.init_i18n()
	widget_tree = gtk.glade.XML(main_ui_filename,"ask_puk_dialog")
        self.dialog = widget_tree.get_widget("ask_puk_dialog")
        self.puk_entry = widget_tree.get_widget("puk_entry")
        self.new_pin_entry = widget_tree.get_widget("new_pin_entry")
        self.new_pin_confirm_entry = widget_tree.get_widget("new_pin_confirm_entry")
        self.puk_error_label = widget_tree.get_widget("puk_error_label")
        self.error_hbox =  widget_tree.get_widget("error_hbox")
	self.ok_button = widget_tree.get_widget("ok_button")
	self.ok_button.set_sensitive(False)

	self.new_pin_entry.connect("changed", self.entries_changed_cb, None)
	self.new_pin_confirm_entry.connect("changed", self.entries_changed_cb, None)
	self.puk_entry.connect("changed", self.entries_changed_cb, None)
	
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
        

    def entries_changed_cb(self, editable, data):
        if len(self.puk_entry.get_text()) > 0 and len(self.new_pin_entry.get_text()) > 0 and len(self.new_pin_confirm_entry.get_text()) > 0:
            self.ok_button.set_sensitive(True)
        else:
            self.ok_button.set_sensitive(False)

    def __clean_dialog_fields(self):
        self.puk_entry.set_text("")
        self.new_pin_entry.set_text("")
        self.new_pin_confirm_entry.set_text("")

    def run(self):
        self.puk_error_label.set_text("")
        self.puk_error_label.hide()

        dev_path = self.mcontroller.GetActiveDevice()
        dev_auth = self.__get_device_auth_from_path(dev_path)
        dev_state = self.__get_device_state_from_path(dev_path)
        dev_info = self.__get_device_info_from_path(dev_path)
		
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI) :
            self.dialog.hide()
            return

        status = dev_auth.PINStatus()

        if status != MobileManager.PIN_STATUS_WAITING_PUK :
            return

        self.__clean_dialog_fields()
        while status == MobileManager.PIN_STATUS_WAITING_PUK :
            response = self.dialog.run()
            if response != gtk.RESPONSE_OK:
                # Cancel action : Show message and turn off the device if necesary               
                dlg = gtk.MessageDialog(type=gtk.MESSAGE_ERROR, buttons=gtk.BUTTONS_OK)
                dlg.set_markup(_("<b>Puk authentication cancel</b>"))
                dlg.format_secondary_markup(_("You have canceled the PUK authentication process, the card will be turn off"))
                dlg.run()
                dlg.destroy()
                self.dialog.destroy()
                dev_state.TurnOff()
		return
            
            puk = self.puk_entry.get_text()
            new_pin = self.new_pin_entry.get_text()
            new_pin_confirm = self.new_pin_confirm_entry.get_text()

            if not is_valid_pin(puk):
                self.puk_error_label.set_markup('<b>%s</b>' % _("You have entered an invalid PUK code"))
                self.error_hbox.show_all()
                continue

            if not is_valid_pin(new_pin):
                self.puk_error_label.set_markup('<b>%s</b>' % _("You have entered an invalid PIN code"))
                self.error_hbox.show_all()
                continue
            
            if new_pin_confirm != new_pin:
                self.puk_error_label.set_markup('<b>%s</b>' % _("The two Pin codes are not equal"))
                self.error_hbox.show_all()
                continue
            
            try:
                send_puk_result = dev_auth.SendPUK(puk,new_pin)
                status = dev_auth.PINStatus()
                if send_puk_result == True and status == MobileManager.PIN_STATUS_READY:
                    print "Puk entered and accepted"
                    self.dialog.destroy()
                    return
                
                self.puk_error_label.set_markup('<b>%s</b>' % _("You have entered an incorrect PUK code"))
                self.error_hbox.show_all()
            except Exception,msg:
                self.puk_error_label.set_markup('<b>%s</b>' % _("There is a problem with your mobile device. The application can not communicate with it"))
                self.error_hbox.show_all()
                print "Error ask puk: %s" ,msg

        
