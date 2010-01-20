# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# «mythbuntu-ui» - Mythbuntu user interface
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007, 2008 Canonical Ltd.
# Copyright (C) 2007-2010, Mario Limonciello, for Mythbuntu
# Copyright (C) 2007, Jared Greenwald, for Mythbuntu
#
# Authors:
#
# - Original gtk-ui.py that this is based upon:
#   - Javier Carranza <javier.carranza#interactors._coop>
#   - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
#   - Antonio Olmo Titos <aolmo#emergya._info>
#   - Gumer Coronel Pérez <gcoronel#emergya._info>
#   - Colin Watson <cjwatson@ubuntu.com>
#   - Evan Dandrea <evand@ubuntu.com>
#   - Mario Limonciello <superm1@ubuntu.com>
#
# - This Document:
#   - Mario Limonciello <superm1@mythbuntu.org>
#   - Jared Greenwald <greenwaldjared@gmail.com>
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import gtk
import os
#Mythbuntu ubiquity imports
from ubiquity.components import mythbuntu_install

#Ubiquity imports
import ubiquity.frontend.gtk_ui as ParentFrontend
ParentFrontend.install = mythbuntu_install

class Wizard(ParentFrontend.Wizard):

#Overriden Methods
    def customize_installer(self):
        """Initial UI setup."""
        #Default to auto login, but don't make it mandatory
        #This requires disabling encrypted FS
        self.set_auto_login(True)
        self.login_encrypt.set_sensitive(False)
        self.backup=False

        ParentFrontend.Wizard.customize_installer(self)

    def run_success_cmd(self):
        """Runs mythbuntu post post install GUI step"""
        if not 'UBIQUITY_AUTOMATIC' in os.environ:
            # Ideally, this next bit (showing the backend-setup page) would
            # be fixed by re-architecting gtk_ui to run the install step after
            # the first 'is_install' plugin and just naturally ask for the rest
            # of the plugins afterward.
            backend_page = None
            type = None
            for page in self.pages:
                if page.module.NAME == 'myth-installtype':
                    type = page.ui.get_installtype()
                    if type == "Frontend":
                        break
                elif page.module.NAME == 'myth-backend-setup':
                    backend_page = page
                if backend_page and type:
                    pagenum = self.steps.page_num(page.optional_widgets[0])
                    self.set_current_page(pagenum)
                    self.live_installer.show()
                    self.installing = False
                    self.back.hide()
                    self.quit.hide()
                    self.next.set_label("Finish")
                    self.step_label.set_text("")
                    gtk.main()
                    self.live_installer.hide()
                    break
        ParentFrontend.Wizard.run_success_cmd(self)
