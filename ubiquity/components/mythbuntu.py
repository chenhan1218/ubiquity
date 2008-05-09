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

from ubiquity.filteredcommand import FilteredCommand

class MythbuntuAdvancedType(FilteredCommand):
    def prepare(self):
        questions = ['mythbuntu/advanced_install']
        answer = self.db.get(questions[0])
        if answer != '':
            self.frontend.set_advanced(answer)
        questions[0]='^'+questions[0]
        return (['/usr/share/ubiquity/ask-advanced'], questions)

    def ok_handler(self):
        self.preseed_bool('mythbuntu/advanced_install', self.frontend.get_advanced())
        FilteredCommand.ok_handler(self)

class MythbuntuInstallType(FilteredCommand):
    def prepare(self):
        questions = ['mythbuntu/install_type']
        answer = self.db.get(questions[0])
        if answer != '':
            self.frontend.set_installtype(answer)
        questions[0] = '^' +questions[0]
        return (['/usr/share/ubiquity/ask-type'], questions)

    def ok_handler(self):
        self.preseed('mythbuntu/install_type',self.frontend.get_installtype())
        FilteredCommand.ok_handler(self)

class MythbuntuPlugins(FilteredCommand):
    
    def prepare(self):
        plugins = self.frontend.get_plugins()
        questions = []
        for this_plugin in plugins:
            answer = self.db.get('mythbuntu/' + this_plugin)
            if answer != plugins[this_plugin]:
                plugins[this_plugin] = answer
                self.frontend.set_plugin(this_plugin,answer)
            questions.append('^mythbuntu/' + this_plugin)
        return (['/usr/share/ubiquity/ask-plugins'], questions)

    def ok_handler(self):
        plugins = self.frontend.get_plugins()
        for this_plugin in plugins:
            self.preseed_bool(this_plugin,plugins[this_plugin])
        FilteredCommand.ok_handler(self)

class MythbuntuThemes(FilteredCommand):
#since all themes are pre-installed, we are seeding the ones
#that will be *removed*
    def prepare(self):
        questions = ['^mythbuntu/officialthemes',
             '^mythbuntu/communitythemes']
        return (['/usr/share/ubiquity/ask-themes'], questions)

    def run(self,priority,question):
        answer = self.db.get(question)
        if answer == '':
            if question.startswith('mythbuntu/officialthemes'):
                official = self.frontend.get_officialthemes()
                for theme in official:
                    if not official[theme].get_active():
                        answer+=theme + " "
            elif question.startswith('mythbuntu/communitythemes'):
                community = self.frontend.get_communitythemes()
                for theme in community:
                    if not community[theme].get_active():
                        answer+=theme + " "
        self.preseed(question, answer)
        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        official = self.frontend.get_officialthemes()
        official_string=""
        for theme in official:
            if not official[theme].get_active():
                official_string+=theme + " "
        self.preseed('mythbuntu/officialthemes', official_string)
        community = self.frontend.get_communitythemes()
        community_string=""
        for theme in community:
            if not community[theme].get_active():
                community_string+=theme + " "
        self.preseed('mythbuntu/communitythemes', community_string)
        FilteredCommand.ok_handler(self)

class MythbuntuServices(FilteredCommand):
    def prepare(self):
        questions = [
             '^mythbuntu/vncservice',
             '^mythbuntu/vnc_password',
             '^mythbuntu/sshservice',
             '^mythbuntu/sambaservice',
             '^mythbuntu/nfsservice',
             '^mythbuntu/mysqlservice']
        return (['/usr/share/ubiquity/ask-services'], questions)

    def run(self,priority,question):
        answer = self.db.get(question)
        if answer == '':
            if question.startswith('mythbuntu/vncservice'):
                answer = self.frontend.get_vnc()
            elif question.startswith('mythbuntu/vnc_password'):
                if not self.frontend.get_vnc():
                    answer = "N/A"
                else:
                    answer = self.frontend.get_vnc_password()
            elif question.startswith('mythbuntu/sshservice'):
                answer = self.frontend.get_ssh()
            elif question.startswith('mythbuntu/sambaservice'):
                answer = self.frontend.get_samba()
            elif question.startswith('mythbuntu/nfsservice'):
                answer = self.frontend.get_nfs()
            elif question.startswith('mythbuntu/mysqlservice'):
                answer = self.frontend.get_mysql_port()
        if answer == True or answer == False:
            self.preseed_bool(question,answer)
        else:
            self.preseed(question,answer)
        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        vnc = self.frontend.get_vnc()
        if not vnc:
            vnc_pass = "N/A"
        else:
            vnc_pass = self.frontend.get_vnc_password()
        self.preseed_bool('mythbuntu/vncservice', vnc)
        self.preseed('mythbuntu/vnc_password', vnc_pass)
        self.preseed_bool('mythbuntu/sshservice', self.frontend.get_ssh())
        self.preseed_bool('mythbuntu/sambaservice', self.frontend.get_samba())
        self.preseed_bool('mythbuntu/nfsservice', self.frontend.get_nfs())
        self.preseed_bool('mythbuntu/mysqlservice', self.frontend.get_mysql_port())
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
    def prepare(self):
        questions = ['^lirc/remote',
             '^lirc/remote_lircd_conf',
             '^lirc/remote_modules',
             '^lirc/remote_driver',
             '^lirc/remote_device',
             '^lirc/transmitter',
             '^lirc/transmitter_lircd_conf',
             '^lirc/transmitter_modules',
             '^lirc/transmitter_driver',
             '^lirc/transmitter_device']
        return (['/usr/share/ubiquity/ask-ir'], questions)

    def run(self,priority,question):
        answer = self.db.get(question)
        if answer == '':
            if question.startswith('lirc/remote'):
                device=self.frontend.get_lirc("remote")
                if question.startswith('lirc/remote_modules'):
                    answer = device["modules"]
                elif question.startswith('lirc/remote_lircd_conf'):
                    answer = device["lircd_conf"]
                elif question.startswith('lirc/remote_driver'):
                    answer = device["driver"]
                elif question.startswith('lirc/remote_device'):
                    answer = device["device"]
                elif question.startswith('lirc/remote'):
                    answer = device["remote"]
            elif question.startswith('lirc/transmitter'):
                device=self.frontend.get_lirc("transmitter")
                if question.startswith('lirc/transmitter_modules'):
                    answer = device["modules"]
                elif question.startswith('lirc/transmitter_lircd_conf'):
                    answer = device["lircd_conf"]
                elif question.startswith('lirc/transmitter_driver'):
                    answer = device["driver"]
                elif question.startswith('lirc/transmitter_device'):
                    answer = device["device"]
                elif question.startswith('lirc/transmitter'):
                    answer = device["transmitter"]
        self.preseed(question,answer)
        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        device = self.frontend.get_lirc("remote")
        self.preseed('lirc/remote_modules',device["modules"])
        self.preseed('lirc/remote_lircd_conf',device["lircd_conf"])
        self.preseed('lirc/remote_driver',device["driver"])
        self.preseed('lirc/remote_device',device["device"])
        self.preseed('lirc/remote',device["remote"])
        device = self.frontend.get_lirc("transmitter")
        self.preseed('lirc/transmitter_modules',device["modules"])
        self.preseed('lirc/transmitter_lircd_conf',device["lircd_conf"])
        self.preseed('lirc/transmitter_driver',device["driver"])
        self.preseed('lirc/transmitter_device',device["device"])
        self.preseed('lirc/transmitter',device["transmitter"])
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
        FilteredCommand.ok_handler(self)
