# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# «usersetup» - User creation plugin.
#
# Copyright (C) 2005, 2006, 2007, 2008, 2009, 2010 Canonical Ltd.
#
# Authors:
#
# - Colin Watson <cjwatson@ubuntu.com>
# - Evan Dandrea <evand@ubuntu.com>
# - Roman Shtylman <shtylman@gmail.com>
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

from ubiquity import validation
from ubiquity.misc import execute
from ubiquity.plugin import *
import debconf

NAME = 'usersetup'
AFTER = 'partman'
WEIGHT = 10

class PageBase(PluginUI):
    def __init__(self):
        self.laptop = execute("laptop-detect")
        self.allow_password_empty = False
        
    def set_fullname(self, value):        
        """Set the user's full name."""
        raise NotImplementedError('set_fullname')

    def get_fullname(self):
        """Get the user's full name."""
        raise NotImplementedError('get_fullname')
        
    def set_username(self, value):        
        """Set the user's Unix user name."""
        raise NotImplementedError('set_username')

    def get_username(self):
        """Get the user's Unix user name."""
        raise NotImplementedError('get_username')
        
    def get_password(self):
        """Get the user's password."""
        raise NotImplementedError('get_password')

    def get_verified_password(self):
        """Get the user's password confirmation."""
        raise NotImplementedError('get_verified_password')

    def select_password(self):
        """Select the text in the first password entry widget."""
        raise NotImplementedError('select_password')

    def set_auto_login(self, value):
        """Set whether the user should be automatically logged in."""
        raise NotImplementedError('set_auto_login')

    def get_auto_login(self):
        """Returns true if the user should be automatically logged in."""
        raise NotImplementedError('get_auto_login')

    def set_encrypt_home(self, value):
        """Set whether the home directory should be encrypted."""
        raise NotImplementedError('set_encrypt_home')

    def get_encrypt_home(self):
        """Returns true if the home directory should be encrypted."""
        raise NotImplementedError('get_encrypt_home')

    def username_error(self, msg):
        """The selected username was bad."""
        raise NotImplementedError('username_error')

    def password_error(self, msg):
        """The selected password was bad."""
        raise NotImplementedError('password_error')
        
    def hostname_error(self, msg):
        """ The hostname had an error """
        raise NotImplementedError('hostname_error')

    def get_hostname(self):
        """Get the selected hostname."""
        raise NotImplementedError('get_hostname')
        
    def set_hostname(self, hostname):
        raise NotImplementedError('set_hostname')
        
    def clear_errors(self):
        pass

    def info_loop(self, *args):
        """Verify user input."""
        pass
    
    def set_allow_password_empty(self, empty):
        self.allow_password_empty = empty

