#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2005 Javier Carranza and others for Guadalinex
# Copyright (C) 2005, 2006, 2007, 2008, 2009 Canonical Ltd.
# Copyright (C) 2007-2009 Mario Limonciello
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

import sys
import os
import errno
import re
import syslog
import debconf

import string

sys.path.insert(0, '/usr/lib/ubiquity')

from install import Install as ParentInstall
from install import InstallStepError
from ubiquity.components import mythbuntu_install

from mythbuntu_common.lirc import LircHandler

class Install(ParentInstall):

    def __init__(self):
        """Initializes the Mythbuntu installer extra objects"""

        #Configure Parent cclass First so we can override things
        ParentInstall.__init__(self)

        self.lirc=LircHandler()
        self.type = self.db.get('mythbuntu/install_type')

        #This forces install_langpacks to do Nothing
        self.langpacks={}

    def configure_user(self):
        """Configures by the regular user configuration stuff
        followed by mythbuntu specific user addons"""
        #Regular ubuntu user configuration
        ParentInstall.configure_user(self)

        #We'll be needing the username, uid, gid
        user = self.db.get('passwd/username')
        self.uid = self.gid = ''
        try:
            self.uid = self.db.get('passwd/user-uid')
        except debconf.DebconfError:
            pass
        try:
            self.gid = self.db.get('passwd/user-gid')
        except debconf.DebconfError:
            pass
        if self.uid == '':
            self.uid = 1000
        else:
            self.uid = int(self.uid)
        if self.gid == '':
            self.gid = 1000
        else:
            self.gid = int(self.gid)

        #Create a .mythtv directory
        home_mythtv_dir = self.target + '/home/' + user + '/.mythtv'
        if not os.path.isdir(home_mythtv_dir):
            #in case someone made a symlink or file for the directory
            if os.path.islink(home_mythtv_dir) or os.path.exists(home_mythtv_dir):
                os.remove(home_mythtv_dir)
            os.mkdir(home_mythtv_dir)
            os.chown(home_mythtv_dir,self.uid,self.gid)

        #Remove mysql.txt from home directory if it's there, then make one
        sql_txt= home_mythtv_dir + '/mysql.txt'
        if os.path.islink(sql_txt) or os.path.exists(sql_txt):
            os.remove(sql_txt)
        try:
            os.symlink('/etc/mythtv/mysql.txt',sql_txt)
        except OSError:
            #on a live disk there is a chance this was a broken link
            #depending on what the user did in the livefs
            pass

        #mythtv.desktop autostart
        if 'Frontend' in self.type:
            config_dir = self.target + '/home/' + user + '/.config'
            autostart_dir =  config_dir + '/autostart'
            autostart_link = autostart_dir + '/mythtv.desktop'
            if not os.path.isdir(config_dir):
                os.makedirs(config_dir)
                os.chown(config_dir,self.uid,self.gid)
            if not os.path.isdir(autostart_dir):
                os.makedirs(autostart_dir)
                os.chown(autostart_dir,self.uid,self.gid)
            elif os.path.islink(autostart_link) or os.path.exists(autostart_link):
                os.remove(autostart_link)
            try:
                os.symlink('/usr/share/applications/mythtv.desktop',autostart_link)
            except OSError:
                #on a live disk, this will appear a broken link, but it works
                pass

        #mythtv group membership
        self.chrex('adduser', user, 'mythtv')

    def configure_ma(self):
        """Overrides module assistant configuration method.  Mythbuntu doesn't
           use module assistant, but we can instead run MySQL and mythweb config
           here"""
        self.db.progress('INFO', 'ubiquity/install/mythbuntu')

        #Copy a few debconf questions that were answered in the installer
        for question in ('mythweb/enable','mythweb/username','mythweb/password',\
                         'mythtv/mysql_mythtv_user','mythtv/mysql_mythtv_password',\
                         'mythtv/mysql_mythtv_dbname','mythtv/mysql_host',\
                         'mythtv/mysql_admin_password'):
            answer=self.db.get(question)
            self.set_debconf(question,answer)
            if question == 'mythtv/mysql_admin_password':
                self.set_debconf('mysql-server/root_password',answer)
                self.set_debconf('mysql-server/root_password_again',answer)

        #Setup mysql.txt nicely
        os.remove(self.target + '/etc/mythtv/mysql.txt')
        self.reconfigure('mythtv-common')

        #only reconfigure database if appropriate
        if 'Master' in self.type:
            #Prepare
            self.chrex('mount', '-t', 'proc', 'proc', '/proc')

            #Setup database
            self.reconfigure('mysql-server-5.0')
            self.reconfigure('mythtv-database')

            #Cleanup
            self.chrex('invoke-rc.d','mysql','stop')
            self.chrex('umount', '/proc')

        #Set up authentication on mythweb if necessary
        self.reconfigure('mythweb')

    def install_extras(self):
        """Overrides main install_extras function to add in Mythbuntu
           drivers and services, and then call the parent function"""
        video_driver = self.db.get('mythbuntu/video_driver')
        vnc = self.db.get('mythbuntu/x11vnc')
        nfs = self.db.get('mythbuntu/nfs-kernel-server')
        hdhomerun = self.db.get('mythbuntu/hdhomerun')
        to_install = []
        to_remove = set()
        if video_driver != "Open Source Driver":
            to_install.append(video_driver)
        if vnc == 'true':
            to_install.append('x11vnc')
        if nfs == 'true':
            to_install.append('nfs-kernel-server')
            to_install.append('portmap')
        if hdhomerun == 'true':
            to_install.append('hdhomerun-config')

        #Remove any conflicts before installing new items
        if to_remove != []:
            self.do_remove(to_remove)
        #Mark new items
        self.record_installed(to_install)

        ParentInstall.install_extras(self)

    def configure_hardware(self):
        """Overrides parent function to add in hooks for configuring
           drivers and services"""

        #Drivers
        self.db.progress('INFO', 'ubiquity/install/drivers')
        control = mythbuntu_install.AdditionalDrivers(None,self.db)
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("Additional Driver Configuration failed with code %d" % ret)

        #Services
        self.db.progress('INFO', 'ubiquity/install/services')
        control = mythbuntu_install.AdditionalServices(None,self.db)
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("Additional Service Configuration failed with code %d" % ret)

        #Remotes & Transmitters
        self.db.progress('INFO', 'ubiquity/install/ir')
        self.configure_ir()

        #Regular parent hardware configure f/n
        self.db.progress('INFO', 'ubiquity/install/hardware')
        ParentInstall.configure_hardware(self)

    def configure_ir(self):
        """Configures the remote & transmitter per user choices"""
        #configure lircd for remote and transmitter
        ir_device={"modules":"","driver":"","device":"","lircd_conf":"","remote":"","transmitter":""}
        self.chroot_setup()
        self.chrex('dpkg-divert', '--package', 'ubiquity', '--rename',
                   '--quiet', '--add', '/sbin/udevd')
        try:
            os.symlink('/bin/true', '/target/sbin/udevd')
        except OSError:
            pass

        try:
            ir_device["remote"] = self.db.get('lirc/remote')
            self.set_debconf('lirc/remote',ir_device["remote"])
            if ir_device["remote"] == "Custom":
                ir_device["modules"] = self.db.get('lirc/remote_modules')
                ir_device["driver"] = self.db.get('lirc/remote_driver')
                ir_device["device"] = self.db.get('lirc/remote_device')
                ir_device["lircd_conf"] = self.db.get('lirc/remote_lircd_conf')
                self.set_debconf('lirc/remote_modules',ir_device["modules"])
                self.set_debconf('lirc/remote_driver',ir_device["driver"])
                self.set_debconf('lirc/remote_device',ir_device["device"])
                self.set_debconf('lirc/remote_lircd_conf',ir_device["lircd_conf"])
            else:
                ir_device["modules"] = ""
                ir_device["driver"] = ""
                ir_device["device"] = ""
                ir_device["lircd_conf"] = ""
            self.lirc.set_device(ir_device,"remote")
        except debconf.DebconfError:
            pass

        try:
            ir_device["transmitter"] = self.db.get('lirc/transmitter')
            self.set_debconf('lirc/transmitter',ir_device["transmitter"])
            if ir_device["transmitter"] == "Custom":
                ir_device["modules"] = self.db.get('lirc/transmitter_modules')
                ir_device["driver"] = self.db.get('lirc/transmitter_driver')
                ir_device["device"] = self.db.get('lirc/transmitter_device')
                ir_device["lircd_conf"] = self.db.get('lirc/transmitter_lircd_conf')
                self.set_debconf('lirc/transmitter_modules',ir_device["modules"])
                self.set_debconf('lirc/transmitter_driver',ir_device["driver"])
                self.set_debconf('lirc/transmitter_device',ir_device["device"])
                self.set_debconf('lirc/transmitter_lircd_conf',ir_device["lircd_conf"])
            else:
                ir_device["modules"] = ""
                ir_device["driver"] = ""
                ir_device["device"] = ""
                ir_device["lircd_conf"] = ""
            self.lirc.set_device(ir_device,"transmitter")
        except debconf.DebconfError:
            pass

        self.lirc.write_hardware_conf(self.target + '/etc/lirc/hardware.conf')

        try:
            self.reconfigure('lirc')
        finally:
            try:
                os.unlink('/target/sbin/udevd')
            except OSError:
                pass
            self.chrex('dpkg-divert', '--package', 'ubiquity', '--rename',
                       '--quiet', '--remove', '/sbin/udevd')
        self.chroot_cleanup()

        #configure lircrc
        home = '/target/home/' + self.db.get('passwd/username')
        os.putenv('HOME',home)
        self.lirc.create_lircrc(self.target + "/etc/lirc/lircd.conf",False)
        os.system('chown ' + str(self.uid) + ':' + str(self.gid) + ' -R ' + home + '/.lirc*')

    def remove_extras(self):
        """Try to remove packages that are installed on the live CD but not on
        the installed system."""
        # Looking through files for packages to remove is pretty quick, so
        # don't bother with a progress bar for that.
        # Check for packages specific to the live CD.
        # Also check for packages that need to be removed based upon the choices made during installation
        # This file (/tmp/filesystem.manifest-mythbuntu) will be created during the summary step
        self.create_removal_list()
        if (os.path.exists("/tmp/filesystem.manifest-mythbuntu") and
            os.path.exists("/cdrom/casper/filesystem.manifest")):
            desktop_packages = set()
            manifest = open("/tmp/filesystem.manifest-mythbuntu")
            for line in manifest:
                if line.strip() != '' and not line.startswith('#'):
                    desktop_packages.add(line.split()[0])
            manifest.close()
            live_packages = set()
            manifest = open("/cdrom/casper/filesystem.manifest")
            for line in manifest:
                if line.strip() != '' and not line.startswith('#'):
                    live_packages.add(line.split()[0])
            manifest.close()
            difference = live_packages - desktop_packages
        else:
            difference = set()

        # Keep packages we explicitly installed.
        difference -= self.query_recorded_installed()

        if len(difference) == 0:
            return

        # Don't worry about failures removing packages; it will be easier
        # for the user to sort them out with a graphical package manager (or
        # whatever) after installation than it will be to try to deal with
        # them automatically here.
        self.do_remove(difference)

    #FIXME
    # I'm ugly
    # I'm unscalable
    # I barely get the job done
    def create_removal_list(self):
        out_f = open("/tmp/filesystem.manifest-mythbuntu", 'w')
        in_f = open("/cdrom/casper/filesystem.manifest-desktop")
        patternline = "^mythbuntu-live|^expect|^tcl8.4"
        if self.type == "Slave Backend/Frontend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mysql-server-5.0|^mysql-server|^mythtv\ "
            patternline += "|^apache2|^libapache2|^php|^mythweb" #mythweb
        elif self.type == "Master Backend":
            patternline += "|^mythtv-frontend|^mythtv\ "
            patternline += "|^mythmusic|^fftw2|^libcdaudio1|^libfaad2-0|^libflac8" #mythmusic
            patternline += "|^mythmovies" #mythmovies
            patternline += "|^mythgallery" #mythgallery
            patternline += "|^mythcontrols" #mythcontrols
            patternline += "|^mytharchive|^ffmpeg|^genisoimage|^dvdauthor|^mjpegtools|^dvd+rw-tools|^python-imaging|^python-mysqldb"
            patternline += "|^mythvideo|^libwww-perl|^libxml-simple-perl" #mythvideo
            patternline += "|^mythweather" #mythweather
        elif self.type == "Slave Backend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mysql-server-5.0|^mythtv-frontend|^mythtv\ "
            patternline += "|^mythmusic|^fftw2|^libcdaudio1|^libfaad2-0|^libflac8" #mythmusic
            patternline += "|^mythmovies" #mythmovies
            patternline += "|^mythgallery" #mythgallery
            patternline += "|^mythcontrols" #mythcontrols
            patternline += "|^mythvideo|^libwww-perl|^libxml-simple-perl" #mythvideo
            patternline += "|^mytharchive|^ffmpeg|^genisoimage|^dvdauthor|^mjpegtools|^dvd+rw-tools|^python-imaging|^python-mysqldb"
            patternline += "|^mythweather" #mythweather
            patternline += "|^apache2|^libapache2|^php|^mythweb" #mythweb
        elif self.type == "Frontend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mythtv-backend|^mysql-server-5.0|^mysql-server|^mythtv\ "
            patternline += "|^apache2|^libapache2|^php|^mythweb" #mythweb
        official = self.db.get('mythbuntu/officialthemes')
        if official != "":
            for theme in string.split(official," "):
                if theme != "":
                    patternline += "|^" + theme
        community = self.db.get('mythbuntu/communitythemes')
        if community != "":
            for theme in string.split(community," "):
                if theme != "":
                    patternline += "|^" + theme
        samba = self.db.get('mythbuntu/samba')
        if samba == "false":
            patternline += "|^samba|^samba-common|^smbfs"
        vnc = self.db.get('mythbuntu/x11vnc')
        if vnc == "false":
            patternline += "|^vnc4-common|^x11vnc"
        ssh = self.db.get('mythbuntu/openssh-server')
        if ssh == "false":
            patternline += "|^openssh-server"
        hdhomerun = self.db.get('mythbuntu/hdhomerun')
        if hdhomerun == "false":
            patternline += "|^hdhomerun-config"
        pattern = re.compile(patternline)
        for line in in_f:
            if pattern.search(line) is None:
                out_f.write(line)
        in_f.close()
        out_f.close()

if __name__ == '__main__':
    if not os.path.exists('/var/lib/ubiquity'):
        os.makedirs('/var/lib/ubiquity')
    if os.path.exists('/var/lib/ubiquity/install.trace'):
        os.unlink('/var/lib/ubiquity/install.trace')

    install = Install()
    sys.excepthook = install.excepthook
    install.run()
    sys.exit(0)
