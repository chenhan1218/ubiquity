# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Tollef Fog Heen <tfheen@ubuntu.com>
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

import re
import os
from ubiquity.filteredcommand import FilteredCommand
from subprocess import Popen

class KbdChooser(FilteredCommand):

    def prepare(self):
        # Always select from list.
        self.debug("kbd-chooser prepare")

        questions = [r'^kbd-chooser/method$',
                     r'^console-keymaps.*/keymap$',
                     'ERROR']

        self.keyboard_question = None

        self.preseed('kbd-chooser/method', self.description("kbd-chooser/do_select"))

#        self.frontend.set_keyboard_choices(self.choices_display_map("console-tools/archs"))
        return (['/bin/sh', '-c', '. /usr/share/debconf/confmodule; exec /usr/lib/ubiquity/kbd-chooser/kbd-chooser'],
                questions,
                {'PATH': '/usr/lib/ubiquity/kbd-chooser:' + os.environ['PATH']})


    def set(self, question, value):
        if question.startswith('console-keymaps-') and question.endswith('/keymap'):
            self.frontend.set_keyboard(value)

    def run(self, priority, question):
        if self.done:
            return self.succeeded

        if question.startswith('kbd-chooser/method'):
#            self.preseed('kbd-chooser/method', "Select from full keyboard list")
            self.preseed('kbd-chooser/method', self.description("kbd-chooser/do_select"))
            return True

        elif question.startswith("console-keymaps-") and question.endswith("/keymap"):
            self.frontend.set_keyboard_choices(self.choices_display_map(question))
            self.frontend.set_keyboard(self.db.get(question))
            self.debug("Display map: %s", self.choices_display_map(question))
            self.debug("Untranslated choices: %s", self.choices_untranslated(question))
            self.debug("Choices: %s", self.choices(question))
            self.debug("%s db: %s", question, self.db.get(question))

            self.keyboard_question = question

        return super(KbdChooser, self).run(priority, question)

    def ok_handler(self):
        if self.keyboard_question is not None:
            keyboard = self.frontend.get_keyboard()
            if keyboard is not None:
                keyboard_value = keyboard.lower().replace(" ", "_")
                self.preseed(self.keyboard_question, keyboard_value)
                update_x_config(keyboard)

        return super(KbdChooser, self).ok_handler()


def map_keyboard(keyboard):
    """
    Takes a keyboard name from the frontend.  This is mapped using the
    same logic (hopefully) as X's configuration script and we get a
    layout which we apply.
    """
    xmap = None
    variant = None
    model = None

    if keyboard.startswith("mac-usb-"):
        keyboard = keyboard[len("mac-usb-"):]

    if keyboard.endswith("-latin1"):
        keyboard = keyboard[:-len("-latin1")]

    for k in [keyboard]: 
        if k == "be2":
            xmap = "be"
            break

        if k == "bg":
            xmap = "bg"
            variant = "bds"
            break

        if k == "br":
            xmap = "us"
            variant = "intl"
            model = "pc104"
            break

        if k == "br-abnt2":
            xmap = "br"
            variant = "abnt2"
            model = "abnt2"
            break

        if k == "by":
            xmap = "by"
            break

        if k == "cz-lat2":
            xmap = "cz"
            break

        if k == "de-latin1-nodeadkeys":
            xmap = "de"
            variant = "nodeadkeys"
            break

        if k == "de":
            xmap = "de"
            break

        if k == "dvorak":
            xmap = "us"
            variant = "dvorak"
            model = "pc104"
            break

        if k == "dk":
            xmap = "dk"
            break

        if k == "es":
            xmap = "es"
            break

        if k == "fr_CH":
            xmap = "ch"
            variant = "fr"
            break

        if k == "fr_CH-latin1":
            xmap = "ch"
            variant = "fr"
            break

        if k == "fr":
            xmap = "fr"
            break

        if k == "fr-latin9":
            xmap = "fr"
            variant = "latin9"
            break

        if k == "fi":
            xmap = "fi"
            break

        if k == "gb":
            xmap = "gb"
            break

        if k == "hebrew":
            xmap = "il"
            break

        if k == "hu":
            xmap = "hu"
            break

        if k == "is":
            xmap = "is"
            break

        if k == "it":
            xmap = "it"
            break

        if k == "jp106":
            xmap = "jp"
            variant = "jp106"
            break

        if k == "la":
            xmap = "latam"
            break

        if k == "lt":
            xmap = "lt"
            break
        
        # XXX should these be MODEL="macintosh"?

        if k == "mac-us-std":
            xmap = "us"
            break

        if k == "mac-de2-ext":
            xmap = "de"
            variant = "nodeadkeys"
            break

        if k == "mac-fr2-ext":
            xmap = "fr"
            break

        if k == "mac-fr3":
            xmap = "fr"
            break

        if k == "mac-es":
            xmap = "es"
            break

        if k == "no":
            xmap = "no"
            break

        if k == "pl":
            xmap = "pl"
            break

        if k == "pt":
            xmap = "pt"
            break

        if k == "uk":
            xmap = "gb"
            break

        if k == "lv-latin4":
            xmap = "lv"
            break

        if k == "se":
            xmap = "se"
            break

        if k == "sg":
            xmap = "ch"
            variant = "de"
            break

        if k == "sg-latin1":
            xmap = "ch"
            variant = "de"
            break

        if k == "slovene":
            xmap = "si"
            break

        if k == "sk-qwerty":
            xmap = "sk"
            variant = "qwerty"
            break

        if k == "sr-cy":
            xmap = "sr"
            break

        if k == "trf":
            xmap = "tr"
            variant = "f"
            break

        if k == "trq":
            xmap = "tr"
            break

        if k == "ua":
            xmap = "ua"
            break

        if k == "us":
            xmap = "us"
            model = "pc104"
            break

    return (xmap, model, variant)

