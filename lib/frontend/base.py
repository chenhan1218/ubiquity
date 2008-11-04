# -*- coding: UTF-8 -*-

# Copyright (C) 2005, 2006, 2007, 2008 Canonical Ltd.
# Copyright (C) 2007 Mario Limonciello <superm1@ubuntu.com>
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

import sys
import os
import syslog

from oem_config import i18n

class BaseFrontend:
    """Abstract oem-config frontend.

    This class consists partly of facilities shared among frontends, and
    partly of documentation of what methods a frontend must implement. A
    frontend must implement all methods whose bodies are declared using
    self._abstract() here, and may want to extend others."""

    # Core infrastructure.

    def __init__(self):
        """Frontend initialisation."""
        self.locale = None
        self.dbfilter = None
        self.dbfilter_status = None
        self.current_layout = None

    def _abstract(self, method):
        raise NotImplementedError("%s.%s does not implement %s" %
                                  (self.__class__.__module__,
                                   self.__class__.__name__, method))

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

    def run_main_loop(self):
        """Block until the UI returns control."""
        pass

    def quit_main_loop(self):
        """Return control blocked in run_main_loop."""
        pass

    def post_mortem(self, exctype, excvalue, exctb):
        """Drop into the debugger if possible."""
        self.run_error_cmd()
        
        # Did the user request this?
        if 'OEM_CONFIG_DEBUG_PDB' not in os.environ:
            return
        # We must not be in interactive mode; if we are, there's no point.
        if hasattr(sys, 'ps1'):
            return
        # stdin and stdout must point to a terminal. (stderr is redirected
        # in debug mode!)
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            return
        # SyntaxErrors can't meaningfully be debugged.
        if issubclass(exctype, SyntaxError):
            return

        import pdb
        pdb.post_mortem(exctb)
        sys.exit(1)

    # Interfaces with various components. If a given component is not used
    # then its abstract methods may safely be left unimplemented.

    # oem_config.components.language

    def set_language_choices(self, choices, choice_map):
        """Called with language choices and a map to localised names."""
        self.language_choice_map = dict(choice_map)

    def set_language(self, language):
        """Set the current selected language."""
        pass

    def get_language(self):
        """Get the current selected language."""
        self._abstract('get_language')

    # oem_config.components.timezone

    def set_timezone(self, timezone):
        """Set the current selected timezone."""
        pass

    def get_timezone(self):
        """Get the current selected timezone."""
        self._abstract('get_timezone')

    # oem_config.components.console_setup

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

    # oem_config.components.user

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

    def set_auto_login(self, value):
        """Set whether the user should be automatically logged in."""
        self._abstract('set_auto_login')

    def get_auto_login(self):
        """Returns true if the user should be automatically logged in."""
        self._abstract('get_auto_login')

    def username_error(self, msg):
        """The selected username was bad."""
        self._abstract('username_error')

    def password_error(self, msg):
        """The selected password was bad."""
        self._abstract('password_error')

    # General facilities for components.

    def error_dialog(self, title, msg):
        """Display an error message dialog."""
        self._abstract('error_dialog')
