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

NAME = 'prepare'
AFTER = 'language'
WEIGHT = 10

# TODO: This cannot be a non-debconf plugin after all as OEMs may want to
# preseed the 'install updates' and 'install non-free software' options.  So?
# Just db_get them.  No need for any other overhead, surely.  Actually, you
# need the dbfilter for that get.
class PageGtk(PluginUI):
    plugin_title = 'ubiquity/text/prepare_heading_label'
    def __init__(self, controller, *args, **kwargs):
        if 'UBIQUITY_AUTOMATIC' in os.environ:
            self.page = None
            return
        self.controller = controller
        try:
            import gtk
            builder = gtk.Builder()
            self.controller.add_builder(builder)
            builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'], 'stepPrepare.ui'))
            builder.connect_signals(self)
            self.page = builder.get_object('stepPrepare')
        except Exception, e:
            self.debug('Could not create prepare page: %s', e)
            self.page = None
        self.plugin_widgets = self.page
