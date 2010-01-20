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
from mythbuntu_common.installer import *
from mythbuntu_common.dictionaries import get_services_dictionary
import os

NAME = 'myth-services'
AFTER = 'myth-installtype'
WEIGHT = 10

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file = 'mythbuntu_stepServices'
        MythPageGtk.__init__(self, controller, *args, **kwargs)

    def toggle_customtype (self,type):
        """Called whenever a custom type is toggled"""

        if "Master" in type:
            self.mysql_option_hbox.show()
        else:
            self.enablemysql.set_active(False)
            self.mysql_option_hbox.hide()

        if "Backend" in type:
            self.samba_option_hbox.show()
            self.nfs_option_hbox.show()
        else:
            self.enablesamba.set_active(False)
            self.enablenfs.set_active(False)
            self.samba_option_hbox.hide()
            self.nfs_option_hbox.hide()

    def set_service(self,name,value):
        """Preseeds the status of a service"""
        lists = [get_services_dictionary(self,self.enablemysql)]
        preseed_list(lists,name,value)

    def get_services(self):
        """Returns the status of all installable services"""
        return build_static_list([get_services_dictionary(self,self.enablemysql)])

    def toggle_offer_vnc(self, sensitive):
        """Decides whether or not to offer VNC"""
        if sensitive:
            self.vnc_option_hbox.show()
        else:
            self.enablevnc.set_active(False)
            self.vnc_option_hbox.hide()

class Page(Plugin):
    def prepare(self):
        services = self.ui.get_services()
        questions = []
        for this_service in services:
            answer = self.db.get('mythbuntu/' + this_service)
            if answer != '':
                self.ui.set_service(this_service,answer)
            questions.append('^mythbuntu/' + this_service)

        #Hide some stuff depending on the type previously selected
        type = self.db.get('mythbuntu/install_type')
        self.ui.toggle_customtype(type)

        #VNC hates us if we have short passwords
        self.ui.toggle_offer_vnc(len(self.frontend.get_password()) >= 6)

        return (['/usr/share/ubiquity/ask-mythbuntu','services'], questions)

    def ok_handler(self):
        services = self.ui.get_services()
        for this_service in services:
            answer = services[this_service]
            if answer is True or answer is False:
                self.preseed_bool('mythbuntu/' + this_service, answer)
            else:
                self.preseed('mythbuntu/' + this_service, answer)
        Plugin.ok_handler(self)