def apply_keyboard(keyboard):
    (xmap, model, variant) = map_keyboard(keyboard)

    import syslog
    syslog.syslog(syslog.LOG_ERR, "kbd: %s" % keyboard)
    syslog.syslog(syslog.LOG_ERR, "kbd: %s %s %s" % (xmap, model, variant))

    if xmap is not None:

        if model is not None:
            model = ["-model", model]
        else:
            model = []

        if variant is not None:
            variant = ["-variant", variant]
        else:
            variant = []

        Popen(["setxkbmap", xmap] + model + variant)

def update_x_config(keyboard):
    # We also need to rewrite xorg.conf with this new setting, so that (a)
    # it persists even if you restart X on the live CD and (b) it gets
    # copied to the installed system.
    # TODO cjwatson 2006-04-05: This is ghastly. We really, really ought to
    # get xserver-xorg to do this itself, perhaps by splitting out bits of
    # the config script into library code and calling dexconf.

    (layout, model, variant) = map_keyboard(keyboard)
    if layout is None:
        return

    oldconfigfile = '/etc/X11/xorg.conf'
    newconfigfile = '/etc/X11/xorg.conf.new'
    oldconfig = open(oldconfigfile)
    newconfig = open(newconfigfile, 'w')

    re_section_inputdevice = re.compile(r'\s*Section\s+"InputDevice"\s*$')
    re_driver_kbd = re.compile(r'\s*Driver\s+"kbd"\s*$')
    re_endsection = re.compile(r'\s*EndSection\s*$')
    re_option_xkbmodel = re.compile(r'(\s*Option\s*"XkbModel"\s*).*')
    re_option_xkblayout = re.compile(r'(\s*Option\s*"XkbLayout"\s*).*')
    re_option_xkbvariant = re.compile(r'(\s*Option\s*"XkbVariant"\s*).*')
    in_inputdevice = False
    in_inputdevice_kbd = False
    done = {'model': model is None, 'layout': False,
            'variant': variant is None}

    for line in oldconfig:
        line = line.rstrip('\n')
        if re_section_inputdevice.match(line) is not None:
            in_inputdevice = True
        elif in_inputdevice and re_driver_kbd.match(line) is not None:
            in_inputdevice_kbd = True
        elif re_endsection.match(line) is not None:
            if in_inputdevice_kbd:
                if not done['model']:
                    print >>newconfig, '\tOption\t\t"XkbModel"\t"%s"' % model
                if not done['layout']:
                    print >>newconfig, '\tOption\t\t"XkbLayout"\t"%s"' % layout
                if not done['variant']:
                    print >>newconfig, \
                          '\tOption\t\t"XkbVariant"\t"%s"' % variant
            in_inputdevice = False
            in_inputdevice_kbd = False
            done = {'model': model is None, 'layout': False,
                    'variant': variant is None}
        elif in_inputdevice_kbd:
            match = re_option_xkbmodel.match(line)
            if match is not None:
                if model is None:
                    # hmm, not quite sure what to do here; guessing that
                    # forcing to pc105 will be reasonable
                    line = match.group(1) + '"pc105"'
                else:
                    line = match.group(1) + '"%s"' % model
                done['model'] = True
            else:
                match = re_option_xkblayout.match(line)
                if match is not None:
                    line = match.group(1) + '"%s"' % layout
                    done['layout'] = True
                else:
                    match = re_option_xkbvariant.match(line)
                    if match is not None:
                        if variant is None:
                            continue # delete this line
                        else:
                            line = match.group(1) + '"%s"' % variant
                        done['variant'] = True
        print >>newconfig, line

    newconfig.close()
    oldconfig.close()
    os.rename(newconfigfile, oldconfigfile)
