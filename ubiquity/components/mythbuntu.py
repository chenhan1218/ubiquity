# -*- coding: UTF-8 -*-

# Written by Mario Limonciello <superm1@ubuntu.com>.
# Copyright (C) 2007 Mario Limonciello
# Copyright (C) 2007 Jared Greenwald
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

from ubiquity.misc import create_bool
from ubiquity.filteredcommand import FilteredCommand

class MythbuntuAdvancedType(FilteredCommand):
#enable advanced preseeding

    def __init__(self,frontend,db=None):
        self.questions = ['advanced_install']
        FilteredCommand.__init__(self,frontend,db)

    def prepare(self):
        questions = []
        for question in self.questions:
            answer = self.db.get('mythbuntu/' + question)
            if answer != '':
                self.frontend.set_advanced(answer)
            questions.append('^mythbuntu/' + question)
        return (['/usr/share/ubiquity/ask-advanced'], questions)

    def ok_handler(self):
        self.preseed_bool('mythbuntu/' + self.questions[0], self.frontend.get_advanced())
        FilteredCommand.ok_handler(self)

class MythbuntuInstallType(FilteredCommand):
#we are seeding one of the possible install types

    def __init__(self,frontend,db=None):
        self.questions = ['install_type']
        FilteredCommand.__init__(self,frontend,db)

    def prepare(self):
        questions = []
        for question in questions:
            answer = self.db.get(questions[0])
            if answer != '':
                self.frontend.set_installtype(answer)
            questions.append('^mythbuntu/' + question)
        return (['/usr/share/ubiquity/ask-type'], questions)

    def ok_handler(self):
        self.preseed('mythbuntu/' + self.questions[0],self.frontend.get_installtype())
        FilteredCommand.ok_handler(self)

class MythbuntuPlugins(FilteredCommand):
#we are seeding the status of each of these plugins, true/false

    def prepare(self):
        plugins = self.frontend.get_plugins()
        questions = []
        for this_plugin in plugins:
            answer = create_bool(self.db.get('mythbuntu/' + this_plugin))
            if answer != plugins[this_plugin]:
                self.frontend.set_plugin(this_plugin,answer)
            questions.append('^mythbuntu/' + this_plugin)
        return (['/usr/share/ubiquity/ask-plugins'], questions)

    def ok_handler(self):
        plugins = self.frontend.get_plugins()
        for this_plugin in plugins:
            self.preseed_bool('mythbuntu/' + this_plugin,plugins[this_plugin])
        FilteredCommand.ok_handler(self)

class MythbuntuThemes(FilteredCommand):
#since all themes are pre-installed, we are seeding the ones
#that will be *removed*

    def __init__(self,frontend,db=None):
        self.themes = ['officialthemes', 'communitythemes']
        FilteredCommand.__init__(self,frontend,db)

    def prepare(self):
        questions = []
        for type in self.themes:
            answers = self.db.get('mythbuntu/' + type)
            if answers != '':
                self.frontend.set_themes(answers)
            questions.append('^mythbuntu/' + type)
        return (['/usr/share/ubiquity/ask-themes'], questions)

    def ok_handler(self):
        for type in self.themes:
            theme_string=""
            dictionary = self.frontend.get_themes(type)
            for theme in dictionary:
                if not dictionary[theme]:
                    theme_string+=theme + " "
            self.preseed('mythbuntu/' + type, theme_string)
        FilteredCommand.ok_handler(self)

class MythbuntuServices(FilteredCommand):
#we are seeding the status of each service

    def prepare(self):
        services = self.frontend.get_services()
        questions = []
        for this_service in services:
            answer = self.db.get('mythbuntu/' + this_service)
            if answer != '':
                self.frontend.set_service(this_service,answer)
        questions.append('^mythbuntu/' + this_service)
        return (['/usr/share/ubiquity/ask-services'], questions)

    def ok_handler(self):
        services = self.frontend.get_services()
        for this_service in services:
            answer = services[this_services]
            if answer is True or answer is False:
                self.preseed_bool('mythbuntu/' + this_service, answer)
            else:
                self.preseed('mythbuntu/' + this_service, answer)
        FilteredCommand.ok_handler(self)

class MythbuntuPasswords(FilteredCommand):
    def prepare(self):
        questions = ['^mythtv/mysql_admin_password',
             '^mythtv/mysql_mythtv_user',
             '^mythtv/mysql_mythtv_password',
             '^mythtv/mysql_mythtv_dbname',
             '^mythtv/mysql_host',
             '^mythweb/enable',
             '^mythweb/username',
             '^mythweb/password']
        return (['/usr/share/ubiquity/ask-passwords'], questions)

    def run(self,priority,question):
        answer=self.db.get(question)
        if answer == '':
            if question.startswith('mythtv/mysql_admin_password'):
                if self.frontend.get_secure_mysql():
                    answer = self.frontend.get_mysql_root_password()
                else:
                    answer = ""
            elif question.startswith('mythtv/mysql_mythtv_user'):
                if not self.frontend.get_uselivemysqlinfo():
                    answer = self.frontend.get_mysqluser()
                else:
                    answer = self.db.get('mythtv/mysql_mythtv_user')
            elif question.startswith('mythtv/mysql_mythtv_password'):
                if not self.frontend.get_uselivemysqlinfo():
                    answer = self.frontend.get_mysqlpass()
                else:
                    answer = self.db.get('mythtv/mysql_mythtv_password')
            elif question.startswith('mythtv/mysql_mythtv_dbname'):
                if not self.frontend.get_uselivemysqlinfo():
                    answer = self.frontend.get_mysqldatabase()
                else:
                    answer = self.db.get('mythtv/mysql_mythtv_dbname')
            elif question.startswith('mythtv/mysql_host'):
                if not self.frontend.get_uselivemysqlinfo():
                    answer = self.frontend.get_mysqlserver()
                else:
                    answer = self.db.get('mythtv/mysql_host')
            elif question.startswith('mythweb/enable'):
                answer = self.frontend.get_secure_mythweb()
            elif question.startswith('mythweb/username'):
                answer = self.frontend.get_mythweb_username()
            elif question.startswith('mythweb/password'):
                answer = self.frontend.get_mythweb_password()
        if answer == True or answer == False:
            self.preseed_bool(question,answer)
        else:
            self.preseed(question,answer)
        return FilteredCommand.run(self, priority, question)

