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

from ubiquity.plugin import *
from ubiquity import misc, install_misc, osextras, i18n
import os
import subprocess

NAME = 'prepare'
AFTER = 'language'
WEIGHT = 11
OEM = False

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

# TODO: Set the 'have at least 3 GB' from /cdrom/casper/filesystem.size + a
# fudge factor.
class PageGtk(PluginUI):
    plugin_title = 'ubiquity/text/prepare_heading_label'
    def __init__(self, controller, *args, **kwargs):
        from ubiquity.gtkwidgets import StateBox
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
            self.prepare_foss_disclaimer  = builder.get_object('prepare_foss_disclaimer')
            self.prepare_download_updates = builder.get_object('prepare_download_updates')
            self.prepare_nonfree_software = builder.get_object('prepare_nonfree_software')
            self.prepare_sufficient_space = builder.get_object('prepare_sufficient_space')
            # TODO we should set these up and tear them down while on this page.
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
        # TODO abstract so we can support connman.
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

    @only_this_page
    def check_returncode(self, *args):
        if self.wget_retcode is not None or self.wget_proc is None:
            self.wget_proc = subprocess.Popen(
                ['wget', '-q', WGET_URL, '--timeout=15'])
        self.wget_retcode = self.wget_proc.poll()
        if self.wget_retcode is None:
            return True
        else:
            state = self.wget_retcode == 0
            self.prepare_network_connection.set_state(state)
            self.controller.dbfilter.set_online_state(state)
    
    def set_download_updates(self, val):
        self.prepare_download_updates.set_active(val)

    def get_download_updates(self):
        return self.prepare_download_updates.get_active()
    
    def set_use_nonfree(self, val):
        if osextras.find_on_path('jockey-text'):
            self.prepare_nonfree_software.set_active(val)
        else:
            self.debug('Could not find jockey-text on the executable path.')
            self.prepare_nonfree_software.set_active(False)
            self.prepare_nonfree_software.set_sensitive(False)

    def get_use_nonfree(self):
        return self.prepare_nonfree_software.get_active()

    def set_sufficient_space(self, state):
        self.prepare_sufficient_space.set_state(state)

    def set_sufficient_space_text(self, space):
        self.prepare_sufficient_space.set_property('label', space)
    
    def plugin_translate(self, lang):
        power = self.controller.get_string('prepare_power_source', lang)
        ether = self.controller.get_string('prepare_network_connection', lang)
        self.prepare_power_source.set_property('label', power)
        self.prepare_network_connection.set_property('label', ether)
        release = misc.get_release()
        text = i18n.get_string('prepare_foss_disclaimer', lang)
        text = text.replace('${RELEASE}', '%s' % release.name)
        self.prepare_foss_disclaimer.set_markup(text)

class Page(Plugin):
    def prepare(self):
        # TODO grey out if free software only option is checked?
        use_nonfree = self.db.get('ubiquity/use_nonfree') == 'true'
        download_updates = self.db.get('ubiquity/download_updates') == 'true'
        self.ui.set_download_updates(download_updates)
        self.ui.set_use_nonfree(use_nonfree)
        self.setup_sufficient_space()
        return (['/usr/share/ubiquity/simple-plugins', 'prepare'], ['.*'])

    def setup_sufficient_space(self):
        # TODO move into prepare.
        size = self.min_size()
        self.db.subst('ubiquity/text/prepare_sufficient_space', 'SIZE', misc.format_size(size))
        space = self.description('ubiquity/text/prepare_sufficient_space')
        self.ui.set_sufficient_space(self.big_enough(size))
        self.ui.set_sufficient_space_text(space)
        self.ui.plugin_translate(None)

    def min_size(self):
        # Default to 3 GB
        size = 3 * 1024 * 1024 * 1024
        try:
            with open('/cdrom/casper/filesystem.size') as fp:
                size = int(fp.readline())
        except Exception, e:
            self.debug('Could not determine squashfs size: %s' % e)
        # TODO substitute into the template for the state box.
        min_disk_size = size * 1.20 # fudge factor.
        return min_disk_size

    def big_enough(self, size):
        with misc.raised_privileges():
            proc = subprocess.Popen(['parted_devices'], stdout=subprocess.PIPE)
            devices = proc.communicate()[0].rstrip('\n').split('\n')
            ret = False
            for device in devices:
                if int(device.split('\t')[1]) > size:
                    ret = True
                    break
        return ret

    def ok_handler(self):
        download_updates = self.ui.get_download_updates()
        use_nonfree = self.ui.get_use_nonfree()
        self.preseed_bool('ubiquity/use_nonfree', use_nonfree)
        self.preseed_bool('ubiquity/download_updates', download_updates)
        if use_nonfree:
            with misc.raised_privileges():
                # Install non-free drivers (Broadcom STA).
                proc = subprocess.Popen(['jockey-text', '-a'])
                proc.communicate()
                # Install ubuntu-restricted-addons.
                self.preseed_bool('apt-setup/universe', True)
                self.preseed_bool('apt-setup/multiverse', True)
                install_misc.record_installed(['ubuntu-restricted-addons'])

        Plugin.ok_handler(self)

    def set_online_state(self, state):
        # TODO make this a python property of the controller.  It does not need
        # to be in debconf as preseeding it makes no sense whatsoever and it
        # never needs to be communicated to a plugin.
        self.preseed_bool('ubiquity/online', state)
