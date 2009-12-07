# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2006, 2007, 2008 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
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

import os
import textwrap
import subprocess

import debconf

from ubiquity.plugin import *
from ubiquity.parted_server import PartedServer
from ubiquity.misc import *
from ubiquity.casper import get_casper

from ubiquity.filteredcommand import FilteredCommand

NAME = 'summary'

class PageBase(PluginUI):
    def __init__(self):
        self.grub_en = None
        self.summary_device = None
        self.popcon = None
        self.http_proxy_host = None
        self.http_proxy_port = 8080

    """ override me in base """
    def set_summary_text(self):
        pass
    
    """Set the GRUB device. A hack until we have something better."""
    def set_summary_device(self, device):
        self.summary_device = device
        
    """Get the selected GRUB device."""
    def get_summary_device(self):
        return self.summary_device
        
    """ return the proxy string """
    def get_proxy(self):
        """Get the selected HTTP proxy."""
        if self.http_proxy_host:
            return 'http://%s:%s/' % (self.http_proxy_host,
                                      self.http_proxy_port)
        else:
            return None
        
    """ enable or disable grub """
    def set_grub(self, enable):
        self.grub_en = enable
        
    """ return if grub is enabled or not """
    def get_grub(self):
        return self.grub_en
        
    """Set whether to participate in popularity-contest."""
    def set_popcon(self, participate):
        self.popcon = participate

    """Set the HTTP proxy host."""
    def set_proxy_host(self, host):
        self.http_proxy_host = host

    """Set the HTTP proxy port."""
    def set_proxy_port(self, port):    
        self.http_proxy_port = port

# TODO convert GTK side to plugin as well
class PageGtk(PluginUI):
    plugin_is_install = True
    plugin_widgets = 'stepReady'

class PageKde(PageBase):
    plugin_is_install = True
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_summary'
    
    def __init__(self, controller, *args, **kwargs):
        PageBase.__init__(self)
        
        self.controller = controller
        
        from PyQt4 import uic
        from PyQt4.QtGui import QDialog
        
        self.plugin_widgets = uic.loadUi('/usr/share/ubiquity/qt/stepSummary.ui')
        self.advanceddialog = QDialog(self.plugin_widgets)
        uic.loadUi("/usr/share/ubiquity/qt/advanceddialog.ui", self.advanceddialog)
        
        self.advanceddialog.grub_enable.stateChanged.connect(self.toggle_grub)
        self.advanceddialog.proxy_host_entry.textChanged.connect(self.enable_proxy_spinbutton)
        
        self.plugin_widgets.advanced_button.clicked.connect(self.on_advanced_button_clicked)
        self.w = self.plugin_widgets
        
    def set_summary_text (self, text):
        text = text.replace("\n", "<br>")
        self.plugin_widgets.ready_text.setText(text)
    
    def set_grub_combo(self, options):
        ''' options gives us a possible list of install locations for the boot loader '''
        self.advanceddialog.grub_device_entry.clear()
        ''' options is from summary.py grub_options() '''
        for opt in options:
           self.advanceddialog.grub_device_entry.addItem(opt[0]);
        
    def enable_proxy_spinbutton(self):
        self.advanceddialog.proxy_port_spinbutton.setEnabled(self.advanceddialog.proxy_host_entry.text() != '')

    def toggle_grub(self):
        grub_en = self.advanceddialog.grub_enable.isChecked()
        self.advanceddialog.grub_device_entry.setEnabled(grub_en)
        self.advanceddialog.grub_device_label.setEnabled(grub_en)
        
    def on_advanced_button_clicked (self):
        
        display = False
        grub_en = self.get_grub()
        summary_device = self.get_summary_device()
        
        if grub_en:
            self.advanceddialog.grub_enable.show()
            self.advanceddialog.grub_enable.setChecked(grub_en)
        else:
            self.advanceddialog.grub_enable.hide()
            summary_device = None
            
        if summary_device:
            display = True
            self.advanceddialog.bootloader_group_label.show()
            self.advanceddialog.grub_device_label.show()
            self.advanceddialog.grub_device_entry.show()
            
            # if the combo box does not yet have the target install device, add it
            # select current device
            target = find_grub_target()
            index = self.advanceddialog.grub_device_entry.findText(target)
            if (index == -1):
                self.advanceddialog.grub_device_entry.addItem(target)
                index = self.advanceddialog.grub_device_entry.count() - 1
            
            # select the target device
            self.advanceddialog.grub_device_entry.setCurrentIndex(index)
            
            self.advanceddialog.grub_device_entry.setEnabled(grub_en)
            self.advanceddialog.grub_device_label.setEnabled(grub_en)
        else:
            self.advanceddialog.bootloader_group_label.hide()
            self.advanceddialog.grub_device_label.hide()
            self.advanceddialog.grub_device_entry.hide()
            
        if self.popcon:
            display = True
            self.advanceddialog.popcon_group_label.show()
            self.advanceddialog.popcon_checkbutton.show()
            self.advanceddialog.popcon_checkbutton.setChecked(self.popcon)
        else:
            self.advanceddialog.popcon_group_label.hide()
            self.advanceddialog.popcon_checkbutton.hide()

        display = True
        if self.http_proxy_host:
            self.advanceddialog.proxy_port_spinbutton.setEnabled(True)
            self.advanceddialog.proxy_host_entry.setText(unicode(self.http_proxy_host))
        else:
            self.advanceddialog.proxy_port_spinbutton.setEnabled(False)
        self.advanceddialog.proxy_port_spinbutton.setValue(self.http_proxy_port)

        if not display:
            return

        response = self.advanceddialog.exec_()
        from PyQt4.QtGui import QDialog
        if response == QDialog.Accepted:
            if summary_device is not None:
                self.set_summary_device(
                    unicode(self.advanceddialog.grub_device_entry.currentText()))
            self.set_popcon(self.advanceddialog.popcon_checkbutton.isChecked())
            self.set_grub(self.advanceddialog.grub_enable.isChecked())
            self.set_proxy_host(unicode(self.advanceddialog.proxy_host_entry.text()))
            self.set_proxy_port(self.advanceddialog.proxy_port_spinbutton.value())

