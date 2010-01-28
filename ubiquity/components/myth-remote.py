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
from ubiquity import osextras
from mythbuntu_common.installer import *
from mythbuntu_common.lirc import LircHandler
from ubiquity import install_misc
import os
import debconf


NAME = 'myth-remote'
AFTER = 'myth-services'
WEIGHT = 10

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file = 'tab_remote_control'
        MythPageGtk.__init__(self, controller, *args, **kwargs)
        self.populate_lirc()
        self.remote_control_support.hide()

    def populate_lirc(self):
        """Fills the lirc pages with the appropriate data"""
        self.remote_count = 0
        self.transmitter_count = 0
        lirchandler=LircHandler()
        for item in lirchandler.get_possible_devices("remote"):
            if "Custom" not in item and "Blaster" not in item:
                self.remote_list.append_text(item)
                self.remote_count = self.remote_count + 1
        for item in lirchandler.get_possible_devices("transmitter"):
            if "Custom" not in item:
                self.transmitter_list.append_text(item)
                self.transmitter_count = self.transmitter_count + 1
        self.remote_list.set_active(0)
        self.transmitter_list.set_active(0)

    def toggle_ir(self,widget):
        """Called whenever a request to enable/disable remote is called"""
        if widget is not None:
            #turn on/off IR remote
            if widget.get_name() == 'remotecontrol':
                self.remote_hbox.set_sensitive(widget.get_active())
                self.generate_lircrc_checkbox.set_sensitive(widget.get_active())
                if widget.get_active() and self.remote_list.get_active() == 0:
                        self.remote_list.set_active(1)
                else:
                    self.remote_list.set_active(0)
            #turn on/off IR transmitter
            elif widget.get_name() == "transmittercontrol":
                self.transmitter_hbox.set_sensitive(widget.get_active())
                if widget.get_active():
                    if self.transmitter_list.get_active() == 0:
                        self.transmitter_list.set_active(1)
                else:
                    self.transmitter_list.set_active(0)
            #if our selected remote itself changed
            elif widget.get_name() == 'remote_list':
                self.generate_lircrc_checkbox.set_active(True)
                if self.remote_list.get_active() == 0:
                    self.remotecontrol.set_active(False)
                    self.generate_lircrc_checkbox.set_active(False)
            #if our selected transmitter itself changed
            elif widget.get_name() == 'transmitter_list':
                if self.transmitter_list.get_active() == 0:
                    self.transmittercontrol.set_active(False)

    def set_lirc(self,question,answer):
        """Preseeds a lirc configuration item"""
        if question == "remote":
            for i in range(0,self.remote_count):
                self.remote_list.set_active(i)
                found=False
                if self.remote_list.get_active_text() == answer:
                    found = True
                    break
                if not found:
                    self.remote_list.set_active(0)
        if question == "transmitter":
            for i in range(0,self.transmitter_count):
                self.transmitter_list.set_active(i)
                found=False
                if self.transmitter_list.get_active_text() == answer:
                    found = True
                    break
                if not found:
                    self.transmitter_list.set_active(0)

    def get_lirc(self,type):
        item = {"modules":"","device":"","driver":"","lircd_conf":""}
        if type == "remote":
            item["remote"]=self.remote_list.get_active_text()
        elif type == "transmitter":
            item["transmitter"]=self.transmitter_list.get_active_text()
        return item

class Page(Plugin):
    def prepare(self):
        self.top = ['remote', 'transmitter']
        questions = []
        for question in self.top:
            answer = self.db.get('lirc/' + question)
            if answer != '':
                self.ui.set_lirc(question,answer)
            questions.append('^lirc/' + question)
        return (['/usr/share/ubiquity/ask-mythbuntu','ir'], questions)

    def ok_handler(self):
        for question in self.top:
            device = self.ui.get_lirc(question)
            self.preseed('lirc/' + question,device[question])
        Plugin.ok_handler(self)

class Install(InstallPlugin):
    def install(self, target, progress, *args, **kwargs):
        progress.info('ubiquity/install/ir')

        lirchandler = LircHandler()

        #configure lircd for remote and transmitter
        ir_device = {"modules":"","driver":"","device":"","lircd_conf":"","remote":"","transmitter":""}
        install_misc.chroot_setup(target)
        install_misc.chrex(target,'dpkg-divert', '--package', 'ubiquity', '--rename',
                   '--quiet', '--add', '/sbin/udevd')
        try:
            os.symlink('/bin/true', '/target/sbin/udevd')
        except OSError:
            pass

        try:
            ir_device["remote"] = progress.get('lirc/remote')
            install_misc.set_debconf(target, 'lirc/remote',ir_device["remote"])
            ir_device["modules"] = ""
            ir_device["driver"] = ""
            ir_device["device"] = ""
            ir_device["lircd_conf"] = ""
            lirchandler.set_device(ir_device,"remote")
        except debconf.DebconfError:
            pass

        try:
            ir_device["transmitter"] = progress.get('lirc/transmitter')
            install_misc.set_debconf(target, 'lirc/transmitter',ir_device["transmitter"])
            ir_device["modules"] = ""
            ir_device["driver"] = ""
            ir_device["device"] = ""
            ir_device["lircd_conf"] = ""
            lirchandler.set_device(ir_device,"transmitter")
        except debconf.DebconfError:
            pass

        lirchandler.write_hardware_conf(target + '/etc/lirc/hardware.conf')

        try:
            install_misc.reconfigure(target, 'lirc')
        finally:
            osextras.unlink_force('/target/sbin/udevd')
            install_misc.chrex(target,'dpkg-divert', '--package', 'ubiquity', '--rename',
                       '--quiet', '--remove', '/sbin/udevd')
        install_misc.chroot_cleanup(target)

        #configure lircrc
        home = '/target/home/' + progress.get('passwd/username')
        os.putenv('HOME',home)
        if not os.path.isdir(home):
            os.makedirs(home)
        lirchandler.create_lircrc(os.path.join(target,"etc/lirc/lircd.conf"),False)

        return InstallPlugin.install(self, target, progress, *args, **kwargs)
