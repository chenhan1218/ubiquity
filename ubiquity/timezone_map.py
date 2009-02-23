# -*- coding: UTF-8 -*-

# Copyright (C) 2009 Canonical Ltd.
# Written by Evan Dandrea <evand@ubuntu.com>.
#
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

# A simple timezone map that highlights timezone bands.

import cairo
import gtk
import glib
from gtk import gdk
import gobject
import os
import datetime

# FIXME: Use the proper 40 time zones:
# http://en.wikipedia.org/wiki/List_of_time_zones
color_codes = {
'-11' : [192, 128, 128, 255],
'-10' : [255, 128, 128, 255],
'-9' : [192, 192, 128, 255],
'-8' : [128, 192, 128, 255],
'-7' : [128, 255, 128, 255],
'-6' : [128, 192, 192, 255],
'-5' : [128, 255, 255, 255],
'-4' : [128, 128, 192, 255],
'-3' : [128, 128, 255, 255],
'-2' : [192, 128, 192, 255],
'-1' : [255, 128, 255, 255],
'0' : [149, 128, 128, 255],
'1' : [170, 145, 128, 255],
'2' : [255, 179, 128, 255],
'3' : [204, 255, 170, 255],
'4' : [145, 128, 149, 255],
'5' : [255, 213, 230, 255],
'6' : [155, 184, 228, 255],
'7' : [255, 128, 179, 255],
'8' : [128, 192, 153, 255],
'9' : [255, 234, 149, 255],
'10' : [228, 184, 155, 255],
'11' : [213, 234, 128, 255],
'12' : [195, 239, 213, 255],
}

