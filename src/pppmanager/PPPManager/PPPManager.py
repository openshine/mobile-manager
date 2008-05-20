#
# Authors : Roberto Majadas <roberto.majadas@openshine.com>
#           Oier Blasco <oierblasco@gmail.com>
#           Alvaro Peña <alvaro.pena@openshine.com>
#
# Copyright (c) 2003-2007, Telefonica Móviles España S.A.U.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or (at your option) any later version.

# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Library General Public License for more details.

# You should have received a copy of the GNU General Public
# License along with this library; if not, write to the Free
# Software Foundation, Inc., 675 Mass Ave, Cambridge, MA 02139, USA.
#
import dbus
import dbus.service
import gobject
if getattr(dbus, 'version', (0,0,0)) >= (0,41,0):
    import dbus.glib

import os
import random
import logging
from pppshared import *
import gobject
import popen2
import signal
import StringIO
import signal
import time

LOG_LEVEL = logging.DEBUG
PPPD_LOG_TAG = "pppd"
CHAT_LOG_TAG ="chat"
MOVISTAR_PEER_FILENAME ="escritorio-movistar"
MOVISTAR_CHAT_FILENAME ="escritorio-movistar-chat"
CHAP_SECRETS_FILENAME ="chap-secrets"
PAP_SECRETS_FILENAME ="pap-secrets"
fake_pppd_stats_response =""" IN   PACK VJCOMP  VJUNC  VJERR  |      OUT   PACK VJCOMP  VJUNC NON-VJ
      60      6      0      0      0  |      510     13      0      0     13"""


def write_section_of_file(section_name,file_name,data):
    f = open(file_name,"r")
    lines = f.readlines()
    f.close()

    #busco el indice de comienzo de seccion y final
    begin_section_offset =  end_section_offet = -1
    begin_section_tag = "# BEGIN - %s -\n" % section_name
    end_section_tag = "# END - %s -\n" % section_name 
    line_count = 0

    for line in lines:
        if line.find(begin_section_tag) != -1:
            begin_section_offset = line_count
        if line.find(end_section_tag) != -1:
            end_section_offet = line_count
        line_count = line_count +1 

    section_lines = [begin_section_tag,data,end_section_tag]


    if begin_section_offset != -1  and end_section_offet != -1:
        #se ha encontrado la seccion la creo
        output_lines =  lines[:begin_section_offset] + section_lines   +lines[end_section_offet + 1:]
    else:
        #no se ha encontrado concateno
        output_lines = lines + section_lines
    
    f = open(file_name,"w")
    f.writelines(output_lines)
    f.close()

    
class FileMonitor:

    def __init__(self,file_name,delegate):
        self.file_name = file_name
        self.file = None
        self.delegate = delegate
        self.timeout_id = None
        self.running = False
        self.input_id = None
        
    def start(self):
        self.file = open(self.file_name,"r")
        st_result = os.stat(self.file_name)
        st_size = st_result[6]
        self.file.seek(st_size)
        self.input_id = gobject.timeout_add(1000,self.read_cb)
        self.running = True
        self.previous_read_unfinished_line = None
        

    def stop(self):
        self.running = False
        if self.input_id :
            gobject.source_remove(self.input_id)
        if self.file is not None and not self.file.closed:
            self.file.close()
            self.file =None
            
    def read_cb(self):
        if not self.running:
            return False
        lines = self.file.readlines()
        if not lines or len(lines) < 1:
            return True

        last_line = lines[-1:][0]

        if self.previous_read_unfinished_line is not None:
            lines[0] = self.previous_read_unfinished_line + lines[0] 
            self.previous_read_unfinished_line = None
            
        if not last_line.endswith("\n"):
            #linea que no se ha finalizado
            self.previous_read_unfinished_line = last_line
            lines = lines [:-1]

        self.delegate.process_lines(lines)
        return True


class ComandOutputMonitor:

    def __init__(self,cmd,callback):
        self.cmd = cmd
        self.running = False
        self.timeout_id =None
        self.callback = callback
        

    def start(self,period=1000):
        self.timeout_id = gobject.timeout_add(period,self.__timeout_cb)
        self.running = True
        
    def stop(self):
        if self.timeout_id is None:
            return 
        gobject.source_remove(self.timeout_id)
        self.timeout_id = None
        self.running = False

    def __timeout_cb(self):
        if not self.running :
            return False
        p = os.popen(self.cmd)
        response = p.readlines()
        error_code = p.close()
        if callable(self.callback):
            self.callback(response)
        return True
    
