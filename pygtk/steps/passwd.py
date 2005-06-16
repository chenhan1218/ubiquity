# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.

import gtk
import debconf
from wizardstep import WizardStep

class Password(WizardStep):
    def __init__(self, db, glade):
        super(Password, self).__init__(db, glade)

        # TODO: skip this if there's already a user configured, or re-ask
        # and create a new one, or what?

        self.glade.get_widget('button_ok').connect('clicked', self.ok_handler)
        self.glade.get_widget('button_cancel').connect('clicked',
                                                       gtk.main_quit)

    def ok_handler(self, widget, data=None):
        fullname = self.glade.get_widget('user_fullname_entry').get_text()
        username = self.glade.get_widget('user_name_entry').get_text()
        password = self.glade.get_widget('user_password_entry').get_text()
        password_confirm = \
            self.glade.get_widget('user_password_confirm_entry').get_text()

        # TODO: validation!

        self.preseed('passwd/user-fullname', fullname)
        self.preseed('passwd/username', username)
        # TODO: maybe encrypt these first
        self.preseed('passwd/user-password', password)
        self.preseed('passwd/user-password-again', password_confirm)

        gtk.main_quit()

    def run(self):
        gtk.main()

stepname = 'Password'
