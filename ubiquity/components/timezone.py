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
import time
import re
import sys

import debconf
import PyICU

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import i18n
from ubiquity import im_switch
import ubiquity.tz

class Timezone(FilteredCommand):
    def prepare(self, unfiltered=False):
        if unfiltered:
            # In unfiltered mode, localechooser is responsible for selecting
            # the country, so there's no need to repeat the job here. As a
            # result, plain tzsetup rather than the wrapper that calls both
            # tzsetup and localechooser will be sufficient.
            return (['/usr/lib/ubiquity/tzsetup/tzsetup'])

        self.timezones = []
        self.regions = {}
        self.tzdb = ubiquity.tz.Database()
        self.multiple = False
        try:
            # Strip .UTF-8 from locale, PyICU doesn't parse it
            locale = self.frontend.locale and self.frontend.locale.rsplit('.', 1)[0]
            self.collator = locale and \
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

    def get_countries_for_region(self, region):
        if region in self.regions: return self.regions[region]

        try:
            codes = self.choices_untranslated('localechooser/countrylist/%s' % region)
        except debconf.DebconfError:
            codes = []
        self.regions[region] = codes
        return codes

    # Returns [('translated country name', None, 'region code')...] list
    def build_region_pairs(self):
        continents = self.choices_display_map('localechooser/continentlist')
        names, codes = zip(*continents.items())
        codes = [c.replace(' ', '_') for c in codes]
        
        nones = [None for key in continents]
        pairs = zip(names, nones, codes)
        pairs.sort(key=self.collation_key)
        return pairs

    # Returns [('translated short list of countries', 'timezone')...] list
    def build_shortlist_region_pairs(self, language_code):
        try:
            shortlist = self.choices_display_map('localechooser/shortlist/%s' % language_code)
            # Remove any 'other' entry
            for pair in shortlist.items():
                if pair[1] == 'other':
                    del shortlist[pair[0]]
                    break
            names, codes = zip(*shortlist.items())
            nones = [None for key in names]
            shortlist = zip(names, codes, nones)
            shortlist.sort(key=self.collation_key)
            return shortlist
        except debconf.DebconfError:
            return []

    # Returns (shortlist, longlist)
    def build_timezone_pairs(self, country_codes):
        if len(country_codes) == 1:
            shortlist = self.build_shortlist_timezone_pairs(country_codes[0])
        else:
            shortlist = []
        
        longlist = []
        for country_code in country_codes:
            longlist += self.build_longlist_timezone_pairs(country_code, sort=False)
        longlist.sort(key=self.collation_key)
        
        # There may be duplicate entries in the shortlist and longlist.
        # Basically, the shortlist is most useful when there are non-city
        # timezones that may be more familiar to denizens of that country.
        # Big examples are the US in which people tend to think in terms of
        # Eastern/Mountain/etc.  If we see a match in tz code, prefer the
        # longlist's translation and strip it from the shortlist.
        # longlist tends to be more complete in terms of translation coverage
        # (i.e. libicu is more translated than tzsetup)
        shortcopy = shortlist[:]
        for short_item in shortcopy:
            for long_item in longlist:
                if short_item[1] == long_item[1]:
                    shortlist.remove(short_item)
                    break
        
        return (shortlist, longlist)

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
        except debconf.DebconfError, e:
            return []

    def get_country_name(self, country):
        # Relatively expensive algorithmically, but we don't call this often.
        try:
            continents = self.choices_untranslated('localechooser/continentlist')
            for continent in continents:
                choices = self.choices_display_map('localechooser/countrylist/%s' % continent.replace(' ', '_'))
                for name, code in choices.items():
                    if code == country:
                        return name
        except debconf.DebconfError, e:
            print "Couldn't get country name for %s: %s" % (country, e)
        return None

    def get_city_name_from_tzdata(self, tz):
        city = tz.split('/', 1)[1]
        # Iterate through tzdata's regions, check each region's tz list for
        # our city.  Like get_country_name, this is inefficient (we could
        # cache this info), but we don't need to run this often.
        try:
            areas = self.choices_untranslated('tzdata/Areas')
            for area in areas:
                zones = self.choices_display_map('tzdata/Zones/%s' % area)
                for name, code in zones.items():
                    if code == city:
                        return name
        except debconf.DebconfError, e:
            print "Couldn't get city name for %s: %s" % (tz, e)
        return None

    def get_fallback_translation_for_tz(self, country, tz):
        # We want to return either 'Country' or 'Country (City)', translated
        # First, get country name.  We need that regardless
        country_name = self.get_country_name(country)
        if country_name is None:
            return None
        show_city = len(self.tzdb.cc_to_locs[country]) > 1
        if show_city:
            # First, try tzdata's translation.
            city_name = self.get_city_name_from_tzdata(tz)
            if city_name is None:
                city_name = tz # fall back to ASCII name
            city_name = city_name.split('/')[-1]
            return "%s (%s)" % (country_name, city_name)
        else:
            return country_name

    # Returns [('translated long list of timezones', 'timezone')...] list
    def build_longlist_timezone_pairs(self, country_code, sort=True):
        locale = self.frontend.locale and self.frontend.locale.rsplit('.', 1)[0]
        if not locale:
            return [] # ?!
        tz_format = PyICU.SimpleDateFormat('VVVV', PyICU.Locale(locale))
        now = time.time()*1000
        rv = []
        try:
            locs = self.tzdb.cc_to_locs[country_code] # BV failed?
        except:
            # Some countries in tzsetup don't exist in zone.tab...
            # Specifically BV (Bouvet Island) and
            # HM (Heard and McDonald Islands).  Both are uninhabited.
            locs = []
        for location in locs:
            tz_format.setTimeZone(PyICU.TimeZone.createTimeZone(location.zone))
            translated = tz_format.format(now)
            # Check if PyICU had a valid translation for this timezone.  If it
            # doesn't, the returned string will look like GMT+0002 or somesuch.
            # Sometimes the GMT is translated (like in Chinese), so we check
            # for the number part.  PyICU does not indicate a 'translation
            # failure' like this in any way...
            if re.search('.*[-+][0-9][0-9]:?[0-9][0-9]$', translated):
                # Wasn't something that PyICU understood...
                name = self.get_fallback_translation_for_tz(country_code, location.zone)
                rv.append((name, location.zone))
            else:
                rv.append((translated, location.zone))
        if sort:
            rv.sort(key=self.collation_key)
        return rv

    # Returns [('translated long list of timezones', 'timezone')...] list
    def build_longlist_timezone_pairs_by_continent(self, continent):
        locale = self.frontend.locale and self.frontend.locale.rsplit('.', 1)[0]
        tz_format = locale and \
                    PyICU.SimpleDateFormat('VVVV', PyICU.Locale(locale))
        now = time.time()*1000
        rv = []
        try:
            regions = self.choices_untranslated('localechooser/countrylist/%s' % continent)
            for region in regions:
                rv += self.build_longlist_timezone_pairs(region, sort=False)
            rv.sort(key=self.collation_key)
        except debconf.DebconfError:
            pass
        return rv

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
