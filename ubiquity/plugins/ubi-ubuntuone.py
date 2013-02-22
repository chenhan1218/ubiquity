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

import http.client
import json
import os
import os.path
import pwd
import subprocess
import shutil
import syslog
import traceback

from ubiquity import plugin, misc

UBUNTU_SSO_URL = "https://login.ubuntu.com/api/v2/"
U1_TOKEN_NAME = "Ubuntu One"

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


# TESTING end-to-end for real
#
# * get a raring cdimage
# * run:
#    kvm -m 1500 -hda /path/to/random-image -cdrom /path/to/raring-arch.iso \
#        -boot d
# * in the VM:
#   - add universe
#   - sudo apt-get install bzr build-essential python3-setuptools debhelper
#   - bzr co --lightweight lp:~mvo/ubiquity/ssologin
#   - cd ssologin
#   - sudo cp ubiquity/plugins/* /usr/lib/ubiquity/plugins
#   - sudo cp ubiquity/* /usr/lib/ubiquity/ubiquity
#   - sudo cp gui/gtk//*.ui /usr/share/ubiquity/gtk
#   - sudo cp scripts/* /usr/share/ubiquity/
#   - sudo cp bin/ubiquity /usr/bin
#   - sudo ubiquity

class Page(plugin.Plugin):

    def prepare(self, unfiltered=False):
        self.ui._user_password = self.db.get('passwd/user-password')
        return plugin.Plugin.prepare(unfiltered)


