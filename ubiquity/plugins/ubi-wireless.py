# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2010 Canonical Ltd.
# Written by Evan Dandrea <evan.dandrea@canonical.com>
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

from ubiquity import plugin
import os

NAME = 'wireless'
AFTER = 'prepare'
WEIGHT = 12

class PageGtk(plugin.PluginUI):
    plugin_title = 'ubiquity/text/wireless_heading_label'
    def __init__(self, controller, *args, **kwargs):
        from ubiquity import nm
        from gi.repository import Gtk
        if (not nm.wireless_hardware_present() or
            'UBIQUITY_AUTOMATIC' in os.environ):
            self.page = None
            return
        self.controller = controller
        builder = Gtk.Builder()
        self.controller.add_builder(builder)
        builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'], 'stepWireless.ui'))
        builder.connect_signals(self)
        self.page = builder.get_object('stepWireless')
        self.nmwidget = builder.get_object('nmwidget')
        self.nmwidget.connect('connection', self.state_changed)
        self.plugin_widgets = self.page
    def state_changed(self, unused, state):
        from ubiquity import nm
        if state == nm.NM_STATE_DISCONNECTED or state == nm.NM_STATE_CONNECTED_GLOBAL:
            self.controller._wizard.connecting_spinner.hide()
            self.controller._wizard.connecting_spinner.stop()
            self.controller._wizard.connecting_label.hide()
        else:
            self.controller._wizard.connecting_spinner.show()
            self.controller._wizard.connecting_spinner.start()
            self.controller._wizard.connecting_label.show()

