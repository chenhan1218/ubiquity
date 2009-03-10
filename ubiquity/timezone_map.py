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

import math
import cairo
import gtk
import glib
from gtk import gdk
import gobject
import os
import datetime

# We need a color coded map so we can only select from the list of points that
# are in the time zone band the user clicked on.  It would be odd if the user
# clicked within UTC-5, but it selected a point in UTC-6 because it was closer
# to the mouse.
color_codes = {
# We don't handle UTC-12, but as that's just the US Minor Outlying Islands, I
# think we're ok, as Wikiepdia says, "As of 2008, none of the islands has any
# permanent residents."
'-11.0' : [43, 0, 0, 255],
'-10.0' : [85, 0, 0, 255],
'-9.5' : [102, 255, 0, 255],
'-9.0' : [128, 0, 0, 255],
'-8.0' : [170, 0, 0, 255],
'-7.0' : [212, 0, 0, 255],
'-6.0' : [255, 0, 0, 255],
'-5.0' : [255, 42, 42, 255],
'-4.0' : [255, 85, 85, 255],
'-3.5' : [0, 255, 0, 255],
'-3.0' : [255, 128, 128, 255],
'-2.0' : [255, 170, 170, 255],
'-1.0' : [255, 213, 213, 255],
'0.0' : [43, 17, 0, 255],
'1.0' : [85, 34, 0, 255],
'2.0' : [128, 51, 0, 255],
'3.0' : [170, 68, 0, 255],
'3.5' : [0, 255, 102, 255],
'4.0' : [212, 85, 0, 255],
'4.5' : [0, 204, 255, 255],
'5.0' : [255, 102, 0, 255],
'5.5' : [0, 102, 255, 255],
'5.75' : [0, 238, 207, 247],
'6.0' : [255, 127, 42, 255],
'6.5' : [204, 0, 254, 254],
'7.0' : [255, 153, 85, 255],
'8.0' : [255, 179, 128, 255],
'9.0' : [255, 204, 170, 255],
'9.5' : [170, 0, 68, 250],
'10.0' : [255, 230, 213, 255],
'10.5' : [212, 124, 21, 250],
'11.0' : [212, 170, 0, 255],
'11.5' : [249, 25, 87, 253],
'12.0' : [255, 204, 0, 255],
'12.75' : [254, 74, 100, 248],
'13.0' : [255, 85, 153, 250],
}

# The South Pole is transformed from 0.0, -90.0 to 0.5, 1 before being adjusted
# for the shifted and missing arctic section of the map.

def convert_longitude_to_x(longitude, map_width):
    # Miller cylindrical map projection is just the longitude as the
    # calculation is the longitude from the central meridian of the projection.
    # Convert to radians.
    x = (longitude * (math.pi / 180)) + math.pi # 0 ... 2pi
    # Convert to a percentage.
    x = x / (2 * math.pi)
    x = x * map_width
    # Adjust for the visible map starting near 170 degrees.
    # Percentage shift required, grabbed from measurements using The GIMP.
    x = x - (map_width * 0.039073402)
    return x

def convert_latitude_to_y(latitude, map_height):
    # Miller cylindrical map projection, as used in the source map from the CIA
    # world factbook.  Convert latitude to radians.
    y = 1.25 * math.log(math.tan((0.25 * math.pi) + \
        (0.4 * (latitude * (math.pi / 180)))))
    # Convert to a percentage.
    y = abs(y - 2.30341254338) # 0 ... 4.606825
    y = y / 4.6068250867599998
    # Adjust for the visible map not including anything beyond 60 degrees south
    # (150 degrees vs 180 degrees).
    y = y * (map_height * 1.2)
    return y


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
            'bg.png'))
        self.orig_color_map = \
            gtk.gdk.pixbuf_new_from_file(os.path.join(self.image_path,
            'cc.png'))
        self.connect('button-press-event', self.button_press)
        self.connect('map-event', self.mapped)
        self.connect('unmap-event', self.unmapped)
        self.selected_offset = None

        self.selected = None
        self.update_timeout = None

        self.distances = []
        self.previous_click = (-1, -1)
        self.dist_pos = 0
        
    def do_size_request(self, requisition):
        # Set a small size request to create an aspect ratio for the parent
        # widget.
        width = self.orig_background.get_width() / 2
        height = self.orig_background.get_height() / 2
        requisition.width = width
        requisition.height = height
        gtk.Widget.do_size_request(self, requisition)

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
        
        # Render highlight.
        # Possibly not the best solution, though in my head it seems better
        # than keeping two copies (original and resized) of every timezone in
        # memory.
        pixbuf = None
        if self.selected_offset != None:
            try:
                pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(self.image_path,
                    'timezone_%s.png' % self.selected_offset))
                pixbuf = pixbuf.scale_simple(self.allocation.width,
                    self.allocation.height, gtk.gdk.INTERP_BILINEAR)
                cr.set_source_pixbuf(pixbuf, 0, 0)
                cr.paint()
            except glib.GError, e:
                print 'Error setting the time zone band highlight:', str(e)
                return

        # Plot cities.
        height = self.background.get_height()
        width = self.background.get_width()

        # Useful for debugging time zone plotting.
        only_draw_selected = True
        for loc in self.tzdb.locations:
            if self.selected and loc.zone == self.selected:
                cr.set_source_color(gtk.gdk.color_parse('black'))
            else:
                if only_draw_selected:
                    continue
                cr.set_source_color(gtk.gdk.color_parse("red"))
            
            pointx = convert_longitude_to_x(loc.longitude, width)
            pointy = convert_latitude_to_y(loc.latitude, height)

            if only_draw_selected:
                cr.set_line_width(2)
                cr.move_to(pointx - 3, pointy - 3)
                cr.line_to(pointx + 3, pointy + 3)
                cr.move_to(pointx + 3, pointy - 3)
                cr.line_to(pointx - 3, pointy + 3)
            else:
                cr.arc(pointx, pointy, 0.5, 0, 2 * math.pi)
            # Draw the time.
            if self.selected and loc.zone == self.selected and only_draw_selected:
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
                offset = (loc.utc_offset.days * 24) + (loc.utc_offset.seconds / 60.0 / 60.0)
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
            height = self.background.get_height()
            width = self.background.get_width()
            for loc in self.tzdb.locations:
                offset = (loc.utc_offset.days * 24) + (loc.utc_offset.seconds / 60.0 / 60.0)
                if str(offset) != self.selected_offset:
                    continue
                pointx = convert_longitude_to_x(loc.longitude, width)
                pointy = convert_latitude_to_y(loc.latitude, height)
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
