# -*- coding: UTF-8 -*-

# Copyright (C) 2006, 2007 Canonical Ltd.
# Copyright (C) 2007, Mario Limonciello
#
# Originally Written by Colin Watson <cjwatson@ubuntu.com>.
# Adapted for Mythbuntu by Mario Limonciello <superm1@ubuntu.com>
#
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

import textwrap
import ubiquity.components.summary
import os

from ubiquity.components.summary import will_be_installed

class Summary(ubiquity.components.summary.Summary):
    def prepare(self):
        return ('/usr/share/ubiquity/mythbuntu_summary', ['^mythbuntu/summary.*'])

    def run(self, priority, question):
        if question == 'mythbuntu/summary':
            text = ''
            wrapper = textwrap.TextWrapper(width=76)
            for line in self.extended_description(question).split("\n"):
                text += wrapper.fill(line) + "\n"

            self.frontend.set_summary_text(text)

            if os.access('/usr/share/grub-installer/grub-installer', os.X_OK):
                # TODO cjwatson 2006-09-04: a bit inelegant, and possibly
                # Ubuntu-specific?
                self.frontend.set_summary_device('(hd0)')
            else:
                self.frontend.set_summary_device(None)

            if will_be_installed('popularity-contest'):
                try:
                    participate = self.db.get('popularity-contest/participate')
                    self.frontend.set_popcon(participate == 'true')
                except DebconfError:
                    self.frontend.set_popcon(None)
            else:
                self.frontend.set_popcon(None)

            # This component exists only to gather some information and then
            # get out of the way.
            return True        