class ProcesMonitor:

    def __init__(self,cmd_path,delegate):
        self.running = False
        self.cmd_path  = cmd_path
        self.child = None
        self.timeout_id = None
        self.delegate = delegate
        
    def start(self,parameters=""):
        cmd_line = "%s %s" %(self.cmd_path,parameters)
        self.child =popen2.Popen3(cmd_line)
        self.running = True
        self.timeout_id = gobject.timeout_add(1000,self.timer_cb)
        return self.child.pid
    
    def stop(self):
        if  self.child is None:
            return False
        
        if  self.child.poll() != -1:
            self.child = None
            return False
        try:
            if os.path.exists("/etc/debian_version") :
                print "matando ppp"
                time.sleep(5)
                os.system("poff escritorio-movistar")
                print "esperando ppp"
                time.sleep(5)
                #self.child.wait()
                print "reiniciando red"
                #os.spawnlp(os.P_NOWAIT,"/etc/init.d/networking","networking","restart")
            
                self.running =False
                self.child = None
                return True
            else:
                print "matando ppp"
                os.kill(self.child.pid,signal.SIGKILL)
                print "esperando ppp"
                self.child.wait()
                print "reiniciando red"
                os.spawnlp(os.P_NOWAIT,"/etc/init.d/network","network","restart")
                
                self.running =False
                self.child = None
                return True  

        
        except Exception , msg:
            self.child = None
            return False
        
        


    def timer_cb(self):
        if not self.running:
            return False

        if self.child is None:
            self.running = False
            return False
        
        if self.child.poll() !=-1:
            #ha muerto el proceso
            print "Se ha muerto el pppd"
            self.delegate.process_died()  
            self.child = None
            self.running = False
            return False

        return True
    
    
