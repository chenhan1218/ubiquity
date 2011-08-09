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
from ubiquity import misc, osextras, i18n
from hashlib import md5
import os
import sys
import subprocess
import dbus

NAME = 'prepare'
AFTER = 'language'
WEIGHT = 11
OEM = False

UPOWER = 'org.freedesktop.UPower'
UPOWER_PATH = '/org/freedesktop/UPower'
PROPS = 'org.freedesktop.DBus.Properties'

NM = 'org.freedesktop.NetworkManager'
NM_PATH = '/org/freedesktop/NetworkManager'

JOCKEY = 'com.ubuntu.DeviceDriver'
JOCKEY_PATH = '/DeviceDriver'

WGET_URL = 'http://start.ubuntu.com/connectivity-check.html'
WGET_HASH = '4589f42e1546aa47ca181e5d949d310b'

# TODO: This cannot be a non-debconf plugin after all as OEMs may want to
# preseed the 'install updates' and 'install non-free software' options.  So?
# Just db_get them.  No need for any other overhead, surely.  Actually, you
# need the dbfilter for that get.

class PreparePageBase(plugin.PluginUI):
    plugin_title = 'ubiquity/text/prepare_heading_label'

    def setup_power_watch(self):
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
        bus = dbus.SystemBus()
        bus.add_signal_receiver(self.network_change, 'DeviceNoLongerActive',
                                NM, NM, NM_PATH)
        bus.add_signal_receiver(self.network_change, 'StateChange',
                                NM, NM, NM_PATH)
        self.timeout_id = None
        self.wget_retcode = None
        self.wget_proc = None
        self.network_change()

    @plugin.only_this_page
    def check_returncode(self, *args):
        if self.wget_retcode is not None or self.wget_proc is None:
            self.wget_proc = subprocess.Popen(
                ['wget', '-q', WGET_URL, '--timeout=15', '-O', '-'],
                stdout=subprocess.PIPE)
        self.wget_retcode = self.wget_proc.poll()
        if self.wget_retcode is None:
            return True
        else:
            state = False
            if self.wget_retcode == 0:
                h = md5()
                h.update(self.wget_proc.stdout.read())
                if WGET_HASH == h.hexdigest():
                    state = True
            self.prepare_network_connection.set_state(state)
            self.enable_download_updates(state)
            if not state:
                self.set_download_updates(False)
            self.controller.dbfilter.set_online_state(state)
            return False

    def set_sufficient_space(self, state):
        if not state:
            # There's either no drives present, or not enough free space.
            # Either way, we cannot continue.
            self.controller.allow_go_forward(False)
        self.prepare_sufficient_space.set_state(state)

    def set_sufficient_space_text(self, space):
        self.prepare_sufficient_space.set_property('label', space)

    def plugin_translate(self, lang):
        power = self.controller.get_string('prepare_power_source', lang)
        ether = self.controller.get_string('prepare_network_connection', lang)
        self.prepare_power_source.set_property('label', power)
        self.prepare_network_connection.set_property('label', ether)

