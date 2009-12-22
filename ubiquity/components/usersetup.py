# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-

# Copyright (C) 2005, 2006, 2007, 2008 Canonical Ltd.
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

from ubiquity.misc import execute
from ubiquity.plugin import *
from ubiquity.filteredcommand import FilteredCommand
import debconf

NAME = 'usersetup'

class PageBase(PluginUI):
    def __init__(self):
        self.laptop = execute("laptop-detect")
        
    # TODO raise the nonimplemented?
    
    """Set the user's full name."""
    def set_fullname(self, value):        
        pass

    """Get the user's full name."""
    def get_fullname(self):
        pass
        
    """Set the user's Unix user name."""
    def set_username(self, value):        
        pass

    """Get the user's Unix user name."""
    def get_username(self):
        pass
        
    """Get the user's password."""
    def get_password(self):
        pass

    """Get the user's password confirmation."""
    def get_verified_password(self):
        pass

    """Select the text in the first password entry widget."""
    def select_password(self):
        pass

    """Set whether the user should be automatically logged in."""
    def set_auto_login(self, value):
        pass

    """Returns true if the user should be automatically logged in."""
    def get_auto_login(self):
        pass

    """Set whether the home directory should be encrypted."""
    def set_encrypt_home(self, value):
        pass

    """Returns true if the home directory should be encrypted."""
    def get_encrypt_home(self):
        pass

    """The selected username was bad."""
    def username_error(self, msg):
        pass

    """The selected password was bad."""
    def password_error(self, msg):
        pass

    """Get the selected hostname."""
    def get_hostname(self):
        pass
        
    def set_hostname(self, hostname):
        pass

class PageGtk(PluginUI):
    plugin_widgets = 'stepUserInfo'

class PageKde(PageBase):
    plugin_breadcrumb = 'ubiquity/text/breadcrumb_user'
    
    def __init__(self, controller, *args, **kwargs):
        PageBase.__init__(self)
        self.controller = controller
        
        from PyQt4 import uic
        from PyQt4.QtGui import QDialog
        from PyKDE4.kdeui import *
        from PyKDE4.kdecore import *
        
        self.plugin_widgets = uic.loadUi('/usr/share/ubiquity/qt/stepUserSetup.ui')
        self.page = self.plugin_widgets
        
        self.username_edited = False
        self.hostname_edited = False
        
        self.oem_config = self.controller.oem_config
        self.oem_user_config = self.controller.oem_user_config
        
        if self.controller.oem_config:
            self.page.setWindowTitle(self.get_string('oem_config_title'))
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
        
        self.page.fullname.textChanged[str].connect(self.on_fullname_changed)
        self.page.username.textChanged[str].connect(self.on_username_changed)
        self.page.password.textChanged[str].connect(self.on_password_changed)
        self.page.verified_password.textChanged[str].connect(self.on_verified_password_changed)
        self.page.hostname.textChanged[str].connect(self.on_hostname_changed)
        
        self.page.password_debug_warning_label.setVisible('UBIQUITY_DEBUG' in os.environ)
    
    # TODO handle validation
    #def info_loop(self, widget):
        #"""check if all entries from Identification screen are filled."""
        #if widget is None:
            #return
        
        
        #complete = True
        #for name in ('username', 'hostname'):
            #if getattr(self.ui, name).text() == '':
                #complete = False
        #if not self.allow_password_empty:
            #for name in ('password', 'verified_password'):
                #if getattr(self.ui, name).text() == '':
                    #complete = False
    
    # TODO validation
    #error_msg = []

        ## Validation stuff

        ## checking hostname entry
        #hostname = self.ui.hostname.text()
        #for result in validation.check_hostname(unicode(hostname)):
            #if result == validation.HOSTNAME_LENGTH:
                #error_msg.append("The hostname must be between 1 and 63 characters long.")
            #elif result == validation.HOSTNAME_BADCHAR:
                #error_msg.append("The hostname may only contain letters, digits, hyphens, and dots.")
            #elif result == validation.HOSTNAME_BADHYPHEN:
                #error_msg.append("The hostname may not start or end with a hyphen.")
            #elif result == validation.HOSTNAME_BADDOTS:
                #error_msg.append('The hostname may not start or end with a dot, or contain the sequence "..".')

        ## showing warning message is error is set
        #if len(error_msg) != 0:
            #self.ui.hostname_error_reason.setText("\n".join(error_msg))
            #self.ui.hostname_error_reason.show()
            #self.ui.hostname_error_image.show()
            #self.stay_on_page = True
        #else:
            #self.stay_on_page = False
    
    def on_fullname_changed(self):
        #if the user did not manually enter a username
        #create one for him
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
        #self.info_loop(self.ui.password)
        # TODO validate
        pass

    def on_verified_password_changed(self):
        #self.info_loop(self.ui.verified_password)
        # TODO validate
        pass

    def on_hostname_changed(self):
        #self.info_loop(self.ui.hostname)
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

    def get_hostname (self):
        return unicode(self.page.hostname.text())

    def set_hostname (self, value):
        self.page.hostname.setText(value)