class PageGtk(PageBase):
    def __init__(self, controller, *args, **kwargs):
        PageBase.__init__(self, *args, **kwargs)
        self.controller = controller
        self.username_changed_id = None
        self.hostname_changed_id = None
        self.username_edited = False
        self.hostname_edited = False
        try:
            import gtk
            builder = gtk.Builder()
            self.controller.add_builder(builder)
            builder.add_from_file('/usr/share/ubiquity/gtk/stepUserInfo.ui')
            builder.connect_signals(self)
            self.page = builder.get_object('stepUserInfo')
            self.username = builder.get_object('username')
            self.fullname = builder.get_object('fullname')
            self.password = builder.get_object('password')
            self.verified_password = builder.get_object('verified_password')
            self.login_auto = builder.get_object('login_auto')
            self.login_encrypt = builder.get_object('login_encrypt')
            self.username_error_reason = builder.get_object('username_error_reason')
            self.username_error_box = builder.get_object('username_error_box')
            self.password_error_reason = builder.get_object('password_error_reason')
            self.password_error_box = builder.get_object('password_error_box')
            self.hostname_error_reason = builder.get_object( 'hostname_error_reason')
            self.hostname_error_box = builder.get_object('hostname_error_box')
            self.hostname = builder.get_object('hostname')
            
            # Some signals need to be connected by hand so that we have the
            # handler ids.
            self.username_changed_id = self.username.connect(
                'changed', self.on_username_changed)
            self.hostname_changed_id = self.hostname.connect(
                'changed', self.on_hostname_changed)

            if self.controller.oem_user_config:
                password_debug_warning_label = \
                    builder.get_object('password_debug_warning_label')
                password_debug_warning_label.show()

            if self.controller.oem_config:
                self.fullname.set_text('OEM Configuration (temporary user)')
                self.fullname.set_editable(False)
                self.fullname.set_sensitive(False)
                self.username.set_text('oem')
                self.username.set_editable(False)
                self.username.set_sensitive(False)
                self.username_edited = True
                if self.laptop:
                    self.hostname.set_text('oem-laptop')
                else:
                    self.hostname.set_text('oem-desktop')
                self.hostname_edited = True
                self.login_vbox.hide()
                # The UserSetup component takes care of preseeding passwd/user-uid.
                execute_root('apt-install', 'oem-config-gtk')
        except Exception, e:
            self.debug('Could not create keyboard page: %s', e)
            self.page = None
        self.plugin_widgets = self.page
    
    # Functions called by the Page.

    def set_fullname(self, value):
        self.fullname.set_text(value)

    def get_fullname(self):
        return self.fullname.get_text()

    def set_username(self, value):
        self.username.set_text(value)

    def get_username(self):
        return self.username.get_text()

    def get_password(self):
        return self.password.get_text()

    def get_verified_password(self):
        return self.verified_password.get_text()

    def select_password(self):
        # LP: 344402, the password should be selected if we just said "go back"
        # to the weak password entry.
        if self.password.get_text_length():
            self.password.select_region(0, -1)
            self.password.grab_focus()

    def set_auto_login(self, value):
        self.login_auto.set_active(value)

    def get_auto_login(self):
        return self.login_auto.get_active()

    def set_encrypt_home(self, value):
        self.login_encrypt.set_active(value)

    def get_encrypt_home(self):
        return self.login_encrypt.get_active()

    def username_error(self, msg):
        self.username_error_reason.set_text(msg)
        self.username_error_box.show()

    def password_error(self, msg):
        self.password_error_reason.set_text(msg)
        self.password_error_box.show()

    def hostname_error(self, msg):
        self.hostname_error_reason.set_text(msg)
        self.hostname_error_box.show()

    def get_hostname (self):
        return self.hostname.get_text()

    def set_hostname(self, value):
        self.hostname.set_text(value)
    
    def clear_errors(self):
        self.username_error_box.hide()
        self.password_error_box.hide()
        self.hostname_error_box.hide()
    
    # Callback functions.

    def info_loop(self, widget):
        """check if all entries from Identification screen are filled. Callback
        defined in ui file."""

        if (self.username_changed_id is None or
            self.hostname_changed_id is None):
            return

        if (widget is not None and widget.get_name() == 'fullname' and
            not self.username_edited):
            self.username.handler_block(self.username_changed_id)
            new_username = widget.get_text().split(' ')[0]
            new_username = new_username.encode('ascii', 'ascii_transliterate')
            new_username = new_username.lower()
            self.username.set_text(new_username)
            self.username.handler_unblock(self.username_changed_id)
        elif (widget is not None and widget.get_name() == 'username' and
              not self.hostname_edited):
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
            self.hostname.handler_block(self.hostname_changed_id)
            self.hostname.set_text(widget.get_text().strip() + hostname_suffix)
            self.hostname.handler_unblock(self.hostname_changed_id)

        complete = True
        for name in ('username', 'hostname'):
            if getattr(self, name).get_text() == '':
                complete = False
        if not self.allow_password_empty:
            for name in ('password', 'verified_password'):
                if getattr(self, name).get_text() == '':
                    complete = False
        self.controller.allow_go_forward(complete)

    def on_username_changed(self, widget):
        self.username_edited = (widget.get_text() != '')

    def on_hostname_changed(self, widget):
        self.hostname_edited = (widget.get_text() != '')

