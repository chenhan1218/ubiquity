# -*- coding: UTF-8 -*-

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
import ubiquity.tz

try:
    import PyICU
except:
    PyICU = None

class Timezone(FilteredCommand):
    def prepare(self):
        self.regions = []
        self.timezones = []
        self.tzdb = ubiquity.tz.Database()
        self.multiple = False
        try:
            # Strip .UTF-8 from locale, PyICU doesn't parse it
            locale = self.frontend.locale and self.frontend.locale.rsplit('.', 1)[0]
            self.collator = locale and PyICU and \
                            PyICU.Collator.createInstance(PyICU.Locale(locale))
        except:
            self.collator = None
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
            self.frontend.set_timezone(zone)

        return FilteredCommand.run(self, priority, question)

    def get_default_for_region(self, region):
        try:
            return self.db.get('tzsetup/country/%s' % region)
        except debconf.DebconfError:
            return None

    def collation_key(self, s):
        if self.collator:
            try:
                return self.collator.getCollationKey(s[0]).getByteArray()
            except:
                pass
        return s[0]

    # Returns [('translated country name', 'country iso3166 code')...] list
    def build_region_pairs(self):
        if self.regions: return self.regions
        continents = self.choices_untranslated('localechooser/continentlist')
        for continent in continents:
            question = 'localechooser/countrylist/%s' % continent.replace(' ', '_')
            self.regions.extend(self.choices_display_map(question).items())
        self.regions.sort(key=self.collation_key)
        return self.regions

    # Returns [('human timezone name', 'timezone')...] list
    def build_timezone_pairs(self):
        if self.timezones: return self.timezones
        for location in self.tzdb.locations:
            self.timezones.append((location.human_zone, location.zone))
        self.timezones.sort(key=self.collation_key)
        return self.timezones

    # Returns [('translated short list of countries', 'timezone')...] list
    def build_shortlist_region_pairs(self, language_code):
        try:
            shortlist = self.choices_display_map('localechooser/shortlist/%s' % language_code)
            # Remove any 'other' entry
            for pair in shortlist.items():
                if pair[1] == 'other':
                    del shortlist[pair[0]]
                    break
            shortlist = shortlist.items()
            shortlist.sort(key=self.collation_key)
            return shortlist
        except debconf.DebconfError:
            return None

    # Returns [('translated short list of timezones', 'timezone')...] list
    def build_shortlist_timezone_pairs(self, country_code):
        try:
            shortlist = self.choices_display_map('tzsetup/country/%s' % country_code)
            for pair in shortlist.items():
                # Remove any 'other' entry, we don't need it
                if pair[1] == 'other':
                    del shortlist[pair[0]]
            shortlist = shortlist.items()
            shortlist.sort(key=self.collation_key)
            return shortlist
        except debconf.DebconfError:
            return None

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
