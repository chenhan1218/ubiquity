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
	self.tree = []
        questions = ['^migration-assistant/partitions',
                            '^migration-assistant/.*/users$',
                            '^migration-assistant/.*/items$',
                            '^migration-assistant/.*/user$',
                            '^migration-assistant/.*/password$',
                            'ERROR']
        return (['/usr/lib/ubiquity/migration-assistant/ma-ask',
		'/usr/lib/ubiquity/migration-assistant'], questions)

    def subst(self, question, key, value):
    	pass

    def run(self, priority, question):
	# Do we need to worry about avoiding preseeding user details or do we
	# avoid having to do that by seeding partitions on a next click?
	self.preseed(question, ", ".join(self.choices(question)))
	#self.done = True
	#self.succeeded = True
	return True # False is backup

    def cleanup(self):
    	for os in self.db.get('migration-assistant/partitions').split(', '):
		part = os[os.rfind('/')+1:-1] # hda1
		for user in self.db.get('migration-assistant/' + part + '/users').split(', '):
			items = self.db.get('migration-assistant/' + part + '/' + user + '/items').split(', ')
			#self.tree.append((user + '  <small><i>' + os + '</i></small>', items))
			self.tree.append(((user, os), items))
	
	print self.tree
	self.frontend.set_ma_choices(self.tree)

	# This is hackish, but what else can we do?
	# We need to jump in after m-a has exited and stop ubiquity from moving on to
	# the next page.
	self.frontend.allow_go_forward(True)
    	self.enter_ui_loop()

    def ok_handler(self):
	FilteredCommand.ok_handler(self)
        
    def error(self, priority, question):
    	pass

# vim:ai:et:sts=4:tw=80:sw=4:
