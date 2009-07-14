# -*- coding: UTF-8 -*-

# Copyright (C) 2008, 2009 Canonical Ltd.
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
#
# Note that this frontend relies on being run under the control of a debconf
# frontend; the main ubiquity program takes care of this.

import sys
import os
import textwrap

from debconf import Debconf

from ubiquity.components import console_setup, language, timezone, usersetup, \
                                network, tasks, \
                                language_apply, timezone_apply, \
                                console_setup_apply
from ubiquity.frontend.base import BaseFrontend

class Wizard(BaseFrontend):
    def __init__(self, distro):
        BaseFrontend.__init__(self, distro)

        db = self.debconf_communicator()
        if self.oem_user_config:
            db.info('ubiquity/text/oem_user_config_title')
        else:
            db.info('ubiquity/text/live_installer')
        db.shutdown()

        self.previous_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        # Set default language.
        dbfilter = language.Language(self, self.debconf_communicator())
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

        self.pagesindex = 0
        pageslen = len(self.pages)

        while(self.pagesindex >= 0 and self.pagesindex < pageslen):
            current_name = self.pagenames[self.current_page]
            step = self.pages[self.pagesindex](self)

            if current_name == 'stepLanguage':
                self.db.settitle('ubiquity/text/language_heading_label')
            elif current_name == 'stepLocation':
                self.db.settitle('ubiquity/text/timezone_heading_label')
            elif current_name == 'stepKeyboardConf':
                self.db.settitle('ubiquity/text/keyboard_heading_label')
            elif current_name == 'stepUserInfo':
                self.db.settitle('ubiquity/text/userinfo_heading_label')
            elif current_name == 'stepNetwork':
                self.db.settitle('ubiquity/text/network_heading_label')
            elif current_name == 'stepTasks':
                self.db.settitle('ubiquity/text/tasks_heading_label')
            else:
                raise ValueError, "step %s not recognised" % current_name

            ret = step.run_unfiltered()

            if ret == 10:
                self.pagesindex -= 1
            else:
                self.pagesindex += 1

        # TODO: handle errors
        if self.pagesindex == pageslen:
            dbfilter = install.Install(self)
            ret = dbfilter.run_command(auto_process=True)
            if ret != 0:
                self.installing = False
                if ret == 3:
                    # error already handled by Install
                    sys.exit(ret)
                elif (os.WIFSIGNALED(ret) and
                      os.WTERMSIG(ret) in (signal.SIGINT, signal.SIGKILL,
                                           signal.SIGTERM)):
                    sys.exit(ret)
                elif os.path.exists('/var/lib/ubiquity/install.trace'):
                    tbfile = open('/var/lib/ubiquity/install.trace')
                    realtb = tbfile.read()
                    tbfile.close()
                    raise RuntimeError, ("Install failed with exit code %s\n%s" %
                                         (ret, realtb))
                else:
                    raise RuntimeError, ("Install failed with exit code %s; see "
                                         "/var/log/syslog" % ret)

            while self.progress_position.depth() != 0:
                self.debconf_progress_stop()

            return 0
        else:
            return 10
