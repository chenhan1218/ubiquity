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
import textwrap
import subprocess

import debconf

from ubiquity.plugin import *
from ubiquity.parted_server import PartedServer
from ubiquity.misc import *
from ubiquity.casper import get_casper

from ubiquity.filteredcommand import FilteredCommand

NAME = 'summary'

class PageGtk(PluginUI):
    plugin_is_install = True
    plugin_widgets = 'stepReady'

class PageKde(PluginUI):
    plugin_is_install = True
    plugin_widgets = 'stepReady'
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_summary'

def installing_from_disk():
    cdromfs = ''
    try:
        fp = open('/proc/mounts')
        for line in fp:
            line = line.split()
            if line[1] == '/cdrom':
                cdromfs = line[2]
                break
    finally:
        if fp:
            fp.close()
    if cdromfs == 'iso9660' or not cdromfs:
        return False
    else:
        return True

@raise_privileges
def find_grub_target():
    # This needs to be somewhat duplicated from grub-installer here because we
    # need to be able to show the user what device GRUB will be installed to
    # well before grub-installer is run.
    try:
        boot = ''
        root = ''
        p = PartedServer()
        for disk in p.disks():
            p.select_disk(disk)
            for part in p.partitions():
                part = part[1]
                if p.has_part_entry(part, 'mountpoint'):
                    mp = p.readline_part_entry(part, 'mountpoint')
                    if mp == '/boot':
                        boot = disk.replace('=', '/')
                    elif mp == '/':
                        root = disk.replace('=', '/')
        if boot:
            return boot
        elif root:
            return root
        return '(hd0)'
    except Exception, e:
        import syslog
        syslog.syslog('Exception in find_grub_target: ' + str(e))
        return '(hd0)'

def will_be_installed(pkg):
    try:
        casper_path = os.path.join(
            '/cdrom', get_casper('LIVE_MEDIA_PATH', 'casper').lstrip('/'))
        manifest = open(os.path.join(casper_path,
                                     'filesystem.manifest-desktop'))
        try:
            for line in manifest:
                if line.strip() == '' or line.startswith('#'):
                    continue
                if line.split()[0] == pkg:
                    return True
        finally:
            manifest.close()
    except IOError:
        return True

class Page(FilteredCommand):
    def prepare(self):
        return ('/usr/share/ubiquity/summary', ['^ubiquity/summary.*'])

    def run(self, priority, question):
        if question.endswith('/summary'):
            text = ''
            wrapper = textwrap.TextWrapper(width=76)
            for line in self.extended_description(question).split("\n"):
                text += wrapper.fill(line) + "\n"

            self.frontend.set_summary_text(text)

            try:
                install_bootloader = self.db.get('ubiquity/install_bootloader')
                self.frontend.set_grub(install_bootloader == 'true')
            except debconf.DebconfError:
                self.frontend.set_grub(None)

            if os.access('/usr/share/grub-installer/grub-installer', os.X_OK):
                # TODO cjwatson 2006-09-04: a bit inelegant, and possibly
                # Ubuntu-specific?
                if installing_from_disk():
                    self.frontend.set_summary_device(find_grub_target())
                else:
                    self.frontend.set_summary_device('(hd0)')
            else:
                self.frontend.set_summary_device(None)

            if will_be_installed('popularity-contest'):
                try:
                    participate = self.db.get('popularity-contest/participate')
                    self.frontend.set_popcon(participate == 'true')
                except debconf.DebconfError:
                    self.frontend.set_popcon(None)
            else:
                self.frontend.set_popcon(None)

            # This component exists only to gather some information and then
            # get out of the way.
            #return True
        return FilteredCommand.run(self, priority, question)
