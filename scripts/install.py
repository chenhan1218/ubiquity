#!/usr/bin/python
# -*- coding: utf-8 -*-

# Copyright (C) 2005 Javier Carranza and others for Guadalinex
# Copyright (C) 2005, 2006 Canonical Ltd.
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
import platform
import errno
import re
import subprocess
import time
import debconf
import apt_pkg
from apt.package import Package
from apt.cache import Cache
from apt.progress import FetchProgress, InstallProgress
from espresso import misc
from espresso.components import language_apply, timezone_apply, usersetup_apply
from espresso.settings import *

class DebconfFetchProgress(FetchProgress):
    """An object that reports apt's fetching progress using debconf."""

    def __init__(self, db, title, info):
        FetchProgress.__init__(self)
        self.db = db
        self.title = title
        self.info = info
        self.old_capb = None
        self.eta = 0.0

    def start(self):
        self.db.progress('START', 0, 100, self.title)
        self.old_capb = self.db.capb()
        capb_list = self.old_capb.split()
        capb_list.append('progresscancel')
        self.db.capb(' '.join(capb_list))

    # TODO cjwatson 2006-02-27: implement updateStatus

    def pulse(self):
        FetchProgress.pulse(self)
        try:
            self.db.progress('SET', int(self.percent))
        except debconf.DebconfError:
            return False
        if self.eta != 0.0:
            time_str = "%d:%02d" % divmod(int(self.eta), 60)
            self.db.subst(self.info, 'TIME', time_str)
            try:
                self.db.progress('INFO', self.info)
            except debconf.DebconfError:
                return False
        return True

    def stop(self):
        if self.old_capb is not None:
            self.db.capb(self.old_capb)
            self.old_capb = None
            self.db.progress('STOP')

class DebconfInstallProgress(InstallProgress):
    """An object that reports apt's installation progress using debconf."""

    def __init__(self, db, title, info, error):
        InstallProgress.__init__(self)
        self.db = db
        self.title = title
        self.info = info
        self.error = error
        self.started = False

    def startUpdate(self):
        self.db.progress('START', 0, 100, self.title)
        self.started = True

    def error(self, pkg, errormsg):
        self.db.subst(self.error, 'PACKAGE', pkg)
        self.db.subst(self.error, 'MESSAGE', errormsg)
        self.db.input('critical', self.error)
        self.db.go()

    def statusChange(self, pkg, percent, status):
        self.percent = percent
        self.status = status
        self.db.progress('SET', int(percent))
        self.db.subst(self.info, 'DESCRIPTION', status)
        self.db.progress('INFO', self.info)

    def updateInterface(self):
        # TODO cjwatson 2006-02-28: InstallProgress.updateInterface doesn't
        # give us a handy way to spot when percentages/statuses change and
        # aren't pmerror/pmconffile, so we have to reimplement it here.
        if self.statusfd != None:
            try:
                while not self.read.endswith("\n"):
                    self.read += os.read(self.statusfd.fileno(),1)
            except OSError, (err,errstr):
                # resource temporarily unavailable is ignored
                if err != errno.EAGAIN:
                    print errstr
            if self.read.endswith("\n"):
                s = self.read
                (status, pkg, percent, status_str) = s.split(":", 3)
                if status == "pmerror":
                    self.error(pkg, status_str)
                elif status == "pmconffile":
                    # we get a string like this:
                    # 'current-conffile' 'new-conffile' useredited distedited
                    match = re.compile("\s*\'(.*)\'\s*\'(.*)\'.*").match(status_str)
                    if match:
                        self.conffile(match.group(1), match.group(2))
                else:
                    self.statusChange(pkg, float(percent), status_str.strip())
                self.read = ""

    def run(self, pm):
        pid = self.fork()
        if pid == 0:
            # child

            # Redirect stdout to stderr to avoid it interfering with our
            # debconf protocol stream.
            os.dup2(2, 1)

            # Make sure all packages are installed non-interactively. We
            # don't have enough passthrough magic here to deal with any
            # debconf questions they might ask.
            os.environ['DEBIAN_FRONTEND'] = 'noninteractive'
            if 'DEBIAN_HAS_FRONTEND' in os.environ:
                del os.environ['DEBIAN_HAS_FRONTEND']
            if 'DEBCONF_USE_CDEBCONF' in os.environ:
                # Probably not a good idea to use this in /target too ...
                del os.environ['DEBCONF_USE_CDEBCONF']

            res = pm.DoInstall(self.writefd)
            sys.exit(res)
        self.child_pid = pid
        res = self.waitChild()
        return res

    def finishUpdate(self):
        if self.started:
            self.db.progress('STOP')
            self.started = False

