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
import pygtk
pygtk.require('2.0')
import gobject
import gtk
import gtk.glade
from debconf import DebconfCommunicator
import filteredcommand
from components import language, keyboard, timezone, user

GLADEDIR = '/usr/lib/oem-config/frontend'

BREADCRUMB_STEPS = {
    "step_language": 1,
    "step_keyboard": 2,
    "step_timezone": 3,
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

    def run(self):
        self.oem_config.show()

        self.glade.signal_autoconnect(self)

        self.steps.set_current_page(self.steps.page_num(self.step_language))
        # TODO cjwatson 2006-07-07: why isn't on_steps_switch_page getting
        # invoked?
        self.current_page = self.steps.page_num(self.step_language)

        while self.current_page is not None:
            self.backup = False
            current_name = self.step_name(self.current_page)
            if current_name == 'step_language':
                self.dbfilter = language.Language(self)
            elif current_name == 'step_keyboard':
                self.dbfilter = keyboard.Keyboard(self)
            elif current_name == 'step_timezone':
                self.dbfilter = timezone.Timezone(self)
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
            else:
                self.steps.next_page()

            while gtk.events_pending():
                gtk.main_iteration()

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

    def set_language_choices(self, choices, choice_map):
        self.language_choice_map = dict(choice_map)
        self.language_combo.clear()
        cell = gtk.CellRendererText()
        self.language_combo.pack_start(cell, True)
        self.language_combo.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.language_combo.set_model(list_store)
        for choice in choices:
            list_store.append([choice])

    def set_language(self, language):
        model = self.language_combo.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == language:
                self.language_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def get_language(self):
        iterator = self.language_combo.get_active_iter()
        if iterator is None:
            return 'C'
        else:
            model = self.language_combo.get_model()
            value = unicode(model.get_value(iterator, 0))
            return self.language_choice_map[value][0]

    def on_language_combo_changed(self, widget):
        if isinstance(self.dbfilter, language.Language):
            self.dbfilter.language_changed()

    def set_country_choices(self, choices):
        self.country_combo.clear()
        cell = gtk.CellRendererText()
        self.country_combo.pack_start(cell, True)
        self.country_combo.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.country_combo.set_model(list_store)
        for choice in choices:
            list_store.append([choice])

    def set_country(self, country):
        model = self.country_combo.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            if unicode(model.get_value(iterator, 0)) == country:
                self.country_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def get_country(self):
        iterator = self.country_combo.get_active_iter()
        if iterator is None:
            return 'C'
        else:
            model = self.country_combo.get_model()
            return unicode(model.get_value(iterator, 0))

    def set_keyboard_choices(self, choice_map):
        self.keyboard_choice_map = dict(choice_map)
        choices = choice_map.keys()
        choices.sort()
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
            value = unicode(model.get_value(iterator, 0))
            if self.keyboard_choice_map[value] == keyboard:
                self.select_keyboard_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    # Give this the untranslated keyboard name.
    def get_keyboard(self):
        keyboard = self.select_keyboard_combo.get_active_iter()
        if keyboard is None:
            return 'C'
        else:
            model = self.select_keyboard_combo.get_model()
            value = unicode(model.get_value(iterator, 0))
            return self.keyboard_choice_map[value]

    def set_timezone_choices(self, choice_map):
        self.timezone_choice_map = dict(choice_map)
        choices = choice_map.keys()
        choices.sort()
        cell = gtk.CellRendererText()
        self.select_zone_combo.pack_start(cell, True)
        self.select_zone_combo.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.select_zone_combo.set_model(list_store)
        for choice in choices:
            list_store.append([choice])

    # Give this the untranslated timezone name.
    def set_timezone(self, timezone):
        model = self.select_zone_combo.get_model()
        iterator = model.iter_children(None)
        while iterator is not None:
            value = unicode(model.get_value(iterator, 0))
            if self.timezone_choice_map[value] == timezone:
                self.select_zone_combo.set_active_iter(iterator)
                break
            iterator = model.iter_next(iterator)

    def get_timezone(self):
        timezone = self.select_zone_combo.get_active_iter()
        if timezone is None:
            return None
        else:
            model = self.select_zone_combo.get_model()
            value = unicode(model.get_value(iterator, 0))
            return self.timezone_choice_map[value]

    def set_fullname(self, value):
        self.fullname.set_text(value)

    def get_fullname(self):
        return self.fullname.get_text()

    def set_username(self, value):
        self.username.set_text(value)

    def get_username(self):
        return self.username.get_text()

    def get_password(self):
        return self.password.get_text()

    def get_verified_password(self):
        return self.verified_password.get_text()
