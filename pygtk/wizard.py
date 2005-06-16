#! /usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import sys
import os
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import debconf

#moduledir = '/usr/lib/firstboot/pygtk/steps'
moduledir = '.'
stepsdir = os.path.join(moduledir, 'steps')

sys.path.insert(0, moduledir)
from steps.timezone import *

class Wizard:
    def __init__(self, db):
        self.db = db

        self.glades = {}
        for glade in [f for f in os.listdir(stepsdir) if f.endswith('.glade')]:
            name = '.'.join(glade.split('.')[:-1])
            self.glades[name] = gtk.glade.XML(os.path.join(stepsdir, glade))

        self.steps = {}
        for step in [f for f in os.listdir(stepsdir) if f.endswith('.py')]:
            name = '.'.join(step.split('.')[:-1])
            mod = getattr(__import__('steps.%s' % name), name)
            if hasattr(mod, 'stepname'):
                self.steps[name] = getattr(mod, mod.stepname)

    def run(self, step):
        self.glades[step].signal_autoconnect(self)
        dialog = self.glades[step].get_widget('dialog')
        dialog.connect('destroy', gtk.main_quit)
        stepper = self.steps[step](self.db, self.glades[step])
        stepper.run()

if __name__ == '__main__':
    debconf.runFrontEnd()
    db = debconf.Debconf()
    Wizard(db).run(sys.argv[1])
