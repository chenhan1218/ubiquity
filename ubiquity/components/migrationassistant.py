# -*- coding: UTF-8 -*-

# Copyright (C) 2006 Evan Dandrea <evan@evalicious.com>.
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
#import commands

from ubiquity.filteredcommand import FilteredCommand
from ubiquity import misc

class MigrationAssistant(FilteredCommand):
    firstrun = True
    err = None
    def prepare(self):
	self.current_question = None
	self.tree = []
        questions = ['^migration-assistant/partitions',
                            '^migration-assistant/.*/users$',
                            '^migration-assistant/.*/items$',
                            '^migration-assistant/.*/user$',
                            '^migration-assistant/.*/password$',
                            'ERROR']
        return (['/usr/lib/ubiquity/migration-assistant/ma-ask',
		'/usr/lib/ubiquity/migration-assistant'], questions)

    def run(self, priority, question):
        # FIXME: This is not preseed friendly.  The nulling of questions below
        # is also an issue.  Perhaps we should check to see if m-a/partitions is
        # set and if so we'll skip this step and modify the step below.  Or
        # should we not worry about partial preseeding and just skip this
        # alltogether if we find any preseeding?
	print 'in run'
        if self.firstrun:
            self.preseed(question, ", ".join(self.choices(question)))
        else:
            print 'got a question in run, %s' % question
            print 'val is: \'%s\'' % self.db.get(question)
            if self.err:
                if question.endswith('password'):
                    # pass in the user as well and then in password_error find
                    # every instance and set the error.  We'll need a way to
                    # keep track of errors between users if we do this.
                    user = question[:question.rfind('/')]
                    user = user[user.rfind('/')+1:]
                    self.frontend.ma_password_error(self.err, user)
                    
	return True # False is backup

    def cleanup(self):
        if not self.firstrun:
            # There were no errors this time around, lets move to the next step.
            if not self.err:
                print 'exiting m-a.'
                self.succeeded = True
                self.done = True
                self.exit_ui_loops()
                return
            # There were errors.
            print 'in cleanup again'
            self.frontend.allow_go_forward(True)
            self.enter_ui_loop()
            return

    	for os in self.db.get('migration-assistant/partitions').split(', '):
            part = os[os.rfind('/')+1:-1] # hda1
            os = os[:os.find('(')-1]
            for user in self.db.get('migration-assistant/' + part + '/users').split(', '):
                items = self.db.get('migration-assistant/' + part + '/' + user + '/items').split(', ')
                self.tree.append({'user': user, \
                                'part': part, \
                                'os': os, \
                                'newuser': '', \
                                'items': items, \
                                'selected': False})
            # We now unset everything as the checkboxes will be unselected
            # by default and debconf needs to match that.
            self.db.set('migration-assistant/%s/users' % part, '')
        #self.db.set('migration-assistant/partitions', '')
	
	#print self.tree
	self.frontend.set_ma_choices(self.tree)

	# We need to jump in after m-a has exited and stop ubiquity from moving on to
	# the next page.  This does that.
	self.frontend.allow_go_forward(True)
        self.firstrun = False
    	self.enter_ui_loop()

    def ok_handler(self):
        # what about questions that haven't been registered because the user
        # didn't fill them in?  They're errors.  Might have to fix them here.
        
        self.frontend.ma_apply()

        choices, new_users = self.frontend.get_ma_choices()
        users = {}

        for c in choices:
            if c['selected']:
                question = 'migration-assistant/%s/%s/' % (c['part'],c['user'])
                self.db.register('migration-assistant/items', question + 'items')
                self.preseed(question + 'items', ', '.join(c['items']))
                self.db.register('migration-assistant/user', question + 'user')
                self.preseed(question + 'user', c['newuser'])
                try:
                    print 'choice newuser: %s' % c['newuser']
                    users[c['part']].append(c['user'])
                except KeyError:
                    users[c['part']] = [c['user']]

        for p in users.iterkeys():
            question = 'migration-assistant/%s/users' % p
            self.db.register('migration-assistant/users', question)
            print 'm-a/%s/users: %s' % (p, users[p])
            self.preseed(question, ', '.join(users[p]))

        for u in new_users.iterkeys():
            user = new_users[u]
            question = 'migration-assistant/new-user/%s/' % u

            try:
                self.db.register('migration-assistant/fullname', question + 'fullname')
                self.preseed(question + 'fullname', user['fullname'])
            except KeyError:
                self.preseed(question + 'fullname', '')
            try:
                self.db.register('migration-assistant/password', question + 'password')
                self.preseed(question + 'password', user['password'])
            except KeyError:
                self.preseed(question + 'password', '')
            try:
                self.db.register('migration-assistant/password-again', question + 'password-again')
                self.preseed(question + 'password-again', user['confirm'])
            except KeyError:
                self.preseed(question + 'password-again', '')
        
        self.err = None
        FilteredCommand.ok_handler(self)
        self.db.shutdown()
        self.run_command()
        
    def error(self, priority, question):
    	print 'error with %s' % question
        # Because we have already seeded the questions and thus will not see
        # them in run() we have to hold onto the error until the next question
        # which will tell us what question, and thus what partition and user
        # this error is tied to.
        # This of course assumes that the next question is related to the error,
        # but that's a safe bet as I cannot think of a question we wouldn't want
        # to re-ask if an error occurred.
        self.err = self.extended_description(question)

        if question != 'migration-assistant/password-mismatch':
            self.frontend.error_dialog(self.description(question),
                self.extended_description(question))
        return FilteredCommand.error(self, priority, question)

# vim:ai:et:sts=4:tw=80:sw=4:
