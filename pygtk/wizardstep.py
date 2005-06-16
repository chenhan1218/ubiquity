# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import debconf

class WizardStep(object):
    def __init__(self, db, glade):
        self.db = db
        self.glade = glade

    def preseed(self, name, value, seen=True):
        try:
            self.db.set(name, value)
        except debconf.DebconfError:
            self.db.register('debian-installer/dummy', name)
            self.db.set(name, value)
            self.db.subst(name, 'ID', name)

        if seen:
            self.db.fset(name, 'seen', 'true')
