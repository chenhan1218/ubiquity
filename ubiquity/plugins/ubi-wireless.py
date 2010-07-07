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

from ubiquity.gtkwidgets import *
from ubiquity.plugin import *
import os

NAME = 'wireless'
AFTER = 'prepare'
WEIGHT = 10

# TODO debconf question for the wireless network / page itself.  Preseed null
# to skip the page.
# TODO on run(), check for a wireless card, and then for APs.  If none, go to
# next page.
# TODO skip if we have an existing connection (ubuntu.com/hiya)?
class PageGtk(PluginUI):
    plugin_title = 'ubiquity/text/wireless_heading_label'
    def __init__(self, controller, *args, **kwargs):
        if 'UBIQUITY_AUTOMATIC' in os.environ:
            self.page = None
            return
        self.controller = controller
        try:
            import gtk
            builder = gtk.Builder()
            self.controller.add_builder(builder)
            builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'], 'stepWireless.ui'))
            builder.connect_signals(self)
            self.page = builder.get_object('stepWireless')
        except Exception, e:
            self.debug('Could not create prepare page: %s', e)
            self.page = None
        self.plugin_widgets = self.page
