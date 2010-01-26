# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2006, 2007, 2009 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
# Copyright (C) 2007-2010 Mario Limonciello
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ubiquity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubiquity.  If not, see <http://www.gnu.org/licenses/>.

from ubiquity.plugin import *
from mythbuntu_common.dictionaries import get_graphics_dictionary
from mythbuntu_common.installer import *
from ubiquity import install_misc
import XKit.xutils
import os

NAME = 'myth-drivers'
AFTER = 'myth-remote'
WEIGHT = 10

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        if len(get_graphics_dictionary()) > 0:
            self.ui_file = 'mythbuntu_stepDrivers'
            MythPageGtk.__init__(self, controller, *args, **kwargs)
            self.populate_video()

    def populate_video(self):
        """Finds the currently active video driver"""
        dictionary=get_graphics_dictionary()
        if len(dictionary) > 0:
            for driver in dictionary:
                self.video_driver.append_text(driver)
            self.video_driver.append_text("Open Source Driver")
            self.video_driver.set_active(len(dictionary))
            self.tvoutstandard.set_active(0)
            self.tvouttype.set_active(0)

    def toggle_tv_out (self,widget):
        """Called when the tv-out type is toggled"""
        if (self.tvouttype.get_active() == 0):
            self.tvoutstandard.set_active(0)
        elif ((self.tvouttype.get_active() == 1 or self.tvouttype.get_active() == 2) and (self.tvoutstandard.get_active() == 0 or self.tvoutstandard.get_active() >= 11 )):
            self.tvoutstandard.set_active(10)
        elif self.tvouttype.get_active() == 3:
            self.tvoutstandard.set_active(11)

    def toggle_tv_standard(self,widget):
        """Called when the tv standard is toggled"""
        if (self.tvoutstandard.get_active() >= 11):
            self.tvouttype.set_active(3)
        elif (self.tvoutstandard.get_active() < 11 and self.tvoutstandard.get_active() > 0 and self.tvouttype.get_active() == 0):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() < 11 and self.tvouttype.get_active() ==3):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() == 0):
            self.tvouttype.set_active(0)

    def video_changed (self,widget):
        """Called whenever the modify video driver option is toggled or its kids"""
        drivers=get_graphics_dictionary()
        if (widget is not None and widget.get_name() == 'video_driver'):
            try:
                self.controller.allow_go_forward(True)
            except AttributeError:
                #depends on when video_changed got called
                #the UI might not be ready yet
                pass
            type = widget.get_active()
            if (type < len(drivers)):
                self.tvout_vbox.set_sensitive(True)
            else:
                self.tvout_vbox.set_sensitive(False)
                self.tvoutstandard.set_active(0)
                self.tvouttype.set_active(0)


    def set_driver(self,name,value):
        """Preseeds the status of a driver"""
        lists = [{'video_driver': self.video_driver,
                  'tvout': self.tvouttype,
                  'tvstandard': self.tvoutstandard}]
        preseed_list(lists,name,value)

    def get_drivers(self):
        video_drivers=get_graphics_dictionary()
        active_video_driver=self.video_driver.get_active_text()
        for item in video_drivers:
            if (active_video_driver == item):
                active_video_driver=video_drivers[item]
                break
        return build_static_list([{'video_driver': active_video_driver,
                                         'tvout': self.tvouttype,
                                         'tvstandard': self.tvoutstandard}])

class Page(Plugin):
    def prepare(self):
        #drivers
        drivers = self.ui.get_drivers()
        questions = []
        for this_driver in drivers:
            answer = self.db.get('mythbuntu/' + this_driver)
            if answer != '':
                self.ui.set_driver(this_driver,answer)
        questions.append('^mythbuntu/' + this_driver)
        return (['/usr/share/ubiquity/ask-mythbuntu','drivers'], questions)

    def ok_handler(self):
        drivers = self.ui.get_drivers()

        for this_driver in drivers:
            if drivers[this_driver] is True or drivers[this_driver] is False:
                self.preseed_bool('mythbuntu/' + this_driver, drivers[this_driver])
            else:
                self.preseed('mythbuntu/' + this_driver, drivers[this_driver])
        Plugin.ok_handler(self)

