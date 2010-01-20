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
from mythbuntu_common.installer import MythPageGtk
import os

NAME = 'myth-installtype'
AFTER = 'usersetup'
WEIGHT = 12

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file='mythbuntu_stepCustomInstallType'
        MythPageGtk.__init__(self,controller,*args,**kwargs)

    def set_installtype(self,type):
        """Preseeds the type of custom install"""
        #if type == "Set Top Box":
        #    self.stb.set_active(True)
        if type == "Frontend":
            self.fe.set_active(True)
        elif type == "Slave Backend":
            self.slave_be.set_active(True)
        elif type == "Master Backend":
            self.master_be.set_active(True)
        elif type == "Slave Backend/Frontend":
            self.slave_be_fe.set_active(True)
        else:
            self.master_be_fe.set_active(True)

    def get_installtype(self):
        """Returns the current custom installation type"""
        if self.master_be_fe.get_active():
            return "Master Backend/Frontend"
        elif self.slave_be_fe.get_active():
            return "Slave Backend/Frontend"
        elif self.master_be.get_active():
            return "Master Backend"
        elif self.slave_be.get_active():
            return "Slave Backend"
        elif self.fe.get_active():
            return "Frontend"
        elif self.stb.get_active():
            return "Set Top Box"

class Page(Plugin):
    def prepare(self):
        self.questions = ['install_type']
        questions = []
        for question in self.questions:
            answer = self.db.get('mythbuntu/' + question)
            if answer != '':
                self.ui.set_installtype(answer)
            questions.append('^mythbuntu/' + question)
        return (['/usr/share/ubiquity/ask-mythbuntu','type'], questions)

    def ok_handler(self):
        self.preseed('mythbuntu/' + self.questions[0],self.ui.get_installtype())
        Plugin.ok_handler(self)
