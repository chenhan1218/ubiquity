#! /usr/bin/env python
# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import sys
import os
import re
import optparse
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import debconf

menudir = '/usr/share/oem-config/menu'
moduledir = '/usr/lib/oem-config/pygtk'
stepsdir = os.path.join(moduledir, 'steps')

menu_line_re = re.compile(r'(.*?): (.*)')

from steps.timezone import *

class Wizard:
    def __init__(self, includes=None, excludes=None):
        self.menus = {}
        for menu in [f for f in os.listdir(menudir) if f.endswith('.mnu')]:
            name = '.'.join(menu.split('.')[:-1])

            # Always include the exit item. Otherwise, check includes and
            # excludes.
            if name != 'exit':
                if includes is not None and not name in includes:
                    continue
                if excludes is not None and name in excludes:
                    continue

            # If the frontend isn't up yet, load any templates that come
            # with this item.
            if 'DEBIAN_HAS_FRONTEND' not in os.environ:
                templates = os.path.join(menudir, '%s.templates' % name)
                if os.access(templates, os.R_OK):
                    if os.spawnlp(os.P_WAIT, 'debconf-loadtemplate',
                                  'debconf-loadtemplate', 'oem-config',
                                  templates) != 0:
                        continue

            # If there is a test script, check that it succeeds.
            testscript = os.path.join(menudir, '%s.tst' % name)
            if os.access(testscript, os.X_OK):
                if os.spawnl(os.P_WAIT, testscript, testscript) != 0:
                    continue

            self.menus[name] = {}
            menufile = open(os.path.join(menudir, menu))
            for line in menufile:
                match = menu_line_re.match(line)
                if match is not None:
                    self.menus[name][match.group(1).lower()] = match.group(2)

            # If there is an Asks: field, match it against the list of
            # question names in the debconf database.
            if 'asks' in self.menus[name]:
                asks_re = self.menus[name]['asks']
                asks = []

                # It isn't possible to use debconf-copydb after the debconf
                # frontend has started up, so we have to resort to this
                # nasty hack: we process the Asks: fields, stuff them into
                # the environment, start the debconf frontend (re-execing
                # ourselves) and fetch the processed Asks: fields back out
                # of the environment again.
                #
                # The best fix for this mess is to make debconf-copydb treat
                # its source database as read-only. Unfortunately, layering
                # issues inside debconf make this difficult for the time
                # being.

                magic_env = 'OEM_CONFIG_ASKS_%s' % name
                if magic_env in os.environ:
                    self.menus[name]['asks'] = os.environ[magic_env].split(' ')
                else:
                    # TODO: os.popen() doesn't take a list, so we have to
                    # quote metacharacters by hand. Once we're entirely
                    # comfortable with relying on Python 2.4, we can use
                    # subprocess.call() instead.
                    asks_re = re.sub(r'\W', r'\\\g<0>', asks_re)
                    for line in os.popen(
                            'debconf-copydb configdb pipe' +
                            ' --config=Name:pipe --config=Driver:Pipe' +
                            ' --config=InFd:none --pattern=%s' % asks_re):
                        line = line.rstrip('\n')
                        if line.startswith('Name: '):
                            asks.append(line[6:])
                    self.menus[name]['asks'] = asks
                    os.environ[magic_env] = ' '.join(asks)

        self.start_debconf()

        self.glades = {}
        for glade in [f for f in os.listdir(stepsdir) if f.endswith('.glade')]:
            name = '.'.join(glade.split('.')[:-1])
            self.glades[name] = os.path.join(stepsdir, glade)

        self.steps = {}
        for step in [f for f in os.listdir(stepsdir) if f.endswith('.py')]:
            name = '.'.join(step.split('.')[:-1])
            mod = getattr(__import__('steps.%s' % name), name)
            if hasattr(mod, 'stepname'):
                self.steps[name] = getattr(mod, mod.stepname)

    def start_debconf(self):
        debconf.runFrontEnd()
        self.db = debconf.Debconf()

        for name in self.menus:
            self.menus[name]['description'] = \
                self.db.metaget('oem-config/menu/%s' % name, 'description')

    # Get a list of the menu items, sorted by their Order: fields.
    def get_menu_items(self):
        def menu_sort(x, y):
            return cmp(int(self.menus[x]['order']),
                       int(self.menus[y]['order']))

        items = self.menus.keys()
        items.sort(menu_sort)
        return items

    def run_step(self, step):
        xml = gtk.glade.XML(self.glades[step])
        xml.signal_autoconnect(self)
        dialog = xml.get_widget('dialog')
        dialog.connect('destroy', gtk.main_quit)
        stepper = self.steps[step](self.db, xml)
        stepper.run()
        return stepper.succeeded

    def run(self):
        items = self.get_menu_items()
        index = 0
        while index >= 0 and index < len(items):
            item = items[index]
            # Set as unseen all questions that we're going to ask.
            if 'asks' in self.menus[item]:
                for name in self.menus[item]['asks']:
                    print >>sys.stderr, 'asks', item, name
                    self.db.fset(name, 'seen', 'false')

            # Is there a custom frontend for this item? If so, run it.
            if item in self.steps:
                if not self.run_step(item):
                    index -= 1
                    continue

            # Run the pure-debconf menu item.
            # TODO: do something more useful on failure
            itempath = os.path.join(menudir, item)
            if os.spawnl(os.P_WAIT, itempath, itempath) != 0:
                index -= 1
                continue

            # Did this menu item finish the configuration process?
            if ('exit-menu' in self.menus[item] and
                self.menus[item]['exit-menu'] == 'true'):
                break

            index += 1

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i', '--include', action='append', metavar='ITEM',
                      help="Display this menu item.")
    parser.add_option('-e', '--exclude', action='append', metavar='ITEM',
                      help="Don't display this menu item.")
    (options, args) = parser.parse_args()

    wizard = Wizard(includes=options.include, excludes=options.exclude)
    wizard.run()
