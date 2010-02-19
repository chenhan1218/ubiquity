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

from ubiquity.misc import execute_root
from mythbuntu_common.installer import MythPageGtk
from ubiquity.plugin import *
import os

NAME = 'myth-backend-setup'
AFTER = 'summary'
WEIGHT = 10
HIDDEN = 'migrationassistant'

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file='mythbuntu_stepBackendSetup'
        MythPageGtk.__init__(self,controller, *args, **kwargs)

    def plugin_get_current_page(self):
        if not os.path.exists('/target/usr/bin/mythtv-setup'):
            self.controller.go_forward()
        return self.plugin_widgets

    def do_mythtv_setup(self,widget):
        """Spawn MythTV-Setup binary."""
        self.controller.toggle_top_level()
        execute_root("/usr/share/ubiquity/mythbuntu-setup")
        self.controller.toggle_top_level()
