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

# We identify as this to debconf.
PACKAGE = 'espresso'

# Bitfield constants for process_input and process_output.
DEBCONF_IO_IN = 1
DEBCONF_IO_OUT = 2
DEBCONF_IO_ERR = 4
DEBCONF_IO_HUP = 8

class FilteredCommand(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.done = False
        self.current_question = None

    def debug(self, fmt, *args):
        if 'ESPRESSO_DEBUG' in os.environ:
            message = fmt % args
            print >>sys.stderr, '%s: %s' % (PACKAGE, message)
            sys.stderr.flush()

    def start(self, auto_process=False):
        self.status = None
        prep = self.prepare()
        self.command = prep[0]
        question_patterns = prep[1]
        if len(prep) > 2:
            env = prep[2]
        else:
            env = {}
        self.ui_loop_level = 0

        self.debug("Starting up '%s' for %s.%s", self.command,
                   self.__class__.__module__, self.__class__.__name__)
        self.debug("Watching for question patterns %s",
                   ', '.join(question_patterns))

        self.db = DebconfCommunicator(PACKAGE)
        widgets = {}
        for pattern in question_patterns:
            widgets[pattern] = self
        self.dbfilter = DebconfFilter(self.db, widgets)

        # TODO: Set as unseen all questions that we're going to ask.

        if auto_process:
            self.dbfilter.start(self.command, blocking=False, extra_env=env)
            # Clearly, this isn't enough for full non-blocking operation.
            # However, debconf itself is generally quick, and the confmodule
            # will generally be listening for a reply when we try to send
            # one; the slow bit is waiting for the confmodule to decide to
            # send a command. Therefore, this is the only file descriptor we
            # bother to watch, which greatly simplifies our life.
            self.frontend.watch_debconf_fd(
                self.dbfilter.subout_fd, self.process_input)
        else:
            self.dbfilter.start(self.command, blocking=True, extra_env=env)

    def process_line(self):
        return self.dbfilter.process_line()

    def wait(self):
        ret = self.dbfilter.wait()

        if ret != 0:
            # TODO: error message if ret != 10
            self.debug("%s exited with code %d", self.command, ret)

        self.cleanup()

        self.db.shutdown()

        return ret

    def cleanup(self):
        pass

    def run_command(self, auto_process=False):
        self.start(auto_process=auto_process)
        if auto_process:
            self.enter_ui_loop()
        else:
            while self.process_line():
                pass
            self.status = self.wait()
        return self.status

    def process_input(self, source, condition):
        if source != self.dbfilter.subout_fd:
            return True

        call_again = True

        if condition & DEBCONF_IO_IN:
            if not self.process_line():
                call_again = False

        if (condition & DEBCONF_IO_ERR) or (condition & DEBCONF_IO_HUP):
            call_again = False

        if not call_again:
            # TODO cjwatson 2006-02-08: We hope this happens quickly! It
            # would be better to do this out-of-band somehow.
            self.status = self.wait()
            self.exit_ui_loops()
            self.frontend.debconffilter_done(self)

        return call_again

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
        choices = unicode(self.db.metaget(question, 'choices-c'), 'utf-8')
        return self.split_choices(choices)

    def choices(self, question):
        choices = unicode(self.db.metaget(question, 'choices'), 'utf-8')
        return self.split_choices(choices)

    def description(self, question):
        return unicode(self.db.metaget(question, 'description'), 'utf-8')

    def extended_description(self, question):
        return unicode(self.db.metaget(question, 'extended_description'),
                       'utf-8')

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
            self.db.register('espresso/dummy', name)
            self.db.set(name, value)
            self.db.subst(name, 'ID', name)

        if seen:
            self.db.fset(name, 'seen', 'true')

    def preseed_as_c(self, name, value, seen=True):
        self.preseed(name, self.translate_to_c(name, value), seen)

    # Cause the frontend to enter a recursive main loop. Will block until
    # something causes the frontend to exit that loop (probably by calling
    # exit_ui_loops).
    def enter_ui_loop(self):
        self.ui_loop_level += 1
        self.frontend.run_main_loop()

    # Exit any recursive main loops we caused the frontend to enter.
    def exit_ui_loops(self):
        while self.ui_loop_level > 0:
            self.ui_loop_level -= 1
            self.frontend.quit_main_loop()

    # User selected OK, Forward, or similar. Subclasses should override this
    # to send user-entered information back to debconf (perhaps using
    # preseed()) and return control to the filtered command. After this
    # point, self.done is set so no further user interaction should take
    # place unless an error resets it.
    def ok_handler(self):
        self.succeeded = True
        self.done = True
        self.exit_ui_loops()

    # User selected Cancel, Back, or similar. Subclasses should override
    # this to send user-entered information back to debconf (perhaps using
    # preseed()) and return control to the filtered command. After this
    # point, self.done is set so no further user interaction should take
    # place unless an error resets it.
    def cancel_handler(self):
        self.succeeded = False
        self.done = True
        self.exit_ui_loops()

    def error(self, priority, question):
        self.succeeded = False
        self.done = False
        self.enter_ui_loop()
        return True

    # The confmodule asked a question; process it. Subclasses only need to
    # override this if they want to do something special like updating their
    # UI depending on what questions were asked.
    def run(self, priority, question):
        self.current_question = question
        if not self.done:
            self.succeeded = False
            self.enter_ui_loop()
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