class TimezoneMap(gtk.Widget):
    __gtype_name__ = 'TimezoneMap'
    __gsignals__ = {
        'city-selected' : (gobject.SIGNAL_RUN_FIRST,
                             gobject.TYPE_NONE,
                             (gobject.TYPE_STRING,))
    }

    def __init__(self, database, image_path):
        gtk.Widget.__init__(self)
        self.tzdb = database
        self.image_path = image_path
        self.orig_background = \
            gtk.gdk.pixbuf_new_from_file(os.path.join(self.image_path,
            'time_zones_background.png'))
        self.orig_color_map = \
            gtk.gdk.pixbuf_new_from_file(os.path.join(self.image_path,
            'time_zones_colorcodes.png'))
        self.connect('button-press-event', self.button_press)
        self.connect('map-event', self.mapped)
        self.connect('unmap-event', self.unmapped)
        self.selected_offset = None

        self.selected = None
        self.update_timeout = None

        self.distances = []
        self.previous_click = (-1, -1)
        self.dist_pos = 0
        
    def do_size_allocate(self, allocation):
        self.background = self.orig_background.scale_simple(allocation.width,
            allocation.height, gtk.gdk.INTERP_BILINEAR)

        color_map = self.orig_color_map.scale_simple(allocation.width,
            allocation.height, gtk.gdk.INTERP_BILINEAR)
        self.visible_map_pixels = color_map.get_pixels()
        self.visible_map_rowstride = color_map.get_rowstride()
        gtk.Widget.do_size_allocate(self, allocation)

    def do_realize(self):
        self.set_flags(self.flags() | gtk.REALIZED)
        self.window = gdk.Window(
            self.get_parent_window(),
            width=self.allocation.width,
            height=self.allocation.height,
            window_type=gdk.WINDOW_CHILD,
            wclass=gdk.INPUT_OUTPUT,
            event_mask=self.get_events() |
                        gdk.EXPOSURE_MASK |
                        gdk.BUTTON_PRESS_MASK)
        self.window.set_user_data(self)
        self.style.attach(self.window)
        self.style.set_background(self.window, gtk.STATE_NORMAL)
        self.window.move_resize(*self.allocation)
        cursor = gtk.gdk.Cursor(gtk.gdk.HAND2)
        self.window.set_cursor(cursor)

    def do_expose_event(self, event):
        cr = self.window.cairo_create()
        cr.set_source_pixbuf(self.background, 0, 0)
        cr.paint()

        # Plot cities.
        height = self.allocation.height
        width = self.allocation.width
        only_draw_selected = True
        for loc in self.tzdb.locations:
            if self.selected and loc.zone == self.selected:
                cr.set_source_color(gtk.gdk.color_parse('black'))
            else:
                if only_draw_selected:
                    continue
                cr.set_source_color(gtk.gdk.color_parse("red"))
            
            pointx = (loc.longitude + 180) / 360
            pointy = 1 - ((loc.latitude + 90) / 180)
            xx = width
            yx = height
            # FIXME: Horribly inaccurate, does not take in to account wrapping
            # some timezone points back to the start of the map.
            pointx = pointx * xx - 20
            pointy = pointy * yx + 42

            cr.set_line_width(2)
            cr.move_to(pointx - 3, pointy - 3)
            cr.line_to(pointx + 3, pointy + 3)
            cr.move_to(pointx + 3, pointy - 3)
            cr.line_to(pointx - 3, pointy + 3)
            if self.selected and loc.zone == self.selected:
                now = datetime.datetime.now(loc.info)
                time_text = now.strftime('%X')
                xbearing, ybearing, width, height, xadvance, yadvance = \
                    cr.text_extents(time_text)
                if pointx + width > self.allocation.width:
                    cr.move_to(pointx - 4 - width, pointy + 4 + height)
                else:
                    cr.move_to(pointx + 4, pointy + 4 + height)
                cr.show_text(time_text)
            cr.stroke()

        
        # Render highlight.
        # Possibly not the best solution, though in my head it seems better
        # than keeping two copies (original an resized) of every timezone in
        # memory.
        if self.selected_offset != None:
            try:
                pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(self.image_path,
                    'time_zones_highlight_%s.png' % self.selected_offset))
                pixbuf = pixbuf.scale_simple(self.allocation.width,
                    self.allocation.height, gtk.gdk.INTERP_BILINEAR)
                cr.set_source_pixbuf(pixbuf, 0, 0)
                cr.paint()
            except glib.GError:
                pass
    def timeout(self):
        self.queue_draw()
        return True
    
    def mapped(self, widget, event):
        if self.update_timeout is None:
            self.update_timeout = gobject.timeout_add(1000, self.timeout)

    def unmapped(self, widget, event):
        if self.update_timeout is not None:
            gobject.source_remove(self.update_timeout)
            self.update_timeout = None

    def select_city(self, city):
        self.selected = city
        for loc in self.tzdb.locations:
            if loc.zone == city:
                offset = (loc.utc_offset.days * 24) + (loc.utc_offset.seconds / 60 / 60)
                self.selected_offset = str(offset)
        self.queue_draw()

    def button_press(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        
        o = None
        try:
            pixels = self.visible_map_pixels
            rowstride = self.visible_map_rowstride
            c = []
            c.append(ord(pixels[(rowstride * y + x * 4)]))
            c.append(ord(pixels[(rowstride * y + x * 4)+1]))
            c.append(ord(pixels[(rowstride * y + x * 4)+2]))
            c.append(ord(pixels[(rowstride * y + x * 4)+3]))
            for offset in color_codes:
                if color_codes[offset] == c:
                    o = offset
                    break
        except IndexError:
            print 'Mouse click outside of the map.'
        if not o:
            return
        
        self.selected_offset = o

        # FIXME: Why do the first two clicks show the same city?
        if (x, y) == self.previous_click and self.distances:
            zone = self.distances[self.dist_pos][1].zone
            self.dist_pos = (self.dist_pos + 1) % len(self.distances)
        else:
            self.distances = []
            for loc in self.tzdb.locations:
                offset = (loc.utc_offset.days * 24) + (loc.utc_offset.seconds / 60 / 60)
                if str(offset) != self.selected_offset:
                    continue
                pointx = (loc.longitude + 180) / 360
                pointy = 1 - ((loc.latitude + 90) / 180)
                pointx = pointx * self.allocation.width - 20
                pointy = pointy * self.allocation.height + 42
                dx = pointx - x
                dy = pointy - y
                dist = dx * dx + dy * dy
                self.distances.append((dist, loc))
            self.distances.sort()
            # Disable for now.  As there are only a handful of cities in each
            # time zone band, it seemingly makes sense to cycle through all of
            # them.
            #self.distances = self.distances[:5]
            self.previous_click = (x, y)
            self.dist_pos = 0
            zone = self.distances[0][1].zone
        self.emit('city-selected', zone)
        self.queue_draw()

gobject.type_register(TimezoneMap)
