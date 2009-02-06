# -*- coding: UTF-8 -*-

# Copyright (C) 2009 Canonical Ltd.
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

from oem_config.filteredcommand import FilteredCommand

class NetworkUnfilteredOnly(Exception):
    pass

# Only supports unfiltered mode.
class Network(FilteredCommand):
    def prepare(self, unfiltered=False):
        if not unfiltered:
            raise NetworkFilteredOnly, \
                "network component only usable with debconf frontend"
        return ['/usr/lib/oem-config/network/netcfg-wrapper']
