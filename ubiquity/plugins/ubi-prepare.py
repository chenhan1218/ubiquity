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

UPOWER = 'org.freedesktop.UPower'
UPOWER_PATH = '/org/freedesktop/UPower'
PROPS = 'org.freedesktop.DBus.Properties'

NM = 'org.freedesktop.NetworkManager'
NM_PATH = '/org/freedesktop/NetworkManager'

WGET_URL = 'http://www.ubuntu.com'

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
            try:
                self.prepare_power_source = builder.get_object('prepare_power_source')
                self.setup_power_watch()
            except Exception, e:
                # TODO use an inconsistent state?
                print 'unable to set up power source watch:', e
            try:
                self.prepare_network_connection = builder.get_object('prepare_network_connection')
                self.setup_network_watch()
            except Exception, e:
                print 'unable to set up network connection watch:', e
        except Exception, e:
            self.debug('Could not create prepare page: %s', e)
            self.page = None
        self.plugin_widgets = self.page

    def setup_power_watch(self):
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        upower = bus.get_object(UPOWER, UPOWER_PATH)
        upower = dbus.Interface(upower, PROPS)
        def power_state_changed():
            self.prepare_power_source.set_state(
                upower.Get(UPOWER_PATH, 'OnBattery') == False)
        bus.add_signal_receiver(power_state_changed, 'Changed', UPOWER, UPOWER)
        power_state_changed()

    def setup_network_watch(self):
        import dbus
        from dbus.mainloop.glib import DBusGMainLoop
        DBusGMainLoop(set_as_default=True)
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.network_change, 'DeviceNoLongerActive',
                                NM, NM, NM_PATH)
        bus.add_signal_receiver(self.network_change, 'StateChange',
                                NM, NM, NM_PATH)
        self.timeout_id = None
        self.wget_retcode = None
        self.wget_proc = None
        self.network_change()

    def network_change(self, state=None):
        import gobject
        if state and (state != 4 and state != 3):
            return
        if self.timeout_id:
            gobject.source_remove(self.timeout_id)
        self.timeout_id = gobject.timeout_add(300, self.check_returncode)

    def check_returncode(self, *args):
        import subprocess
        if self.wget_retcode is not None or self.wget_proc is None:
            self.wget_proc = subprocess.Popen(
                ['wget', '-q', WGET_URL, '--timeout=15'])
        self.wget_retcode = self.wget_proc.poll()
        if self.wget_retcode is None:
            return True
        else:
            self.prepare_network_connection.set_state(self.wget_retcode == 0)
