# -*- coding: UTF-8 -*-

# Copyright (C) 2006 Canonical Ltd.
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

import textwrap
from ubiquity.filteredcommand import FilteredCommand

class Summary(FilteredCommand):
    # TODO cjwatson 2006-03-10: Having partition_info passed this way is a
    # hack; it should really live in debconf. However, this is a lot easier
    # to deal with for now.
    def __init__(self, frontend, partition_info=None):
        super(Summary, self).__init__(frontend)
        self.partition_info = partition_info

    def prepare(self):
        self.substcache = {}
        return (['/usr/share/ubiquity/summary'], ['^ubiquity/summary$'])

    def subst(self, question, key, value):
        self.substcache[key] = unicode(value, 'utf-8', 'replace')

    def run(self, question, priority):
        # TODO: untranslatable
        text = textwrap.dedent("""\
        Language: %(LANGUAGE)s
        Keyboard layout: %(KEYMAP)s
        Name: %(FULLNAME)s
        Login name: %(USERNAME)s
        Location: %(LOCATION)s
        """ % self.substcache)

        if self.partition_info is not None:
            text += "Partitioning:\n"
            wrapper = textwrap.TextWrapper(
                initial_indent='  ', subsequent_indent='  ', width=76)
            for line in self.partition_info.split("\n"):
                text += wrapper.fill(line) + "\n"

        self.frontend.set_summary_text(text)

        return super(Summary, self).run(question, priority)
