# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2012 Canonical Ltd.
# Written by Michael Vogt <mvo@ubuntu.com>
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

from ubiquity import plugin
#from ubiquity.plugin import InstallPlugin


NAME = 'ubuntuone'
AFTER = 'usersetup'
WEIGHT = 10

(PAGE_REGISTER,
 PAGE_LOGIN,
 PAGE_SPINNER,
 ) = range(3)

# TODO:
#  - network awareness (steal from timezone map page)
#  - rename this all to ubuntu sso instead of ubuntuone to avoid confusion
#    that we force people to sign up for payed services on install (?) where
#    what we want is to make it super simple to use our services
#  - take the username from the usersetup step when creating the token
#  - get a design for the UI
#    * to create a new account
#    * to login into a existing account
#    * deal with forgoten passwords
#    * skip account creation
#  - implement actual logic/verification etc *cough*
#    * make next button sensitive/insensitive depending on valid choice
#    * requires the logic to login/create accounts without email verify
#    * simplified way to talk to login.ubuntu.com as the installer
#      won't have twisted, either piston-mini-client based (and embedd
#      it) or entirely hand done via something like the spawn helper
#  - take the oauth token and put into the users keyring (how?)
#  - make the keyring unlocked by default

class UbuntuSSO(object):

    def login(self, email, password,
              callback, errback):
        pass

    def register(self, email, password,
                 callback, errback):
        pass


class PageGtk(plugin.PluginUI):
    plugin_title = 'ubiquity/text/ubuntuone_heading_label'

    def __init__(self, controller, *args, **kwargs):
        from gi.repository import Gtk
        self.controller = controller
        builder = Gtk.Builder()
        self.controller.add_builder(builder)
        builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'],
            'stepUbuntuOne.ui'))
        builder.connect_signals(self)
        # make the widgets available under their gtkbuilder name
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                setattr(self, Gtk.Buildable.get_name(obj), obj)
        builder.connect_signals(self)
        self.page = builder.get_object('stepUbuntuOne')
        self.notebook_main.set_show_tabs(False)
        self.plugin_widgets = self.page
        self.oauth_token = None

    def plugin_get_current_page(self):
        self.page.show_all()
        # do setup stuff
        return self.page

    def plugin_on_back_clicked(self):
        # stop whatever needs stopping
        return False

    def plugin_on_next_clicked(self):
        # verify that we actually have a valid token or that the
        # user skiped the sso creation
        if self.oauth_token is not None:
            # XXX: security, security, security! is the dir secure? if
            #      not ensure mode 0600
            with open('/var/lib/ubiquity/ubuntuone_oauth_token', "w") as fp:
                fp.write(self.oauth_token)
        return False

    def plugin_translate(self, lang):
        # ???
        pass

    def on_button_have_account_clicked(self, button):
        self.notebook_main.set_current_page(PAGE_LOGIN)

    def on_button_need_account_clicked(self, button):
        self.notebook_main.set_current_page(PAGE_REGISTER)

    def on_button_skip_account_clicked(self, button):
        self.oauth_token = None
        self.plugin_on_next_clicked()

# FIXME: should we use this here instead of:
#         configure_oauth_token() in  scripts/plugininstall.py ?
#class Install(InstallPlugin):
#    def install(self, target, progress, *args, **kwargs):
#        pass
