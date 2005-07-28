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
from debconffilter import DebconfFilter
from debconfcommunicator import DebconfCommunicator

moduledir = '/usr/lib/oem-config'
menudir = '/usr/lib/oem-config/menu'

menu_line_re = re.compile(r'(.*?): (.*)')

from menu.timezone import *

class WizardException(Exception): pass

class Wizard:
    def __init__(self, includes=None, excludes=None):
        if 'OEM_CONFIG_DEBUG' in os.environ:
            self.debug_enabled = True
        else:
            self.debug_enabled = False

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

            menudata = {}
            menufile = open(os.path.join(menudir, menu))
            for line in menufile:
                match = menu_line_re.match(line)
                if match is not None:
                    menudata[match.group(1).lower()] = match.group(2)

            # Load any templates that come with this item.
            templates = os.path.join(menudir, '%s.templates' % name)
            if os.path.exists(templates):
                if self.load_template(templates) != 0:
                    continue

            if 'extra-templates' in menudata:
                extras = menudata['extra-templates']
                for extra in extras.split(' '):
                    if not extra.startswith('/'):
                        extra = os.path.join(menudir, extra)
                    if self.load_template(extra) != 0:
                        continue

            # If there is a test script, check that it succeeds.
            testscript = os.path.join(menudir, '%s.tst' % name)
            if os.access(testscript, os.X_OK):
                if os.spawnl(os.P_WAIT, testscript, testscript) != 0:
                    continue

            self.menus[name] = menudata

            # If there is an Asks: field, match it against the list of
            # question names in the debconf database.
            if 'asks' in self.menus[name]:
                asks_re = self.menus[name]['asks']
                asks = []

                # It isn't possible to use debconf-copydb after the debconf
                # frontend has started up, so we have to use
                # DebconfCommunicator to talk to a separate
                # debconf-communicate process rather than starting a proper
                # frontend.
                #
                # The best fix for this mess is to make debconf-copydb treat
                # its source database as read-only. Unfortunately, layering
                # issues inside debconf make this difficult for the time
                # being.

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
                self.menus[name]['asks-questions'] = asks

        db = DebconfCommunicator('oem-config')

        for name in self.menus:
            self.menus[name]['description'] = \
                db.metaget('oem-config/menu/%s' % name, 'description')

        self.glades = {}
        for glade in [f for f in os.listdir(menudir) if f.endswith('.glade')]:
            name = '.'.join(glade.split('.')[:-1])
            self.glades[name] = os.path.join(menudir, glade)

        self.steps = {}
        for step in [f for f in os.listdir(menudir) if f.endswith('.py')]:
            name = '.'.join(step.split('.')[:-1])
            mod = getattr(__import__('menu.%s' % name), name)
            if hasattr(mod, 'stepname'):
                stepmethod = getattr(mod, mod.stepname)
                self.steps[name] = stepmethod(self.glades[name])

        self.widgets = {}
        for name in self.menus:
            if name in self.steps:
                self.widgets[self.menus[name]['asks']] = self.steps[name]

        db.shutdown()

    def debug(self, message):
        if self.debug_enabled:
            print >>sys.stderr, message

    def load_template(self, template):
        return os.spawnlp(os.P_WAIT, 'debconf-loadtemplate',
                          'debconf-loadtemplate', 'oem-config', template)

    # Get a list of the menu items, sorted by their Order: fields.
    def get_menu_items(self):
        def menu_sort(x, y):
            return cmp(int(self.menus[x]['order']),
                       int(self.menus[y]['order']))

        items = self.menus.keys()
        items.sort(menu_sort)
        return items

    def run(self):
        db = DebconfCommunicator('oem-config')
        debconffilter = DebconfFilter(db, self.widgets)

        items = self.get_menu_items()
        index = 0
        while index >= 0 and index < len(items):
            item = items[index]
            self.debug("oem-config: Running menu item %s" % item)

            # Hack to allow a menu item to repeat on backup as long as the
            # value of any one of a named set of questions has changed. This
            # allows the locale question to back up when the language
            # changes and start a new debconf frontend, while still backing
            # up normally if the user cancels.
            if 'repeat-if-changed' in self.menus[item]:
                oldrepeat = {}
                for name in self.menus[item]['repeat-if-changed'].split():
                    oldrepeat[name] = db.get(name)

            # Set as unseen all questions that we're going to ask.
            if 'asks-questions' in self.menus[item]:
                for name in self.menus[item]['asks-questions']:
                    db.fset(name, 'seen', 'false')

            if item in self.steps:
                self.steps[item].prepare(db)

            # Run the menu item through a debconf filter, which may display
            # custom widgets as required.
            itempath = os.path.join(menudir, item)
            ret = debconffilter.run(itempath)
            if (ret / 256) == 10:
                if 'repeat-if-changed' in self.menus[item]:
                    for name in self.menus[item]['repeat-if-changed'].split():
                        if oldrepeat[name] != db.get(name):
                            break
                    else:
                        index -= 1
                else:
                    index -= 1
                continue
            elif ret != 0:
                raise WizardException, "Menu item %s exited %d" % (item, ret)

            # Did this menu item finish the configuration process?
            if ('exit-menu' in self.menus[item] and
                self.menus[item]['exit-menu'] == 'true'):
                break

            index += 1

        db.shutdown()

if __name__ == '__main__':
    parser = optparse.OptionParser()
    parser.add_option('-i', '--include', action='append', metavar='ITEM',
                      help="Display this menu item.")
    parser.add_option('-e', '--exclude', action='append', metavar='ITEM',
                      help="Don't display this menu item.")
    (options, args) = parser.parse_args()

    wizard = Wizard(includes=options.include, excludes=options.exclude)
    wizard.run()