def installing_from_disk():
    cdromfs = ''
    try:
        fp = open('/proc/mounts')
        for line in fp:
            line = line.split()
            if line[1] == '/cdrom':
                cdromfs = line[2]
                break
    finally:
        if fp:
            fp.close()
    if cdromfs == 'iso9660' or not cdromfs:
        return False
    else:
        return True

def find_grub_target():
    # This needs to be somewhat duplicated from grub-installer here because we
    # need to be able to show the user what device GRUB will be installed to
    # well before grub-installer is run.
    try:
        boot = ''
        root = ''
        regain_privileges()
        p = PartedServer()
        for disk in p.disks():
            p.select_disk(disk)
            for part in p.partitions():
                part = part[1]
                if p.has_part_entry(part, 'mountpoint'):
                    mp = p.readline_part_entry(part, 'mountpoint')
                    if mp == '/boot':
                        boot = disk.replace('=', '/')
                    elif mp == '/':
                        root = disk.replace('=', '/')
        drop_privileges()
        if boot:
            return boot
        elif root:
            return root
        return '(hd0)'
    except Exception, e:
        drop_privileges()
        import syslog
        syslog.syslog('Exception in find_grub_target: ' + str(e))
        return '(hd0)'

def will_be_installed(pkg):
    try:
        casper_path = os.path.join(
            '/cdrom', get_casper('LIVE_MEDIA_PATH', 'casper').lstrip('/'))
        manifest = open(os.path.join(casper_path,
                                     'filesystem.manifest-desktop'))
        try:
            for line in manifest:
                if line.strip() == '' or line.startswith('#'):
                    continue
                if line.split()[0] == pkg:
                    return True
        finally:
            manifest.close()
    except IOError:
        return True

class Page(Plugin):
    def prepare(self):
        return ('/usr/share/ubiquity/summary', ['^ubiquity/summary.*'])

    def run(self, priority, question):
        frontend = self.frontend
        
        if self.ui:
            frontend = self.ui
    
        if question.endswith('/summary'):
            text = ''
            wrapper = textwrap.TextWrapper(width=76)
            for line in self.extended_description(question).split("\n"):
                text += wrapper.fill(line) + "\n"

            frontend.set_summary_text(text)

            try:
                install_bootloader = self.db.get('ubiquity/install_bootloader')
                frontend.set_grub(install_bootloader == 'true')
            except debconf.DebconfError:
                frontend.set_grub(None)

            if os.access('/usr/share/grub-installer/grub-installer', os.X_OK):
                # TODO cjwatson 2006-09-04: a bit inelegant, and possibly
                # Ubuntu-specific?
                if installing_from_disk():
                    frontend.set_summary_device(find_grub_target())
                else:
                    frontend.set_summary_device('(hd0)')
            else:
                frontend.set_summary_device(None)

            if will_be_installed('popularity-contest'):
                try:
                    participate = self.db.get('popularity-contest/participate')
                    frontend.set_popcon(participate == 'true')
                except debconf.DebconfError:
                    frontend.set_popcon(None)
            else:
                frontend.set_popcon(None)

            # This component exists only to gather some information and then
            # get out of the way.
            #return True
        return FilteredCommand.run(self, priority, question)
