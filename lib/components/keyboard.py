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
# Foundation, Inc., 59 Temple Place, Suite 330, Boston, MA  02111-1307  USA

from filteredcommand import FilteredCommand

class Keyboard(FilteredCommand):
    def prepare(self):
        self.default_keymap = None

        # cdebconf doesn't translate selects back to C for storage in the
        # database, so kbd-chooser isn't prepared for it. (I think this is a
        # cdebconf bug. Nevertheless ...)
        self.method = self.description('kbd-chooser/do_select')
        self.preseed('kbd-chooser/method', self.method)

        questions = ['^kbd-chooser/method$',
                     '^console-keymaps.*/keymap$',
                     'ERROR']
        self.keyboard_question = None
        return (['/usr/lib/oem-config/keyboard/kbd-chooser-wrapper'],
                questions)

    def ok_handler(self):
        if self.keyboard_question is not None:
            keyboard = self.frontend.get_keyboard()
            if keyboard is not None:
                keyboard_value = keyboard.lower().replace(" ", "_")
                self.preseed(self.keyboard_question, keyboard_value)
                # TODO cjwatson 2006-07-05: reconfigure X (or wait for
                # sane-installer-keyboard so that we don't have to?)

        return super(Keyboard, self).ok_handler()

    def run(self, priority, question):
        if self.done:
            return self.succeeded

        if question == 'kbd-chooser/method':
            self.preseed('kbd-chooser/method', self.method)
            return True

        elif (question.startswith('console-keymaps-') and
              question.endswith('/keymap')):
            self.frontend.set_keyboard_choices(
                self.choices_display_map(question))
            self.frontend.set_keyboard(self.db.get(question))
            self.keyboard_question = question

        return super(Keyboard, self).run(priority, question)