class PageKde(PageBase):
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_user'
    
    def __init__(self, controller, *args, **kwargs):
        PageBase.__init__(self, *args, **kwargs)
        self.controller = controller
        
        from PyQt4 import uic
        from PyQt4.QtGui import QDialog
        from PyKDE4.kdeui import KIconLoader
        
        self.plugin_widgets = uic.loadUi('/usr/share/ubiquity/qt/stepUserSetup.ui')
        self.page = self.plugin_widgets
        
        self.username_edited = False
        self.hostname_edited = False
        
        if self.controller.oem_config:
            self.page.fullname.setText('OEM Configuration (temporary user)')
            self.page.fullname.setReadOnly(True)
            self.page.fullname.setEnabled(False)
            self.page.username.setText('oem')
            self.page.username.setReadOnly(True)
            self.page.username.setEnabled(False)
            self.page.login_pass.hide()
            self.page.login_auto.hide()
            self.page.login_encrypt.hide()
            self.username_edited = True
            self.hostname_edited = True
            
            if self.laptop:
                self.page.hostname.setText('oem-laptop')
            else:
                self.page.hostname.setText('oem-desktop')
                
        iconLoader = KIconLoader()
        warningIcon = iconLoader.loadIcon("dialog-warning", KIconLoader.Desktop)
        self.page.fullname_error_image.setPixmap(warningIcon)
        self.page.username_error_image.setPixmap(warningIcon)
        self.page.password_error_image.setPixmap(warningIcon)
        self.page.hostname_error_image.setPixmap(warningIcon)
        
        self.clear_errors()
        
        self.page.fullname.textChanged[str].connect(self.on_fullname_changed)
        self.page.username.textChanged[str].connect(self.on_username_changed)
        self.page.hostname.textChanged[str].connect(self.on_hostname_changed)
        #self.page.password.textChanged[str].connect(self.on_password_changed)
        #self.page.verified_password.textChanged[str].connect(self.on_verified_password_changed)
        
        self.page.password_debug_warning_label.setVisible('UBIQUITY_DEBUG' in os.environ)                    
    
    def on_fullname_changed(self):
        # If the user did not manually enter a username create one for him.
        if not self.username_edited:
            self.page.username.blockSignals(True)
            new_username = unicode(self.page.fullname.text()).split(' ')[0]
            new_username = new_username.encode('ascii', 'ascii_transliterate').lower()
            self.page.username.setText(new_username)
            self.page.username.blockSignals(False)

    def on_username_changed(self):
        if not self.hostname_edited:
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
                
            self.page.hostname.blockSignals(True)
            self.page.hostname.setText(unicode(self.page.hostname.text()).strip() + hostname_suffix)
            self.page.hostname.blockSignals(False)
            
        self.username_edited = (self.page.username.text() != '')

    def on_password_changed(self):
        pass

    def on_verified_password_changed(self):
        pass

    def on_hostname_changed(self):
        self.hostname_edited = (self.page.hostname.text() != '')
        
    def set_fullname(self, value):
        self.page.fullname.setText(unicode(value, "UTF-8"))

    def get_fullname(self):
        return unicode(self.page.fullname.text())

    def set_username(self, value):
        self.page.username.setText(unicode(value, "UTF-8"))

    def get_username(self):
        return unicode(self.page.username.text())

    def get_password(self):
        return unicode(self.page.password.text())

    def get_verified_password(self):
        return unicode(self.page.verified_password.text())

    def select_password(self):
        self.page.password.selectAll()

    def set_auto_login(self, value):
        return self.page.login_auto.setChecked(value)

    def get_auto_login(self):
        return self.page.login_auto.isChecked()
    
    def set_encrypt_home(self, value):
        self.page.login_encrypt.setChecked(value)

    def get_encrypt_home(self):
        return self.page.login_encrypt.isChecked()

    def username_error(self, msg):
        self.page.username_error_reason.setText(msg)
        self.page.username_error_image.show()
        self.page.username_error_reason.show()

    def password_error(self, msg):
        self.page.password_error_reason.setText(msg)
        self.page.password_error_image.show()
        self.page.password_error_reason.show()
        
    def hostname_error(self, msg):
        self.page.hostname_error_reason.setText(msg)
        self.page.hostname_error_image.show()
        self.page.hostname_error_reason.show();

    def get_hostname (self):
        return unicode(self.page.hostname.text())

    def set_hostname (self, value):
        self.page.hostname.setText(value)
        
    def clear_errors(self):
        self.page.fullname_error_image.hide()
        self.page.username_error_image.hide()
        self.page.password_error_image.hide()
        self.page.hostname_error_image.hide()
        
        self.page.username_error_reason.hide()
        self.page.password_error_reason.hide()
        self.page.hostname_error_reason.hide()

