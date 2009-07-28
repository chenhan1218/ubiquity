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
import sys
import debconf

from ubiquity.plugin import Plugin
from ubiquity import i18n
import ubiquity.tz

NAME = 'timezone'
AFTER = 'language'

class PageGtk:
    def __init__(self, *args, **kwargs):
        try:
            import gtk
            builder = gtk.Builder()
            builder.add_from_file('/usr/share/ubiquity/gtk/stepLocation.ui')
            builder.connect_signals(self)
            self.page = builder.get_object('page')
            self.region_combo = builder.get_object('timezone_zone_combo')
            self.city_combo = builder.get_object('timezone_city_combo')
            self.map_window = builder.get_object('timezone_map_window')
            self.setup_page()
        except Exception, e:
            print >>sys.stderr, 'Could not create timezone page: %s' % e
            self.page = None

    def get_ui(self):
        return self.page

    def set_timezone(self, timezone):
        self.select_city(None, timezone)

    def get_timezone(self):
        i = self.region_combo.get_active()
        m = self.region_combo.get_model()
        region = m[i][0]

        i = self.city_combo.get_active()
        m = self.city_combo.get_model()
        city = m[i][0].replace(' ', '_')
        city = region + '/' + city
        return city

    def select_city(self, widget, city):
        region, city = city.replace('_', ' ').split('/', 1)
        m = self.region_combo.get_model()
        iterator = m.get_iter_first()
        while iterator:
            if m[iterator][0] == region:
                self.region_combo.set_active_iter(iterator)
                break
            iterator = m.iter_next(iterator)
        
        m = self.city_combo.get_model()
        iterator = m.get_iter_first()
        while iterator:
            if m[iterator][0] == city:
                self.city_combo.set_active_iter(iterator)
                break
            iterator = m.iter_next(iterator)

    def setup_page(self):
        import gobject, gtk
        from ubiquity import timezone_map
        self.tzdb = ubiquity.tz.Database()
        self.tzmap = timezone_map.TimezoneMap(self.tzdb, '/usr/share/ubiquity/pixmaps/timezone')
        self.tzmap.connect('city-selected', self.select_city)
        self.map_window.add(self.tzmap)
        self.tzmap.show()

        renderer = gtk.CellRendererText()
        self.region_combo.pack_start(renderer, True)
        self.region_combo.add_attribute(renderer, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        self.region_combo.set_model(list_store)

        renderer = gtk.CellRendererText()
        self.city_combo.pack_start(renderer, True)
        self.city_combo.add_attribute(renderer, 'text', 0)
        city_store = gtk.ListStore(gobject.TYPE_STRING)
        self.city_combo.set_model(city_store)

        self.regions = {}
        for location in self.tzdb.locations:
            region, city = location.zone.replace('_', ' ').split('/', 1)
            if region in self.regions:
                self.regions[region].append(city)
            else:
                self.regions[region] = [city]

        r = self.regions.keys()
        r.sort()
        for region in r:
            list_store.append([region])

    def on_region_combo_changed(self, *args):
        i = self.region_combo.get_active()
        m = self.region_combo.get_model()
        region = m[i][0]

        m = self.city_combo.get_model()
        m.clear()
        for city in self.regions[region]:
            m.append([city])

    def on_city_combo_changed(self, *args):
        i = self.region_combo.get_active()
        m = self.region_combo.get_model()
        region = m[i][0]

        i = self.city_combo.get_active()
        if i < 0:
            # There's no selection yet.
            return
        m = self.city_combo.get_model()
        city = m[i][0].replace(' ', '_')
        city = region + '/' + city
        self.tzmap.select_city(city)

class PageKde:
    def __init__(self, controller, *args, **kwargs):
        try:
            from PyQt4 import uic
            from PyQt4.QtGui import QVBoxLayout
            from ubiquity.frontend.kde_components.Timezone import TimezoneMap
            self.page = uic.loadUi('/usr/share/ubiquity/qt/stepLocation.ui')
            self.tzmap = TimezoneMap(self.page)
            self.page.map_frame.layout().addWidget(self.tzmap)
        except:
            print >>sys.stderr, 'Could not create timezone page: %s' % e
            self.page = None

    def get_ui(self):
        return [self.page, 'ubiquity/text/step_name_timezone']

    def set_timezone (self, timezone):
        self.tzmap.set_timezone(timezone)

    def get_timezone (self):
        return self.tzmap.get_timezone()

class PageDebconf:
    def __init__(self, *args, **kwargs):
        pass
    def get_ui(self):
        return 'ubiquity/text/timezone_heading_label'

class Page(Plugin):
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
            self.ui.set_timezone(zone)

        return Plugin.run(self, priority, question)

    def ok_handler(self):
        zone = self.ui.get_timezone()
        if zone is None:
            zone = self.db.get('time/zone')
        else:
            self.preseed('time/zone', zone)
        for location in self.tzdb.locations:
            if location.zone == zone:
                self.preseed('debian-installer/country', location.country)
                break
        Plugin.ok_handler(self)

    def cleanup(self):
        Plugin.cleanup(self)
        i18n.reset_locale(just_country=True)
