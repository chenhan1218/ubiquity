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
    def prepare(self):
        self.current_question = None
        self.existing_users = []
        first_user = self.db.get('passwd/username')
        if first_user:
            #self.existing_users.append(first_user)
	    self.frontend.set_ma_item_users(first_user)
        
        questions = ['^migration-assistant/partitions',
                            '^migration-assistant/.*/users$',
                            '^migration-assistant/.*/items$',
                            '^migration-assistant/.*/user$',
                            '^migration-assistant/.*/password$',
                            'ERROR']
        return (['/usr/lib/ubiquity/migration-assistant/ma-ask',
		'/usr/lib/ubiquity/migration-assistant'], questions)

    def subst(self, question, key, value):
    	print
	print 'Question: %s' % question
	print 'Key: %s' % key
	print 'Value: %s' % value
	print

	if question == 'migration-assistant/partitions':
		os_choices = value.split(',')
		self.frontend.set_ma_os_choices(os_choices)

    def run(self, priority, question):
        #if question.startswith('migration-assistant/partitions'):
        #    self.current_question = question
    
        #    # parse os-prober logic
        #    def reformat_output(x):
        #        ret = x.split(':')
        #        return (ret[1] + ' (' + ret[0] + ')')
    
        #    # FIME: replace this with pulling the already set question data using metaget.
        #    os_choices = commands.getoutput('/usr/bin/os-prober').split('\n')
        #    os_choices = map(reformat_output, os_choices)
    
        #    self.frontend.set_ma_os_choices(os_choices)

            
        if question.endswith('users'):
            self.current_question = question
            user_choices = self.choices(question)
            label = self.extended_description(question)
            if label:
                self.frontend.set_ma_user_label(label)
            self.frontend.set_ma_user_choices(user_choices)
            
        elif question.endswith('items'):
            self.current_question = question
            
            item_choices = self.choices(question)
            # this is very ugly, but you can't METAGET variables and I cannot
            # think of another way to grab this.
            user = self.current_question.split('/')[-2]
            
            #self.frontend.set_ma_item_users(self.existing_users)
            self.frontend.set_ma_item_choices(item_choices, user)
            
            # Apparently needed to stop the UI from skipping past the item selection and user setup pages for any users beyond the first one.
            self.done = False
            
        elif question.endswith('user'):
            self.current_question = question
            self.frontend.set_ma_user()
    
        return super(MigrationAssistant, self).run(priority, question)

    def ok_handler(self):
        if self.current_question == 'migration-assistant/partitions':
            os_choice = self.frontend.get_ma_os_choices()
	    
	    if len(os_choice) != 1:
		formatted_choice = ', '.join(os_choice)
	    else:
		formatted_choice = "".join(os_choice)
	    
	    self.preseed(self.current_question, formatted_choice)
	    
	    #FIXME: Why did I do this again?
	    self.succeeded = True
	    self.done = False
	    self.exit_ui_loops()
	    return
    
        elif self.current_question.endswith('users'):
            user_choice = self.frontend.get_ma_user_choices()
            if not user_choice:
		# needed?
		self.preseed(self.current_question, "")
            else:
                if len(user_choice) != 1:
                    formatted_choice = ', '.join(user_choice)
                else:
                    formatted_choice = "".join(user_choice)
                self.preseed(self.current_question, formatted_choice)
            
            self.succeeded = True
            self.done = False
            self.exit_ui_loops()
            return
        
        elif self.current_question.endswith('items'):
            item_choice = self.frontend.get_ma_item_choices()
            if item_choice:
                if len(item_choice) != 1:
                    formatted_choice = ', '.join(item_choice)
                else:
                    formatted_choice = "".join(item_choice)
                self.preseed(self.current_question, formatted_choice)
                temp = self.db.get(self.current_question)
                
                # To user
                user = self.frontend.get_ma_item_user()
                if user != "add-user":
		    # If the user selected one of the existing accounts to
		    # import into, then we should seed the username and move to
		    # the next user.
		    
		    q = self.current_question.replace('/items', '/user')
		    print 'preseeding %s with %s.' % (q, user)
		    self.db.register('migration-assistant/user', q)
                    self.preseed(q, user)
		else:
		    # If the user selected "Add new user", then we move to the
		    # create account page.

		    self.succeeded = True
		    self.done = False
		    self.exit_ui_loops()
		    return
        
        elif self.current_question.endswith('password'):
            # If the user triggered mismatched passwords, this will get called.
            # FIXME: move down into endswith('user') or endswith('password')?
            # If the user changes any other fields, they wont get updated.
            password = self.frontend.get_ma_password()
            password_confirm = self.frontend.get_ma_verified_password()
            self.preseed(self.current_question, password)
            self.preseed(self.current_question + '-again', password_confirm)
            
        elif self.current_question.endswith('user'):
            
            fullname = self.frontend.get_ma_fullname()
            username = self.frontend.get_ma_username()
            password = self.frontend.get_ma_password()
            password_confirm = self.frontend.get_ma_verified_password()
            administrator = self.frontend.get_ma_administrator()
            
            self.preseed(self.current_question, username)
            
            base = 'migration-assistant/new-user/' + username + '/'
            # TODO: maybe encrypt these first
            self.preseed(base + 'password', password, escape=True)
            self.preseed(base + 'password-again', password_confirm, escape=True)
            self.preseed(base + 'fullname', fullname)
            self.preseed(base + 'administrator', administrator)
            
            #self.existing_users.append(username)
	    self.frontend.set_ma_item_users(username)
    
	super(MigrationAssistant, self).ok_handler()
	import pdb; pdb.set_trace() #added for test
        
    def error(self, priority, question):
        if question.startswith('migration-assistant/password-'):
            self.frontend.ma_password_error(self.extended_description(question))
        return super(MigrationAssistant, self).error(priority, question)