class PageGtk(PreparePageBase):
    restricted_package_name = 'ubuntu-restricted-addons'
    def __init__(self, controller, *args, **kwargs):
        if 'UBIQUITY_AUTOMATIC' in os.environ:
            self.page = None
            return
        self.controller = controller
        try:
            from gi.repository import Gtk
            builder = Gtk.Builder()
            self.controller.add_builder(builder)
            builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'], 'stepPrepare.ui'))
            builder.connect_signals(self)
            self.page = builder.get_object('stepPrepare')
            self.prepare_download_updates = builder.get_object('prepare_download_updates')
            self.prepare_nonfree_software = builder.get_object('prepare_nonfree_software')
            self.prepare_sufficient_space = builder.get_object('prepare_sufficient_space')
            self.prepare_foss_disclaimer = builder.get_object('prepare_foss_disclaimer')
            self.prepare_foss_disclaimer_extra = builder.get_object('prepare_foss_disclaimer_extra_label')
            # TODO we should set these up and tear them down while on this page.
            try:
                from dbus.mainloop.glib import DBusGMainLoop
                DBusGMainLoop(set_as_default=True)
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

    def network_change(self, state=None):
        from gi.repository import GObject
        if state and (state != 4 and state != 3):
            return
        if self.timeout_id:
            GObject.source_remove(self.timeout_id)
        self.timeout_id = GObject.timeout_add(300, self.check_returncode)

    def enable_download_updates(self, val):
        self.prepare_download_updates.set_sensitive(val)

    def set_download_updates(self, val):
        self.prepare_download_updates.set_active(val)

    def get_download_updates(self):
        return self.prepare_download_updates.get_active()

    def set_allow_nonfree(self, allow):
        if not allow:
            self.prepare_nonfree_software.set_active(False)
            self.prepare_nonfree_software.set_property('visible', False)
            self.prepare_foss_disclaimer.set_property('visible', False)
            self.prepare_foss_disclaimer_extra.set_property('visible', False)

    def set_use_nonfree(self, val):
        if osextras.find_on_path('jockey-text'):
            self.prepare_nonfree_software.set_active(val)
        else:
            self.debug('Could not find jockey-text on the executable path.')
            self.set_allow_nonfree(False)

    def get_use_nonfree(self):
        return self.prepare_nonfree_software.get_active()

    def plugin_translate(self, lang):
        PreparePageBase.plugin_translate(self, lang)
        release = misc.get_release()
        from gi.repository import Gtk
        for widget in [self.prepare_foss_disclaimer]:
            text = i18n.get_string(Gtk.Buildable.get_name(widget), lang)
            text = text.replace('${RELEASE}', release.name)
            widget.set_label(text)

class PageKde(PreparePageBase):
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_prepare'
    restricted_package_name = 'kubuntu-restricted-addons'

    def __init__(self, controller, *args, **kwargs):
        from ubiquity.qtwidgets import StateBox
        if 'UBIQUITY_AUTOMATIC' in os.environ:
            self.page = None
            return
        self.controller = controller
        try:
            from PyQt4 import uic
            self.page = uic.loadUi('/usr/share/ubiquity/qt/stepPrepare.ui')
            self.prepare_download_updates = self.page.prepare_download_updates
            self.prepare_nonfree_software = self.page.prepare_nonfree_software
            self.prepare_foss_disclaimer = self.page.prepare_foss_disclaimer
            self.prepare_sufficient_space = StateBox(self.page)
            self.page.vbox1.addWidget(self.prepare_sufficient_space)
            # TODO we should set these up and tear them down while on this page.
            try:
                self.prepare_power_source = StateBox(self.page)
                self.page.vbox1.addWidget(self.prepare_power_source)
                self.setup_power_watch()
            except Exception, e:
                # TODO use an inconsistent state?
                print 'unable to set up power source watch:', e
            try:
                self.prepare_network_connection = StateBox(self.page)
                self.page.vbox1.addWidget(self.prepare_network_connection)
                self.setup_network_watch()
            except Exception, e:
                print 'unable to set up network connection watch:', e
        except Exception, e:
            print >>sys.stderr,"Could not create prepare page:", str(e)
            self.debug('Could not create prepare page: %s', e)
            self.page = None
        self.plugin_widgets = self.page

    def network_change(self, state=None):
        from PyQt4.QtCore import QTimer, SIGNAL
        if state and (state != 4 and state != 3):
            return
        QTimer.singleShot(300, self.check_returncode)
        self.timer = QTimer(self.page)
        self.timer.connect(self.timer, SIGNAL("timeout()"), self.check_returncode)
        self.timer.start(300)

    def check_returncode(self, *args):
        from PyQt4.QtCore import SIGNAL
        if not super(PageKde, self).check_returncode(args):
            self.timer.disconnect(self.timer, SIGNAL("timeout()"),
                self.check_returncode)

    def enable_download_updates(self, val):
        self.prepare_download_updates.setEnabled(val)

    def set_download_updates(self, val):
        self.prepare_download_updates.setChecked(val)

    def get_download_updates(self):
        from PyQt4.QtCore import Qt
        return self.prepare_download_updates.checkState() == Qt.Checked
    
    def set_allow_nonfree(self, allow):
        if not allow:
            self.prepare_nonfree_software.setChecked(False)
            self.prepare_nonfree_software.setVisible(False)
            self.prepare_foss_disclaimer.setVisible(False)

    def set_use_nonfree(self, val):
        if osextras.find_on_path('jockey-text'):
            self.prepare_nonfree_software.setChecked(val)
        else:
            self.debug('Could not find jockey-text on the executable path.')
            self.set_allow_nonfree(False)

    def get_use_nonfree(self):
        from PyQt4.QtCore import Qt
        return self.prepare_nonfree_software.checkState() == Qt.Checked

    def plugin_translate(self, lang):
        PreparePageBase.plugin_translate(self, lang)
        #gtk does the ${RELEASE} replace for the title in gtk_ui but we do it per plugin because our title widget is per plugin
        #also add Bold here (not sure how the gtk side keeps that formatting)
        release = misc.get_release()
        for widget in (self.page.prepare_heading_label, self.page.prepare_best_results, self.page.prepare_foss_disclaimer):
            text = widget.text()
            text = text.replace('${RELEASE}', release.name)
            text = text.replace('Ubuntu', 'Kubuntu')
            text = "<b>" + text + "</b>"
            widget.setText(text)

