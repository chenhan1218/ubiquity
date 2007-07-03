#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2005 Javier Carranza and others for Guadalinex
# Copyright (C) 2005, 2006 Canonical Ltd.
# Copyright (C) 2007 Mario Limonciello for Mythbuntu
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
import install
import sys
import syslog

sys.path.insert(0, '/usr/lib/ubiquity')

from apt.cache import Cache
from install import InstallStepError, DebconfFetchProgress, \
                    DebconfInstallProgress
from ubiquity import misc
from ubiquity.components import language_apply, apt_setup, timezone_apply, \
                                clock_setup, console_setup_apply, \
                                usersetup_apply, hw_detect, check_kernels, \
                                mythbuntu_apply, mythbuntu_drivers, \
                                mythbuntu_services

class Install(install.Install):
    def __init__(self):
        install.Install.__init__(self)
        
    def run(self):
        """Run the install stage: copy everything to the target system, then
        configure it as necessary."""

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
            self.configure_mythbuntu()

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
            self.db.progress('REGION', 89, 92)
            self.db.progress('INFO', 'ubiquity/install/hardware')
            self.configure_hardware()

            self.db.progress('SET', 92)
            self.db.progress('REGION', 92, 93)
            self.db.progress('INFO', 'ubiquity/install/bootloader')
            self.configure_bootloader()

            self.db.progress('SET', 93)
            self.db.progress('REGION', 93, 95)
            self.db.progress('INFO', 'ubiquity/install/drivers')
            self.add_drivers_services()
            self.configure_drivers()

            self.db.progress('SET', 94)
            self.db.progress('INFO', 'ubiquity/install/services')
            self.configure_services()
            
            self.db.progress('SET', 96)
            self.db.progress('REGION', 96, 99)
            self.db.progress('INFO', 'ubiquity/install/removing')
            self.remove_extras()
            
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
                
    def configure_mythbuntu(self):
        """Sets up mythbuntu items such as the initial database and username/password for mythtv user"""
        control = mythbuntu_apply.MythbuntuApply(None,self.db)
        #process package removal lists
        ret = control.run()
        if ret != 0:
            raise InstallStepError("MythbuntuApply Package List Generation failed with code %d" % ret)
        #process mythtv debconf info to be xfered
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("MythbuntuApply Debconf Xfer failed with code %d" % ret)

    def add_drivers_services(self):
        """Installs Additional Drivers, Services & Firmware"""
        video_driver = self.db.get('mythbuntu/proprietary_driver')
        vnc = self.db.get('mythbuntu/vncservice')
        nfs = self.db.get('mythbuntu/nfsservice')
        to_install = []
        if video_driver == "nvidia":
            to_install.append('nvidia-glx')
        elif video_driver == "fglrx":
            to_install.append('xorg-driver-fglrx')
        if vnc == "yes":
            to_install.append('vnc4server')
        if nfs == "yes":
            to_install.append('nfs-kernel-server')
            to_install.append('portmap')

        self.record_installed(to_install)

        self.db.progress('START', 0, 100, 'ubiquity/install/drivers')

        self.db.progress('REGION', 0, 10)
        fetchprogress = DebconfFetchProgress(
            self.db, 'ubiquity/install/drivers',
            'ubiquity/install/apt_indices_starting',
            'ubiquity/install/apt_indices')
        cache = Cache()

        if cache._depcache.BrokenCount > 0:
            syslog.syslog(
                'not installing drivers, since there are broken '
                'packages: %s' % ', '.join(self.broken_packages(cache)))
            self.db.progress('STOP')
            return

        try:
            # update() returns False on failure and 0 on success. Madness!
            if cache.update(fetchprogress) not in (0, True):
                fetchprogress.stop()
                self.db.progress('STOP')
                return
        except IOError, e:
            for line in str(e).split('\n'):
                syslog.syslog(syslog.LOG_WARNING, line)
            self.db.progress('STOP')
            raise
        cache.open(None)
        self.db.progress('SET', 10)

        self.db.progress('REGION', 10, 100)
        fetchprogress = DebconfFetchProgress(
            self.db, 'ubiquity/install/drivers', None,
            'ubiquity/install/drivers')
        installprogress = DebconfInstallProgress(
            self.db, 'ubiquity/install/services', 'ubiquity/install/apt_info')

        for lp in to_install:
            self.mark_install(cache, lp)
        installed_pkgs = []
        for pkg in cache.keys():
            if (cache[pkg].markedInstall or cache[pkg].markedUpgrade or
                cache[pkg].markedReinstall or cache[pkg].markedDowngrade):
                installed_pkgs.append(pkg)
        self.record_installed(installed_pkgs)

        commit_error = None
        try:
            if not cache.commit(fetchprogress, installprogress):
                fetchprogress.stop()
                installprogress.finishUpdate()
                self.db.progress('STOP')
                return
        except IOError, e:
            for line in str(e).split('\n'):
                syslog.syslog(syslog.LOG_WARNING, line)
            commit_error = str(e)
        except SystemError, e:
            for line in str(e).split('\n'):
                syslog.syslog(syslog.LOG_WARNING, line)
            commit_error = str(e)
        self.db.progress('SET', 100)

        cache.open(None)
        if commit_error or cache._depcache.BrokenCount > 0:
            if commit_error is None:
                commit_error = ''
            brokenpkgs = self.broken_packages(cache)
            syslog.syslog('broken packages after driver installation: '
                          '%s' % ', '.join(brokenpkgs))
            self.db.subst('ubiquity/install/broken_install', 'ERROR',
                          commit_error)
            self.db.subst('ubiquity/install/broken_install', 'PACKAGES',
                          ', '.join(brokenpkgs))
            self.db.input('critical', 'ubiquity/install/broken_install')
            self.db.go()

        self.db.progress('STOP')
        
    def configure_drivers(self):
        """Activates any necessary driver configuration"""
        control = mythbuntu_drivers.AdditionalDrivers(None,self.db)
        ret = control.run_command(auto_process=True)
        if ret != 0:
            raise InstallStepError("Additional Driver Configuration failed with code %d" % ret)

    def configure_services(self):
        """Activates any necessary service configuration"""
        vnc = self.db.get('mythbuntu/vncservice')
        if vnc == "yes":
            handler = mythbuntu_services.VNCHandler('/target')
            handler.run()
        control = mythbuntu_services.AdditionalServices(None,self.db)
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
        apt_installed = set()
        if os.path.exists("/var/lib/ubiquity/apt-installed"):
            apt_installed_file = open("/var/lib/ubiquity/apt-installed")
            for line in apt_installed_file:
                apt_installed.add(line.strip())
            apt_installed_file.close()
        difference -= apt_installed

        if len(difference) == 0:
            return

        # Don't worry about failures removing packages; it will be easier
        # for the user to sort them out with a graphical package manager (or
        # whatever) after installation than it will be to try to deal with
        # them automatically here.
        self.do_remove(difference)

if __name__ == '__main__':
    if not os.path.exists('/var/lib/ubiquity'):
        os.makedirs('/var/lib/ubiquity')
    if os.path.exists('/var/lib/ubiquity/install.trace'):
        os.unlink('/var/lib/ubiquity/install.trace')

    install = Install()
    sys.excepthook = install.excepthook
    install.run()
    sys.exit(0)
