# -*- coding: UTF-8 -*-

# Copyright (C) 2008 Canonical Ltd.
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

# This is a simple frontend that does not perform any filtering; instead, it
# just runs everything using the usual debconf frontend. This is suitable
# for use on a server.

import sys
import os
import textwrap

from debconf import DebconfCommunicator

from oem_config.components import console_setup, language, timezone, user, \
                                  language_apply, timezone_apply, \
                                  console_setup_apply
from oem_config.frontend.base import BaseFrontend

PAGES = [
    'step_language',
    'step_timezone',
    'step_keyboard',
    'step_user',
]

class Frontend(BaseFrontend):
    def __init__(self):
        BaseFrontend.__init__(self)

        self.previous_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        # Set default language.
        dbfilter = language.Language(self, DebconfCommunicator('oem-config',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()

    def excepthook(self, exctype, excvalue, exctb):
        """Crash handler."""

        if (issubclass(exctype, KeyboardInterrupt) or
            issubclass(exctype, SystemExit)):
            return

        self.post_mortem(exctype, excvalue, exctb)

        self.previous_excepthook(exctype, excvalue, exctb)

    def run(self):
        if os.getuid() != 0:
            print >>sys.stderr, textwrap.fill(
                'This program must be run with administrative privileges, and '
                'cannot continue without them.')
            sys.exit(1)

        self.current_page = 0

        while self.current_page >= 0 and self.current_page < len(PAGES):
            current_name = PAGES[self.current_page]
            if current_name == 'step_language':
                step = language.Language(self)
            elif current_name == 'step_timezone':
                step = timezone.Timezone(self)
            elif current_name == 'step_keyboard':
                step = console_setup.ConsoleSetup(self)
            elif current_name == 'step_user':
                step = user.User(self)
            else:
                raise ValueError, "step %s not recognised" % current_name

            ret = step.run_unfiltered()

            if ret == 10:
                self.current_page -= 1
            else:
                self.current_page += 1

        # TODO: handle errors
        if self.current_page >= len(PAGES):
            step = language_apply.LanguageApply(self)
            step.run_unfiltered()

            step = timezone_apply.TimezoneApply(self)
            step.run_unfiltered()

            step = console_setup_apply.ConsoleSetupApply(self)
            step.run_unfiltered()
