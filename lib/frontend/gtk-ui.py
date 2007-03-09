# -*- coding: UTF-8 -*-

# Copyright (C) 2005, 2006 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
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

import os
import datetime
import gettext
import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.glade
from debconf import DebconfCommunicator
from oem_config import filteredcommand
from oem_config.components import console_setup, language, timezone, user, \
                                  language_apply, timezone_apply
import oem_config.emap
import oem_config.tz

PATH = '/usr/share/oem-config'
GLADEDIR = '/usr/lib/oem-config/oem_config/frontend'

BREADCRUMB_STEPS = {
    "step_language": 1,
    "step_timezone": 2,
    "step_keyboard": 3,
    "step_user": 4,
}
BREADCRUMB_MAX_STEP = 4

class Frontend:
    def __init__(self):
        self.current_page = None
        self.locale = None
        self.allowed_change_step = True
        self.allowed_go_forward = True
        self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        # Set default language.
        dbfilter = language.Language(self, DebconfCommunicator('oem-config',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()

        if 'OEM_CONFIG_GLADE' in os.environ:
            gladefile = os.environ['OEM_CONFIG_GLADE']
        else:
            gladefile = '%s/oem-config.glade' % GLADEDIR
        self.glade = gtk.glade.XML(gladefile)

        # Map widgets into our namespace.
        for widget in self.glade.get_widget_prefix(""):
            setattr(self, widget.get_name(), widget)
            # We generally want labels to be selectable so that people can
            # easily report problems in them
            # (https://launchpad.net/bugs/41618), but GTK+ likes to put
            # selectable labels in the focus chain, and I can't seem to turn
            # this off in glade and have it stick. Accordingly, make sure
            # labels are unfocusable here.
            if isinstance(widget, gtk.Label):
                widget.set_property('can-focus', False)

        self.tzmap = TimezoneMap(self)
        self.tzmap.tzmap.show()

    def run(self):
        self.oem_config.show()

        self.glade.signal_autoconnect(self)

        self.steps.set_current_page(self.steps.page_num(self.step_language))
        # TODO cjwatson 2006-07-07: why isn't on_steps_switch_page getting
        # invoked?
        self.set_current_page(self.steps.page_num(self.step_language))

        apply_changes = False

        while self.current_page is not None:
            self.backup = False
            current_name = self.step_name(self.current_page)
            if current_name == 'step_language':
                self.dbfilter = language.Language(self)
            elif current_name == 'step_timezone':
                self.dbfilter = timezone.Timezone(self)
            elif current_name == 'step_keyboard':
                self.dbfilter = console_setup.ConsoleSetup(self)
            elif current_name == 'step_user':
                self.dbfilter = user.User(self)
            else:
                raise ValueError, "step %s not recognised" % current_name

            self.allow_change_step(False)
            self.dbfilter.start(auto_process=True)
            gtk.main()

            if self.backup:
                pass
            elif current_name == 'step_user':
                self.oem_config.hide()
                self.current_page = None
                apply_changes = True
            else:
                self.steps.next_page()

            while gtk.events_pending():
                gtk.main_iteration()

        # TODO: handle errors
        if apply_changes:
            dbfilter = language_apply.LanguageApply(None)
            dbfilter.run_command(auto_process=True)

            dbfilter = timezone_apply.TimezoneApply(None)
            dbfilter.run_command(auto_process=True)

    # I/O helpers.

    def watch_debconf_fd (self, from_debconf, process_input):
        gobject.io_add_watch(from_debconf,
                             gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                             self.watch_debconf_fd_helper, process_input)


    def watch_debconf_fd_helper (self, source, cb_condition, callback):
        debconf_condition = 0
        if (cb_condition & gobject.IO_IN) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_IN
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)

    # Run the UI's main loop until it returns control to us.
    def run_main_loop(self):
        self.allow_change_step(True)
        gtk.main()

    # Return control to the next level up.
    def quit_main_loop(self):
        gtk.main_quit()

    # Step-handling functions.

    def step_name(self, step_index):
        return self.steps.get_nth_page(step_index).get_name()

    def set_current_page(self, current):
        global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
        self.current_page = current
        if current == 0:
            self.back.hide()
        else:
            self.back.show()
        current_name = self.step_name(current)
        # TODO cjwatson 2006-07-04: i18n infrastructure
        #label_text = get_string("step_label", self.locale)
        label_text = "Step ${INDEX} of ${TOTAL}"
        curstep = "<i>?</i>"
        if current_name in BREADCRUMB_STEPS:
            curstep = str(BREADCRUMB_STEPS[current_name])
        label_text = label_text.replace("${INDEX}", curstep)
        label_text = label_text.replace("${TOTAL}", str(BREADCRUMB_MAX_STEP))
        self.step_label.set_markup(label_text)

    def on_steps_switch_page(self, foo, bar, current):
        self.set_current_page(current)

    def allow_change_step(self, allowed):
        if allowed:
            cursor = None
        else:
            cursor = self.watch
        self.oem_config.window.set_cursor(cursor)
        self.back.set_sensitive(allowed)
        self.next.set_sensitive(allowed and self.allowed_go_forward)
        self.allowed_change_step = allowed

    def allow_go_forward(self, allowed):
        self.next.set_sensitive(allowed and self.allowed_change_step)
        self.allowed_go_forward = allowed

    def debconffilter_done(self, dbfilter):
        if dbfilter == self.dbfilter:
            self.dbfilter = None
            gtk.main_quit()

    def on_back_clicked(self, widget):
        self.backup = True
        self.steps.prev_page()
        if self.dbfilter is not None:
            self.allow_change_step(False)
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits

    def on_next_clicked(self, widget):
        if self.dbfilter is not None:
            self.allow_change_step(False)
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits

    # Callbacks provided to components.

    def redo_step(self):
        """Redo the current step. Used by the language component to rerun
        itself when the language changes."""
        self.backup = True

    def selected_language(self, selection):
        (model, iterator) = selection.get_selected()
        if iterator is not None:
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][1]
        else:
            return ''

    def set_language_choices(self, choices, choice_map):
        self.language_choice_map = dict(choice_map)
        if len(self.language_treeview.get_columns()) < 1:
            column = gtk.TreeViewColumn(None, gtk.CellRendererText(), text=0)
            column.set_sizing(gtk.TREE_VIEW_COLUMN_FIXED)
            self.language_treeview.append_column(column)
            selection = self.language_treeview.get_selection()
            selection.connect('changed',
                              self.on_language_treeview_selection_changed)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.language_treeview.set_model(list_store)
        for choice in choices:
            list_store.append([choice])

    def set_language(self, language):
        model = self.language_treeview.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == language:
                path = model.get_path(iterator)
                self.language_treeview.get_selection().select_path(path)
                self.language_treeview.scroll_to_cell(
                    path, use_align=True, row_align=0.5)
                break
            iterator = model.iter_next(iterator)

    def get_language(self):
        selection = self.language_treeview.get_selection()
        (model, iterator) = selection.get_selected()
        if iterator is None:
            return 'C'
        else:
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][0]

    def on_language_treeview_row_activated(self, treeview, path, view_column):
        self.next.activate()

    def on_language_treeview_selection_changed(self, selection):
        lang = self.selected_language(selection)
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            for widget in self.language_questions:
                self.translate_widget(getattr(self, widget), lang)

    def set_timezone (self, timezone):
        self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        return self.tzmap.get_selected_tz_name()

    def set_keyboard_choices(self, choices):
        self.select_keyboard_combo.clear()
        cell = gtk.CellRendererText()
        self.select_keyboard_combo.pack_start(cell, True)
        self.select_keyboard_combo.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.select_keyboard_combo.set_model(list_store)
        for choice in choices:
            list_store.append([choice])

    def set_keyboard(self, keyboard):
        model = self.select_keyboard_combo.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == keyboard:
                self.select_keyboard_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    # Give this the untranslated keyboard name.
    def get_keyboard(self):
        iterator = self.select_keyboard_combo.get_active_iter()
        if iterator is None:
            return 'C'
        else:
            model = self.select_keyboard_combo.get_model()
            return unicode(model.get_value(iterator, 0))

    def set_fullname(self, value):
        self.user_fullname_entry.set_text(value)

    def get_fullname(self):
        return self.user_fullname_entry.get_text()

    def set_username(self, value):
        self.user_name_entry.set_text(value)

    def get_username(self):
        return self.user_name_entry.get_text()

    def get_password(self):
        return self.user_password_entry.get_text()

    def get_verified_password(self):
        return self.user_password_confirm_entry.get_text()


