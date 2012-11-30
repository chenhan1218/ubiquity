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

import re
import os
import shutil
import syslog

from ubiquity import plugin, misc


NAME = 'ubuntuone'
AFTER = 'usersetup'
WEIGHT = 10

(PAGE_REGISTER,
 PAGE_LOGIN,
 PAGE_SPINNER,
 ) = range(3)

# XXX: store the token in the DB instead (just like the user password)
#      and pull out there during "Install" (?)
OAUTH_TOKEN_FILE = '/var/lib/ubiquity/ubuntuone_oauth_token'

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
#  - run the ubuntu-sso-cli helper
#  - take the oauth token and put into the users keyring (how?)
#    * probably on first login as the keyring is using a daemon that is 
#      not available on the target fs
#  - make the keyring unlocked by default


class UbuntuSSO(object):

    # this will need the helper 
    #   lp:~mvo/+junk/cli-sso-login installed

    BINARY = "/usr/bin/ubuntu-sso-cli"

    def _child_exited(self, pid, status, data):
        stdin_fd, stdout_fd, stderr_fd, callback, errback, user_data = data
        exit_code = os.WEXITSTATUS(status)
        # the delayed reading will only work if the amount of data is
        # small enough to not cause the pipe to block which on most
        # system is ok as "ulimit -p" shows 8 pages by default (4k)
        stdout = os.read(stdout_fd, 1024).decode("utf-8")
        stderr = os.read(stderr_fd, 1024).decode("utf-8")
        if exit_code == 0:
            callback(stdout, user_data)
        else:
            errback(stderr, user_data)

    def _spawn_sso_helper(self, cmd, password, callback, errback, data):
        from gi.repository import GLib
        res, pid, stdin_fd, stdout_fd, stderr_fd = GLib.spawn_async_with_pipes(
            "/", cmd, None, 
            (GLib.SpawnFlags.LEAVE_DESCRIPTORS_OPEN|
             GLib.SpawnFlags.DO_NOT_REAP_CHILD), None, None)
        if res:
            os.write(stdin_fd, password.encode("utf-8"))
            os.write(stdin_fd, "\n".encode("utf-8"))
            GLib.child_watch_add(
                GLib.PRIORITY_DEFAULT, pid, self._child_exited, 
                (stdin_fd, stdout_fd, stderr_fd, callback, errback, data))
        else:
            errback("Failed to spawn %s" % cmd, data)

    def login(self, email, password, callback, errback, data=None):
        cmd = [self.BINARY, "--login", email]
        self._spawn_sso_helper(cmd, password, callback, errback, data)
                         
    def register(self, email, password, callback, errback, data=None):
        cmd = [self.BINARY, "--register", email]
        self._spawn_sso_helper(cmd, password, callback, errback, data)


