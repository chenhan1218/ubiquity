#! /usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

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

    def run(self, subprocess):
        subp = popen2.Popen3(subprocess)
        (subin, subout) = (subp.tochild, subp.fromchild)

        while True:
            line = subout.readline()
            if line == '':
                break

            line = line.rstrip('\n')
            params = line.split(' ')
            if not params:
                continue
            command = params[0].upper()
            params = params[1:]

            self.debug('filter', '<--', command, *params)

            if command == 'INPUT' and len(params) > 1:
                (priority, question) = params
                for pattern in self.widgets.keys():
                    if re.search(pattern, question):
                        widget = self.widgets[pattern]
                        break
                else:
                    widget = None
                if widget is not None:
                    self.debug('filter', 'widget found for', question)
                    widget.run(priority, question)

            try:
                data = self.db.command(command, *params)
                if data == '':
                    subin.write("0\n")
                else:
                    subin.write("0 %s\n" % data)
                subin.flush()
            except debconf.DebconfError, e:
                self.debug('filter',
                    "error returned by frontend: %d (%s)" % e.args)
                subin.write("%d %s\n" % e.args)
                subin.flush()

        return subp.wait()

if __name__ == '__main__':
    class Widget:
        def __init__(self, db, text):
            self.db = db
            self.text = text
        def run(self, priority, question):
            print '%s (%s): %s' % (question, priority, self.text)

    debconf.runFrontEnd()
    db = debconf.Debconf()
    widgets = {}
    widgets['tzconfig/change_timezone'] = Widget(db, 'I am a custom widget')
    df = DebconfFilter(db, widgets)
    ret = df.run(sys.argv[1])
    print >>sys.stderr, "%s exited with code %d" % (sys.argv[1], ret)