class PageDebconf(PluginUI):
    plugin_title = 'ubiquity/text/userinfo_heading_label'

class PageNoninteractive(PluginUI):
    def __init__(self, controller, *args, **kwargs):
        PageBase.__init__(self, *args, **kwargs)
        self.controller = controller
        self.fullname = ''
        self.username = ''
        self.password = ''
        self.verifiedpassword = ''
        self.auto_login = False
        self.encrypt_home = False

    def set_fullname(self, value):
        """Set the user's full name."""
        self.fullname = value

    def get_fullname(self):
        """Get the user's full name."""
        if self.oem_config:
            return 'OEM Configuration (temporary user)'
        return self.fullname

    def set_username(self, value):
        """Set the user's Unix user name."""
        self.username = value

    def get_username(self):
        """Get the user's Unix user name."""
        if self.oem_config:
            return 'oem'
        return self.username

    def get_password(self):
        """Get the user's password."""
        return self.dbfilter.db.get('passwd/user-password')

    def get_verified_password(self):
        """Get the user's password confirmation."""
        return self.dbfilter.db.get('passwd/user-password-again')

    def set_auto_login(self, value):
        self.auto_login = value

    def get_auto_login(self):
        return self.auto_login
    
    def set_encrypt_home(self, value):
        self.encrypt_home = value

    def get_encrypt_home(self):
        return self.encrypt_home

    def username_error(self, msg):
        """The selected username was bad."""
        print >>self.console, '\nusername error: %s' % msg
        self.username = raw_input('Username: ')

    def password_error(self, msg):
        """The selected password was bad."""
        print >>self.console, '\nBad password: %s' % msg
        self.password = getpass.getpass('Password: ')
        self.verifiedpassword = getpass.getpass('Password again: ')

    def get_hostname(self):
        """Get the selected hostname."""
        # We set a default in install.py in case it isn't preseeded but when we
        # preseed, we are looking for None anyhow.
        return ''
    
    def clear_errors(self):
        pass