class PPPHelper(dbus.service.Object):
    """
    Levanta y apaga el pppd
    """
    def __init__(self,
                 bus_name,
                 object_path=PPP_MANAGER_OBJECT_PATH,
                 ppp_conf_dir="/etc/ppp",
                 ppp_executable_path="/usr/sbin/pppd",
                 ppp_log_path="/var/log/messages"):

        dbus.service.Object.__init__(self,
                                     bus_name,
                                     object_path)
                        
        self.init_log()
        self.timer_id = None
        self.status = PPP_STATUS_DISCONNECTED
        self.last_traffic_time = 0.0
        self.ppp_executable_path = ppp_executable_path
        self.ppp_conf_dir = ppp_conf_dir
        self.ppp_log_path = ppp_log_path
        self.log_monitor = FileMonitor(self.ppp_log_path,self)
        self.pppd_monitor = ProcesMonitor(self.ppp_executable_path,self)
        self.ppp_stats_monitor = ComandOutputMonitor("/usr/sbin/pppstats",self.stats_cb)
        self.log.info("PPPManger iniciado")
        signal.signal(signal.SIGTERM,self.__signal_handler)

    def __signal_handler(self,signum,frame):
        self.log.info("recibida snial ")

        
    def stats_cb(self,response):
        self.log.debug("Comienzo")
        try:
            if response is None :
                return
            if len(response) < 2 :
                return


            recived_bytes , sent_bytes = self.__parse_stats_response(response)
            if self.last_traffic_time == 0.0 :
                self.last_traffic_time = time.time()
            else:
                if recived_bytes > 0 and sent_bytes > 0 :
                    new_time = time.time()
                    interval_time = new_time - self.last_traffic_time
                    self.last_traffic_time = new_time
                    self.pppstats_signal(recived_bytes,sent_bytes, interval_time)
        finally:
            self.log.debug("Fin de stats_cb")
            return True


    def __parse_stats_response(self,response):
        raw_line = response[1]
        self.log.debug("stas raw line %s", raw_line)
        frags = raw_line.split()
        inbytes = int(frags[0]) 
        outbytes = int (frags[6])
        return inbytes ,outbytes
        
            
        
        
    @dbus.service.method(PPP_MANAGER_INTERFACE_NAME)    
    def start(self,parameters):
        self.log.info("Iniciando conexion")
        self.last_traffic_time = 0.0
        try:
            self.connecting_signal()
            self.prepare_scripts(parameters)
            self.log_monitor.start()
            self.pppd_monitor.start("call %s" % MOVISTAR_PEER_FILENAME)
        except Exception , msg:
            self.log.error("inicializando conexion: %s" % msg)
            self.stop()
        
    @dbus.service.method(PPP_MANAGER_INTERFACE_NAME)    
    def stop(self):
        self.last_traffic_time = 0.0
        self.disconnecting_signal()
        self.log_monitor.stop()
        self.pppd_monitor.stop()
        self.disconnected_signal()

    @dbus.service.method(PPP_MANAGER_INTERFACE_NAME)
    def status(self):
        return self.status

    
    @dbus.service.signal(PPP_MANAGER_INTERFACE_NAME)    
    def connecting_signal(self):
        self.log.debug("Enviando conectando..")
        self.status = PPP_STATUS_CONNECTING
        
    
    @dbus.service.signal(PPP_MANAGER_INTERFACE_NAME)
    def connected_signal(self):
        self.ppp_stats_monitor.start(period=2000)
        self.log.debug("Enviando conectado")
        self.status = PPP_STATUS_CONNECTED
        
        
    @dbus.service.signal(PPP_MANAGER_INTERFACE_NAME)
    def disconnecting_signal(self):
        self.log.debug("Enviando desconectando..")
        self.ppp_stats_monitor.stop()
        self.status = PPP_STATUS_DISCONNECTING
        
        
    @dbus.service.signal(PPP_MANAGER_INTERFACE_NAME)
    def disconnected_signal(self):
        self.log.debug("Enviando deconectando")
        self.status = PPP_STATUS_DISCONNECTED

    @dbus.service.signal(PPP_MANAGER_INTERFACE_NAME)
    def pppstats_signal(self,recived_bytes,sent_bytes, interval_time):
        self.log.debug("Enviando stats")

        


    def init_log(self):
        self.log  = logging.getLogger('em-ppp-helper')
        hdlr = logging.FileHandler("/var/log/em-ppp-helper.log")
        formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        hdlr.setFormatter(formatter)
        self.log.addHandler(hdlr)
        self.log.setLevel(LOG_LEVEL)

    def prepare_scripts(self,connection_parameters):
        """
        Prepara los scripts de conexion para los paramtros especificados
        retorna un string con el nombre del fichero peer que se debe usar para la conexion
        """
        self.log.debug("Preparando los scripte")
        #create peer file
        self.create_peer_file(connection_parameters)
        
        #create chat file
        self.create_chat_file(connection_parameters)
        
        #create secret file
        self.create_secret__file(connection_parameters)

        #update route
        os.system("/sbin/route del default")

        #update dns 
        if connection_parameters.get(PPP_PARAM_AUTO_DNS_KEY,"NO") =="NO":
           self.create_dns_file(connection_parameters) 

        #update proxy
        if connection_parameters.get(PPP_PARAM_USE_PROXY_KEY,"NO") == "YES":
            proxy = connection_parameters.get(PPP_PARAM_PROXY_ADDRESS_KEY,"").strip()
            port  = connection_parameters.get(PPP_PARAM_PROXY_PORT_KEY,"").strip()
            if proxy != "" and port != "":
                os.system("gconftool-2 -t string -s /system/http_proxy/host %s" % str(proxy))
                os.system("gconftool-2 -t int -s /system/http_proxy/port %s" % str(port)) 
    
        
    def create_dns_file(self, connection_parameters):
        self.log.debug("Preparando dns")
        try:
            file_path = "/etc/resolv.conf"
            f = open(file_path,"w")
            f.write(";creado por Escritorio movistar\n")
        
            #creo los dns sufix
            suffixes_raw = connection_parameters.get(PPP_PARAM_DNS_SUFFIX_KEY,"").strip()
            suffixes = suffixes_raw.split(",")
            self.log.debug("Preparando dominios de busqueda raw =%s" % suffixes_raw)
            if len(suffixes) > 1 :
                self.log.debug("Escribiendo dominios de busqueda")
                search_line = "search %s \n" % " ".join(suffixes) 
                f.write(search_line)
            primary_server = connection_parameters.get(PPP_PARAM_PRIMARY_DNS_KEY,"")
            secondary_server =  connection_parameters.get(PPP_PARAM_SECUNDARY_DNS_KEY,"")
            f.write("nameserver %s\n" % primary_server)
            f.write("nameserver %s\n" %  secondary_server)
        finally:
            f.close()

    def create_peer_file(self,connection_parameters):
        self.log.debug("creando Peer file")
        p = connection_parameters
        out = StringIO.StringIO()
        out.write("%s %s\n" % (p[PPP_PARAM_DEVICE_PORT_KEY],p[PPP_PARAM_DEVICE_SPEED_KEY]))
        chat_script = os.path.join(self.ppp_conf_dir,MOVISTAR_CHAT_FILENAME)
        out.write("user %s\n"%p[PPP_PARAM_LOGIN_KEY])
        out.write("connect '/usr/sbin/chat -v -f \"%s\"'\n" % chat_script)
        print >>out, "defaultroute"
        print >>out, "nodetach"
        print >>out, "noauth"
        print >>out, "debug"
        print >>out, "noipdefault"
        print >>out, "ipcp-accept-local"
        print >>out, ":10.0.0.1"
        print >>out, "lcp-echo-failure 0"
        print >>out, "kdebug 7"

        auto_dns_str =  p.get(PPP_PARAM_AUTO_DNS_KEY,"NO")
        if auto_dns_str == "YES":
            print >>out, "usepeerdns"

        if p.get(PPP_PARAM_FLOW_CONTROL_KEY,"YES") == "YES" :
            print >>out, "crtscts"
        else:
            print >>out, "nocrtscts"
            
        if p.get(PPP_PARAM_CYPHER_PASSWORD_KEY,"NO") == "YES" :
            print >>out, "refuse-pap"
            
        if p.get(PPP_PARAM_COMPRESSION_KEY,"YES") == "NO":
            print >>out, "novj"
            print >>out," nobsdcomp"
            print >>out, "novjccomp"
            print >>out, "nopcomp"
            print >>out, "noaccomp"
        peer_filename_path = os.path.join(self.ppp_conf_dir,"peers",MOVISTAR_PEER_FILENAME)
        try:
            f = open(peer_filename_path,"w")
            f.write(out.getvalue())
        finally:
            out.close()
            f.close()
            
    def create_chat_file(self,connection_parameters):
        short_apn = connection_parameters.get(PPP_PARAM_APN_KEY,"").strip()

        if short_apn == "" :
            apn = "movistar.es"
        else:
            if not short_apn.endswith ("telefonica.es"):
                apn= "%s.movistar.es" % short_apn
            else:
                apn = short_apn

        self.log.debug("APN : %s" % apn)
        chat_line = '"" "at+cgdcont=1,\\"IP\\",\\"%s\\",\\"0.0.0.0\\",0,0" "OK"\r\n"" "atd*99***1#""CONNECT"\r\n' % apn
        self.log.debug("Chat LINE : '%s'" % chat_line)
        file_name = os.path.join(self.ppp_conf_dir,MOVISTAR_CHAT_FILENAME)
        f = open(file_name,"w")
        f.write(chat_line)
        f.close()

    def create_secret__file(self,connection_parameters):
        if connection_parameters.get(PPP_PARAM_CYPHER_PASSWORD_KEY,"NO") == "NO":
            self.log.debug("Creando fichero PAP-SECRETS")
            file_name = os.path.join(self.ppp_conf_dir,PAP_SECRETS_FILENAME)
        else:
            self.log.debug("Creando fichero CHAP-SECRETS")
            file_name = os.path.join(self.ppp_conf_dir,CHAP_SECRETS_FILENAME)

        secret_Line = "%s      *     %s \n" % (connection_parameters.get(PPP_PARAM_LOGIN_KEY,"MOVISTAR"),connection_parameters.get(PPP_PARAM_PASSWORD_KEY,"MOVISTAR"))
        section_name ="Escritorio movistar"
        write_section_of_file(section_name,file_name,secret_Line)

        
    def process_lines(self,lines):
        """
        procesa las lineas de log
        """

        if not lines:
            return
        for line in lines:
            if line.find(PPPD_LOG_TAG) == -1 and line.find(CHAT_LOG_TAG) == -1:
                continue
            else:
                if not self.decode_log_event(line):
                    return 

    def decode_log_event(self,log_line):
        child_pid = self.pppd_monitor.child.pid
        if log_line.find("local  IP address") != -1:
            self.log.info("Conectado")
            self.connected_signal()
            return True                      
                        
        if log_line.find("pppd[%s]: Terminating on signal " % child_pid) != -1 :
            self.process_died()
            return False
            
        if  log_line.find("pppd[%s]: Exit." % child_pid) != -1 :
            self.process_died()
            return False
        return True
    
    def process_died(self):
        if self.status == PPP_STATUS_DISCONNECTING or  self.status == PPP_STATUS_DISCONNECTED:
            return 
        self.disconnecting_signal()
        self.log_monitor.stop()
        self.pppd_monitor.stop()
        self.disconnected_signal()
        
def get_manager():
    session_bus = dbus.SystemBus()
    bus_name = dbus.service.BusName(PPP_MANAGER_SERVICE_NAME, bus=session_bus)
    object = PPPHelper(bus_name,PPP_MANAGER_OBJECT_PATH)
    return object

#mainloop = gobject.MainLoop()
#mainloop.run()
