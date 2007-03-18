# -*- coding: UTF-8 -*-

# Copyright (C) 2005 Canonical Ltd.
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

from ubiquity.filteredcommand import FilteredCommand

class UserSetup(FilteredCommand):
    def prepare(self):
        if self.frontend.get_fullname() == '':
            fullname = self.db.get('passwd/user-fullname')
            if fullname != '':
                self.frontend.set_fullname(fullname)
        if self.frontend.get_username() == '':
            username = self.db.get('passwd/username')
            if username != '':
                self.frontend.set_username(username)

        questions = ['^passwd/user-fullname$', '^passwd/username$',
                     '^passwd/user-password$', '^passwd/user-password-again$',
                     'ERROR']
        return (['/usr/lib/ubiquity/user-setup/user-setup-ask', '/target'],
                questions)

    def set(self, question, value):
        if question == 'passwd/username':
            if self.frontend.get_username() != '':
                self.frontend.set_username(value)

    def ok_handler(self):
	fullname = self.frontend.get_fullname()
        username = self.frontend.get_username()
        password = self.frontend.get_password()
        password_confirm = self.frontend.get_verified_password()

        self.preseed('passwd/user-fullname', fullname)
        self.preseed('passwd/username', username)
        # TODO: maybe encrypt these first
        self.preseed('passwd/user-password', password, escape=True)
        self.preseed('passwd/user-password-again', password_confirm,
                     escape=True)
        self.preseed('passwd/user-uid', '')

        # evand 2007-01-13: This is probably unnecessary as migration-assistant
        # is run after user-setup in d-i, but it might be best to do this anyway
        # to avoid potential future headaches.
        import os
        if 'UBIQUITY_MIGRATION_ASSISTANT' in os.environ and \
            self.db.get('migration-assistant/partitions'):
            q = 'migration-assistant/new-user/%s/' % username
	    self.preseed(q + 'fullname', fullname)
	    self.preseed(q + 'password', password, escape=True)
	    self.preseed(q + 'password-again', password_confirm,
	                escape=True)

        FilteredCommand.ok_handler(self)

    def error(self, priority, question):
        if question.startswith('passwd/username-'):
            self.frontend.username_error(self.extended_description(question))
        elif question.startswith('user-setup/password-'):
            self.frontend.password_error(self.extended_description(question))
        else:
            self.frontend.error_dialog(self.description(question),
                                       self.extended_description(question))
        return FilteredCommand.error(self, priority, question)
