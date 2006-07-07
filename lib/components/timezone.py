# -*- coding: UTF-8 -*-

# Copyright (C) 2005, 2006 Canonical Ltd.
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

import os
from filteredcommand import FilteredCommand

class Timezone(FilteredCommand):
    def prepare(self):
        questions = ['^tzsetup/', '^time/zone$']
        return (['/usr/lib/oem-config/timezone/tzsetup-wrapper'], questions)

    def ok_handler(self):
        zone = self.frontend.get_timezone()
        if zone is not None:
            self.preseed('time/zone', zone)

        super(Timezone, self).ok_handler()

    def run(self, priority, question):
        if question == 'time/zone':
            self.frontend.set_timezone_choices(
                self.choices_display_map(question))

            timezone = self.db.get(question)
            if timezone == '':
                if os.path.isfile('/etc/timezone'):
                    timezone = open('/etc/timezone').readline().strip()
                elif os.path.islink('/etc/localtime'):
                    timezone = os.readlink('/etc/localtime')
                    if timezone.startswith('/usr/share/zoneinfo/'):
                        timezone = timezone[len('/usr/share/zoneinfo/'):]
                    else:
                        timezone = None
                else:
                    timezone = None
            if timezone is None:
                timezone = self.choices_untranslated(question)[0]

            self.frontend.set_timezone(timezone)

        elif question == 'tzsetup/selected':
            # ignored for now
            return True

        return super(Timezone, self).run(priority, question)
