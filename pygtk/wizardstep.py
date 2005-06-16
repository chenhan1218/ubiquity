# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import gtk
import debconf

class WizardStep(object):
    def __init__(self, db, glade):
        self.db = db
        self.glade = glade

        self.glade.get_widget('button_ok').connect('clicked', self.ok_handler)
        self.glade.get_widget('button_cancel').connect('clicked',
                                                       gtk.main_quit)

    def preseed(self, name, value, seen=True):
        try:
            self.db.set(name, value)
        except debconf.DebconfError:
            self.db.register('debian-installer/dummy', name)
            self.db.set(name, value)
            self.db.subst(name, 'ID', name)

        if seen:
            self.db.fset(name, 'seen', 'true')

    def ok_handler(self, widget, data=None):
        gtk.main_quit()

    def run(self):
        gtk.main()