class Install:

    def __init__(self):
        """Initial attributes."""

        if os.path.isdir('/rofs'):
            self.source = '/rofs'
        else:
            self.source = '/source'
        self.target = '/target'
        self.unionfs = False
        self.kernel_version = platform.release()
        self.db = debconf.Debconf()

        apt_pkg.InitConfig()
        apt_pkg.Config.Set("Dir", "/target")
        apt_pkg.Config.Set("APT::GPGV::TrustedKeyring",
                           "/target/etc/apt/trusted.gpg")
        apt_pkg.Config.Set("DPkg::Options::", "--root=/target")
        # We don't want apt-listchanges or dpkg-preconfigure, so just clear
        # out the list of pre-installation hooks.
        apt_pkg.Config.Clear("DPkg::Pre-Install-Pkgs")
        apt_pkg.InitSystem()

    def run(self):
        """Run the install stage: copy everything to the target system, then
        configure it as necessary."""

        self.db.progress('START', 0, 100, 'espresso/install/title')
        self.db.progress('INFO', 'espresso/install/mounting_source')
        if self.source == '/source':
            if not self.mount_source():
                self.db.progress('STOP')
                return False

        self.db.progress('SET', 1)
        self.db.progress('REGION', 1, 78)
        if not self.copy_all():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 78)
        self.db.progress('INFO', 'espresso/install/log_files')
        if not self.copy_logs():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 79)
        self.db.progress('INFO', 'espresso/install/cleanup')
        if self.source == '/source':
            if not self.umount_source():
                self.db.progress('STOP')
                return False

        self.db.progress('SET', 80)
        self.db.progress('REGION', 80, 81)
        if not self.run_target_config_hooks():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 81)
        self.db.progress('REGION', 81, 82)
        self.db.progress('INFO', 'espresso/install/locales')
        if not self.get_locales():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 82)
        self.db.progress('REGION', 82, 87)
        # Ignore failures from language pack installation.
        self.install_language_packs()

        self.db.progress('SET', 87)
        self.db.progress('REGION', 87, 88)
        self.db.progress('INFO', 'espresso/install/timezone')
        if not self.configure_timezone():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 88)
        self.db.progress('REGION', 88, 89)
        self.db.progress('INFO', 'espresso/install/user')
        if not self.configure_user():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 89)
        self.db.progress('REGION', 89, 95)
        self.db.progress('INFO', 'espresso/install/hardware')
        if not self.configure_hardware():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 95)
        self.db.progress('REGION', 95, 96)
        self.db.progress('INFO', 'espresso/install/network')
        if not self.configure_network():
            self.db.progress('STOP')
            return False

        # TODO cjwatson 2006-02-25: needs direct access to frontend;
        # disabled until we have espresso-netcfg
        #self.db.progress('SET', 98)
        #self.db.progress('REGION', 98, 99)
        #self.db.progress('INFO', 'espresso/install/hostname')
        #if not self.configure_hostname():
        #    self.db.progress('STOP')
        #    return False

        self.db.progress('SET', 96)
        self.db.progress('REGION', 96, 97)
        self.db.progress('INFO', 'espresso/install/bootloader')
        if not self.configure_bootloader():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 97)
        self.db.progress('REGION', 97, 100)
        self.db.progress('INFO', 'espresso/install/removing')
        if not self.remove_extras():
            self.db.progress('STOP')
            return False

        self.db.progress('SET', 100)
        self.db.progress('STOP')

        return True


    def copy_all(self):
        """Core copy process. This is the most important step of this
        stage. It clones live filesystem into a local partition in the
        selected hard disk."""

        files = []
        total_size = 0

        self.db.progress('START', 0, 100, 'espresso/install/title')
        self.db.progress('INFO', 'espresso/install/scanning')

        # Obviously doing os.walk() twice is inefficient, but I'd rather not
        # suck the list into espresso's memory, and I'm guessing that the
        # kernel's dentry cache will avoid most of the slowness anyway.
        walklen = 0
        for entry in os.walk(self.source):
            walklen += 1
        walkpos = 0
        walkprogress = 0

        for dirpath, dirnames, filenames in os.walk(self.source):
            walkpos += 1
            if int(float(walkpos) / walklen * 10) != walkprogress:
                walkprogress = int(float(walkpos) / walklen * 10)
                self.db.progress('SET', walkprogress)

            sourcepath = dirpath[len(self.source) + 1:]

            for name in dirnames + filenames:
                relpath = os.path.join(sourcepath, name)
                fqpath = os.path.join(self.source, dirpath, name)

                if os.path.isfile(fqpath):
                    size = os.path.getsize(fqpath)
                    total_size += size
                    files.append((relpath, size))
                else:
                    files.append((relpath, None))

        self.db.progress('SET', 10)
        self.db.progress('INFO', 'espresso/install/copying')

        copy = subprocess.Popen(['cpio', '-d0mp', '--quiet', self.target],
                cwd = self.source,
                stdin = subprocess.PIPE)

        # Progress bar handling:
        # We sample progress every half-second (assuming time.time() gives
        # us sufficiently good granularity) and use the average of progress
        # over the last minute or so to decide how much time remains. We
        # don't bother displaying any progress for the first ten seconds in
        # order to allow things to settle down, and we only update the "time
        # remaining" indicator at most every two seconds after that.

        copy_progress = 0
        copied_bytes, counter = 0, 0
        time_start = time.time()
        times = [(time_start, copied_bytes)]
        long_enough = False
        time_last_update = time_start

        for path, size in files:
            copy.stdin.write(path + '\0')
            if size is not None:
                copied_bytes += size

            if int((copied_bytes * 90) / total_size) != copy_progress:
                copy_progress = int((copied_bytes * 90) / total_size)
                self.db.progress('SET', 10 + copy_progress)

            time_now = time.time()
            if (time_now - times[-1][0]) >= 0.5:
                times.append((time_now, copied_bytes))
                if not long_enough and time_now - times[0][0] >= 10:
                    long_enough = True
                if long_enough and time_now - time_last_update >= 2:
                    time_last_update = time_now
                    while (time_now - times[0][0] > 60 and
                           time_now - times[1][0] >= 60):
                        times.pop(0)
                    speed = ((times[-1][1] - times[0][1]) /
                             (times[-1][0] - times[0][0]))
                    time_remaining = int(total_size / speed)
                    time_str = "%d:%02d" % divmod(time_remaining, 60)
                    self.db.subst('espresso/install/copying_time',
                                  'TIME', time_str)
                    self.db.progress('INFO', 'espresso/install/copying_time')

        copy.stdin.close()
        copy.wait()

        self.db.progress('SET', 100)
        self.db.progress('STOP')

        return True


    def copy_logs(self):
        """copy log files into installed system."""

        log_file = '/var/log/installer/espresso'
        target_log_file = os.path.join(self.target, log_file[1:])

        if not os.path.exists(os.path.dirname(target_log_file)):
            os.makedirs(os.path.dirname(target_log_file))

        if not misc.ex('cp', '-a', log_file, target_log_file):
            misc.pre_log('error', 'No se pudieron copiar los registros de instalación')

        return True


    def mount_source(self):
        """mounting loop system from cloop or squashfs system."""

        self.dev = ''
        if not os.path.isdir(self.source):
            try:
                os.mkdir(self.source)
            except Exception, e:
                print e
            misc.pre_log('info', 'mkdir %s' % self.source)

        # Autodetection on unionfs systems
        for line in open('/proc/mounts'):
            if line.split()[2] == 'squashfs':
                misc.ex('mount', '--bind', line.split()[1], self.source)
                self.unionfs = True
                return True

        # Manual Detection on non unionfs systems
        fsfiles = ['/cdrom/casper/filesystem.cloop',
                   '/cdrom/META/META.squashfs']

        for fsfile in fsfiles:
            if os.path.isfile(fsfile):
                if os.path.splitext(fsfile)[1] == '.cloop':
                    self.dev = '/dev/cloop1'
                    break
                elif os.path.splitext(fsfile)[1] == '.squashfs':
                    self.dev = '/dev/loop3'
                    break

        if self.dev == '':
            return False

        misc.ex('losetup', self.dev, file)
        try:
            misc.ex('mount', self.dev, self.source)
        except Exception, e:
            print e
        return True


    def umount_source(self):
        """umounting loop system from cloop or squashfs system."""

        if not misc.ex('umount', self.source):
            return False
        if self.unionfs:
            return True
        if not misc.ex('losetup', '-d', self.dev) and self.dev != '':
            return False
        return True


    def run_target_config_hooks(self):
        """Run hook scripts from /usr/lib/espresso/target-config. This allows
        casper to hook into us and repeat bits of its configuration in the
        target system."""

        hookdir = '/usr/lib/espresso/target-config'

        if os.path.isdir(hookdir):
            # Exclude hooks containing '.', so that *.dpkg-* et al are avoided.
            hooks = filter(lambda entry: '.' not in entry, os.listdir(hookdir))
            self.db.progress('START', 0, len(hooks), 'espresso/install/title')
            for hookentry in hooks:
                hook = os.path.join(hookdir, hookentry)
                if not os.access(hook, os.X_OK):
                    self.db.progress('STEP', 1)
                    continue
                self.db.subst('espresso/install/target_hook',
                              'SCRIPT', hookentry)
                self.db.progress('INFO', 'espresso/install/target_hook')
                # Errors are ignored at present, although this may change.
                subprocess.call(hook)
                self.db.progress('STEP', 1)
            self.db.progress('STOP')

        return True


    def get_locales(self):
        """set keymap attributes from debconf. It uses the same values
        the user have selected on live system.

        get_locales() -> keymap, locales"""

        try:
            self.keymap = self.db.get('debian-installer/keymap')
        except debconf.DebconfError:
            self.keymap = None

        dbfilter = language_apply.LanguageApply(None)
        return (dbfilter.run_command(auto_process=True) == 0)


    def get_cache_pkg(self, cache, pkg):
        # work around broken has_key in python-apt 0.6.16
        try:
            return cache[pkg]
        except KeyError:
            return None


    def mark_install(self, cache, pkg):
        cachedpkg = self.get_cache_pkg(cache, pkg)
        if cachedpkg is not None and not cachedpkg.isInstalled:
            apt_error = False
            try:
                cachedpkg.markInstall()
            except SystemError:
                apt_error = True
            if cache._depcache.BrokenCount > 0 or apt_error:
                cachedpkg.markKeep()
                assert cache._depcache.BrokenCount == 0


    def record_installed(self, cache):
        """Record which packages we've explicitly installed so that we don't
        try to remove them later."""

        record_file = "/var/lib/espresso/apt-installed"
        if not os.path.exists(os.path.dirname(record_file)):
            os.makedirs(os.path.dirname(record_file))
        record = open(record_file, "a")

        for pkg in cache.keys():
            if (cache[pkg].markedInstall or cache[pkg].markedUpgrade or
                cache[pkg].markedReinstall or cache[pkg].markedDowngrade):
                print >>record, pkg

        record.close()


    def install_language_packs(self):
        langpacks = []
        try:
            langpack_db = self.db.get('base-config/language-packs')
            langpacks = langpack_db.replace(',', '').split()
        except debconf.DebconfError:
            pass
        if not langpacks:
            try:
                langpack_db = self.db.get('pkgsel/language-packs')
                langpacks = langpack_db.replace(',', '').split()
            except debconf.DebconfError:
                pass
        if not langpacks:
            try:
                langpack_db = self.db.get('localechooser/supported-locales')
                langpack_set = set()
                for locale in langpack_db.replace(',', '').split():
                    langpack_set.add(locale.split('_')[0])
                langpacks = sorted(langpack_set)
            except debconf.DebconfError:
                pass
        if not langpacks:
            langpack_db = self.db.get('debian-installer/locale')
            langpacks = [langpack_db.split('_')[0]]

        try:
            lppatterns = self.db.get('pkgsel/language-pack-patterns').split()
        except debconf.DebconfError:
            return True

        self.db.progress('START', 0, 100, 'espresso/langpacks/title')

        self.db.progress('REGION', 0, 10)
        fetchprogress = DebconfFetchProgress(
            self.db, 'espresso/langpacks/title',
            'espresso/install/apt_indices')
        cache = Cache()
        try:
            # update() returns False on failure and 0 on success. Madness!
            if cache.update(fetchprogress) not in (0, True):
                fetchprogress.stop()
                self.db.progress('STOP')
                return True
        except IOError, e:
            print >>sys.stderr, e
            sys.stderr.flush()
            self.db.progress('STOP')
            return False
        cache.open(None)
        self.db.progress('SET', 10)

        self.db.progress('REGION', 10, 100)
        fetchprogress = DebconfFetchProgress(
            self.db, 'espresso/langpacks/title', 'espresso/langpacks/packages')
        installprogress = DebconfInstallProgress(
            self.db, 'espresso/langpacks/title', 'espresso/install/apt_info',
            'espresso/install/apt_error_install')

        for lp in langpacks:
            # Basic language packs, required to get localisation working at
            # all. We install these almost unconditionally; if you want to
            # get rid of even these, you can preseed pkgsel/language-packs
            # to the empty string.
            self.mark_install(cache, 'language-pack-%s' % lp)
            # Other language packs, typically selected by preseeding.
            for pattern in lppatterns:
                self.mark_install(cache, pattern.replace('$LL', lp))
            # More extensive language support packages.
            self.mark_install(cache, 'language-support-%s' % lp)
        self.record_installed(cache)

        try:
            if not cache.commit(fetchprogress, installprogress):
                fetchprogress.stop()
                installprogress.finishUpdate()
                self.db.progress('STOP')
                return True
        except SystemError, e:
            print >>sys.stderr, e
            sys.stderr.flush()
            self.db.progress('STOP')
            return False
        self.db.progress('SET', 100)

        self.db.progress('STOP')
        return True


    def configure_timezone(self):
        """Set timezone on installed system."""

        dbfilter = timezone_apply.TimezoneApply(None)
        return (dbfilter.run_command(auto_process=True) == 0)


    def configure_keymap(self):
        """set keymap on installed system (which was obtained from
        get_locales)."""

        if self.keymap is not None:
            self.set_debconf('debian-installer/keymap', self.keymap)
            self.chrex('install-keymap', self.keymap)

        return True


    def configure_user(self):
        """create the user selected along the installation process
        into the installed system. Default user from live system is
        deleted and skel for this new user is copied to $HOME."""

        dbfilter = usersetup_apply.UserSetupApply(None)
        return (dbfilter.run_command(auto_process=True) == 0)


    def configure_hostname(self):
        """setting hostname into installed system from data got along
        the installation process."""

        fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
        print >>fp, self.frontend.get_hostname()
        fp.close()

        hosts = open(os.path.join(self.target, 'etc/hosts'), 'w')
        print >>hosts, """127.0.0.1             localhost.localdomain     localhost
%s

# The following lines are desirable for IPv6 capable hosts
::1         ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts""" % self.frontend.get_hostname()
        hosts.close()

        return True


    def configure_hardware(self):
        """reconfiguring several packages which depends on the
        hardware system in which has been installed on and need some
        automatic configurations to get work."""

        self.chrex('mount', '-t', 'proc', 'proc', '/proc')
        self.chrex('mount', '-t', 'sysfs', 'sysfs', '/sys')

        packages = ['linux-image-' + self.kernel_version]

        try:
            for package in packages:
                self.reconfigure(package)
        finally:
            self.chrex('umount', '/proc')
            self.chrex('umount', '/sys')
        return True


    def configure_network(self):
        """setting network configuration into installed system from
        live system data. It's provdided by setup-tool-backends."""

        conf = subprocess.Popen(['/usr/share/setup-tool-backends/scripts/network-conf',
                '--platform', 'ubuntu-5.04', '--get'], stdout=subprocess.PIPE)
        subprocess.Popen(['chroot', self.target, '/usr/share/setup-tool-backends/scripts/network-conf', 
                '--platform', 'ubuntu-5.04', '--set'], stdin=conf.stdout)
        return True


    def configure_bootloader(self):
        """configuring and installing boot loader into installed
        hardware system."""

        misc.ex('mount', '--bind', '/proc', self.target + '/proc')
        misc.ex('mount', '--bind', '/dev', self.target + '/dev')

        try:
            from espresso.components import grubinstaller
            dbfilter = grubinstaller.GrubInstaller(None)
            ret = (dbfilter.run_command(auto_process=True) == 0)
        except ImportError:
            ret = False

        misc.ex('umount', '-f', self.target + '/proc')
        misc.ex('umount', '-f', self.target + '/dev')

        return ret


    def remove_extras(self):
        """Try to remove packages that are needed on the live CD but not on
        the installed system."""

        if (not os.path.exists("/cdrom/casper/filesystem.manifest-desktop") or
            not os.path.exists("/cdrom/casper/filesystem.manifest")):
            return True

        self.db.progress('START', 0, 5, 'espresso/install/title')

        self.db.progress('INFO', 'espresso/install/find_removables')
        desktop_packages = set()
        for line in open("/cdrom/casper/filesystem.manifest-desktop"):
            desktop_packages.add(line.split()[0])
        live_packages = set()
        for line in open("/cdrom/casper/filesystem.manifest"):
            live_packages.add(line.split()[0])
        apt_installed = set()
        if os.path.exists("/var/lib/espresso/apt-installed"):
            for line in open("/var/lib/espresso/apt-installed"):
                apt_installed.add(line.strip())
        difference = live_packages - desktop_packages - apt_installed

        fetchprogress = DebconfFetchProgress(
            self.db, 'espresso/install/title', 'espresso/install/apt_indices')
        cache = Cache()

        while True:
            removed = set()
            for pkg in difference:
                cachedpkg = self.get_cache_pkg(cache, pkg)
                if cachedpkg is not None and cachedpkg.isInstalled:
                    apt_error = False
                    try:
                        cachedpkg.markDelete(autoFix=False)
                    except SystemError:
                        apt_error = True
                    if apt_error:
                        cachedpkg.markKeep()
                    elif cache._depcache.BrokenCount > 0:
                        # If all of the broken packages are in the
                        # difference set, then go ahead and try to remove
                        # them too.
                        brokenpkgs = set()
                        for pkg in cache.keys():
                            if cache._depcache.IsInstBroken(cache._cache[pkg]):
                                brokenpkgs.add(pkg)
                        broken_removed = set()
                        if brokenpkgs <= difference:
                            for pkg in brokenpkgs:
                                cachedpkg2 = self.get_cache_pkg(cache, pkg)
                                if cachedpkg2 is not None:
                                    broken_removed.add(pkg)
                                    try:
                                        cachedpkg2.markDelete(autoFix=False)
                                    except SystemError:
                                        apt_error = True
                                        break
                        if apt_error or cache._depcache.BrokenCount > 0:
                            # That didn't work. Revert all the removals we
                            # just tried.
                            for pkg in broken_removed:
                                self.get_cache_pkg(cache, pkg).markKeep()
                            cachedpkg.markKeep()
                        else:
                            removed.add(pkg)
                            removed |= broken_removed
                    else:
                        removed.add(pkg)
                    assert cache._depcache.BrokenCount == 0
            if len(removed) == 0:
                break
            difference -= removed

        self.db.progress('SET', 1)
        self.db.progress('REGION', 1, 5)
        fetchprogress = DebconfFetchProgress(
            self.db, 'espresso/install/title', 'espresso/install/fetch_remove')
        installprogress = DebconfInstallProgress(
            self.db, 'espresso/install/title', 'espresso/install/apt_info',
            'espresso/install/apt_error_remove')
        try:
            if not cache.commit(fetchprogress, installprogress):
                fetchprogress.stop()
                installprogress.finishUpdate()
                self.db.progress('STOP')
                return True
        except SystemError, e:
            print >>sys.stderr, e
            sys.stderr.flush()
            self.db.progress('STOP')
            return False
        self.db.progress('SET', 5)

        self.db.progress('STOP')
        return True


    def chrex(self, *args):
        """executes commands on chroot system (provided by *args)."""

        msg = ''
        for word in args:
            msg += str(word) + ' '
        if not misc.ex('chroot', self.target, *args):
            misc.post_log('error', 'chroot ' + msg)
            return False
        return True


    def copy_debconf(self, package):
        """setting debconf database into installed system."""

        # TODO cjwatson 2006-02-25: unusable here now because we have a
        # running debconf frontend that's locked the database; fortunately
        # this isn't critical. We still need to think about how to handle
        # preseeding in general, though.
        targetdb = os.path.join(self.target, 'var/cache/debconf/config.dat')

        misc.ex('debconf-copydb', 'configdb', 'targetdb', '-p',
                '^%s/' % package, '--config=Name:targetdb',
                '--config=Driver:File','--config=Filename:' + targetdb)


    def set_debconf(self, question, value):
        dccomm = subprocess.Popen(['chroot', self.target,
                                   'debconf-communicate',
                                   '-fnoninteractive', 'espresso'],
                                  stdin=subprocess.PIPE,
                                  stdout=subprocess.PIPE, close_fds=True)
        dc = debconf.Debconf(read=dccomm.stdout, write=dccomm.stdin)
        dc.set(question, value)
        dc.fset(question, 'seen', 'true')
        dccomm.stdin.close()
        dccomm.wait()


    def reconfigure(self, package):
        """executes a dpkg-reconfigure into installed system to each
        package which provided by args."""

        self.chrex('dpkg-reconfigure', '-fnoninteractive', package)


if __name__ == '__main__':
    if Install().run():
        sys.exit(0)
    else:
        sys.exit(1)

# vim:ai:et:sts=4:tw=80:sw=4:
