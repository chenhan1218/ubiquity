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

from espresso.filteredcommand import FilteredCommand
import espresso.tz

class Timezone(FilteredCommand):
    def prepare(self):
        self.tzdb = espresso.tz.Database()
        questions = ['^time/zone$']
        return (['/usr/share/espresso/tzsetup'], questions)

    def run(self, priority, question):
        if question == 'time/zone':
            zone = self.db.get(question)
            # special cases where default is not in zone.tab
            if zone == 'Canada/Eastern':
                zone = 'America/Toronto'
            elif zone == 'US/Eastern':
                zone = 'America/New_York'
            self.frontend.set_timezone(zone)

        return super(Timezone, self).run(priority, question)

    def ok_handler(self):
        zone = self.frontend.get_timezone()
        self.preseed('time/zone', zone)
        for location in self.tzdb.locations:
            if location.zone == zone:
                self.preseed('debian-installer/country', location.country)
                break
        super(Timezone, self).ok_handler()