# Much of this timezone map widget is a rough translation of
# gnome-system-tools/src/time/tz-map.c. Thanks to Hans Petter Jansson
# <hpj@ximian.com> for that.

NORMAL_RGBA = 0xc070a0ffL
HOVER_RGBA = 0xffff60ffL
SELECTED_1_RGBA = 0xff60e0ffL
SELECTED_2_RGBA = 0x000000ffL

class TimezoneMap(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.tzdb = oem_config.tz.Database()
        self.tzmap = oem_config.emap.EMap()
        self.update_timeout = None
        self.point_selected = None
        self.point_hover = None
        self.location_selected = None

        self.tzmap.set_smooth_zoom(False)
        zoom_in_file = os.path.join(PATH, 'pixmaps', 'zoom-in.png')
        if os.path.exists(zoom_in_file):
            display = self.frontend.oem_config.get_display()
            pixbuf = gtk.gdk.pixbuf_new_from_file(zoom_in_file)
            self.cursor_zoom_in = gtk.gdk.Cursor(display, pixbuf, 10, 10)
        else:
            self.cursor_zoom_in = None

        self.tzmap.add_events(gtk.gdk.LEAVE_NOTIFY_MASK |
                              gtk.gdk.VISIBILITY_NOTIFY_MASK)

        self.frontend.timezone_map_window.add(self.tzmap)

        timezone_city_combo = self.frontend.timezone_city_combo

        renderer = gtk.CellRendererText()
        timezone_city_combo.pack_start(renderer, True)
        timezone_city_combo.add_attribute(renderer, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING, gobject.TYPE_STRING)
        timezone_city_combo.set_model(list_store)

        prev_continent = ''
        for location in self.tzdb.locations:
            self.tzmap.add_point("", location.longitude, location.latitude,
                                 NORMAL_RGBA)
            zone_bits = location.zone.split('/')
            if len(zone_bits) == 1:
                continue
            continent = zone_bits[0]
            if continent != prev_continent:
                list_store.append(['', None])
                list_store.append(["--- %s ---" % continent, None])
                prev_continent = continent
            human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
            list_store.append([human_zone, location.zone])

        self.tzmap.connect("map-event", self.mapped)
        self.tzmap.connect("unmap-event", self.unmapped)
        self.tzmap.connect("motion-notify-event", self.motion)
        self.tzmap.connect("button-press-event", self.button_pressed)
        self.tzmap.connect("leave-notify-event", self.out_map)

        timezone_city_combo.connect("changed", self.city_changed)

    def set_city_text(self, name):
        model = self.frontend.timezone_city_combo.get_model()
        iterator = model.get_iter_first()
        while iterator is not None:
            location = model.get_value(iterator, 1)
            if location == name:
                self.frontend.timezone_city_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def set_zone_text(self, location):
        offset = location.utc_offset
        if offset >= datetime.timedelta(0):
            minuteoffset = int(offset.seconds / 60)
        else:
            minuteoffset = int(offset.seconds / 60 - 1440)
        if location.zone_letters == 'GMT':
            text = location.zone_letters
        else:
            text = "%s (GMT%+d:%02d)" % (location.zone_letters,
                                         minuteoffset / 60, minuteoffset % 60)
        self.frontend.timezone_zone_text.set_text(text)
        translations = gettext.translation('iso_3166',
                                           languages=[self.frontend.locale],
                                           fallback=True)
        self.frontend.timezone_country_text.set_text(
            translations.ugettext(location.human_country))
        self.update_current_time()

    def update_current_time(self):
        if self.location_selected is not None:
            try:
                now = datetime.datetime.now(self.location_selected.info)
                self.frontend.timezone_time_text.set_text(now.strftime('%X'))
            except ValueError:
                # Some versions of Python have problems with clocks set
                # before the epoch (http://python.org/sf/1646728).
                self.frontend.timezone_time_text.set_text('<clock error>')

    def set_tz_from_name(self, name):
        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        if self.point_selected is not None:
            self.tzmap.point_set_color_rgba(self.point_selected, NORMAL_RGBA)

        self.point_selected = self.tzmap.get_closest_point(longitude, latitude,
                                                           False)

        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)
        self.frontend.allow_go_forward(True)

    def city_changed(self, widget):
        iterator = widget.get_active_iter()
        if iterator is not None:
            model = widget.get_model()
            location = model.get_value(iterator, 1)
            if location is not None:
                self.set_tz_from_name(location)

    def get_selected_tz_name(self):
        if self.location_selected is not None:
            return self.location_selected.zone
        else:
            return None

    def location_from_point(self, point):
        if point is None:
            return None

        (longitude, latitude) = point.get_location()

        best_location = None
        best_distance = None
        for location in self.tzdb.locations:
            if (abs(location.longitude - longitude) <= 1.0 and
                abs(location.latitude - latitude) <= 1.0):
                distance = ((location.longitude - longitude) ** 2 +
                            (location.latitude - latitude) ** 2) ** 0.5
                if best_distance is None or distance < best_distance:
                    best_location = location
                    best_distance = distance

        return best_location

    def timeout(self):
        self.update_current_time()

        if self.point_selected is None:
            return True

        if self.point_selected.get_color_rgba() == SELECTED_1_RGBA:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_2_RGBA)
        else:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_1_RGBA)

        return True

    def mapped(self, widget, event):
        if self.update_timeout is None:
            self.update_timeout = gobject.timeout_add(100, self.timeout)

    def unmapped(self, widget, event):
        if self.update_timeout is not None:
            gobject.source_remove(self.update_timeout)
            self.update_timeout = None

    def motion(self, widget, event):
        if self.tzmap.get_magnification() <= 1.0:
            if self.cursor_zoom_in is not None:
                self.frontend.oem_config.window.set_cursor(self.cursor_zoom_in)
        else:
            self.frontend.oem_config.window.set_cursor(None)

            (longitude, latitude) = self.tzmap.window_to_world(event.x,
                                                               event.y)

            if (self.point_hover is not None and
                self.point_hover != self.point_selected):
                self.tzmap.point_set_color_rgba(self.point_hover, NORMAL_RGBA)

            self.point_hover = self.tzmap.get_closest_point(longitude,
                                                            latitude, True)

            if self.point_hover != self.point_selected:
                self.tzmap.point_set_color_rgba(self.point_hover, HOVER_RGBA)

        return True

    def out_map(self, widget, event):
        if event.mode != gtk.gdk.CROSSING_NORMAL:
            return False

        if (self.point_hover is not None and
            self.point_hover != self.point_selected):
            self.tzmap.point_set_color_rgba(self.point_hover, NORMAL_RGBA)

        self.point_hover = None

        self.frontend.oem_config.window.set_cursor(None)

        return True

    def button_pressed(self, widget, event):
        (longitude, latitude) = self.tzmap.window_to_world(event.x, event.y)

        if event.button != 1:
            self.tzmap.zoom_out()
            if self.cursor_zoom_in is not None:
                self.frontend.oem_config.window.set_cursor(self.cursor_zoom_in)
        elif self.tzmap.get_magnification() <= 1.0:
            self.tzmap.zoom_to_location(longitude, latitude)
            if self.cursor_zoom_in is not None:
                self.frontend.oem_config.window.set_cursor(None)
        else:
            if self.point_selected is not None:
                self.tzmap.point_set_color_rgba(self.point_selected,
                                                NORMAL_RGBA)
            self.point_selected = self.point_hover

            new_location_selected = \
                self.location_from_point(self.point_selected)
            if new_location_selected is not None:
                old_city = self.get_selected_tz_name()
                if old_city is None or old_city != new_location_selected.zone:
                    self.set_city_text(new_location_selected.zone)
                    self.set_zone_text(new_location_selected)
            self.location_selected = new_location_selected
            self.frontend.allow_go_forward(self.location_selected is not None)

        return True