class PageGtk(plugin.PluginUI):
    plugin_title = 'ubiquity/text/ubuntuone_heading_label'
    
    def __init__(self, controller, *args, **kwargs):
        from gi.repository import Gtk
        self.controller = controller
        # add builder/signals
        builder = Gtk.Builder()
        self.controller.add_builder(builder)
        builder.add_from_file(os.path.join(os.environ['UBIQUITY_GLADE'],
            'stepUbuntuOne.ui'))
        builder.connect_signals(self)
        # make the widgets available under their gtkbuilder name
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                setattr(self, Gtk.Buildable.get_name(obj), obj)
        self.page = builder.get_object('stepUbuntuOne')
        self.notebook_main.set_show_tabs(False)
        self.plugin_widgets = self.page
        self.oauth_token = None
        self.skip_step = False
        self.online = False
        self.label_global_error.set_text("")
        # the worker
        self.ubuntu_sso = UbuntuSSO()
        self.info_loop(None)

    def plugin_set_online_state(self, state):
        self.online = state

    def plugin_get_current_page(self):
        self.page.show_all()
        self.notebook_main.set_current_page(PAGE_REGISTER)
        return self.page

    def plugin_on_back_clicked(self):
        # stop whatever needs stopping
        return False

    def plugin_on_next_clicked(self):
        from gi.repository import Gtk
        if self.skip_step:
            return False
        if self.notebook_main.get_current_page() == PAGE_REGISTER:
            self.ubuntu_sso.register(self.entry_email.get_text(),
                                     self.entry_new_password.get_text(),
                                     callback=self._ubuntu_sso_callback,
                                     errback=self._ubuntu_sso_errback,
                                     data=PAGE_REGISTER)
        elif self.notebook_main.get_current_page() == PAGE_LOGIN:
            self.ubuntu_sso.login(self.entry_existing_email.get_text(),
                                  self.entry_existing_password.get_text(),
                                  callback=self._ubuntu_sso_callback,
                                  errback=self._ubuntu_sso_errback,
                                  data=PAGE_LOGIN)
        else:
            raise AssertionError("Should never be reached happen")

        self.notebook_main.set_current_page(PAGE_SPINNER)
        self.spinner_connect.start()
        Gtk.main()
        self.spinner_connect.stop()

        # stop moving forward if there is a error
        if self.oauth_token is None:
            return True
        else:
            with misc.raised_privileges():
                # security, security, security! ensure mode 0600
                old_umask = os.umask(0o077)
                with open(OAUTH_TOKEN_FILE, "w") as fp:
                    fp.write(self.oauth_token)
                os.umask(old_umask)
            return False

    def plugin_translate(self, lang):
        pasw = self.controller.get_string('password_inactive_label', lang)
        self.entry_new_password.set_placeholder_text(pasw)
        self.entry_new_password2.set_placeholder_text(pasw)
        self.entry_existing_password.set_placeholder_text(pasw)

    # callbacks 
    def _ubuntu_sso_callback(self, oauth_token, data):
        from gi.repository import Gtk
        self.oauth_token = oauth_token
        Gtk.main_quit()

    def _ubuntu_sso_errback(self, error, data):
        from gi.repository import Gtk
        syslog.syslog("ubuntu sso failed: '%s'" % error)
        self.notebook_main.set_current_page(data)
        if data == PAGE_REGISTER:
            err = "Error registering account"
        else:
            err = "Error loging into the account"
        self.label_global_error.set_markup("<b><big>%s</big></b>" % err)
        Gtk.main_quit()

    # signals
    def on_button_have_account_clicked(self, button):
        self.notebook_main.set_current_page(PAGE_LOGIN)

    def on_button_need_account_clicked(self, button):
        self.notebook_main.set_current_page(PAGE_REGISTER)

    def on_button_skip_account_clicked(self, button):
        self.oauth_token = None
        self.skip_step = True
        self.controller.go_forward()

    def _verify_email_entry(self, email):
        EMAIL_REGEXP = "[a-zA-Z]+@[a-zA-Z]+\.[a-zA-Z]+"
        match = re.match(EMAIL_REGEXP, email)
        return (match is not None)

    def _verify_password_entry(self, password):
        return len(password) > 0

    def info_loop(self, widget):
        complete = False
        if self.notebook_main.get_current_page() == PAGE_REGISTER:
            email = self.entry_email.get_text()
            password = self.entry_new_password.get_text()
            password2 = self.entry_new_password2.get_text()
            complete = (self._verify_email_entry(email) and
                        len(password) > 0 and
                        (password == password2))
        elif self.notebook_main.get_current_page() == PAGE_LOGIN:
            email = self.entry_existing_email.get_text()
            password = self.entry_existing_password.get_text()
            complete = (self._verify_email_entry(email) and
                        self._verify_password_entry(password))
        self.controller.allow_go_forward(complete)


class Install(plugin.InstallPlugin):

    def install(self, target, progress, *args, **kwargs):
        self.configure_oauth_token()

    # XXX: I am untested
    def configure_oauth_token(self):
        target_user = self.db.get('passwd/username')
        uid, gid = self._get_uid_gid_on_target(target_user)
        if os.path.exists(OAUTH_TOKEN_FILE) and uid and gid:
            # XXX: not copy but put into keyring really - we may need
            # to the import on first login if its too complicated to setup
            # the keyring-daemon in the target chroot
            targetpath = self.target_file(
                'home', target_user, '.ubuntuone_oauth_token')
            shutil.copy2(OAUTH_TOKEN_FILE, targetpath)
            os.lchown(targetpath, uid, gid)
            os.chmod(targetpath, 0o600)
            os.remove(OAUTH_TOKEN_FILE)
