#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2005 Javier Carranza and others for Guadalinex
# Copyright (C) 2005, 2006 Canonical Ltd.
# Copyright (C) 2007-2008 Mario Limonciello for Mythbuntu
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
import syslog
import debconf
import re
import string

sys.path.insert(0, '/usr/lib/ubiquity')

from install import Install as ParentInstall
from install import InstallStepError
from ubiquity.components import mythbuntu_install

from mythbuntu_common.lirc import LircHandler
from mythbuntu_common.mysql import MySQLHandler

class Install(ParentInstall):
    def __init__(self):
        """Initializes the Mythbuntu installer extra objects"""
        self.lirc=LircHandler()
        self.mysql=MySQLHandler()
        ParentInstall.__init__(self)

    def run(self):
        """Run the install stage: copy everything to the target system, then
        configure it as necessary."""

        self.type = self.db.get('mythbuntu/install_type')

        self.db.progress('START', 0, 100, 'ubiquity/install/title')
        self.db.progress('INFO', 'ubiquity/install/mounting_source')

        try:
            if self.source == '/var/lib/ubiquity/source':
                self.mount_source()

            self.db.progress('SET', 1)
            self.db.progress('REGION', 1, 75)
            try:
                self.copy_all()
            except EnvironmentError, e:
                if e.errno in (errno.ENOENT, errno.EIO, errno.EFAULT,
                               errno.ENOTDIR, errno.EROFS):
                    if e.filename is None:
                        error_template = 'cd_hd_fault'
                    elif e.filename.startswith('/target'):
                        error_template = 'hd_fault'
                    else:
                        error_template = 'cd_fault'
                    error_template = ('ubiquity/install/copying_error/%s' %
                                      error_template)
                    self.db.subst(error_template, 'ERROR', str(e))
                    self.db.input('critical', error_template)
                    self.db.go()
                    # Exit code 3 signals to the frontend that we have
                    # handled this error.
                    sys.exit(3)
                elif e.errno == errno.ENOSPC:
                    error_template = 'ubiquity/install/copying_error/no_space'
                    self.db.subst(error_template, 'ERROR', str(e))
                    self.db.input('critical', error_template)
                    self.db.go()
                    sys.exit(3)
                else:
                    raise

            self.db.progress('SET', 75)
            self.db.progress('REGION', 75, 76)
            self.db.progress('INFO', 'ubiquity/install/locales')
            self.configure_locales()

            self.db.progress('SET', 76)
            self.db.progress('REGION', 76, 77)
            self.db.progress('INFO', 'ubiquity/install/user')
            self.configure_user()

            self.db.progress('SET', 77)
            self.db.progress('REGION', 77, 78)
            self.run_target_config_hooks()

            self.db.progress('SET', 78)
            self.db.progress('REGION', 78, 79)
            self.db.progress('INFO', 'ubiquity/install/network')
            self.configure_network()

            self.db.progress('SET', 79)
            self.db.progress('REGION', 79, 80)
            self.db.progress('INFO', 'ubiquity/install/apt')
            self.configure_apt()

            self.db.progress('SET', 80)
            self.db.progress('REGION', 80, 85)
            self.db.progress('INFO', 'ubiquity/install/mythbuntu')
            self.configure_mysql()
            self.configure_mythweb()

            self.db.progress('SET', 85)
            self.db.progress('REGION', 85, 86)
            self.db.progress('INFO', 'ubiquity/install/timezone')
            self.configure_timezone()

            self.db.progress('SET', 86)
            self.db.progress('REGION', 86, 87)
            self.db.progress('INFO', 'ubiquity/install/keyboard')
            self.configure_keyboard()

            self.db.progress('SET', 88)
            self.db.progress('REGION', 88, 89)
            self.remove_unusable_kernels()

            self.db.progress('SET', 89)
            self.db.progress('REGION', 89, 93)
            self.db.progress('INFO', 'ubiquity/install/hardware')
            self.configure_hardware()

            self.db.progress('SET', 93)
            self.db.progress('REGION', 93, 94)
            self.db.progress('INFO', 'ubiquity/install/bootloader')
            self.configure_bootloader()

            self.db.progress('SET', 94)
            self.db.progress('REGION', 94, 95)
            self.db.progress('INFO', 'ubiquity/install/installing')
            self.add_drivers_services()
            self.install_extras()

            self.db.progress('SET', 95)
            self.db.progress('REGION', 95, 96)
            self.db.progress('INFO', 'ubiquity/install/drivers')
            self.configure_drivers()

            self.db.progress('SET', 96)
            self.db.progress('INFO', 'ubiquity/install/services')
            self.configure_services()

            self.db.progress('SET', 96)
            self.db.progress('INFO', 'ubiquity/install/ir')
            self.configure_ir()

            self.db.progress('SET', 97)
            self.db.progress('REGION', 97, 99)
            self.db.progress('INFO', 'ubiquity/install/removing')
            self.remove_extras()

            self.remove_broken_cdrom()

            self.db.progress('SET', 99)
            self.db.progress('INFO', 'ubiquity/install/log_files')
            self.copy_logs()

            self.db.progress('SET', 100)
        finally:
            self.cleanup()
            try:
                self.db.progress('STOP')
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                pass

    def configure_user(self):
        """Configures by the regular user configuration stuff
        followed by mythbuntu specific user addons"""
        #Regular ubuntu user configuration
        ParentInstall.configure_user(self)

        #We'll be needing the username, uid, gid
        user = self.db.get('passwd/username')
        uid = gid = ''
        try:
            uid = self.db.get('passwd/user-uid')
        except debconf.DebconfError:
            pass
        try:
            gid = self.db.get('passwd/user-gid')
        except debconf.DebconfError:
            pass
        if uid == '':
            uid = 1000
        else:
            uid = int(uid)
        if gid == '':
            gid = 1000
        else:
            gid = int(gid)

        #Create a .mythtv directory
        home_mythtv_dir = self.target + '/home/' + user + '/.mythtv'
        if not os.path.isdir(home_mythtv_dir):
            #in case someone made a symlink or file for the directory
            if os.path.islink(home_mythtv_dir) or os.path.exists(home_mythtv_dir):
                os.remove(home_mythtv_dir)
            os.mkdir(home_mythtv_dir)
            os.chown(home_mythtv_dir,uid,gid)

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
            autostart_dir = self.target + '/home/' + user + '/.config/autostart/'
            autostart_link = autostart_dir + 'mythtv.desktop'
            if not os.path.isdir(autostart_dir):
                os.makedirs(autostart_dir)
            elif os.path.islink(autostart_link) or os.path.exists(autostart_link):
                os.remove(autostart_link)
            try:
                os.symlink('/usr/share/applications/mythtv.desktop',autostart_link)
            except OSError:
                #on a live disk, this will appear a broken link, but it works
                pass
            
        #mythtv group membership
        self.chrex('adduser', user, 'mythtv')

    def configure_mysql(self):
        """Configures the SQL server and mythtv access to it"""
        #Check if we have a new mysql pass. If not, we'll generate one
        config = {}
        config["user"] = self.db.get('mythtv/mysql_mythtv_user')
        config["password"] = self.db.get('mythtv/mysql_mythtv_password')
        config["database"] = self.db.get('mythtv/mysql_mythtv_dbname')
        config["server"] = self.db.get('mythtv/mysql_host')
        self.mysql.update_config(config)

        #Clear out "old" mysql.txt
        sql_txt  = self.target + '/etc/mythtv/' + 'mysql.txt'
        os.remove(sql_txt)
        
        #Write new mysql.txt
        self.mysql.write_mysql_txt(sql_txt)

        #only reconfigure database if appropriate
        if 'Master' in self.type:
            self.chrex('mount', '-t', 'proc', 'proc', '/proc')
            self.reconfigure('mythtv-database')
            self.chrex('invoke-rc.d','mysql','stop')
            self.chrex('umount', '/proc')

    def configure_mythweb(self):
        """Sets up mythbuntu items such as the initial database and username/password for mythtv user"""

        #FIXME:
        # 1) only run a reconfigure on mythweb if we are keeping it
        # 2) make sure digest is set up
        # 3) move package inversion out
        self.reconfigure('mythweb')

    def add_drivers_services(self):
        """Installs Additional Drivers, Services & Firmware"""
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
        #Install new items
        self.record_installed(to_install)

    def configure_drivers(self):
        """Activates any necessary driver configuration"""
        control = mythbuntu_install.AdditionalDrivers(None,self.db)
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("Additional Driver Configuration failed with code %d" % ret)

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
        os.system('chown 1000:1000 -R ' + home)

    def configure_services(self):
        """Activates any necessary service configuration"""
        control = mythbuntu_install.AdditionalServices(None,self.db)
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("Additional Service Configuration failed with code %d" % ret)

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
        elif self.type == "Master Backend":
            patternline += "|^mythtv-frontend|^mythtv\ "
        elif self.type == "Slave Backend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mysql-server-5.0|^mythtv-frontend|^mythtv\ "
        elif self.type == "Frontend":
            patternline += "|^mythtv-backend-master|^mythtv-database|^mythtv-backend|^mysql-server-5.0|^mysql-server|^mythtv\ |^mythtv-status"
        mytharchive = self.db.get('mythbuntu/mytharchive')
        if mytharchive == "false":
            patternline += "|^mytharchive|^ffmpeg|^genisoimage|^dvdauthor|^mjpegtools|^dvd+rw-tools|^python-imaging|^python-mysqldb"
        mythbrowser = self.db.get('mythbuntu/mythbrowser')
        if mythbrowser == "false":
            patternline += "|^kdelibs4c2a|^mythbrowser"
        mythcontrols = self.db.get('mythbuntu/mythcontrols')
        if mythcontrols == "false":
            patternline += "|^mythcontrols"
        mythflix = self.db.get('mythbuntu/mythflix')
        if mythflix == "false":
            patternline += "|^mythflix"
        mythgallery = self.db.get('mythbuntu/mythgallery')
        if mythgallery == "false":
            patternline += "|^mythgallery"
        mythgame = self.db.get('mythbuntu/mythgame')
        if mythgame == "false":
            patternline += "|^mythgame"
        mythmovies = self.db.get('mythbuntu/mythmovies')
        if mythmovies == "false":
            patternline += "|^mythmovies"
        mythmusic = self.db.get('mythbuntu/mythmusic')
        if mythmusic == "false":
            patternline += "|^mythmusic|^fftw2|^libcdaudio1|^libfaad2-0|^libflac8"
        mythnews = self.db.get('mythbuntu/mythnews')
        if mythnews == "false":
            patternline += "|^mythnews"
        mythphone = self.db.get('mythbuntu/mythphone')
        if mythphone == "false":
            patternline += "|^mythphone"
        mythstream = self.db.get('mythbuntu/mythstream')
        if mythstream == "false":
            patternline += "|^mythstream"
        mythvideo = self.db.get('mythbuntu/mythvideo')
        if mythvideo == "false":
            patternline += "|^mythvideo|^libwww-perl|^libxml-simple-perl"
        mythweather = self.db.get('mythbuntu/mythweather')
        if mythweather == "false":
            patternline += "|^mythweather"
        mythweb = self.db.get('mythbuntu/mythweb')
        if mythweb == "false":
            patternline += "|^apache2|^libapache2|^php|^mythweb"
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