class PageGtk(plugin.PluginUI):
    plugin_title = 'ubiquity/text/ubuntuone_heading_label'

    def __init__(self, controller, *args, **kwargs):
        from gi.repository import Gtk
        self.controller = controller
        # check if we are needed at all
        if ('UBIQUITY_AUTOMATIC' in os.environ or
                'UBIQUITY_NO_SSO' in os.environ):
            self.page = None
            return
        # check dependencies
        try:
            from gi.repository import GnomeKeyring
            assert(GnomeKeyring)
        except ImportError as e:
            syslog.syslog("skipping SSO page, no GnomeKeyring (%s)" % e)
            self.page = None
            return
        # add builder/signals
        builder = Gtk.Builder()
        self.controller.add_builder(builder)
        builder.add_from_file(
            os.path.join(os.environ['UBIQUITY_GLADE'], 'stepUbuntuOne.ui'))
        builder.connect_signals(self)
        # make the widgets available under their gtkbuilder name
        for obj in builder.get_objects():
            if issubclass(type(obj), Gtk.Buildable):
                setattr(self, Gtk.Buildable.get_name(obj), obj)
        self.page = builder.get_object('stepUbuntuOne')
        self.notebook_main.set_show_tabs(False)
        self.plugin_widgets = self.page
        self.skip_step = False
        self.online = False
        self.label_global_error.set_text("")

        self.oauth_token = None
        from gi.repository import Soup
        self.soup = Soup
        self.session = Soup.SessionAsync()
        if "DEBUG_SSO_API" in os.environ:
            self.session.add_feature(Soup.Logger.new(Soup.LoggerLogLevel.BODY,
                                                     -1))

        self.info_loop(None)

    def login_to_sso(self, email, password, token_name,
                     service_url=UBUNTU_SSO_URL):
        """Queue POST message to /tokens to get oauth token.
        See _handle_soup_message_done() for completion details.
        """
        body = json.dumps({'email': email,
                           'password': password,
                           'token_name': token_name})
        message = self.soup.Message.new("POST", service_url + "tokens")
        message.set_request('application/json',
                            self.soup.MemoryUse.COPY,
                            body, len(body))
        message.request_headers.append('Accept', 'application/json')

        self.session.queue_message(message, self._handle_soup_message_done,
                                   PAGE_LOGIN)

    def register_new_sso_account(self, email, password, displayname=None,
                                 service_url=UBUNTU_SSO_URL):
        """Queue POST to /accounts to register new account and get token.
        See _handle_soup_message_done() for completion details.
        """
        params = {'email': email,
                  'password': password}
        if displayname:
            params['displayname'] = displayname
        body = json.dumps(params)
        message = self.soup.Message.new("POST", service_url + "accounts")
        message.set_request('application/json',
                            self.soup.MemoryUse.COPY,
                            body, len(body))
        message.request_headers.append('Accept', 'application/json')

        self.session.queue_message(message, self._handle_soup_message_done,
                                   PAGE_REGISTER)

    def _handle_soup_message_done(self, session, message, from_page):
        """Handle message completion, check for errors."""
        from gi.repository import Gtk
        syslog.syslog("soup message status code %r" % message.status_code)
        content = message.response_body.flatten().get_data().decode("utf-8")

        if message.status_code in [http.client.OK, http.client.CREATED]:
            self.oauth_token = content
        else:
            response_dict = json.loads(content)
            self.notebook_main.set_current_page(from_page)
            self.label_global_error.set_markup("<b><big>%s</big></b>" %
                                               response_dict["message"])
            syslog.syslog("Error in soup message: %r" % message.reason_phrase)
            syslog.syslog("Error response headers: %r" %
                          message.get_property("response-headers"))
            syslog.syslog("error response body: %r " %
                          message.response_body.flatten().get_data())

        Gtk.main_quit()

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

        from_page = self.notebook_main.get_current_page()
        self.notebook_main.set_current_page(PAGE_SPINNER)
        self.spinner_connect.start()

        if from_page == PAGE_REGISTER:
            email = self.entry_email.get_text()
            password = self.entry_new_password.get_text()
            displayname = None # TODO get from UI
            try:
                self.register_new_sso_account(email, password,
                                              displayname=displayname)
            except Exception:
                syslog.syslog("exception in register_new_sso_account: %r" %
                              traceback.format_exc())

        elif from_page == PAGE_LOGIN:
            email = self.entry_existing_email.get_text()
            password = self.entry_existing_password.get_text()
            try:
                self.login_to_sso(email, password, U1_TOKEN_NAME)
            except Exception:
                syslog.syslog("exception in login_to_sso: %r" %
                              traceback.format_exc())

        else:
            raise AssertionError("'Next' from invalid page: %r" % from_page)

        # Start a subordinate event loop - _handle_soup_message_done stops it.
        Gtk.main()

        self.spinner_connect.stop()

        # if there is no token at this point, there is a error,
        # so stop moving forward
        if self.oauth_token is None:
            syslog.syslog("Error getting oauth_token, not creating keyring")
            return True

        # all good, create a (encrypted) keyring and store the token for later
        rv = self._create_keyring_and_store_u1_token(self.oauth_token)
        if rv != 0:
            return True
        return False

    def _create_keyring_and_store_u1_token(self, token):
        """Helper that spawns a external helper to create the keyring"""
        # this needs to be a external helper as ubiquity is running as
        # root and it seems that anything other than "drop_all_privileges"
        # will not trigger the correct dbus activation for the
        # gnome-keyring daemon
        p = subprocess.Popen(
            ["/usr/share/ubiquity/ubuntuone-keyring-helper"],
            stdin=subprocess.PIPE,
            preexec_fn=misc.drop_all_privileges,
            universal_newlines=True)
        p.stdin.write(self._user_password)
        p.stdin.write("\n")
        p.stdin.write(token)
        p.stdin.write("\n")
        res = p.wait()
        syslog.syslog("keyring helper returned %s" % res)
        return res

    def plugin_translate(self, lang):
        pasw = self.controller.get_string('password_inactive_label', lang)
        self.entry_new_password.set_placeholder_text(pasw)
        self.entry_existing_password.set_placeholder_text(pasw)
        pasw_again = self.controller.get_string(
            'password_again_inactive_label', lang)
        self.entry_new_password2.set_placeholder_text(pasw_again)
        email_p = self.controller.get_string('email_inactive_label', lang)
        self.entry_email.set_placeholder_text(email_p)
        self.entry_existing_email.set_placeholder_text(email_p)
        # error messages
        self._error_register = self.controller.get_string(
            'error_register', lang)
        self._error_login = self.controller.get_string(
            'error_login', lang)

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
        """Return True if the email address looks valid"""
        return '@' in email

    def _verify_password_entry(self, password):
        """Return True if there is a valid password"""
        return len(password) > 0

    def info_loop(self, widget):
        """Run each time the user inputs something to make controlls
           sensitive or insensitive
        """
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
        self.configure_oauth_token(target)

    def _get_target_uid(self, target_path, target_user):
        # stolen from: plugininstall.py, is there a better way?
        p = subprocess.Popen(
            ['chroot', target_path, 'sudo', '-u', target_user, '--',
             'id', '-u'], stdout=subprocess.PIPE, universal_newlines=True)
        uid = int(p.communicate()[0].strip('\n'))
        return uid

    def _get_casper_user_keyring_file_path(self):
        # stolen (again) from pluginstall.py
        try:
            casper_user = pwd.getpwuid(999).pw_name
        except KeyError:
            # We're on a weird system where the casper user isn't uid 999
            # just stop there
            return ""
        casper_user_home = os.path.expanduser('~%s' % casper_user)
        keyring_file = os.path.join(casper_user_home, ".local", "share",
                                    "keyrings", "login.keyring")
        return keyring_file

    # XXX: I am untested
    def configure_oauth_token(self, target):
        target_user = self.db.get('passwd/username')
        uid = self._get_target_uid(target, target_user)
        keyring_file = self._get_casper_user_keyring_file_path()
        if os.path.exists(keyring_file) and uid:
            targetpath = os.path.join(
                target, 'home', target_user, '.local', 'share', 'keyrings',
                'login.keyring')
            # skip copy if the target already exists, this can happen
            # if e.g. the user selected reinstall-with-keep-home
            if os.path.exists(targetpath):
                syslog.syslog("keyring path: '%s' already exists, skip copy" %
                              targetpath)
                return
            basedir = os.path.dirname(targetpath)
            # ensure we have the basedir with the righ permissions
            if not os.path.exists(basedir):
                basedir_in_chroot = os.path.join(
                    "home", target_user, ".local", "share", "keyrings")
                subprocess.call(
                    ["chroot", target,  "sudo", "-u", target_user, "--",
                     "mkdir", "-p", basedir_in_chroot])
            shutil.copy2(self.KEYRING_FILE, targetpath)
            os.lchown(targetpath, uid, uid)
            os.chmod(targetpath, 0o600)
            os.chmod(basedir, 0o700)
