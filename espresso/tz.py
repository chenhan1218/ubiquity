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

import os
import datetime
import time


TZ_DATA_FILE = '/usr/share/zoneinfo/zone.tab'

def _seconds_since_epoch(dt):
    # TODO cjwatson 2006-02-23: %s escape is not portable
    return int(dt.replace(tzinfo=None).strftime('%s'))


class SystemTzInfo(datetime.tzinfo):
    def __init__(self, tz=None):
        self.tz = tz

    def _select_tz(self):
        self.tzbackup = None
        if 'TZ' in os.environ:
            self.tzbackup = os.environ['TZ']
        if self.tz is not None:
            os.environ['TZ'] = self.tz
        time.tzset()

    def _restore_tz(self):
        if self.tzbackup is None:
            if 'TZ' in os.environ:
                del os.environ['TZ']
        else:
            os.environ['TZ'] = self.tzbackup
            self.tzbackup = None
        time.tzset()

    def utcoffset(self, dt):
        self._select_tz()
        try:
            if time.daylight == 0:
                # no DST information
                dstminutes = -time.timezone / 60
            else:
                localtime = time.localtime(_seconds_since_epoch(dt))
                if localtime.tm_isdst != 1:
                    # not in DST
                    dstminutes = -time.timezone / 60
                else:
                    # in DST
                    dstminutes = -time.altzone / 60
            return datetime.timedelta(minutes=int(dstminutes))
        finally:
            self._restore_tz()

    def dst(self, dt):
        self._select_tz()
        try:
            if time.daylight == 0:
                # no DST information
                return None
            else:
                localtime = time.localtime(_seconds_since_epoch(dt))
                if localtime.tm_isdst != 1:
                    # not in DST
                    return datetime.timedelta(0)
                else:
                    dstminutes = (time.timezone - time.altzone) / 60
                    return datetime.timedelta(minutes=int(dstminutes))
        finally:
            self._restore_tz()

    def tzname(self, dt):
        return self.tz

    def tzname_letters(self, dt):
        self._select_tz()
        try:
            localtime = time.localtime(_seconds_since_epoch(dt))
            return time.strftime('%Z', localtime)
        finally:
            self._restore_tz()


# Much of the Location and Database classes are a rough translation of
# gnome-system-tools/src/time/tz.c. Thanks to Hans Petter Jansson
# <hpj@ximian.com> for that.

def _parse_position(position, wholedigits):
    if position == '' or len(position) < 4 or wholedigits > 9:
        return 0.0
    wholestr = position[:wholedigits + 1]
    fractionstr = position[wholedigits + 1:]
    whole = float(wholestr)
    fraction = float(fractionstr)
    if whole >= 0.0:
        return whole + fraction / pow(10.0, len(fractionstr))
    else:
        return whole - fraction / pow(10.0, len(fractionstr))

class Location(object):
    def __init__(self, zonetab_line):
        bits = zonetab_line.rstrip().split('\t', 3)
        latlong = bits[1]
        latlongsplit = latlong.find('-', 1)
        if latlongsplit == -1:
            latlongsplit = latlong.find('+', 1)
        if latlongsplit != -1:
            latitude = latlong[:latlongsplit]
            longitude = latlong[latlongsplit:]
        else:
            latitude = latlong
            longitude = '+0'

        self.country = bits[0]
        self.zone = bits[2]
        if len(bits) > 3:
            self.comment = bits[3]
        else:
            self.comment = None
        self.latitude = _parse_position(latitude, 2)
        self.longitude = _parse_position(longitude, 3)

        today = datetime.datetime.today()
        self.info = SystemTzInfo(self.zone)
        self.utc_offset = self.info.utcoffset(today)
        self.zone_letters = self.info.tzname_letters(today)


class Database(object):
    def __init__(self):
        self.locations = []
        tzdata = open(TZ_DATA_FILE)
        for line in tzdata:
            if line.startswith('#'):
                continue
            self.locations.append(Location(line))
        tzdata.close()
        self.locations.sort(cmp, lambda location: location.zone)
