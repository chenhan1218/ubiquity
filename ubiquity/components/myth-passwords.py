# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
#
# Copyright (C) 2006, 2007, 2009 Canonical Ltd.
# Written by Colin Watson <cjwatson@ubuntu.com>.
# Copyright (C) 2007-2010 Mario Limonciello
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# Ubiquity is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ubiquity.  If not, see <http://www.gnu.org/licenses/>.

import string
import subprocess
from ubiquity.plugin import *
from mythbuntu_common.installer import *
from mythbuntu_common.mysql import MySQLHandler
import os

NAME = 'myth-passwords'
AFTER = 'myth-drivers'
WEIGHT = 10

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file = 'mythbuntu_stepPasswords'
        MythPageGtk.__init__(self, controller, *args, **kwargs)
        self.populate_mysql()

    def set_type(self,type):
        """Prevents the user from going forward initially because of the
           type that was selected"""
        if "Master" not in type:
            self.controller.allow_go_forward(False)

    def populate_mysql(self):
        """Puts a new random mysql password into the UI for each run
           This ensures that passwords don't ever get cached"""
        self.mysql=MySQLHandler()
        new_pass_caller = subprocess.Popen(['pwgen','-s','8'],stdout=subprocess.PIPE)
        self.mysql_password.set_text(string.split(new_pass_caller.communicate()[0])[0])

    def do_connection_test(self,widget):
        """Tests to make sure that the backend is accessible"""
        config={}
        config["user"]=self.mysql_user.get_text()
        config["password"]=self.mysql_password.get_text()
        config["server"]=self.mysql_server.get_text()
        config["database"]=self.mysql_database.get_text()
        self.mysql.update_config(config)
        result=self.mysql.do_connection_test()
        self.controller.allow_go_forward(True)
        self.connection_results_label.show()
        self.connection_results.set_text(result)

    def set_password(self,name,value):
        """Preseeds a password"""
        lists = [{'mysql_mythtv_user':self.mysql_user,
                  'mysql_mythtv_password':self.mysql_password,
                  'mysql_mythtv_dbname':self.mysql_database,
                  'mysql_host':self.mysql_server}]
        preseed_list(lists,name,value)

    def get_mythtv_passwords(self):
        return build_static_list([{'mysql_mythtv_user':self.mysql_user,
                                         'mysql_mythtv_password':self.mysql_password,
                                         'mysql_mythtv_dbname':self.mysql_database,
                                         'mysql_host':self.mysql_server}])

class Page(Plugin):
    def prepare(self):
        #mythtv passwords
        passwords = self.ui.get_mythtv_passwords()
        questions = []
        for this_password in passwords:
            answer = self.db.get('mythtv/' + this_password)
            if answer != '':
                self.ui.set_password(this_password,answer)
            questions.append('^mythtv/' + this_password)

        if 'UBIQUITY_AUTOMATIC' not in os.environ:
            #if we are a Master type, we'll skip this page
            type = self.db.get('mythbuntu/install_type')
            if 'Master' in type:
                os.environ['UBIQUITY_AUTOMATIC'] = "2"
                #regrab the passwords in case any of them actually were supposed preseeded
                passwords = self.ui.get_mythtv_passwords()
                for this_password in passwords:
                    self.preseed('mythtv/' + this_password, passwords[this_password])
            else:
                self.ui.set_type(type)


        return (['/usr/share/ubiquity/ask-mythbuntu','passwords'], questions)

    def ok_handler(self):
        #mythtv passwords
        passwords = self.ui.get_mythtv_passwords()
        for this_password in passwords:
            self.preseed('mythtv/' + this_password, passwords[this_password])

        Plugin.ok_handler(self)

    def cleanup(self):
        #Clear out our skipping if we did it only because of Master
        if 'UBIQUITY_AUTOMATIC' in os.environ and os.environ['UBIQUITY_AUTOMATIC'] == "2":
            del os.environ['UBIQUITY_AUTOMATIC']

        Plugin.cleanup(self)
