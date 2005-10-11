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

import gtk
import debconf

class WizardStep(object):
    def __init__(self, glade):
        self.gladefile = glade
        self.done = False
        self.current_question = None

    # Split a string on commas, stripping surrounding whitespace, and
    # honouring backslash-quoting.
    def split_choices(self, text):
        textlen = len(text)
        index = 0
        items = []
        item = ''

        while index < textlen:
            if text[index] == '\\' and index + 1 < textlen:
                if text[index + 1] == ',' or text[index + 1] == ' ':
                    item += text[index + 1]
                    index += 1
            elif text[index] == ',':
                items.append(item.strip())
                item = ''
            else:
                item += text[index]
            index += 1

        if item != '':
            items.append(item.strip())

        return items

    def choices_untranslated(self, question):
        choices = unicode(self.db.metaget(question, 'choices-c'))
        return self.split_choices(choices)

    def choices(self, question):
        choices = unicode(self.db.metaget(question, 'choices'))
        return self.split_choices(choices)

    def description(self, question):
        return unicode(self.db.metaget(question, 'description'))

    def translate_title(self, question):
        widget = self.glade.get_widget('dialog')
        widget.set_title(self.description(question))

    def translate_labels(self, questions):
        for label in questions:
            widget = self.glade.get_widget(label)
            widget.set_label(self.description(questions[label]))

    def translate_to_c(self, question, value):
        choices = self.choices(question)
        choices_c = self.choices_untranslated(question)
        for i in range(len(choices)):
            if choices[i] == value:
                return choices_c[i]
        raise ValueError, value

    def value_index(self, question):
        value = self.db.get(question)
        choices_c = self.choices_untranslated(question)
        for i in range(len(choices_c)):
            if choices_c[i] == value:
                return i
        raise ValueError, value

    def preseed(self, name, value, seen=True):
        try:
            self.db.set(name, value)
        except debconf.DebconfError:
            self.db.register('debian-installer/dummy', name)
            self.db.set(name, value)
            self.db.subst(name, 'ID', name)

        if seen:
            self.db.fset(name, 'seen', 'true')

    def preseed_as_c(self, name, value, seen=True):
        self.preseed(name, self.translate_to_c(name, value), seen)

    def ok_handler(self, widget, data=None):
        self.succeeded = True
        self.done = True
        self.dialog.hide()
        gtk.main_quit()

    def cancel_handler(self, widget, data=None):
        self.succeeded = False
        self.done = True
        self.dialog.hide()
        gtk.main_quit()

    def prepare(self, db):
        self.done = False

        self.db = db

        self.glade = gtk.glade.XML(self.gladefile)
        self.glade.signal_autoconnect(self)
        self.dialog = self.glade.get_widget('dialog')
        self.dialog.connect('destroy', gtk.main_quit)

        self.glade.get_widget('button_ok').connect('clicked', self.ok_handler)
        self.glade.get_widget('button_cancel').connect('clicked',
                                                       self.cancel_handler)

    def run(self, priority, question):
        self.current_question = question
        if not self.done:
            self.succeeded = False
            self.dialog.show()
            gtk.main()
        return self.succeeded