class Install(InstallPlugin):

    def enable_nvidia(self, type, fmt):
        """Enables an NVIDIA graphics driver using XKit"""
        xorg_conf=XKit.xutils.XUtils()

        extra_conf_options={'NoLogo': '1',
                           'DPI': '100x100'}

        if type == 'Composite Video Output':
            extra_conf_options["ConnectedMonitor"]="TV"
            extra_conf_options["TVOutFormat"]="COMPOSITE"
            extra_conf_options["TVStandard"]=fmt
        elif type == 'S-Video Video Output':
            extra_conf_options["ConnectedMonitor"]="TV"
            extra_conf_options["TVOutFormat"]="SVIDEO"
            extra_conf_options["TVStandard"]=fmt
        elif type == 'Component Video Output':
            extra_conf_options["ConnectedMonitor"]="TV"
            extra_conf_options["TVOutFormat"]="COMPONENT"
            extra_conf_options["TVStandard"]=fmt

        #Set up device section
        relevant_devices = []
        if len(xorg_conf.globaldict['Device']) == 0:
            device = xorg_conf.makeSection('Device', identifier='Default Device')
            relevant_devices.append(device)
            xorg_conf.setDriver('Device', 'nvidia', device)
        else:
            devices = xorg_conf.getDevicesInUse()
            if len(devices) > 0:
                relevant_devices = devices
            else:
                relevant_devices = xorg_conf.globaldict['Device'].keys()
            for device in relevant_devices:
                xorg_conf.setDriver('Device', 'nvidia', device)

        for device_section in relevant_devices:
            for k, v in extra_conf_options.iteritems():
                xorg_conf.addOption('Device', k, v, optiontype='Option', position=device_section)

        #Set up screen section
        if len(xorg_conf.globaldict['Screen']) == 0:
            screen = xorg_conf.makeSection('Screen', identifier='Default Screen')

        xorg_conf.addOption('Screen', 'DefaultDepth', '24', position=0, prefix='')

        xorg_conf.writeFile(self.target + "/etc/X11/xorg.conf")

    def enable_amd(self):
        """Enables an AMD graphics driver using XKit"""
        xorg_conf=XKit.xutils.XUtils()

        #Set up device section
        relevant_devices = []
        if len(xorg_conf.globaldict['Device']) == 0:
            device = xorg_conf.makeSection('Device', identifier='Default Device')
            relevant_devices.append(device)
            xorg_conf.setDriver('Device', 'fglrx', device)
        else:
            devices = xorg_conf.getDevicesInUse()
            if len(devices) > 0:
                relevant_devices = devices
            else:
                relevant_devices = xorg_conf.globaldict['Device'].keys()
            for device in relevant_devices:
                xorg_conf.setDriver('Device', 'fglrx', device)

        #Set up screen section
        if len(xorg_conf.globaldict['Screen']) == 0:
            screen = xorg_conf.makeSection('Screen', identifier='Default Screen')

        xorg_conf.addOption('Screen', 'DefaultDepth', '24', position=0, prefix='')

        xorg_conf.writeFile(self.target + "/etc/X11/xorg.conf")

    def install(self, target, progress, *args, **kwargs):
        progress.info('ubiquity/install/drivers')
        self.target = target
        to_install = []
        video_driver = progress.get('mythbuntu/video_driver')
        if video_driver != "Open Source Driver":
            #Install driver
            to_install.append(video_driver)

            #Build tvout/tvstandard
            out = progress.get('mythbuntu/tvout')
            standard = progress.get('mythbuntu/tvstandard')
            #Enabling xorg.conf stuff
            if 'nvidia' in video_driver:
                self.enable_nvidia(out,standard)
            else:
                self.enable_amd()

        #Mark new items
        install_misc.record_installed(to_install)

        return InstallPlugin.install(self, target, progress, *args, **kwargs)
