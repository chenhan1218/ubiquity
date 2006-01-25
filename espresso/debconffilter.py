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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

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
#
# If present, the metaget(self, question, field) method will be called
# whenever the confmodule uses METAGET. This may be useful to spot questions
# being assembled out of individually-translatable pieces.
#
# If a widget is registered for the 'ERROR' pseudo-question, then its
# error(self, priority, question) method will be called whenever the
# confmodule asks an otherwise-unhandled question whose template has type
# error.

class DebconfFilter:
    def __init__(self, db, widgets={}):
        self.db = db
        self.widgets = widgets
        if 'DEBCONF_DEBUG' in os.environ:
            self.debug_re = re.compile(os.environ['DEBCONF_DEBUG'])
        else:
            self.debug_re = None
        self.progress_bar = None

    def debug(self, key, *args):
        if self.debug_re is not None and self.debug_re.search(key):
            print >>sys.stderr, "debconf (%s):" % key, ' '.join(args)

    def reply(self, code, text='', log=False):
        ret = '%d %s' % (code, text)
        if log:
            self.debug('filter', '-->', ret)
        self.subin.write('%s\n' % ret)
        self.subin.flush()

    def find_widgets(self, question, method=None):
        found = []
        for pattern in self.widgets.keys():
            if re.search(pattern, question):
                widget = self.widgets[pattern]
                if method is None or hasattr(widget, method):
                    found.append(widget)
        return found

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

            if line == '' or line.startswith(' '):
                # Work around confmodules that try to send multi-line
                # commands; this works (sort of, and by fluke) in cdebconf,
                # but debconf doesn't like it.
                self.debug('filter', 'ignoring unknown (multi-line?) command')
                continue

            if command == 'INPUT' and len(params) == 2:
                (priority, question) = params
                input_widgets = self.find_widgets(question)

                if len(input_widgets) > 0:
                    self.debug('filter', 'widget found for', question)
                    if not input_widgets[0].run(priority, question):
                        self.debug('filter', 'widget requested backup')
                        next_go_backup = True
                    else:
                        next_go_backup = False
                    self.reply(0, 'question will be asked', log=True)
                    continue
                elif 'ERROR' in self.widgets:
                    # If it's an error template, fall back to generic error
                    # handling.
                    try:
                        if self.db.metaget(question, 'Type') == 'error':
                            widget = self.widgets['ERROR']
                            self.debug('filter', 'error widget found for',
                                       question)
                            if not widget.error(priority, question):
                                self.debug('filter', 'widget requested backup')
                                next_go_backup = True
                            else:
                                next_go_backup = False
                            self.reply(0, 'question will be asked', log=True)
                            continue
                    except debconf.DebconfError:
                        pass

            if command == 'SET' and len(params) == 2:
                (question, value) = params
                for widget in self.find_widgets(question, 'set'):
                    self.debug('filter', 'widget found for', question)
                    widget.set(question, value)

            if command == 'SUBST' and len(params) == 3:
                (question, key, value) = params
                for widget in self.find_widgets(question, 'subst'):
                    self.debug('filter', 'widget found for', question)
                    widget.subst(question, key, value)

            if command == 'METAGET' and len(params) == 2:
                (question, field) = params
                for widget in self.find_widgets(question, 'metaget'):
                    self.debug('filter', 'widget found for', question)
                    widget.metaget(question, field)

            if command == 'PROGRESS' and len(params) >= 1:
                subcommand = params[0].upper()
                if subcommand == 'START' and len(params) == 4:
                    progress_min = int(params[1])
                    progress_max = int(params[2])
                    progress_title = params[3]
                    for widget in self.find_widgets(progress_title,
                                                    'progress_start'):
                        self.debug('filter', 'widget found for', progress_title)
                        widget.progress_start(progress_min, progress_max,
                                              progress_title)
                    self.progress_bar = progress_title
                elif self.progress_bar is not None:
                    if subcommand == 'SET' and len(params) == 2:
                        progress_val = int(params[1])
                        for widget in self.find_widgets(self.progress_bar,
                                                        'progress_set'):
                            self.debug('filter', 'widget found for',
                                       self.progress_bar)
                            widget.progress_set(self.progress_bar,
                                                progress_val)
                    elif subcommand == 'STEP' and len(params) == 2:
                        progress_inc = int(params[1])
                        for widget in self.find_widgets(self.progress_bar,
                                                        'progress_step'):
                            self.debug('filter', 'widget found for',
                                       self.progress_bar)
                            widget.progress_step(self.progress_bar,
                                                 progress_inc)
                    elif subcommand == 'INFO' and len(params) == 2:
                        progress_info = params[1]
                        for widget in self.find_widgets(self.progress_bar,
                                                        'progress_info'):
                            self.debug('filter', 'widget found for',
                                       self.progress_bar)
                            widget.progress_info(self.progress_bar,
                                                 progress_info)
                    elif subcommand == 'STOP' and len(params) == 1:
                        for widget in self.find_widgets(self.progress_bar,
                                                        'progress_stop'):
                            self.debug('filter', 'widget found for',
                                       self.progress_bar)
                            widget.progress_stop(self.progress_bar)
                        self.progress_bar = None

            if command == 'GO' and next_go_backup:
                self.reply(30, 'backup', log=True)
                continue

            if command == 'STOP':
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