class Page(Plugin):
    def prepare(self, unfiltered=False):
        if ('UBIQUITY_FRONTEND' not in os.environ or
            os.environ['UBIQUITY_FRONTEND'] != 'debconf_ui'):
            if self.ui.get_hostname() == '':
                try:
                    seen = self.db.fget('netcfg/get_hostname', 'seen') == 'true'
                    if seen:
                        hostname = self.db.get('netcfg/get_hostname')
                        domain = self.db.get('netcfg/get_domain')
                        if hostname and domain:
                            hostname = '%s.%s' % (hostname, domain)
                        if hostname != '':
                            self.ui.set_hostname(hostname)
                except debconf.DebconfError:
                    pass
            if self.ui.get_fullname() == '':
                try:
                    fullname = self.db.get('passwd/user-fullname')
                    if fullname != '':
                        self.ui.set_fullname(fullname)
                except debconf.DebconfError:
                    pass
            if self.ui.get_username() == '':
                try:
                    username = self.db.get('passwd/username')
                    if username != '':
                        self.ui.set_username(username)
                except debconf.DebconfError:
                    pass
            try:
                auto_login = self.db.get('passwd/auto-login')
                self.ui.set_auto_login(auto_login == 'true')
            except debconf.DebconfError:
                pass
            try:
                encrypt_home = self.db.get('user-setup/encrypt-home')
                self.ui.set_encrypt_home(encrypt_home == 'true')
            except debconf.DebconfError:
                pass
        try:
            empty = self.db.get('user-setup/allow-password-empty') == 'true'
        except debconf.DebconfError:
            empty = False
        self.ui.set_allow_password_empty(empty)

        # We intentionally don't listen to passwd/auto-login or
        # user-setup/encrypt-home because we don't want those alone to force
        # the page to be shown, if they're the only questions not preseeded.
        questions = ['^passwd/user-fullname$', '^passwd/username$',
                     '^passwd/user-password$', '^passwd/user-password-again$',
                     '^user-setup/password-weak$',
                     'ERROR']
        if 'UBIQUITY_OEM_USER_CONFIG' in os.environ:
            environ = {'OVERRIDE_SYSTEM_USER': '1'}
            return (['/usr/lib/ubiquity/user-setup/user-setup-ask-oem'],
                    questions, environ)
        else:
            return (['/usr/lib/ubiquity/user-setup/user-setup-ask', '/target'],
                    questions)

    def set(self, question, value):
        if question == 'passwd/username':
            if self.ui.get_username() != '':
                self.ui.set_username(value)

    def run(self, priority, question):
        if question.startswith('user-setup/password-weak'):
            # A dialog is a bit clunky, but workable for now. Perhaps it would
            # be better to display some text in the style of password_error,
            # and then let the user carry on anyway by clicking next again?
            response = self.frontend.question_dialog(
                self.description(question),
                self.extended_description(question),
                ('ubiquity/text/choose_another_password',
                 'ubiquity/text/continue'))
            if response is None or response == 'ubiquity/text/continue':
                self.preseed(question, 'true')
            else:
                self.preseed(question, 'false')
                self.succeeded = False
                self.done = False
                self.ui.select_password()
            return True
        # We need to call info_loop as we switch to the page so the next button
        # gets disabled.
        self.ui.info_loop(None)
        return Plugin.run(self, priority, question)

    def ok_handler(self):
        self.ui.clear_errors()
    
        fullname = self.ui.get_fullname()
        username = self.ui.get_username().strip()
        password = self.ui.get_password()
        password_confirm = self.ui.get_verified_password()
        auto_login = self.ui.get_auto_login()
        encrypt_home = self.ui.get_encrypt_home()

        self.preseed('passwd/user-fullname', fullname)
        self.preseed('passwd/username', username)
        # TODO: maybe encrypt these first
        self.preseed('passwd/user-password', password)
        self.preseed('passwd/user-password-again', password_confirm)
        if self.ui.controller.oem_config:
            self.preseed('passwd/user-uid', '29999')
        else:
            self.preseed('passwd/user-uid', '')
        self.preseed_bool('passwd/auto-login', auto_login)
        self.preseed_bool('user-setup/encrypt-home', encrypt_home)
        
        hostname = self.ui.get_hostname()
        
        # TODO: i18n
        # check if the hostname had errors
        error_msg = []
        for result in validation.check_hostname(unicode(hostname)):
            if result == validation.HOSTNAME_LENGTH:
                error_msg.append("The hostname must be between 1 and 63 characters long.")
            elif result == validation.HOSTNAME_BADCHAR:
                error_msg.append("The hostname may only contain letters, digits, hyphens, and dots.")
            elif result == validation.HOSTNAME_BADHYPHEN:
                error_msg.append("The hostname may not start or end with a hyphen.")
            elif result == validation.HOSTNAME_BADDOTS:
                error_msg.append('The hostname may not start or end with a dot, or contain the sequence "..".')
            
        # showing warning message is error is set
        if len(error_msg) != 0:
            self.ui.hostname_error("\n".join(error_msg))
            self.done = False
            self.enter_ui_loop()
            return
        
        if hostname is not None and hostname != '':
            hd = hostname.split('.', 1)
            self.preseed('netcfg/get_hostname', hd[0])
            if len(hd) > 1:
                self.preseed('netcfg/get_domain', hd[1])
            else:
                self.preseed('netcfg/get_domain', '')

        Plugin.ok_handler(self)

    def error(self, priority, question):
        if question.startswith('passwd/username-'):
            self.ui.username_error(self.extended_description(question))
        elif question.startswith('user-setup/password-'):
            self.ui.password_error(self.extended_description(question))
        else:
            self.ui.error_dialog(self.description(question),
                                       self.extended_description(question))
        return Plugin.error(self, priority, question)

class Install(InstallPlugin):
    def prepare(self, unfiltered=False):
        if 'UBIQUITY_OEM_USER_CONFIG' in os.environ:
            environ = {'OVERRIDE_SYSTEM_USER': '1'}
            return (['/usr/lib/ubiquity/user-setup/user-setup-apply'], [], environ)
        else:
            return (['/usr/lib/ubiquity/user-setup/user-setup-apply', '/target'],
                    [])

    def error(self, priority, question):
        self.ui.error_dialog(self.description(question),
                             self.extended_description(question))
        return InstallPlugin.error(self, priority, question)
    
    def install(self, target, progress, *args, **kwargs):
        progress.info('ubiquity/install/user')
        return InstallPlugin.install(self, target, progress, *args, **kwargs)

