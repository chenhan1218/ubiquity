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

from ubiquity.plugin import *
from mythbuntu_common.installer import MythPageGtk
from ubiquity import install_misc
from ubiquity import misc
import os
import subprocess

NAME = 'myth-installtype'
AFTER = ['usersetup', None]
WEIGHT = 12

class PageGtk(MythPageGtk):
    def __init__(self, controller, *args, **kwargs):
        self.ui_file='mythbuntu_stepCustomInstallType'
        MythPageGtk.__init__(self,controller,*args,**kwargs)

    def set_installtype(self,type):
        """Preseeds the type of custom install"""
        #if type == "Set Top Box":
        #    self.stb.set_active(True)
        if type == "Frontend":
            self.fe.set_active(True)
        elif type == "Slave Backend":
            self.slave_be.set_active(True)
        elif type == "Master Backend":
            self.master_be.set_active(True)
        elif type == "Slave Backend/Frontend":
            self.slave_be_fe.set_active(True)
        else:
            self.master_be_fe.set_active(True)

    def get_installtype(self):
        """Returns the current custom installation type"""
        if self.master_be_fe.get_active():
            return "Master Backend/Frontend"
        elif self.slave_be_fe.get_active():
            return "Slave Backend/Frontend"
        elif self.master_be.get_active():
            return "Master Backend"
        elif self.slave_be.get_active():
            return "Slave Backend"
        elif self.fe.get_active():
            return "Frontend"
        elif self.stb.get_active():
            return "Set Top Box"

class Page(Plugin):
    def prepare(self):
        self.questions = ['install_type']
        questions = []
        for question in self.questions:
            answer = self.db.get('mythbuntu/' + question)
            if answer != '':
                self.ui.set_installtype(answer)
            questions.append('^mythbuntu/' + question)
        return (['/usr/share/ubiquity/ask-mythbuntu','type'], questions)

    def ok_handler(self):
        self.preseed('mythbuntu/' + self.questions[0],self.ui.get_installtype())
        Plugin.ok_handler(self)

class Install(InstallPlugin):
    def process_package_removals(self):
        packages=set()
        ## system role
        if 'Backend' not in self.type:
            packages.add('libnet-upnp-perl') #causes mythtv-backend to be removed
            packages.add('php5-common')      #causes mythweb to be removed
            packages.add('libaprutil1')      #causes apache2 to be removed
        if 'Slave' in self.type or self.type == 'Frontend':
            packages.add('ntp')              #causes mythtv-backend-master to go
            packages.add('mythtv-database')
            packages.add('mysql-server-core-5.1')
        if 'Frontend' not in self.type:
            packages.add('mythtv-frontend')
        ## services that are installed by default
        for service in ['samba','openssh-server']:
            if not misc.create_bool(self.db.get('mythbuntu/' + service)):
                packages.add(service)
        if len(packages) >= 0:
            #recursively remove to make sure we get plugins and services that
            #aren't necessary anymore
            install_misc.record_removed(packages,True)

    def setup_common(self):
        #All types
        for question in ('mythtv/mysql_mythtv_user','mythtv/mysql_mythtv_password',\
                         'mythtv/mysql_mythtv_dbname','mythtv/mysql_host'):
            answer = self.progress.get(question)
            install_misc.set_debconf(self.target, question,answer)

        os.remove(self.target + '/etc/mythtv/mysql.txt')
        install_misc.reconfigure(self.target, 'mythtv-common')

    def setup_master_backend(self):
        if 'Master' in self.type:
            #Setup database
            install_misc.reconfigure(self.target, 'mysql-server-5.1')
            proc=subprocess.Popen(['chroot',self.target,'mysqld'])
            install_misc.reconfigure(self.target, 'mythtv-database')

            #Cleanup
            install_misc.chrex(self.target,'mysqladmin','--defaults-file=/etc/mysql/debian.cnf','shutdown')
            proc.communicate()

            #Mythweb
            passwd = self.progress.get('passwd/user-password')
            user = self.progress.get('passwd/username')
            install_misc.set_debconf(self.target, 'mythweb/enable', 'true')
            install_misc.set_debconf(self.target, 'mythweb/username', user)
            install_misc.set_debconf(self.target, 'mythweb/password', passwd)
            install_misc.reconfigure(self.target, 'mythweb')

    def install(self, target, progress, *args, **kwargs):
        self.target = target
        self.progress = progress

        self.progress.info('ubiquity/install/mythbuntu')
        self.type = self.progress.get('mythbuntu/install_type')

        self.setup_common()
        self.setup_master_backend()
        self.process_package_removals()

        return InstallPlugin.install(self, target, progress, *args, **kwargs)
