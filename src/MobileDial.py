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

PPP_STATUS_DISCONNECTED = 0
PPP_STATUS_CONNECTED = 1 
PPP_STATUS_CONNECTING = 2
PPP_STATUS_DISCONNECTING = 3

class MobileDial(gobject.GObject):

    __gsignals__ = { 'connecting' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,()) ,
                     'connected' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,()) ,
                     'disconnecting' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,()) ,
                     'disconnected' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,()),
                     'pppstats_signal' : (gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE,(gobject.TYPE_INT, gobject.TYPE_INT, gobject.TYPE_FLOAT))
                     }
    
    def __init__(self, mcontroller):
        print "MobileDial __init__"
        self.mcontroller = mcontroller
        gobject.GObject.__init__(self)

    def start(self, parameters):
        print "MobileDial start"

    def stop(self):
        print "MobileDial stop"

    def status(self):
        print "MobileDial status"


gobject.type_register(MobileDial)
