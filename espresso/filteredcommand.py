#! /usr/bin/python
# -*- coding: UTF-8 -*-

import sys
import os
import debconf
try:
    from debconf import DebconfCommunicator
except ImportError:
    from espresso.debconfcommunicator import DebconfCommunicator
from espresso.debconffilter import DebconfFilter

class FilteredCommand(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.done = False
        self.current_question = None
        self.package = 'espresso'

    def debug(self, fmt, *args):
        if 'ESPRESSO_DEBUG' in os.environ:
            message = fmt % args
            print >>sys.stderr, '%s: %s' % (self.package, message)

    def run_command(self, command, question_patterns=[]):
        self.db = DebconfCommunicator(self.package)
        widgets = {}
        for pattern in question_patterns:
            widgets[pattern] = self
        dbfilter = DebconfFilter(self.db, widgets)

        # TODO: Set as unseen all questions that we're going to ask.

        ret = dbfilter.run(command)

        if ret != 0:
            # TODO: error message if (ret / 256) != 10
            self.debug("%s exited with code %d", command, ret)

        self.db.shutdown()

        return ret

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

    def extended_description(self, question):
        return unicode(self.db.metaget(question, 'extended_description'))

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
            self.db.register('espresso/dummy', name)
            self.db.set(name, value)
            self.db.subst(name, 'ID', name)

        if seen:
            self.db.fset(name, 'seen', 'true')

    def preseed_as_c(self, name, value, seen=True):
        self.preseed(name, self.translate_to_c(name, value), seen)

    # User selected OK, Forward, or similar. Subclasses should override this
    # to send user-entered information back to debconf (perhaps using
    # preseed()) and return control to the filtered command. After this
    # point, self.done is set so no further user interaction should take
    # place unless an error resets it.
    def ok_handler(self):
        self.succeeded = True
        self.done = True
        self.frontend.quit_main_loop()

    # User selected Cancel, Back, or similar. Subclasses should override
    # this to send user-entered information back to debconf (perhaps using
    # preseed()) and return control to the filtered command. After this
    # point, self.done is set so no further user interaction should take
    # place unless an error resets it.
    def cancel_handler(self):
        self.succeeded = False
        self.done = True
        self.frontend.quit_main_loop()

    def error(self, priority, question):
        self.succeeded = False
        self.done = False
        self.frontend.run_main_loop()
        return True

    # The confmodule asked a question; process it. Subclasses only need to
    # override this if they want to do something special like updating their
    # UI depending on what questions were asked.
    def run(self, priority, question):
        self.current_question = question
        if not self.done:
            self.succeeded = False
            self.frontend.run_main_loop()
        return self.succeeded

    # Default progress bar handling: just pass it through to the frontend.

    def progress_start(self, progress_min, progress_max, progress_title):
        self.frontend.debconf_progress_start(progress_min, progress_max,
                                             self.description(progress_title))
        self.frontend.refresh()

    def progress_set(self, progress_title, progress_val):
        self.frontend.debconf_progress_set(progress_val)
        self.frontend.refresh()

    def progress_step(self, progress_title, progress_inc):
        self.frontend.debconf_progress_step(progress_inc)
        self.frontend.refresh()

    def progress_info(self, progress_title, progress_info):
        try:
            self.frontend.debconf_progress_info(self.description(progress_info))
            self.frontend.refresh()
        except debconf.DebconfError:
            # ignore unknown info templates
            pass

    def progress_stop(self, progress_title):
        self.frontend.debconf_progress_stop()
        self.frontend.refresh()

if __name__ == '__main__':
    import sys
    fc = FilteredCommand()
    fc.run(sys.argv[1])
