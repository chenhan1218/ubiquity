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
import locale

from oem_config.filteredcommand import FilteredCommand
from oem_config import i18n
from oem_config import im_switch
import oem_config.tz

class Timezone(FilteredCommand):
    def prepare(self):
        self.tzdb = oem_config.tz.Database()
        self.db.fset('time/zone', 'seen', 'false')
        questions = ['^time/zone$']
        return (['/usr/lib/oem-config/timezone/tzsetup'], questions)

    def run(self, priority, question):
        if question == 'time/zone':
            zone = self.db.get(question)
            if not zone:
                if os.path.isfile('/etc/timezone'):
                    zone = open('/etc/timezone').readline().strip()
                elif os.path.islink('/etc/localtime'):
                    zone = os.readlink('/etc/localtime')
                    if zone.startswith('/usr/share/zoneinfo/'):
                        zone = zone[len('/usr/share/zoneinfo/'):]
                    else:
                        zone = None
                else:
                    zone = None
            # Some countries don't have a default zone, so just pick the
            # first choice in the list.
            if not zone:
                choices_c = self.choices_untranslated(question)
                if choices_c:
                    zone = choices_c[0]
            # special cases where default is not in zone.tab
            if zone == 'Canada/Eastern':
                zone = 'America/Toronto'
            elif zone == 'US/Eastern':
                zone = 'America/New_York'
            self.frontend.set_timezone(zone)

        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        zone = self.frontend.get_timezone()
        if zone is None:
            zone = self.db.get('time/zone')
        else:
            self.preseed('time/zone', zone)
        for location in self.tzdb.locations:
            if location.zone == zone:
                self.preseed('debian-installer/country', location.country)
                break
        FilteredCommand.ok_handler(self)

    def cleanup(self):
        di_locale = self.db.get('debian-installer/locale')
        if di_locale not in i18n.get_supported_locales():
            di_locale = self.db.get('debian-installer/fallbacklocale')
        if di_locale != self.frontend.locale:
            self.frontend.locale = di_locale
            os.environ['LANG'] = di_locale
            os.environ['LANGUAGE'] = di_locale
            try:
                locale.setlocale(locale.LC_ALL, '')
            except locale.Error, e:
                self.debug('locale.setlocale failed: %s (LANG=%s)',
                           e, di_locale)
            im_switch.start_im()
