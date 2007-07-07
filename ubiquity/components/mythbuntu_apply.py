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

import re
from ubiquity.filteredcommand import FilteredCommand

class MythbuntuApply(FilteredCommand):
    def prepare(self):
        return (['/usr/share/ubiquity/mythbuntu-apply', '/target'],
                [])

    def run(self):
        out_f = open("/tmp/filesystem.manifest-mythbuntu", 'w')
        in_f = open("/cdrom/casper/filesystem.manifest-desktop")
        patternline = "^mythbuntu-live|^expect|^tcl8.4"
        installtype = self.db.get('mythbuntu/install_type')
        if installtype == "Slave Backend/Frontend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mysql-server-5.0|^mysql-server|^mythtv\ "
        elif installtype == "Master Backend":
            patternline += "|^ubuntu-mythtv-frontend|^mythtv-frontend|^mythtv\ "
        elif installtype == "Slave Backend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mysql-server-5.0|^ubuntu-mythtv-frontend|^mythtv-frontend|^mythtv\ "
        elif installtype == "Frontend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mythtv-backend|^mysql-server-5.0|^mysql-server|^mythtv\ "
        mytharchive = self.db.get('mythbuntu/mytharchive')
        if mytharchive == "no":
            patternline += "|^mytharchive|^ffmpeg|^mkisofs|^dvdauthor|^mjpegtools|^dvd+rw-tools|^python-imaging|^python-mysqldb"
        mythbrowser = self.db.get('mythbuntu/mythbrowser')
        if mythbrowser == "no":
            patternline += "|^kdelibs4c2a|^mythbrowser"
        mythcontrols = self.db.get('mythbuntu/mythcontrols')
        if mythcontrols == "no":
            patternline += "|^mythcontrols"
        mythdvd = self.db.get('mythbuntu/mythdvd')
        if mythdvd == "no":
            patternline += "|^mythdvd"
        mythflix = self.db.get('mythbuntu/mythflix')
        if mythflix == "no":
            patternline += "|^mythflix"
        mythgallery = self.db.get('mythbuntu/mythgallery')
        if mythgallery == "no":
            patternline += "|^mythgallery"
        mythgame = self.db.get('mythbuntu/mythgame')
        if mythgame == "no":
            patternline += "|^mythgame"
        mythmusic = self.db.get('mythbuntu/mythmusic')
        if mythmusic == "no":
            patternline += "|^mythmusic|^fftw2|^libcdaudio1|^libfaad2-0|^libflac8"
        mythnews = self.db.get('mythbuntu/mythnews')
        if mythnews == "no":
            patternline += "|^mythnews"
        mythphone = self.db.get('mythbuntu/mythphone')
        if mythphone == "no":
            patternline += "|^mythphone"
        mythvideo = self.db.get('mythbuntu/mythvideo')
        if mythvideo == "no":
            patternline += "|^mythvideo|^libwww-perl|^libxml-simple-perl"
        mythweather = self.db.get('mythbuntu/mythweather')
        if mythweather == "no":
            patternline += "|^mythweather"
        mythweb = self.db.get('mythbuntu/mythweb')
        if mythweb == "no":
            patternline += "|^apache2|^libapache2|^php|^mythweb"
        official = self.db.get('mythbuntu/officialthemes')
        if official == "no":
            patternline += "|^mythtv-themes"
        community = self.db.get('mythbuntu/communitythemes')
        samba = self.db.get('mythbuntu/sambaservice')
        if samba == "no":
            patternline += "|^samba|^samba-common"
        vnc = self.db.get('mythbuntu/vncservice')
        if vnc == "no":
            patternline += "|^vnc4-common"
        ssh = self.db.get('mythbuntu/sshservice')
        if ssh == "no":
            patternline += "|^openssh-server"
        pattern = re.compile(patternline)
        for line in in_f:
            if pattern.search(line) is None:
                out_f.write(line)
        in_f.close()
        out_f.close()
        return 0
