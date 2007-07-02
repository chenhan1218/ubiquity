# -*- coding: UTF-8 -*-

# Based upon Restricted Manager xorg_driver.py by Martin Pitt.
# Written to adapt to VNC by Mario Limonciello <superm1@ubuntu.com>.
#
# Copyright (C) 2006-2007 Martin Pitt
# Written by Mario Limonciello <superm1@ubuntu.com>.
# Copyright (C) 2007 Mario Limonciello
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

import os, os.path
import sys

import xorgconfig

from ubiquity.filteredcommand import FilteredCommand

class VNCHandler:
    """Used to properly enable VNC in a target configuration"""
    
    def __init__(self,root):
        self.add_modules = ["vnc"]
        self.add_screen = [ ['SecurityTypes', 'VncAuth'], ['UserPasswdVerifier', 'VncAuth'], ['PasswordFile', '/root/.vnc/passwd']]
        self.root = root
        
        try:
            self.xorg_conf = xorgconfig.readConfig(root + '/etc/X11/xorg.conf')
        except (IOError, xorgconfig.ParseException, AttributeError):
            self.xorg_conf = None

    def run(self):
        """Adds necessary lines for enabling VNC upon the next boot"""
        
        # backup the current xorg.conf
        open(os.path.join(self.root + "/etc/X11/xorg.conf.oldconf"), "w").write(open(self.root + '/etc/X11/xorg.conf').read())

        have_modules = len(self.xorg_conf.getSections("module")) > 0
        if self.add_modules:
            if not have_modules:
                self.xorg_conf.append(self.xorg_conf.makeSection(None, ["Section",
                    "Module"]))
            for m in self.add_modules:
                self.xorg_conf.getSections("module")[0].addModule(m)        
        
        screen_opts=self.xorg_conf.getSections("screen")[0].option
        for item in self.add_screen:
            screen_opts.append(screen_opts.makeLine(None,item))

        self.xorg_conf.writeConfig(self.root + '/etc/X11/xorg.conf')

class AdditionalServices(FilteredCommand):
    def prepare(self):
        return (['/usr/share/ubiquity/mythbuntu-services', '/target'],[])
