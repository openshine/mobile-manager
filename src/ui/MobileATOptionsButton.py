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

import gtk
import gtk.glade
import gobject
import MobileManager.ui
import os
import dbus
import dbus.glib

import MobileManager
from MobileManager.MobileManagerDbus import MOBILE_MANAGER_CONTROLLER_PATH,MOBILE_MANAGER_CONTROLLER_URI,MOBILE_MANAGER_CONTROLLER_INTERFACE_URI,MOBILE_MANAGER_DEVICE_PATH,MOBILE_MANAGER_DEVICE_URI,MOBILE_MANAGER_DEVICE_INFO_INTERFACE_URI,MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI,MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI,MOBILE_MANAGER_DEVICE_XZONE_INTERFACE_URI,MOBILE_MANAGER_DIALER_INTERFACE_URI,MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU


class MobileATOptionsButton(gtk.Button) :
    def __init__(self):
        gtk.Button.__init__(self)

	MobileManager.ui.init_i18n()
        
        self.dbus = None
        self.mm_manager_obj = None
        self.mcontroller = None
        self.mdialer = None
        
        if self.__init_bus() == False:
            return
        
        self.xml = gtk.glade.XML(os.path.join(MobileManager.ui.mobilemanager_glade_path, "mm_menu_at_options.glade"))
        
        self.menu = self.xml.get_widget("menu_pcmcia")
        self.gest_pin_branch = self.xml.get_widget("gest_pin_branch")
        self.gest_pin_branch_menu = self.xml.get_widget("gest_pin_branch_menu")
        self.activate_pin = self.xml.get_widget("activate_pin")
        self.deactivate_pin = self.xml.get_widget("deactivate_pin")
        self.change_pin = self.xml.get_widget("change_pin")
        self.select_tech = self.xml.get_widget("select_tech")
        self.select_tech_menu = self.xml.get_widget("select_tech_menu")
        self.auto_tech = self.xml.get_widget("auto_tech")
        self.only_utms = self.xml.get_widget("only_utms")
        self.preferred_utms = self.xml.get_widget("preferred_utms")
        self.only_gprs = self.xml.get_widget("only_gprs")
        self.preferred_gprs = self.xml.get_widget("preferred_gprs")
        self.select_operator = self.xml.get_widget("select_operator")
        self.select_operator_menu = self.xml.get_widget("select_operator_menu")
        self.auto_oper = self.xml.get_widget("auto_oper")
        self.manual_oper = self.xml.get_widget("manual_oper")
        self.activate_card = self.xml.get_widget("activate_card")
        self.deactivate_card = self.xml.get_widget("deactivate_card")
        
        dict = {"on_pin_activate" : self.__on_pin_activate,
                "on_pin_deactivate" : self.__on_pin_deactivate,
                "on_card_activate" : self.__on_card_activate,
                "on_card_deactivate" : self.__on_card_deactivate,
                "on_change_pin_activate" : self.__on_change_pin_activate,
                "on_auto_tech_activate" : self.__on_auto_tech_activate,
                "on_only_utms_activate" : self.__on_only_utms_activate,
                "on_preferred_utms_activate" : self.__on_preferred_utms_activate,
                "on_only_gprs_activate" : self.__on_only_gprs_activate,
                "on_preferred_gprs_activate" : self.__on_preferred_gprs_activate
                }  
        self.xml.signal_autoconnect(dict)
        

        self.manual_oper_hid = self.manual_oper.connect("toggled",  self.__on_manual_oper_activate)
        self.auto_oper_hid = self.auto_oper.connect("toggled",  self.__on_auto_oper_activate)
        
        self.mcontroller.connect_to_signal("ActiveDevPinActStatusChanged", self.__pin_activate_status_changed_cb)
        self.mcontroller.connect_to_signal("ActiveDevCardStatusChanged", self.__card_status_changed_cb)
        self.mcontroller.connect_to_signal("ActiveDeviceChanged", self.__active_device_changed_cb)


        self.mdialer.connect_to_signal("Connected", self.__connected_cb)
        self.mdialer.connect_to_signal("Disconnected", self.__disconnected_cb)
        
        self.connect("clicked", self.__show_menu_cb, None)

        dev_path = self.mcontroller.GetActiveDevice()
        if dev_path == "" :
            self.set_sensitive(False)
            return
        
        dev_info = self.__get_device_info_from_path(dev_path)
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI) :
            self.set_sensitive(False)
            return
        else:
            if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU) :
                self.set_sensitive(False)
                return 
            
            self.set_sensitive(True)
            dev_state = self.__get_device_state_from_path(dev_path)
            state = dev_state.GetCardStatus()
            self.__card_status_changed_cb(state)

        print "End"

    def __init_bus(self):
        try:
            self.dbus = dbus.SystemBus()
            
            self.mm_manager_obj = self.dbus.get_object(MOBILE_MANAGER_CONTROLLER_URI,
                                                       MOBILE_MANAGER_CONTROLLER_PATH)
            self.mcontroller = dbus.Interface(self.mm_manager_obj,
                                              MOBILE_MANAGER_CONTROLLER_INTERFACE_URI)
            self.mdialer = dbus.Interface(self.mm_manager_obj,
                                          MOBILE_MANAGER_DIALER_INTERFACE_URI)
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

    def __show_menu_cb(self, widget, data):
        self.popup(self)

    def __card_status_changed_cb(self, status):
        dev_path = self.mcontroller.GetActiveDevice()
        if dev_path == "" :
            self.set_sensitive(False)
            return

        dev_info = self.__get_device_info_from_path(dev_path)
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI):
            self.set_sensitive(False)
            return

        if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU) :
            self.set_sensitive(False)
            return False


        dev_state = self.__get_device_state_from_path(dev_path)
        dev_auth =  self.__get_device_auth_from_path(dev_path)
        
        self.set_sensitive(True)
        
        self.set_sensitive_all_options(False)

        if status == None :
            status = dev_state.GetCardStatus()
        
        if status == MobileManager.CARD_STATUS_READY or status == MobileManager.CARD_STATUS_ATTACHING:
            self.set_sensitive_tech_options(True)
            self.set_sensitive_operator_options(True)

        if status == MobileManager.CARD_STATUS_READY :
            if dev_auth.IsPINActive():
                self.deactivate_pin.show()
                self.activate_pin.hide()
                self.set_sensitive_pin_options(True)
            else:
                self.deactivate_pin.hide()
                self.activate_pin.show()
                self.set_sensitive_pin_options(False)
                self.activate_pin.set_sensitive(True)

            self.auto_oper.handler_block(self.auto_oper_hid)
            self.manual_oper.handler_block(self.manual_oper_hid)
            if dev_state.IsCarrierAuto() == True:
                self.auto_oper.set_active(True)
                self.manual_oper.set_active(False)
            else:
                self.auto_oper.set_active(False)
                self.manual_oper.set_active(True)
                
            self.auto_oper.handler_unblock(self.auto_oper_hid)
            self.manual_oper.handler_unblock(self.manual_oper_hid)
            
        else:
            self.deactivate_pin.hide()
            self.activate_pin.show()
            self.set_sensitive_pin_options(False)
            
        if dev_state.IsOn() :
            self.activate_card.hide()
            self.deactivate_card.show()
        else:
            self.activate_card.show()
            self.deactivate_card.hide()
            

    def __active_device_changed_cb(self, device):
        dev_path = self.mcontroller.GetActiveDevice()
        if dev_path == "" :
            self.set_sensitive(False)
            return
        
        dev_info = self.__get_device_info_from_path(dev_path)
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI) :
            self.set_sensitive(False)
            return
        else:
            if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU) :
                self.set_sensitive(False)
                return
            
            self.set_sensitive(True)
            dev_state = self.__get_device_state_from_path(dev_path)
            state = dev_state.GetCardStatus()
            self.__card_status_changed_cb(state)

    def __pin_activate_status_changed_cb(self, status):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state = self.__get_device_state_from_path(dev_path)
        state = dev_state.GetCardStatus()
        self.__card_status_changed_cb(state)
        
    def popup(self, widget=None):
        dev_path = self.mcontroller.GetActiveDevice()
        if dev_path == "" :
            return
        
        dev_info = self.__get_device_info_from_path(dev_path)
        
        if not dev_info.HasCapability(MOBILE_MANAGER_DEVICE_AUTH_INTERFACE_URI) :
            return False

        if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_NO_OPTIONS_MENU) :
            return False


        if widget == None :
            self.menu.popup(None, None, self.__widget_pos, 0, 0, data=self)
        else:
            self.menu.popup(None, None, self.__widget_pos, 0, 0, data=widget)
        
        self.menu.show()
        return True

    def set_active(self, value):
        self.menu_activated = value
        
    def set_sensitive_all_options(self, value):
        self.set_sensitive_tech_options(value)
        self.set_sensitive_pin_options(value)
        self.set_sensitive_operator_options(value)

    def set_sensitive_tech_options(self, value):
        self.auto_tech.set_sensitive(value)
        self.only_utms.set_sensitive(value)
        self.preferred_utms.set_sensitive(value)
        self.only_gprs.set_sensitive(value)
        self.preferred_gprs.set_sensitive(value)

    def set_sensitive_pin_options(self, value):
        self.activate_pin.set_sensitive(value)
        self.deactivate_pin.set_sensitive(value)
        self.change_pin.set_sensitive(value)

    def set_sensitive_operator_options(self, value):
        self.auto_oper.set_sensitive(value)
        self.manual_oper.set_sensitive(value)
    
    def __widget_pos(self, widget, data):
        widget_window = data.window
        x, y = widget_window.get_position()
        widget_rect = data.get_allocation()
        return (x+widget_rect.x, y+widget_rect.y+widget_rect.height, True)

    def __on_toogle_pin_activate (self, widget):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_auth =  self.__get_device_auth_from_path(dev_path)
        pin_status = dev_auth.IsPINActive()
        if pin_status == None:
            return
        
        dialog = MobileManager.ui.MobileManagePinDialog()
        if pin_status == True:
            dialog.run_deactivate()
        else:
            dialog.run_activate()
        self.menu.hide()

    def __on_pin_activate (self, widget):
        dialog = MobileManager.ui.MobileManagePinDialog()
        dialog.run_activate()
        
        self.menu.hide()
        
    def __on_pin_deactivate (self, widget):
        dialog = MobileManager.ui.MobileManagePinDialog()
        dialog.run_deactivate()
        
        self.menu.hide()

    def __on_change_pin_activate (self, widget):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_auth =  self.__get_device_auth_from_path(dev_path)
        pin_status = dev_auth.IsPINActive()
        
        if pin_status == None:
            return
        
        if pin_status == True:
            dialog = MobileManager.ui.MobileChangePinDialog()
            dialog.run()
        
        self.menu.hide()

    def __on_card_activate(self, widget):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI):
            dev_state =  self.__get_device_state_from_path(dev_path)
            dev_state.TurnOn()

    def __on_card_deactivate(self, widget):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        if dev_path != "":
            if self.mdialer.Status() != MobileManager.PPP_STATUS_DISCONNECTED :
               self.mdialer.Stop()
               gobject.timeout_add(1500, self.__on_card_deactivate_timeout, 6)
               return
               
            if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI):
                dev_state =  self.__get_device_state_from_path(dev_path)
                dev_state.TurnOff()

    def __on_card_deactivate_timeout(self, attempt):
        print "Deactivate timeout (attempt = %s)" % attempt
        dev_path = self.mcontroller.GetActiveDevice()
        
        if attempt == 0 :
            dev_state = self.__get_device_state_from_path(dev_path)
            dev_state.TurnOff()
            return False
        
        dev_info = self.__get_device_info_from_path(dev_path)
        if dev_path != "":
            if self.mdialer.Status() == MobileManager.PPP_STATUS_DISCONNECTED :
                dev_state =  self.__get_device_state_from_path(dev_path)
                dev_state.TurnOff()
                return False
            else:
                gobject.timeout_add(1000, self.__on_card_deactivate_timeout, attempt - 1)
                return False
        
        return False
            
    def __on_auto_tech_activate (self, widget):
        self.menu.hide()
        if self.auto_tech.get_active() != True:
            return
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetModeDomain(MobileManager.CARD_TECH_SELECTION_AUTO, MobileManager.CARD_DOMAIN_CS_PS)

    def __on_only_utms_activate (self, widget):
        self.menu.hide()
        if self.only_utms.get_active() != True:
            return
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetModeDomain(MobileManager.CARD_TECH_SELECTION_UMTS, MobileManager.CARD_DOMAIN_CS_PS)

    def __on_preferred_utms_activate (self, widget):
        self.menu.hide()
        if self.preferred_utms.get_active() != True:
            return
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetModeDomain(MobileManager.CARD_TECH_SELECTION_UMTS_PREFERED, MobileManager.CARD_DOMAIN_CS_PS)

    def __on_only_gprs_activate (self, widget):
        self.menu.hide()
        if self.only_gprs.get_active() != True:
            return
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetModeDomain (MobileManager.CARD_TECH_SELECTION_GPRS, MobileManager.CARD_DOMAIN_CS_PS)

    def __on_preferred_gprs_activate (self, widget):
        self.menu.hide()
        if self.preferred_gprs.get_active() != True:
            return
        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetModeDomain(MobileManager.CARD_TECH_SELECTION_GRPS_PREFERED, MobileManager.CARD_DOMAIN_CS_PS)

    def __on_auto_oper_activate (self, widget):
        
        self.menu.hide()
        self.auto_oper.handler_block(self.auto_oper_hid)
        self.manual_oper.handler_block(self.manual_oper_hid)
        self.manual_oper.set_active(False)
        self.auto_oper.set_active(True)
        self.manual_oper.handler_unblock(self.manual_oper_hid)
        self.auto_oper.handler_unblock(self.auto_oper_hid)

        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        dev_state.SetCarrierAutoSelection()

            
    def __on_manual_oper_activate (self, widget):
        if self.manual_oper.get_active() == False :
            if self.auto_oper.get_active() != False :
                return
        
        self.menu.hide()

        dev_path = self.mcontroller.GetActiveDevice()
        dev_state =  self.__get_device_state_from_path(dev_path)
        
        dialog = MobileManager.ui.MobileCarrierSelectorDialog()
        res = dialog.run()
        
        self.auto_oper.handler_block(self.auto_oper_hid)
        self.manual_oper.handler_block(self.manual_oper_hid)
        if not dev_state.IsAttached():
            print "-------> Set radio to AUTO_OPER = True"
            dev_state.SetCarrierAutoSelection()
            self.auto_oper.set_active(True)
            self.manual_oper.set_active(False)
        else:
            print "-------> Set radio to MANUAL_OPER = True"
            self.manual_oper.set_active(True)
            self.auto_oper.set_active(False)
        
        self.auto_oper.handler_unblock(self.auto_oper_hid)
        self.manual_oper.handler_unblock(self.manual_oper_hid)


    def __connected_cb (self):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI) :
            self.set_sensitive_all_options(False)
            self.deactivate_card.show()
            self.activate_card.hide()

    def __disconnected_cb (self):
        dev_path = self.mcontroller.GetActiveDevice()
        dev_info = self.__get_device_info_from_path(dev_path)
        if dev_info.HasCapability(MOBILE_MANAGER_DEVICE_STATE_INTERFACE_URI) :
            self.__card_status_changed_cb(None)

gobject.type_register(MobileATOptionsButton)
