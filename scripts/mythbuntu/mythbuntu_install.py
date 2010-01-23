#!/usr/bin/python
# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2005 Javier Carranza and others for Guadalinex
# Copyright (C) 2005, 2006, 2007, 2008, 2009 Canonical Ltd.
# Copyright (C) 2007-2009 Mario Limonciello
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

import sys
import os
sys.path.insert(0, '/usr/lib/ubiquity')

from install import Install as ParentInstall
from ubiquity import install_misc
from ubiquity import osextras


class Install(ParentInstall):

    def __init__(self):
        """Initializes the Mythbuntu installer extra objects"""

        #Configure Parent cclass First so we can override things
        ParentInstall.__init__(self)

        #This forces install_langpacks to do Nothing
        self.langpacks={}

    def install_extras(self):
        """Overrides main install_extras function to add in Mythbuntu
           drivers and services, and then call the parent function"""
        #Actually install extras
        ParentInstall.install_extras(self)

        #Run depmod if we might be using a DKMS enabled driver
        video_driver = self.db.get('mythbuntu/video_driver')
        if video_driver != "Open Source Driver":
            install_misc.chrex(self.target,'/sbin/depmod','-a')

if __name__ == '__main__':
    if not os.path.exists('/var/lib/ubiquity'):
        os.makedirs('/var/lib/ubiquity')
    osextras.unlink_force('/var/lib/ubiquity/install.trace')

    install = Install()
    sys.excepthook = install.excepthook
    install.run()
    sys.exit(0)
