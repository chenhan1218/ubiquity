# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

import sys
import os
import popen2
import re
import debconf

# Each widget should have a run(self, priority, question) method; this
# should ask the question in whatever way is appropriate, and may then
# communicate with the debconf frontend using db. In particular, they may
# want to:
#
#   * fetch the question's description using METAGET
#   * set the question's value using SET
#   * set the question's seen flag using FSET
#
# If run() returns a false value, the next call to GO will return 30
# (backup).
#
# Widgets may also have a set(self, question, value) method; if present,
# this will be called whenever the confmodule uses SET. They may wish to use
# this to adjust the values of questions in their user interface.

class DebconfFilter:
    def __init__(self, db, widgets={}):
        self.db = db
        self.widgets = widgets
        if 'DEBCONF_DEBUG' in os.environ:
            self.debug_re = re.compile(os.environ['DEBCONF_DEBUG'])
        else:
            self.debug_re = None

    def debug(self, key, *args):
        if self.debug_re is not None and self.debug_re.search(key):
            print >>sys.stderr, "debconf (%s):" % key, ' '.join(args)

    def reply(self, code, text='', log=False):
        ret = '%d %s' % (code, text)
        if log:
            self.debug('filter', '-->', ret)
        self.subin.write('%s\n' % ret)
        self.subin.flush()

    def run(self, subprocess):
        os.environ['DEBIAN_HAS_FRONTEND'] = '1'
        os.environ['PERL_DL_NONLAZY'] = '1'
        subp = popen2.Popen3(subprocess)
        del os.environ['PERL_DL_NONLAZY']
        del os.environ['DEBIAN_HAS_FRONTEND']
        (self.subin, self.subout) = (subp.tochild, subp.fromchild)
        next_go_backup = False

        while True:
            line = self.subout.readline()
            if line == '':
                break

            line = line.rstrip('\n')
            params = line.split(' ')
            if not params:
                continue
            command = params[0].upper()
            params = params[1:]

            self.debug('filter', '<--', command, *params)

            if command == 'INPUT' and len(params) == 2:
                (priority, question) = params
                for pattern in self.widgets.keys():
                    if re.search(pattern, question):
                        widget = self.widgets[pattern]
                        break
                else:
                    widget = None
                if widget is not None:
                    self.debug('filter', 'widget found for', question)
                    if not widget.run(priority, question):
                        self.debug('filter', 'widget requested backup')
                        next_go_backup = True
                    else:
                        next_go_backup = False
                    self.reply(0, 'question will be asked', log=True)
                    continue

            if command == 'SET' and len(params) == 2:
                (question, value) = params
                for pattern in self.widgets.keys():
                    if re.search(pattern, question):
                        self.debug('filter', 'widget found for', question)
                        widget = self.widgets[pattern]
                        if hasattr(widget, 'set'):
                            widget.set(question, value)

            if command == 'GO' and next_go_backup:
                self.reply(30, 'backup', log=True)
                continue

            try:
                data = self.db.command(command, *params)
                self.reply(0, data)

                # Visible elements reset the backup state. If we just reset
                # the backup state on GO, then invisible elements would not
                # be properly skipped over in multi-stage backups.
                if command == 'INPUT':
                    next_go_backup = False
            except debconf.DebconfError, e:
                self.reply(*e.args)

        return subp.wait()
