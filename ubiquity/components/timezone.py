# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2006, 2007, 2008 Canonical Ltd.
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

import debconf

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import i18n
from ubiquity import im_switch
import ubiquity.tz

NAME = 'timezone'

class PageGtk:
    def __init__(self, *args, **kwargs):
        pass
    def get_ui(self):
        return 'stepLocation'

class PageKde:
    def __init__(self, *args, **kwargs):
        pass
    def get_ui(self):
        return 'stepLocation'

class PageDebconf:
    def __init__(self, *args, **kwargs):
        pass
    def get_ui(self):
        return 'stepLocation'

class Page(FilteredCommand):
    def prepare(self, unfiltered=False):
        if unfiltered:
            # In unfiltered mode, localechooser is responsible for selecting
            # the country, so there's no need to repeat the job here. As a
            # result, plain tzsetup rather than the wrapper that calls both
            # tzsetup and localechooser will be sufficient.
            return (['/usr/lib/ubiquity/tzsetup/tzsetup'])

        self.tzdb = ubiquity.tz.Database()
        self.multiple = False
        if not 'UBIQUITY_AUTOMATIC' in os.environ:
            self.db.fset('time/zone', 'seen', 'false')
            cc = self.db.get('debian-installer/country')
            try:
                self.db.get('tzsetup/country/%s' % cc)
                # ... and if that succeeded:
                self.multiple = True
            except debconf.DebconfError:
                pass
        self.preseed('tzsetup/selected', 'false')
        questions = ['^time/zone$']
        return (['/usr/share/ubiquity/tzsetup-wrapper'], questions)

    def run(self, priority, question):
        if question == 'time/zone':
            if self.multiple:
                # Work around a debconf bug: REGISTER does not appear to
                # give a newly-registered question the same default as the
                # question associated with its template, unless we also
                # RESET it.
                self.db.reset(question)
            zone = self.db.get(question)
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
        FilteredCommand.cleanup(self)
        i18n.reset_locale(just_country=True)
