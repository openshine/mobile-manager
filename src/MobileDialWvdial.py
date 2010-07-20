#!/usr/bin/python
# -*- coding: iso-8859-15 -*-
#
# Authors : Roberto Majadas <roberto.majadas@openshine.com>
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
import time
from subprocess import Popen, PIPE
from MobileDial import *
import StringIO
import MobileManager
import re

from MobileManager.MobileCapabilities import *

from MobileManager import MobileDeviceIO

class MobileDialWvdial(MobileDial):

    def __init__(self, mcontroller):

        self.wvdial_conf_file = "/var/tmp/mobile-manager.conf"
        self.wvdial_p = None
        self.wvdial_pid = None
        self.pppd_pid = None
        self.ppp_if = None
        self.last_traffic_time = 0.0
        self.dns_data = None
        self.status_flag = PPP_STATUS_DISCONNECTED
        self.active_device = None
         
        self.__upower_actions()

        MobileDial.__init__(self, mcontroller)

    def status(self):
        return self.status_flag

    def start(self, username, password, apn, auto_dns, primary_dns, secundary_dns, dns_suffixes):
        print "DAEMON ----> dns info %s, %s, %s" % (primary_dns, secundary_dns, dns_suffixes)

        if self.status_flag != PPP_STATUS_DISCONNECTED :
            return 
        
        wvdial_conf = "[Dialer Defaults]\n"
        wvdial_conf = wvdial_conf + "Phone = *99***1#\n"
        wvdial_conf = wvdial_conf + "Stupid Mode = 1\n"
        wvdial_conf = wvdial_conf + "Dial Command = ATDT\n"
        wvdial_conf = wvdial_conf + "Modem Type = Analog Modem\n"
        wvdial_conf = wvdial_conf + "ISDN = 0\n"
        wvdial_conf = wvdial_conf + "Dial Attempts = 3\n"
        wvdial_conf = wvdial_conf + "Init1 = ATZ\n"
        #wvdial_conf = wvdial_conf + "Init2 = ATQ0 V1 E1 S0=0 &C1 &D2 +FCLASS=0\n"
        
        init5 = 'Init2 = AT+CGDCONT=1,"IP","%s","0.0.0.0",0,0;\n' % apn
        wvdial_conf = wvdial_conf + init5
        
        self.active_device = self.mcontroller.get_active_device()

        if self.active_device == None :
            return
        else:
            if AT_COMM_CAPABILITY in self.active_device.capabilities :
                multi_port = self.active_device.get_property("multiport-device")
                if multi_port == False :
                    self.active_device.stop_polling()

        data_device = self.active_device.get_property("data-device")
        velocity = self.active_device.get_property("velocity")

        wvdial_conf = wvdial_conf + "Modem = %s\n" % data_device
        wvdial_conf = wvdial_conf + "Baud = %s\n" % velocity
        
        
        hfc = self.active_device.get_property('hardware-flow-control')
        hec = self.active_device.get_property('hardware-error-control')
        hc = self.active_device.get_property('hardware-compress')

        if username != "" :
            wvdial_conf = wvdial_conf + "Username = %s\n" % username
        else:
            wvdial_conf = wvdial_conf + "Username = ''\n"

        if password != "" :
            wvdial_conf = wvdial_conf + "Password = %s\n" % password
        else:
            wvdial_conf = wvdial_conf + "Password = ''\n"

        if auto_dns == False:
            wvdial_conf = wvdial_conf + "Auto DNS = 0\n"
            self.dns_data = [primary_dns, secundary_dns, dns_suffixes]
        else:
            wvdial_conf = wvdial_conf + "Auto DNS = 1\n"

        os.system("rm -f %s" % self.wvdial_conf_file)
        fd = open(self.wvdial_conf_file, "w")
        fd.write(wvdial_conf)
        fd.close()

        self.__pppd_options(hfc, hec, hc, auto_dns)
            
        self.__start_wvdial()

    def __detect_roaming(self):
        print "__detect_roaming"

        if not os.path.exists(self.active_device.get_property("data-device")) :
            return

        data_dev = self.active_device.get_property("data-device")
        if data_dev.startswith("/dev/rfcomm") == True:
            return
        
        io = MobileDeviceIO(self.active_device.get_property("data-device"))
        io.open()
        io.write("AT+CGREG?\r")

        self.active_device.dbg_msg("DETECTING ROAMING SUPPORT (AT+CGREG?)")

        attempts = 2
        res = io.readline()
        while attempts != 0 :
            self.active_device.dbg_msg ("Recv from DATA PORT : %s" % res)
            if res == "OK" :
                return
            elif "ERROR" in res :
                return
            elif res.startswith("+CGREG"):
                pattern = re.compile("\+CGREG:.*,(?P<state>\d+)")
                matched_res = pattern.match(res)
                if matched_res != None:
                    if matched_res.group("state") == "5" :
                        self.active_device.dbg_msg ("YES ROAMING")
                        self.active_device.cached_status_values["is_roaming"] = True
                        self.mcontroller.emit('active-dev-roaming-status-changed', True)
                        self.mcontroller.emit('dev-roaming-status-changed', self.active_device.dev_props["info.udi"], True)
                    else:
                        self.active_device.dbg_msg ("NO ROAMING")
                        self.active_device.cached_status_values["is_roaming"] = False
                        self.mcontroller.emit('active-dev-roaming-status-changed', False)
                        self.mcontroller.emit('dev-roaming-status-changed', self.active_device.dev_props["info.udi"], False)
            
            res = io.readline()
            attempts = attempts - 1

        io.close()
        

    def __pppd_options(self, hfc, hec, hc, auto_dns):
        print "__pppd_options"
        
        out = StringIO.StringIO()
        
        if os.system ("test -f /etc/SuSE-release && test 1 == $(/usr/bin/lsb_release -r | grep 11.2 | wc -l)") == 0 :
            print >>out,"plugin passwordfd.so"

        if os.system ("test -f /etc/SuSE-release && test 1 == $(/usr/bin/lsb_release -r | grep 11.3 | wc -l)") == 0 :
            print >>out,"plugin passwordfd.so"

        print >>out,"debug"
        print >>out,"noauth"
        print >>out,"name wvdial"
        if os.path.exists("/etc/debian_version") :
            print >>out,"replacedefaultroute"
        else:
            os.system("/sbin/route del default")
            print >>out,"defaultroute"
        print >>out,"nomagic"
        print >>out,"ipcp-accept-local"
        print >>out,"ipcp-accept-remote"
        print >>out,"lcp-echo-failure 0"
        print >>out,"kdebug 7"

        ## print >>out, "defaultroute"
        ## print >>out, "nodetach"
        ## print >>out, "noauth"
        ## print >>out, "debug"
        ## print >>out, "noipdefault"
        ## print >>out, "ipcp-accept-local"
        ## print >>out, ":10.0.0.1"
        ## print >>out, "lcp-echo-failure 0"
        ## print >>out, "kdebug 7"

        if auto_dns == True:
            print >>out, "usepeerdns"

        if hfc == True :
            print >>out, "crtscts"
        else:
            print >>out, "nocrtscts"
            
        if hc == False:
            print >>out, "novj"
            print >>out," nobsdcomp"
            print >>out, "novjccomp"
            print >>out, "nopcomp"
            print >>out, "noaccomp"
            
        peer_filename_path = "/etc/ppp/peers/wvdial"
        try:
            f = open(peer_filename_path,"w")
            f.write(out.getvalue())
        finally:
            out.close()
            f.close()


    def __get_real_wvdial_pid(self):
        cmd = "ps -eo ppid,pid | grep '^[ ]*%s' | awk '{print $2}'" % self.wvdial_p.pid
        pm =  Popen(cmd, shell=True, stdout=PIPE, close_fds=True)

        ret = pm.stdout.readline().strip("\n")
        if ret != "" :
            return ret
        else:
            return None

    def __start_wvdial(self):
        print "Starting Wvdial"
        if os.path.exists("/etc/fedora-release") :
            try:
                os.system("/etc/init.d/NetworkManager stop")
                if self.dns_data == None:
                    os.system("echo 'PEERDNS=yes' > /etc/sysconfig/network-scripts/ifcfg- ")
                    os.system("echo 'DEFROUTE=yes' >> /etc/sysconfig/network-scripts/ifcfg- ")
            except:
                print "No network manager to stop"

        self.emit('connecting')
        self.status_flag = PPP_STATUS_CONNECTING
        
        self.active_device.set_using_data_device(True)
        
        cmd = "/usr/bin/wvdial -C %s" % self.wvdial_conf_file
        self.wvdial_p = Popen(cmd, shell=True, stdin=PIPE, stdout=PIPE,
                              stderr=PIPE, close_fds=True)
         
        gobject.timeout_add(1, self.__wvdial_monitor)
        gobject.timeout_add(3000, self.__pppd_monitor)

    def __wvdial_monitor(self):
        self.__real_wvdial_monitor()
        gobject.timeout_add(2000, self.__real_wvdial_monitor)
        return False

    def __real_wvdial_monitor(self):
        if self.wvdial_p.poll() == None :
            print "Wvdial monitor : Wvdial running"
            return True
        else:
            print  "Wvdial monitor : Wvdial killed"
            self.wvdial_p = None
            self.wvdial_p = None
            self.wvdial_pid = None
            self.pppd_pid = None
            self.ppp_if = None
            self.last_traffic_time = 0.0
            self.dns_data = None
            self.status_flag = PPP_STATUS_DISCONNECTED

            if self.active_device != None :
                if MobileManager.AT_COMM_CAPABILITY in self.active_device.capabilities :
                    #Some devices need reopen port when wdial is killed
                    self.active_device.set_using_data_device(False)
                    self.active_device.serial.reopen()
                    self.active_device.start_polling()

            if os.path.exists("/etc/fedora-release") :
                try:
                    os.system("/etc/init.d/NetworkManager start")
                    if os.path.exists("/etc/sysconfig/network-scripts/ifcfg-") :
                        os.system("rm -f /etc/sysconfig/network-scripts/ifcfg-")
                except:
                    print "No network manager to start"
            elif os.path.exists("/etc/SuSE-release"):
                try:
                    os.system("/etc/init.d/network restart")
                except:
                    print "No network to start"

            print "emit disconnected"
            self.emit('disconnected')
            
            if os.path.exists("/etc/resolv.conf.mm") :
                os.system("mv /etc/resolv.conf.mm /etc/resolv.conf")
                
            return False
        
    def __pppd_monitor(self):
        if self.status_flag == PPP_STATUS_DISCONNECTING or self.status_flag == PPP_STATUS_DISCONNECTED :
            print "pppd monitor stopped, status disconnecting or disconected"
            self.pppd_pid == None
            self.ppp_if = None
            return False
        
        if self.wvdial_p == None:
            print "pppd monitor stopped, not wvdial running"
            return False
        elif self.wvdial_p.poll() != None:
            print "pppd monitor stopped, not wvdial running"
            return False
        
        if self.pppd_pid == None :
            if self.wvdial_pid == None :
                if os.path.exists("/etc/debian_version") :
                    self.wvdial_pid = self.__get_real_wvdial_pid()
                else:
                    self.wvdial_pid = self.wvdial_p.pid
                print "--------> WVDIAL PID %s" % self.wvdial_pid
                if self.wvdial_pid == None :
                    return True
                
            print  "pppd monitor : looking for pppd"
            cmd = "ps -eo ppid,pid | grep '^[ ]*%s' | awk '{print $2}'" % self.wvdial_pid
            pm =  Popen(cmd, shell=True, stdout=PIPE, close_fds=True)

            pppd_pid = pm.stdout.readline().strip("\n")
            
            if pppd_pid != "" :
                self.pppd_pid = pppd_pid
                print "--------> PPPD PID %s" % self.pppd_pid
                
                wvdial_stderr = self.wvdial_p.stderr
                while True:
                    tmp_str = wvdial_stderr.readline()
                    if "Using interface" in tmp_str :
                        self.ppp_if = tmp_str.split()[-1]
                        print  "pppd monitor : %s" % self.ppp_if
                        break
                
            return True
        elif self.ppp_if != None :
            print  "pppd monitor : looking for ip"
            cmd = "LANG=C ifconfig %s | grep 'inet addr'" % self.ppp_if
            pm =  Popen(cmd, shell=True, stdout=PIPE, close_fds=True)
            out = pm.stdout.readline()
            if out != "" :
                print  "pppd monitor : pppd connected"
                self.emit('connected')
                self.__set_dns_info()
                self.status_flag = PPP_STATUS_CONNECTED
                gobject.timeout_add(2000, self.__stats_monitor)
                return False
            else:
                return True
        else:
            return True

    def __set_dns_info(self):
        print "-----> __set_dns_info (%s)" % self.dns_data
        if self.dns_data == None :
            return
        
        os.system("cp /etc/resolv.conf /etc/resolv.conf.mm")
        
        os.system("echo ';Mobile manager dns data' > /etc/resolv.conf")
        if self.dns_data[2] != "" :
            os.system("echo 'search %s' >> /etc/resolv.conf" % self.dns_data[2])

        if self.dns_data[0] != "" :
            os.system("echo 'nameserver %s' >> /etc/resolv.conf" % self.dns_data[0])

        if self.dns_data[1] != "" :
            os.system("echo 'nameserver %s' >> /etc/resolv.conf" % self.dns_data[1])

    def __parse_stats_response(self):
        cmd = "cat /proc/net/dev | grep %s | sed s/.*://g | awk '{print $1; print $9}'" % self.ppp_if
        pm =  Popen(cmd, shell=True, stdout=PIPE, close_fds=True)
        rb = pm.stdout.readline().strip("\n")
        tb = pm.stdout.readline().strip("\n")

        if rb == "" and tb == "" :
            return 0, 0
        else:
            return int(rb) , int(tb)           

    def __stats_monitor(self):
        if self.status_flag == PPP_STATUS_DISCONNECTING or self.status_flag == PPP_STATUS_DISCONNECTED :
            print "stats monitor stopped, status flag disconnecting or disconnected"
            return False
            
        if self.wvdial_p == None:
            print "stats monitor stopped, not wvdial running"
            return False
        elif self.wvdial_p.poll() != None:
            print "stats monitor stopped, not wvdial running"
            return False
        
        if self.ppp_if == None :
            return False
        
        recived_bytes , sent_bytes = self.__parse_stats_response()
        if self.last_traffic_time == 0.0 :
            self.last_traffic_time = time.time()
        else:
            if recived_bytes > 0 and sent_bytes > 0 :
                new_time = time.time()
                interval_time = new_time - self.last_traffic_time
                self.last_traffic_time = new_time
                if self.status_flag == PPP_STATUS_CONNECTED :
                    self.emit("pppstats_signal", recived_bytes, sent_bytes, interval_time)
                    print "stats monitor : %i %i %d" % (recived_bytes, sent_bytes, interval_time)

        return True
    
    def stop(self):
        print "Stopping pppd"

        if self.wvdial_p == None:
            print "Stop : no wvdial_p"  
            return
        elif self.wvdial_p.poll() != None:
            print "Stop : wvdial_p.poll() != None"
            return
            
        
        if self.wvdial_pid != None :
            
            if self.active_device != None :
                if MobileManager.AT_COMM_CAPABILITY in self.active_device.capabilities :
                    self.active_device.stop_polling()
             
            print "emit disconnecting"
            self.emit('disconnecting')
            self.status_flag = PPP_STATUS_DISCONNECTING
            print "kill -15 %s" % self.wvdial_pid
            os.kill(int(self.wvdial_pid), 15)
            
        elif self.wvdial_p != None :
            if os.path.exists("/etc/debian_version") :
                self.wvdial_pid = self.__get_real_wvdial_pid()
            else:
                self.wvdial_pid = self.wvdial_p.pid
            
            self.emit('disconnecting')
            print "emit disconnecting"
            self.status_flag = PPP_STATUS_DISCONNECTING
            
            if self.active_device != None :
                if MobileManager.AT_COMM_CAPABILITY in self.active_device.capabilities :
                    self.active_device.stop_polling()
            
            print "kill -15 %s" % self.wvdial_pid
            os.kill(int(self.wvdial_pid), 15)
        
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
        self.stop()

    def __upower_resuming_cb(self):
        print "%s ---> Resuming" % self
