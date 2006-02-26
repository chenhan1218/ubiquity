#!/usr/bin/python
# -*- coding: utf-8 -*-

from espresso import misc
from espresso.components import language_apply, timezone_apply, usersetup_apply
from espresso.settings import *

import os
import platform
import debconf
import subprocess

class Config:

    def __init__(self):
        """Initial attributes."""

        self.kernel_version = platform.release()
        self.target = '/target/'
        self.db = debconf.Debconf()


    def run(self):
        """Run configuration stage. These are the last steps to launch in live
        installer."""

        self.db.progress('START', 0, 7, 'espresso/config/title')
        self.db.progress('REGION', 0, 1)
        if not self.run_target_config_hooks():
            return False

        self.db.progress('SET', 1)
        self.db.progress('REGION', 1, 2)
        self.db.progress('INFO', 'espresso/config/locales')
        if not self.get_locales():
            return False

        self.db.progress('SET', 2)
        self.db.progress('REGION', 2, 3)
        self.db.progress('INFO', 'espresso/config/timezone')
        if not self.configure_timezone():
            return False

        self.db.progress('SET', 3)
        self.db.progress('REGION', 3, 4)
        self.db.progress('INFO', 'espresso/config/user')
        if not self.configure_user():
            return False

        self.db.progress('SET', 4)
        self.db.progress('REGION', 4, 5)
        self.db.progress('INFO', 'espresso/config/hardware')
        if not self.configure_hardware():
            return False

        self.db.progress('SET', 5)
        self.db.progress('REGION', 5, 6)
        self.db.progress('INFO', 'espresso/config/network')
        if not self.configure_network():
            return False

        # TODO cjwatson 2006-02-25: needs direct access to frontend;
        # disabled until we have espresso-netcfg
        #self.db.progress('SET', 6)
        #self.db.progress('REGION', 6, 7)
        #self.db.progress('INFO', 'espresso/config/hostname')
        #if not self.configure_hostname():
        #    return False

        self.db.progress('SET', 6)
        self.db.progress('REGION', 6, 7)
        self.db.progress('INFO', 'espresso/config/bootloader')
        if not self.configure_bootloader():
            return False

        self.db.progress('SET', 7)
        self.db.progress('STOP')


    def run_target_config_hooks(self):
        """Run hook scripts from /usr/lib/espresso/target-config. This allows
        casper to hook into us and repeat bits of its configuration in the
        target system."""

        hookdir = '/usr/lib/espresso/target-config'

        if os.path.isdir(hookdir):
            # Exclude hooks containing '.', so that *.dpkg-* et al are avoided.
            hooks = filter(lambda entry: '.' not in entry, os.listdir(hookdir))
            self.db.progress('START', 0, len(hooks), 'espresso/config/title')
            for hookentry in hooks:
                hook = os.path.join(hookdir, hookentry)
                if not os.access(hook, os.X_OK):
                    self.db.progress('STEP', 1)
                    continue
                self.db.subst('espresso/config/target_hook',
                              'SCRIPT', hookentry)
                self.db.progress('INFO', 'espresso/config/target_hook')
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


    def set_debconf(self, owner, question, value):
        dccomm = subprocess.Popen(['chroot', self.target,
                                   'debconf-communicate',
                                   '-fnoninteractive', owner],
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
    config = Config()
    config.run()

# vim:ai:et:sts=4:tw=80:sw=4:
