# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import gtk
import debconf

class WizardStep(object):
    def __init__(self, glade):
        self.gladefile = glade
        self.succeeded = False
        self.prepared = False

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

    def translate_to_c(self, question, value):
        choices = self.choices(question)
        choices_c = self.choices_untranslated(question)
        for i in range(len(choices)):
            if choices[i] == value:
                return choices_c[i]
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

    def ok_handler(self, widget, data=None):
        self.succeeded = True
        self.prepared = False
        self.dialog.destroy()

    def cancel_handler(self, widget, data=None):
        self.succeeded = False
        self.prepared = False
        self.dialog.destroy()

    def prepare(self, db):
        self.prepared = True

        self.db = db

        self.glade = gtk.glade.XML(self.gladefile)
        self.glade.signal_autoconnect(self)
        self.dialog = self.glade.get_widget('dialog')
        self.dialog.connect('destroy', gtk.main_quit)

        self.glade.get_widget('button_ok').connect('clicked', self.ok_handler)
        self.glade.get_widget('button_cancel').connect('clicked',
                                                       self.cancel_handler)

    def run(self, priority, question):
        gtk.main()