def ok_handler(self):
        if self.frontend.get_secure_mysql():
            mysql_root = self.frontend.get_mysql_root_password()
        else:
            mysql_root = ""
        self.preseed('mythtv/mysql_admin_password',mysql_root)
        if not self.frontend.get_uselivemysqlinfo():
            mysqluser = self.frontend.get_mysqluser()
        else:
            mysqluser = self.db.get('mythtv/mysql_mythtv_user')
        self.preseed('mythtv/mysql_mythtv_user', mysqluser)
        if not self.frontend.get_uselivemysqlinfo():
            mysqlpass = self.frontend.get_mysqlpass()
        else:
            mysqlpass = self.db.get('mythtv/mysql_mythtv_password')
        self.preseed('mythtv/mysql_mythtv_password', mysqlpass)
        if not self.frontend.get_uselivemysqlinfo():
            mysqldatabase = self.frontend.get_mysqldatabase()
        else:
            mysqldatabase = self.db.get('mythtv/mysql_mythtv_dbname')
        self.preseed('mythtv/mysql_mythtv_dbname', mysqldatabase)
        if not self.frontend.get_uselivemysqlinfo():
            mysqlserver = self.frontend.get_mysqlserver()
        else:
            mysqlserver = self.db.get('mythtv/mysql_host')
        self.preseed('mythtv/mysql_host', mysqlserver)
        self.preseed_bool('mythweb/enable', self.frontend.get_secure_mythweb())
        self.preseed('mythweb/username', self.frontend.get_mythweb_username())
        self.preseed('mythweb/password', self.frontend.get_mythweb_password())
        FilteredCommand.ok_handler(self)

class MythbuntuRemote(FilteredCommand):

    def __init__(self,frontend,db=None):
        self.top = ['remote', 'transmitter']
        self.subitems = ['','lircd_conf','modules','driver','device']
        FilteredCommand.__init__(self,frontend,db)

    def prepare(self):
        questions = []
        for question in self.top:
            for subquestion in self.subitems:
                if subquestion != '':
                    real_question = question + '_' + subquestion
                else:
                    real_question = question
                answer = self.db.get('lirc/' + real_question)
                if answer != '':
                    self.frontend.set_lirc(real_question,answer)
                questions.append('^lirc/' + real_question)
        return (['/usr/share/ubiquity/ask-ir'], questions)

    def ok_handler(self):
        for question in self.top:
            device = self.frontend.get_lirc(question)
            for subquestion in self.subitems:
                if subquestion != '':
                    real_question = question + '_' + subquestion
                else:
                    real_question = question
                    subquestion = question
                self.preseed('lirc/' + real_question,device[subquestion])
        FilteredCommand.ok_handler(self)

class MythbuntuDrivers(FilteredCommand):
    def prepare(self):
        questions = ['^mythbuntu/video_driver',
             '^mythbuntu/tvout',
             '^mythbuntu/tvstandard',
             '^mythbuntu/hdhomerun',
             '^mythbuntu/xmltv',
             '^mythbuntu/dvbutils']
        return (['/usr/share/ubiquity/ask-drivers'], questions)

    def run(self,priority,question):
        answer = self.db.get(question)
        if answer == '':
            if question.startswith('mythbuntu/video_driver'):
                answer = self.frontend.get_video()
            elif question.startswith('mythbuntu/tvout'):
                answer = self.frontend.get_tvout()
            elif question.startswith('mythbuntu/tvstandard'):
                answer = self.frontend.get_tvstandard()
            elif question.startswith('mythbuntu/hdhomerun'):
                answer = self.frontend.get_hdhomerun()
            elif question.startswith('mythbuntu/xmltv'):
                answer = self.frontend.get_xmltv()
            elif question.startswith('mythbuntu/dvbutils'):
                answer = self.frontend.get_dvbutils()
        if answer == True or answer == False:
            self.preseed_bool(question,answer)
        else:
            self.preseed(question,answer)
        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        self.preseed('mythbuntu/video_driver', self.frontend.get_video())
        self.preseed('mythbuntu/tvout', self.frontend.get_tvout())
        self.preseed('mythbuntu/tvstandard', self.frontend.get_tvstandard())
        self.preseed_bool('mythbuntu/hdhomerun',self.frontend.get_hdhomerun())
        self.preseed_bool('mythbuntu/xmltv',self.frontend.get_xmltv())
        self.preseed_bool('mythbuntu/dvbutils',self.frontend.get_dvbutils())
        FilteredCommand.ok_handler(self)
