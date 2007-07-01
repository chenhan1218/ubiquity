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
import ubiquity.components.install
from ubiquity.filteredcommand import FilteredCommand

class Install(ubiquity.components.install.Install):
    def prepare(self):
        hostname = self.frontend.get_hostname()
        if hostname is not None and hostname != '':
            hd = hostname.split('.', 1)
            self.preseed('netcfg/get_hostname', hd[0])
            if len(hd) > 1:
                self.preseed('netcfg/get_domain', hd[1])
            else:
                self.preseed('netcfg/get_domain', '')

        if os.access('/usr/share/grub-installer/grub-installer', os.X_OK):
            bootdev = self.frontend.get_summary_device()
            if bootdev is None or bootdev == '':
                bootdev = '(hd0)'
            self.preseed('grub-installer/with_other_os', 'false')
            self.preseed('grub-installer/only_debian', 'false')
            self.preseed('grub-installer/bootdev', bootdev)

        popcon = self.frontend.get_popcon()
        if popcon is not None:
            if popcon:
                self.preseed('popularity-contest/participate', 'true')
            else:
                self.preseed('popularity-contest/participate', 'false')

        questions = ['^.*/apt-install-failed$',
                     'migration-assistant/failed-unmount',
                     'grub-installer/install_to_xfs',
                     'CAPB',
                     'ERROR',
                     'PROGRESS']
        return (['/usr/share/ubiquity/mythbuntu_install.py'], questions)
