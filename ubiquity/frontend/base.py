# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007 Canonical Ltd.
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import syslog

from ubiquity import i18n

class BaseFrontend:
    """Abstract ubiquity frontend.

    This class consists partly of facilities shared among frontends, and
    partly of documentation of what methods a frontend must implement. A
    frontend must implement all methods whose bodies are declared using
    self._abstract() here, and may want to extend others."""

    # Core infrastructure.

    def __init__(self, distro):
        """Frontend initialisation."""
        self.distro = distro
        self.locale = None
        self.dbfilter = None
        self.dbfilter_status = None
        self.current_layout = None
        self.resize_choice = None
        self.manual_choice = None
        self.summary_device = None
        self.popcon = None

    def _abstract(self, method):
        raise NotImplementedError("%s.%s does not implement %s" %
                                  self.__class__.__module__,
                                  self.__class__.__name__, method)

    def run(self):
        """Main entry point."""
        self._abstract('run')

    def get_string(self, name, lang=None):
        """Get the string name in the given lang or a default."""
        if lang is None:
            lang = self.locale
        return i18n.get_string(name, lang)

    def watch_debconf_fd(self, from_debconf, process_input):
        """Event loop interface to debconffilter.

        A frontend typically provides its own event loop. When a
        debconffiltered command is running, debconffilter must be given an
        opportunity to process input from that command as it arrives. This
        method will be called with from_debconf as a file descriptor reading
        from the filtered command and a process_input callback which should
        be called when input events are received."""

        self._abstract('watch_debconf_fd')

    def debconffilter_done(self, dbfilter):
        """Called when an asynchronous debconffiltered command exits.

        Returns True if the exiting command is self.dbfilter; frontend
        implementations may wish to do something special (such as exiting
        their main loop) in this case."""

        if dbfilter is None:
            name = 'None'
            self.dbfilter_status = None
        else:
            name = dbfilter.__class__.__name__
            if dbfilter.status:
                self.dbfilter_status = (name, dbfilter.status)
            else:
                self.dbfilter_status = None
        if self.dbfilter is None:
            currentname = 'None'
        else:
            currentname = self.dbfilter.__class__.__name__
        syslog.syslog(syslog.LOG_DEBUG,
                      "debconffilter_done: %s (current: %s)" %
                      (name, currentname))
        if dbfilter == self.dbfilter:
            self.dbfilter = None
            return True
        else:
            return False

    def refresh(self):
        """Take the opportunity to process pending items in the event loop."""
        pass

    def run_main_loop(self):
        """Block until the UI returns control."""
        pass

    def quit_main_loop(self):
        """Return control blocked in run_main_loop."""
        pass

    # Progress bar handling.

    def debconf_progress_start(self, progress_min, progress_max,
                               progress_title):
        """Start a progress bar. May be nested."""
        self._abstract('debconf_progress_start')

    def debconf_progress_set(self, progress_val):
        """Set the current progress bar's position to progress_val."""
        self._abstract('debconf_progress_set')

    def debconf_progress_step(self, progress_inc):
        """Increment the current progress bar's position by progress_inc."""
        self._abstract('debconf_progress_step')

    def debconf_progress_info(self, progress_info):
        """Set the current progress bar's message to progress_info."""
        self._abstract('debconf_progress_info')

    def debconf_progress_stop(self):
        """Stop the current progress bar."""
        self._abstract('debconf_progress_stop')

    def debconf_progress_region(self, region_start, region_end):
        """Confine nested progress bars to a region of the current bar."""
        self._abstract('debconf_progress_region')

    def debconf_progress_cancellable(self, cancellable):
        """Control whether the current progress bar may be cancelled."""
        pass

    # Interfaces with various components. If a given component is not used
    # then its abstract methods may safely be left unimplemented.

    # ubiquity.components.language

    def set_language_choices(self, choices, choice_map):
        """Called with language choices and a map to localised names."""
        self.language_choice_map = dict(choice_map)

    def set_language(self, language):
        """Set the current selected language."""
        pass

    def get_language(self):
        """Get the current selected language."""
        self._abstract('get_language')

    # ubiquity.components.timezone

    def set_timezone(self, timezone):
        """Set the current selected timezone."""
        pass

    def get_timezone(self):
        """Get the current selected timezone."""
        self._abstract('get_timezone')

    # ubiquity.components.console_setup

    def set_keyboard_choices(self, choices):
        """Set the available keyboard layout choices."""
        pass

    def set_keyboard(self, layout):
        """Set the current keyboard layout."""
        self.current_layout = layout

    def get_keyboard(self):
        """Get the current keyboard layout."""
        self._abstract('get_keyboard')

    def set_keyboard_variant_choices(self, choices):
        """Set the available keyboard variant choices."""
        pass

    def set_keyboard_variant(self, variant):
        """Set the current keyboard variant."""
        pass

    def get_keyboard_variant(self):
        self._abstract('get_keyboard_variant')
    # ubiquity.components.partman

    def set_autopartition_choices(self, choices, extra_options,
                                  resize_choice, manual_choice):
        """Set available autopartitioning choices."""
        self.resize_choice = resize_choice
        self.manual_choice = manual_choice

    def get_autopartition_choice(self):
        """Get the selected autopartitioning choice."""
        self._abstract('get_autopartition_choice')

    def update_partman(self, disk_cache, partition_cache, cache_order):
        """Update the manual partitioner display."""
        # not flagged as abstract because some frontends may only implement
        # autopartitioning
        pass

    # ubiquity.components.partman_commit

    def return_to_partitioning(self):
        """Return to partitioning following a commit error."""
        self._abstract('return_to_partitioning')

    # ubiquity.components.migrationassistant

    def ma_set_choices(self, choices):
        """Set the available migration-assistant choices."""
        pass

    def ma_get_choices(self):
        """Get the selected migration-assistant choices."""
        self._abstract('ma_get_choices')

    def ma_user_error(self, error, user):
        """The selected migration-assistant username was bad."""
        self._abstract('ma_user_error')

    def ma_password_error(self, error, user):
        """The selected migration-assistant password was bad."""
        self._abstract('ma_password_error')

    # ubiquity.components.usersetup

    def set_fullname(self, value):
        """Set the user's full name."""
        pass

    def get_fullname(self):
        """Get the user's full name."""
        self._abstract('get_fullname')

    def set_username(self, value):
        """Set the user's Unix user name."""
        pass

    def get_username(self):
        """Get the user's Unix user name."""
        self._abstract('get_username')

    def get_password(self):
        """Get the user's password."""
        self._abstract('get_password')

    def get_verified_password(self):
        """Get the user's password confirmation."""
        self._abstract('get_password')

    def username_error(self, msg):
        """The selected username was bad."""
        self._abstract('username_error')

    def password_error(self, msg):
        """The selected password was bad."""
        self._abstract('password_error')

    # typically part of the usersetup UI but actually called from
    # ubiquity.components.install
    def get_hostname(self):
        """Get the selected hostname."""
        self._abstract('get_hostname')

    # ubiquity.components.summary

    def set_summary_text(self, text):
        """Set text to be displayed in the installation summary."""
        pass

    def set_summary_device(self, device):
        """Set the GRUB device. A hack until we have something better."""
        if device is not None:
            if not device.startswith('(') and not device.startswith('/dev/'):
                device = '/dev/%s' % device
        self.summary_device = device

    # called from ubiquity.components.install
    def get_summary_device(self):
        """Get the selected GRUB device."""
        return self.summary_device

    def set_popcon(self, participate):
        """Set whether to participate in popularity-contest."""
        self.popcon = participate

    # called from ubiquity.components.install
    def get_popcon(self):
        """Get whether to participate in popularity-contest."""
        return self.popcon

    # General facilities for components.

    def error_dialog(self, title, msg, fatal=True):
        """Display an error message dialog."""
        self._abstract('error_dialog')

    def question_dialog(self, title, msg, options, use_templates=True):
        """Ask a question."""
        self._abstract('question_dialog')
