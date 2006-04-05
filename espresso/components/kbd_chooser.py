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

import os
from espresso.filteredcommand import FilteredCommand
from gtk import ListStore
import gobject
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
        return (['/bin/sh', '-c', '. /usr/share/debconf/confmodule; exec /usr/lib/espresso/kbd-chooser/kbd-chooser'],
                questions,
                {'PATH': '/usr/lib/espresso/kbd-chooser:' + os.environ['PATH']})


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
            current_kbd = self.frontend.get_keyboard().lower().replace(" ", "_")
            self.preseed(self.keyboard_question, current_kbd)

        return super(KbdChooser, self).ok_handler()


def apply_keyboard(keyboard):
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

        if k == "sr-cy":
            xmap = "sr"
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
