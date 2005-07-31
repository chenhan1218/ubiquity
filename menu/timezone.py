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
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import os
import gobject
import gtk
import debconf
from wizardstep import WizardStep

def _find_in_choices(choices, item):
    for index in range(len(choices)):
        if choices[index] == item:
            return index
    return None

class Timezone(WizardStep):
    area_map = {
        'Atlantic Ocean':               'Atlantic',
        'Indian Ocean':                 'Indian',
        'Pacific Ocean':                'Pacific',
        'System V style time zones':    'SystemV',
        'None of the above':            'Etc',
    }

    def update_zone_list(self, area, default_zone=None):
        select_zone = self.glade.get_widget('select_zone_combo')
        list_store = select_zone.get_model()
        list_store.clear()

        try:
            question = 'tzconfig/choose_country_zone/%s' % area
            choices = self.choices(question)
            choices_c = self.choices_untranslated(question)
        except debconf.DebconfError:
            if area in self.area_map:
                area = self.area_map[area]
            choices = []
            for root, dirs, files in os.walk('/usr/share/zoneinfo/%s' % area):
                for name in files:
                    if os.path.isfile(os.path.join(root, name)):
                        choices.append(name)
            choices.sort()
            choices_c = choices

        self.zone_c_map = {}
        for i in range(len(choices)):
            list_store.append([choices[i]])
            self.zone_c_map[choices[i]] = choices_c[i]

        if default_zone is None:
            select_zone.set_active(0)
        else:
            active = _find_in_choices(choices_c, default_zone)
            if active is None:
                select_zone.set_active(0)
            else:
                select_zone.set_active(active)

    def prepare(self, db):
        super(Timezone, self).prepare(db)

        geographic_area_choices = self.choices('tzconfig/geographic_area')
        geographic_area_choices_c = \
            self.choices_untranslated('tzconfig/geographic_area')

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

        if timezone is not None and timezone.find('/') != -1:
            (area, timezone) = timezone.split('/', 1)
        else:
            area = None

        geographic_area = self.glade.get_widget('geographic_area_combo')
        cell = gtk.CellRendererText()
        geographic_area.pack_start(cell, True)
        geographic_area.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        geographic_area.set_model(list_store)
        self.area_c_map = {}
        for i in range(len(geographic_area_choices)):
            list_store.append([geographic_area_choices[i]])
            self.area_c_map[geographic_area_choices[i]] = \
                geographic_area_choices_c[i]

        if area is not None:
            active = _find_in_choices(geographic_area_choices_c, area)
            if active is not None:
                geographic_area.set_active(active)

        select_zone = self.glade.get_widget('select_zone_combo')
        cell = gtk.CellRendererText()
        select_zone.pack_start(cell, True)
        select_zone.add_attribute(cell, 'text', 0)
        list_store = gtk.ListStore(gobject.TYPE_STRING)
        select_zone.set_model(list_store)

        self.update_zone_list(area, timezone)
        geographic_area.connect('changed', self.area_handler)

    def area_handler(self, widget, data=None):
        area = unicode(widget.get_active_text())
        self.update_zone_list(
            self.translate_to_c('tzconfig/geographic_area', area))

    def ok_handler(self, widget, data=None):
        utc = self.glade.get_widget('utc_button').get_active()
        if utc:
            self.preseed('tzconfig/gmt', 'true')
        else:
            self.preseed('tzconfig/gmt', 'false')

        area = self.glade.get_widget('geographic_area_combo').get_active_text()
        area = self.area_c_map[unicode(area)]
        zone = self.glade.get_widget('select_zone_combo').get_active_text()
        zone = self.zone_c_map[unicode(zone)]
        self.preseed('tzconfig/preseed_zone', '%s/%s' % (area, zone))

        super(Timezone, self).ok_handler(widget, data)

    def set(self, question, value):
        if question == 'tzconfig/gmt':
            utc_button = self.glade.get_widget('utc_button')
            if value == 'true':
                utc_button.set_active(True)
            else:
                utc_button.set_active(False)

    def run(self, priority, question):
        if question == 'tzconfig/verify_choices':
            # ignored for now
            return True

        return super(Timezone, self).run(priority, question)

stepname = 'Timezone'
