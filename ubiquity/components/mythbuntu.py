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

class MythbuntuSetup(FilteredCommand):
    def prepare(self):
        questions = ['^mythbuntu/install_type',
             '^mythbuntu/mytharchive',
             '^mythbuntu/mythbrowser',
             '^mythbuntu/mythcontrols',
             '^mythbuntu/mythdvd',
             '^mythbuntu/mythflix',
             '^mythbuntu/mythgallery',
             '^mythbuntu/mythgame',
             '^mythbuntu/mythmusic',
             '^mythbuntu/mythnews',
             '^mythbuntu/mythphone',
             '^mythbuntu/mythvideo',
             '^mythbuntu/mythweather',
             '^mythbuntu/mythweb',
             '^mythbuntu/officialthemes',
             '^mythbuntu/communitythemes',
             '^mythbuntu/communitythemes',
             '^mythbuntu/vncservice',
             '^mythbuntu/vnc_password',
             '^mythbuntu/sshservice',
             '^mythbuntu/sambaservice',
             '^mythbuntu/nfsservice',
             '^mythbuntu/mysqlservice',
             '^mythbuntu/proprietary_driver',
             '^mythbuntu/tvout',
             '^mythbuntu/tvstandard',
             '^mythtv/mysql_admin_password',
             '^mythtv/mysql_mythtv_user',
             '^mythtv/mysql_mythtv_password',
             '^mythtv/mysql_mythtv_dbname',
             '^mythtv/mysql_host',
             '^mythweb/enable',
             '^mythweb/username',
             '^mythweb/password',
             '^mythbuntu/en_lirc',
             '^lirc/remote',
             '^lirc/lircd_conf',
             '^lirc/modules',
             '^lirc/driver']
        return (['/usr/share/ubiquity/mythbuntu-ask'], questions)

    def run(self,priority,question):
        if question.startswith('mythbuntu/install_type'):
            installtype = self.frontend.get_installtype()
            self.preseed('mythbuntu/install_type', installtype)
            return True
        elif question.startswith('mythbuntu/mytharchive'):
            mytharchive = self.frontend.get_mytharchive()
            self.preseed_bool('mythbuntu/mytharchive', mytharchive)
            return True
        elif question.startswith('mythbuntu/mythbrowser'):
            mythbrowser = self.frontend.get_mythbrowser()
            self.preseed_bool('mythbuntu/mythbrowser', mythbrowser)
            return True
        elif question.startswith('mythbuntu/mythcontrols'):
            mythcontrols = self.frontend.get_mythcontrols()
            self.preseed_bool('mythbuntu/mythcontrols', mythcontrols)
            return True
        elif question.startswith('mythbuntu/mythdvd'):
            mythdvd = self.frontend.get_mythdvd()
            self.preseed_bool('mythbuntu/mythdvd', mythdvd)
            return True
        elif question.startswith('mythbuntu/mythflix'):
            mythflix = self.frontend.get_mythflix()
            self.preseed_bool('mythbuntu/mythflix', mythflix)
            return True
        elif question.startswith('mythbuntu/mythgallery'):
            mythgallery = self.frontend.get_mythgallery()
            self.preseed_bool('mythbuntu/mythgallery', mythgallery)
            return True
        elif question.startswith('mythbuntu/mythgame'):
            mythgame = self.frontend.get_mythgame()
            self.preseed_bool('mythbuntu/mythgame', mythgame)
            return True
        elif question.startswith('mythbuntu/mythmusic'):
            mythmusic = self.frontend.get_mythmusic()
            self.preseed_bool('mythbuntu/mythmusic', mythmusic)
            return True
        elif question.startswith('mythbuntu/mythnews'):
            mythnews = self.frontend.get_mythnews()
            self.preseed_bool('mythbuntu/mythnews', mythnews)
            return True
        elif question.startswith('mythbuntu/mythphone'):
            mythphone = self.frontend.get_mythphone()
            self.preseed_bool('mythbuntu/mythphone', mythphone)
            return True
        elif question.startswith('mythbuntu/mythvideo'):
            mythvideo = self.frontend.get_mythvideo()
            self.preseed_bool('mythbuntu/mythvideo', mythvideo)
            return True
        elif question.startswith('mythbuntu/mythweather'):
            mythweather = self.frontend.get_mythweather()
            self.preseed_bool('mythbuntu/mythweather', mythweather)
            return True
        elif question.startswith('mythbuntu/mythweb'):
            mythweb = self.frontend.get_mythweb()
            self.preseed_bool('mythbuntu/mythweb', mythweb)
            return True
        elif question.startswith('mythbuntu/officialthemes'):
            official = self.frontend.get_officialthemes()
            self.preseed_bool('mythbuntu/officialthemes', official)
            return True
        elif question.startswith('mythbuntu/communitythemes'):
            community = self.frontend.get_communitythemes()
            self.preseed_bool('mythbuntu/communitythemes', community)
            return True
        elif question.startswith('mythtv/mysql_admin_password'):
            if self.frontend.get_secure_mysql():
                mysql_root = self.frontend.get_mysql_root_password()
            else:
                mysql_root = ""
            self.preseed('mythtv/mysql_admin_password',mysql_root)
            return True
        elif question.startswith('mythtv/mysql_mythtv_user'):
            if not self.frontend.get_uselivemysqlinfo():
                mysqluser = self.frontend.get_mysqluser()
            else:
                mysqluser = self.db.get('mythtv/mysql_mythtv_user')
            self.preseed('mythtv/mysql_mythtv_user', mysqluser)
            return True
        elif question.startswith('mythtv/mysql_mythtv_password'):
            if not self.frontend.get_uselivemysqlinfo():
                mysqlpass = self.frontend.get_mysqlpass()
            else:
                mysqlpass = self.db.get('mythtv/mysql_mythtv_password')
            self.preseed('mythtv/mysql_mythtv_password', mysqlpass)
            return True
        elif question.startswith('mythtv/mysql_mythtv_dbname'):
            if not self.frontend.get_uselivemysqlinfo():
                mysqldatabase = self.frontend.get_mysqldatabase()
            else:
                mysqldatabase = self.db.get('mythtv/mysql_mythtv_dbname')
            self.preseed('mythtv/mysql_mythtv_dbname', mysqldatabase)
            return True
        elif question.startswith('mythtv/mysql_host'):
            if not self.frontend.get_uselivemysqlinfo():
                mysqlserver = self.frontend.get_mysqlserver()
            else:
                mysqlserver = self.db.get('mythtv/mysql_host')
            self.preseed('mythtv/mysql_host', mysqlserver)
            return True
        elif question.startswith('mythbuntu/vncservice'):
            vnc = self.frontend.get_vnc()
            self.preseed_bool('mythbuntu/vncservice', vnc)
            return True
        elif question.startswith('mythbuntu/vnc_password'):
            if not self.frontend.get_vnc():
                vnc_pass = "N/A"
            else:
                vnc_pass = self.frontend.get_vnc_password()
            self.preseed('mythbuntu/vnc_password', vnc_pass)
            return True
        elif question.startswith('mythbuntu/sshservice'):
            ssh = self.frontend.get_ssh()
            self.preseed_bool('mythbuntu/sshservice', ssh)
            return True
        elif question.startswith('mythbuntu/sambaservice'):
            samba = self.frontend.get_samba()
            self.preseed_bool('mythbuntu/sambaservice', samba)
            return True
        elif question.startswith('mythbuntu/nfsservice'):
            nfs = self.frontend.get_nfs()
            self.preseed_bool('mythbuntu/nfsservice', nfs)
            return True
        elif question.startswith('mythbuntu/mysqlservice'):
            mysql_secure = self.frontend.get_mysql_port()
            self.preseed_bool('mythbuntu/mysqlservice', mysql_secure)
            return True
        elif question.startswith('mythweb/enable'):
            auth = self.frontend.get_secure_mythweb()
            self.preseed_bool('mythweb/enable', auth)
            return True
        elif question.startswith('mythweb/username'):
            user = self.frontend.get_mythweb_username()
            self.preseed('mythweb/username', user)
            return True
        elif question.startswith('mythweb/password'):
            passw = self.frontend.get_mythweb_password()
            self.preseed('mythweb/password', passw)
            return True
        elif question.startswith('mythbuntu/en_lirc'):
            en_lirc = self.frontend.get_lirc()
            self.preseed_bool('mythbuntu/en_lirc',en_lirc)
            return True
        elif question.startswith('lirc/remote'):
            if self.frontend.get_lirc():
                remote = self.frontend.get_lirc_remote()
            else:
                remote = "n/a"
            self.preseed('lirc/remote',remote)
            return True
        elif question.startswith('lirc/lircd_conf'):
            if self.frontend.get_lirc():
                config = self.frontend.get_lirc_rc()
            else:
                config = "n/a"
            self.preseed('lirc/lircd_conf',config)
            return True
        elif question.startswith('lirc/modules'):
            if self.frontend.get_lirc():
                modules = self.frontend.get_lirc_modules()
            else:
                modules = "n/a"
            self.preseed('lirc/modules',modules)
            return True
        elif question.startswith('lirc/driver'):
            if self.frontend.get_lirc():
                driver = self.frontend.get_lirc_driver()
            else:
                driver = "n/a"
            self.preseed('lirc/driver',driver)
            return True
        return FilteredCommand.run(self, priority, question)

    def ok_handler(self):
        proprietary_driver = self.frontend.get_proprietary()
        self.preseed('mythbuntu/proprietary_driver', proprietary_driver)
        tvout = self.frontend.get_tvout()
        self.preseed('mythbuntu/tvout', tvout)
        tvstandard = self.frontend.get_tvstandard()
        self.preseed('mythbuntu/tvstandard', tvstandard)
        return FilteredCommand.ok_handler(self)