class PageDebconf(PluginUI):
    plugin_title = 'ubiquity/text/userinfo_heading_label'

class PageNoninteractive(PluginUI):
    pass

class Page(Plugin):
    def prepare(self, unfiltered=False):
        frontend = self.frontend
        if self.ui:
            frontend = self.ui
    
        if ('UBIQUITY_FRONTEND' not in os.environ or
            os.environ['UBIQUITY_FRONTEND'] != 'debconf_ui'):
            if frontend.get_hostname() == '':
                try:
                    seen = self.db.fget('netcfg/get_hostname', 'seen') == 'true'
                    if seen:
                        hostname = self.db.get('netcfg/get_hostname')
                        domain = self.db.get('netcfg/get_domain')
                        if hostname and domain:
                            hostname = '%s.%s' % (hostname, domain)
                        if hostname != '':
                            frontend.set_hostname(hostname)
                except debconf.DebconfError:
                    pass
            if frontend.get_fullname() == '':
                try:
                    fullname = self.db.get('passwd/user-fullname')
                    if fullname != '':
                        frontend.set_fullname(fullname)
                except debconf.DebconfError:
                    pass
            if frontend.get_username() == '':
                try:
                    username = self.db.get('passwd/username')
                    if username != '':
                        frontend.set_username(username)
                except debconf.DebconfError:
                    pass
            try:
                auto_login = self.db.get('passwd/auto-login')
                frontend.set_auto_login(auto_login == 'true')
            except debconf.DebconfError:
                pass
            try:
                encrypt_home = self.db.get('user-setup/encrypt-home')
                frontend.set_encrypt_home(encrypt_home == 'true')
            except debconf.DebconfError:
                pass

        # We intentionally don't listen to passwd/auto-login or
        # user-setup/encrypt-home because we don't want those alone to force
        # the page to be shown, if they're the only questions not preseeded.
        questions = ['^passwd/user-fullname$', '^passwd/username$',
                     '^passwd/user-password$', '^passwd/user-password-again$',
                     '^user-setup/password-weak$',
                     'ERROR']
        if frontend.oem_user_config:
            environ = {'OVERRIDE_SYSTEM_USER': '1'}
            return (['/usr/lib/ubiquity/user-setup/user-setup-ask-oem'],
                    questions, environ)
        else:
            return (['/usr/lib/ubiquity/user-setup/user-setup-ask', '/target'],
                    questions)

    def set(self, question, value):
        if question == 'passwd/username':
            frontend = self.frontend
            if self.ui:
                frontend = self.ui
            if frontend.get_username() != '':
                frontend.set_username(value)

    def run(self, priority, question):
        frontend = self.frontend
        if self.ui:
            frontend = self.ui
        
        if question.startswith('user-setup/password-weak'):
            # A dialog is a bit clunky, but workable for now. Perhaps it
            # would be better to display some text in the style of
            # password_error, and then let the user carry on anyway by
            # clicking next again?
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
                frontend.select_password()
            return True

        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        frontend = self.frontend
        if self.ui:
            frontend = self.ui
    
        fullname = frontend.get_fullname()
        username = frontend.get_username().strip()
        password = frontend.get_password()
        password_confirm = frontend.get_verified_password()
        auto_login = frontend.get_auto_login()
        encrypt_home = frontend.get_encrypt_home()

        self.preseed('passwd/user-fullname', fullname)
        self.preseed('passwd/username', username)
        # TODO: maybe encrypt these first
        self.preseed('passwd/user-password', password)
        self.preseed('passwd/user-password-again', password_confirm)
        if frontend.oem_config:
            self.preseed('passwd/user-uid', '29999')
        else:
            self.preseed('passwd/user-uid', '')
        self.preseed_bool('passwd/auto-login', auto_login)
        self.preseed_bool('user-setup/encrypt-home', encrypt_home)
        
        hostname = frontend.get_hostname()
        if hostname is not None and hostname != '':
            hd = hostname.split('.', 1)
            self.preseed('netcfg/get_hostname', hd[0])
            if len(hd) > 1:
                self.preseed('netcfg/get_domain', hd[1])
            else:
                self.preseed('netcfg/get_domain', '')

        FilteredCommand.ok_handler(self)

    def error(self, priority, question):
        frontend = self.frontend
        if self.ui:
            frontend = self.ui
            
        if question.startswith('passwd/username-'):
            frontend.username_error(self.extended_description(question))
        elif question.startswith('user-setup/password-'):
            frontend.password_error(self.extended_description(question))
        else:
            frontend.error_dialog(self.description(question),
                                       self.extended_description(question))
        return FilteredCommand.error(self, priority, question)
