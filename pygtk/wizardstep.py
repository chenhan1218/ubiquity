# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import debconf

class WizardStep:
    def preseed(self, db, name, value, seen=True):
        try:
            db.set(name, value)
        except debconf.DebconfError:
            db.register('debian-installer/dummy', name)
            db.set(name, value)
            db.subst(name, 'ID', name)

        if seen:
            db.fset(name, 'seen', 'true')