class Page(plugin.Plugin):
    def prepare(self):
        if (self.db.get('apt-setup/restricted') == 'false' or
            self.db.get('apt-setup/multiverse') == 'false'):
            self.ui.set_allow_nonfree(False)
        else:
            use_nonfree = self.db.get('ubiquity/use_nonfree') == 'true'
            self.ui.set_use_nonfree(use_nonfree)

        download_updates = self.db.get('ubiquity/download_updates') == 'true'
        self.ui.set_download_updates(download_updates)
        self.setup_sufficient_space()
        return (['/usr/share/ubiquity/simple-plugins', 'prepare'], ['ubiquity/use_nonfree'])

    def setup_sufficient_space(self):
        # TODO move into prepare.
        size = self.min_size()
        self.db.subst('ubiquity/text/prepare_sufficient_space', 'SIZE', misc.format_size(size))
        space = self.description('ubiquity/text/prepare_sufficient_space')
        self.ui.set_sufficient_space(self.big_enough(size))
        self.ui.set_sufficient_space_text(space)

    def min_size(self):
        # Default to 5 GB
        size = 5 * 1024 * 1024 * 1024
        try:
            with open('/cdrom/casper/filesystem.size') as fp:
                size = int(fp.readline())
        except IOError, e:
            self.debug('Could not determine squashfs size: %s' % e)
        # TODO substitute into the template for the state box.
        min_disk_size = size * 2 # fudge factor.
        return min_disk_size

    def big_enough(self, size):
        with misc.raised_privileges():
            proc = subprocess.Popen(['parted_devices'], stdout=subprocess.PIPE)
            devices = proc.communicate()[0].rstrip('\n').split('\n')
            ret = False
            for device in devices:
                if device and int(device.split('\t')[1]) > size:
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
                # Install ubuntu-restricted-addons.
                self.preseed_bool('apt-setup/universe', True)
                self.preseed_bool('apt-setup/multiverse', True)
                if self.db.fget('ubiquity/nonfree_package', 'seen') != 'true':
                    self.preseed('ubiquity/nonfree_package',
                        self.ui.restricted_package_name)
                bus = dbus.SystemBus()
                obj = bus.get_object(JOCKEY, JOCKEY_PATH)
                i = dbus.Interface(obj, JOCKEY)
                i.shutdown()
                env = os.environ.copy()
                env['DEBCONF_DB_REPLACE'] = 'configdb'
                env['DEBCONF_DB_OVERRIDE'] = 'Pipe{infd:none outfd:none}'
                subprocess.Popen(['/usr/share/jockey/jockey-backend', '--timeout=120'], env=env)
        plugin.Plugin.ok_handler(self)

    def set_online_state(self, state):
        # We maintain this state in debconf so that plugins, specficially the
        # timezone plugin and apt-setup, can be told to not hit the Internet.
        self.preseed_bool('ubiquity/online', state)
