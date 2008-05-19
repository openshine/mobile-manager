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
import gtk
import gtk.gdk
import math
import cairo
import time
import copy

class MobileTrafficGraph(gtk.DrawingArea):
	def __init__(self, dial):
		gtk.DrawingArea.__init__(self)
		self.modify_bg(gtk.STATE_NORMAL, gtk.gdk.color_parse("white"))
		
		self.in_list_values = []
		self.out_list_values = []
		
		self.connect("expose-event", self.expose)
		self.default_rows_number = 5
		self.default_row_step = 32
		
		self.rows_number = self.default_rows_number
		self.row_step = self.default_row_step

		dial.connect("updated_stats", self.__update_stats_cb, None)


	def expose(self, widget, event):
		self.context = widget.window.cairo_create()
		self.context.rectangle(event.area.x, event.area.y,
				event.area.width, event.area.height)
		self.context.clip()
		self.__recalculate_scale()
		self.draw(self.context)
		return False	

	def draw(self, context):
		#rect.x , rect.y , rect.width, rect.height 
		rect = self.get_allocation()

		row_height = rect.height / self.rows_number
		col_width = rect.width / 61
		
		for x in range(self.rows_number):
			context.select_font_face("Sans", cairo.FONT_SLANT_NORMAL,
						 cairo.FONT_WEIGHT_NORMAL)
			context.move_to(2, rect.height - (row_height*x))
			context.show_text("%i" % int(x*self.row_step))
			context.stroke()

			context.move_to(20, rect.height - (row_height*x))
			context.line_to(rect.width - 5, rect.height - (row_height*x))
			context.set_line_width(0.2)
			
			context.stroke()
			
		for x in range(len(self.in_list_values)-1):
			point_a = rect.height - (self.in_list_values[x]*(float(row_height)/float(self.row_step)))
			point_b = rect.height - (self.in_list_values[x+1]*(float(row_height)/float(self.row_step)))
			context.move_to((x*col_width)+20, point_a)
			context.line_to(((x+1)*col_width)+20, point_b)
			context.set_line_width(1)
			context.set_source_rgb(0, 0.71, 0.12)
			context.stroke()

		for x in range(len(self.out_list_values)-1):
			point_a = rect.height - (self.out_list_values[x]*(float(row_height)/float(self.row_step)))
			point_b = rect.height - (self.out_list_values[x+1]*(float(row_height)/float(self.row_step)))
			context.move_to((x*col_width)+20, point_a)
			context.line_to(((x+1)*col_width)+20, point_b)
			context.set_line_width(1)
			context.set_source_rgb(0, 0.24, 0.98)
			context.stroke()

	def __update_stats_cb(self, dial_stats, in_value, out_value, data=None):
		print in_value
		print out_value

	def __set_in_value(self, value):
		if len(self.in_list_values) <= 60 :
			self.in_list_values.append(value)
		else:
			self.in_list_values.reverse()
			self.in_list_values.pop()
			self.in_list_values.reverse()
			self.in_list_values.append(value)

		if self.window:
			alloc = self.get_allocation()
			rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
			self.window.invalidate_rect(rect, True)
			self.window.process_updates(True)

	def __set_out_value(self, value):
		if len(self.out_list_values) <= 60 :
			self.out_list_values.append(value)
		else:
			self.out_list_values.reverse()
			self.out_list_values.pop()
			self.out_list_values.reverse()
			self.out_list_values.append(value)

		if self.window:
			alloc = self.get_allocation()
			rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
			self.window.invalidate_rect(rect, True)
			self.window.process_updates(True)

	def __recalculate_scale(self):
		in_values = copy.copy(self.in_list_values)
		out_values = copy.copy(self.out_list_values)

		merge_list = in_values + out_values
		merge_list.sort()
		merge_list.reverse()

		if len(merge_list) == 0:
			self.rows_number = self.default_rows_number
			self.row_step = self.default_row_step
			return

		max_value = merge_list[0]

		if max_value <= self.default_rows_number * self.default_row_step:
			self.rows_number = self.default_rows_number
			self.row_step = self.default_row_step
		else:
			for x in range(1,6):
				if max_value <= self.default_rows_number * self.default_row_step * x:
					self.rows_number = self.default_rows_number
					self.row_step = self.default_row_step * x
					return
		
	def reset(self):
		self.out_list_values=[]
		self.in_list_values=[]
		if self.window:
			alloc = self.get_allocation()
			rect = gtk.gdk.Rectangle(0, 0, alloc.width, alloc.height)
			self.window.invalidate_rect(rect, True)
			self.window.process_updates(True)

def main():
	window = gtk.Window()
	mds = MobileDialStats()
	mtg = MobileTrafficGraph(mds)

	window.add(mtg) 	
	window.connect("destroy", gtk.main_quit)
	window.show_all()

	gtk.main()

if __name__ == "__main__":
	main()
