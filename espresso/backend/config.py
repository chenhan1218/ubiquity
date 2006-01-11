#!/usr/bin/python
# -*- coding: utf-8 -*-

from espresso import misc
from espresso.components import usersetup
from espresso.settings import *

import debconf, os
try:
  from debconf import DebconfCommunicator
except ImportError:
  from espresso.debconfcommunicator import DebconfCommunicator
import subprocess

class Config:

  def __init__(self, vars):
    """Initial attributes."""

    # We get here the current kernel version
    self.kernel_version = open('/proc/sys/kernel/osrelease').readline().strip()
    # FIXME: Hack (current kernel loaded on liveCD doesn't work on installed systems)
    self.kernel_version = '2.6.12-9-386'
    self.distro = misc.distribution().lower()
    self.target = '/target/'
    # Getting vars: fullname, username, password, hostname
    # and mountpoints
    for var in vars.keys():
      setattr(self,var,vars[var])


  def run(self, queue):
    """Run configuration stage. These are the last steps to launch in live
    installer."""

    queue.put('92 92% Configuring system locales')
    misc.post_log('info', 'Configuring distro')
    if self.get_locales():
      queue.put('92 92% System locales configured')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('93 93% Configuring mount points')
    misc.post_log('info', 'Configuring distro')
    if self.configure_fstab():
      queue.put('93 93% Mount points configured')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    #queue.put('94 94% Configure time zone')
    #misc.post_log('info', 'Configuring distro')
    #if self.configure_timezone():
    #  queue.put('94 94% Time zone configured')
    #  misc.post_log('info', 'Configured distro')
    #else:
    #  misc.post_log('error', 'Configuring distro')
    #  return False
    queue.put('95 95% Creating user')
    misc.post_log('info', 'Configuring distro')
    if self.configure_user():
      queue.put('95 95% User created')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('96 96% Configuring hardware')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hardware():
      queue.put('96 96% Hardware configured')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('97 97% Configuring network')
    misc.post_log('info', 'Configuring distro')
    if self.configure_network():
      queue.put('97 97% Network configured')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('98 98% Setting computer name')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hostname():
      queue.put('98 98% Computer name set')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('99 99% Configuring boot loader')
    misc.post_log('info', 'Configuring distro')
    if self.configure_bootloader():
      queue.put('100 100% Installation complete')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False


  def get_locales(self):
    """set timezone and keymap attributes from debconf. It uses the same values
    the user have selected on live system.

    get_locales() -> timezone, keymap, locales"""

    db = DebconfCommunicator('espresso')

    try:
      self.timezone = db.get('express/timezone')
      if self.timezone == '':
          self.timezone = db.get('tzconfig/choose_country_zone_multiple')
    except:
      self.timezone = open('/etc/timezone').readline().strip()
    self.keymap = db.get('debian-installer/keymap')

    self.locales = db.get('locales/default_environment_locale')
    return True


  def configure_fstab(self):
    """create and configure /etc/fstab depending on our installation selections.
    It creates a swapfile instead of swap partition if it isn't defined along the
    installation process. """

    swap = 0
    fstab = open(os.path.join(self.target,'etc/fstab'), 'w')
    print >>fstab, 'proc\t/proc\tproc\tdefaults\t0\t0\nsysfs\t/sys\tsysfs\tdefaults\t0\t0'
    for device, path in self.mountpoints.items():
        if path == '/':
            passno, options, filesystem = 1, 'defaults,errors=remount-ro', 'ext3'
        elif path == 'swap':
            swap, passno, filesystem, options, path = 1, 0, 'swap', 'sw', 'none'
        else:
            passno, filesystem, options = 2, 'ext3', 'defaults'

        print >>fstab, '%s\t%s\t%s\t%s\t%d\t%d' % (device, path, filesystem, options, 0, passno)

    counter = 1
    for device, fs in misc.get_filesystems().items():
      if ( fs in ['vfat', 'ntfs'] ):
        passno = 2
        if fs == 'vfat' :
          options = 'rw,exec,users,sync,noauto,umask=022'
        else:
          options = 'utf8,noauto,user,exec,uid=1000,gid=1000'
        path = '/media/Windows%d' % counter
        os.mkdir(os.path.join(self.target, path[1:]))
        counter += 1

        print >>fstab, '%s\t%s\t%s\t%s\t%d\t%d' % (device, path, fs, options, 0, passno)

    # if swap partition isn't defined, we create a swapfile
    if ( swap != 1 ):
      print >>fstab, '/swapfile\tnone\tswap\tsw\t0\t0'
      os.system("dd if=/dev/zero of=%s/swapfile bs=1024 count=%d" % (self.target, MINIMAL_PARTITION_SCHEME ['swap'] * 1024) )
      os.system("mkswap %s/swapfile" % self.target)

    fstab.close()
    return True


  def configure_timezone(self):
    """set timezone on installed system (which was obtained from get_locales)."""

    # tzsetup ignores us if these exist
    for tzfile in ('etc/timezone', 'etc/localtime'):
        path = os.path.join(self.target, tzfile)
        if os.path.exists(path):
            os.unlink(path)

    self.set_debconf('base-config', 'tzconfig/preseed_zone', self.timezone)
    self.chrex('tzsetup', '-y')
    return True


  def configure_keymap(self):
    """set keymap on installed system (which was obtained from get_locales)."""

    self.set_debconf('debian-installer', 'debian-installer/keymap', self.keymap)
    self.chrex('install-keymap', self.keymap)
    return True


  def configure_user(self):
    """create the user selected along the installation process into the installed
    system. Default user from live system is deleted and skel for this new user is
    copied to $HOME."""

    usersetup.UserSetup().apply_configuration()

    return True


  def configure_hostname(self):
    """setting hostname into installed system from data got along the installation
    process."""

    fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
    print >>fp, self.hostname
    fp.close()

    hosts = open(os.path.join(self.target, 'etc/hosts'), 'w')
    print >>hosts, """127.0.0.1       localhost.localdomain   localhost
%s

# The following lines are desirable for IPv6 capable hosts
::1     ip6-localhost ip6-loopback
fe00::0 ip6-localnet
ff00::0 ip6-mcastprefix
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
ff02::3 ip6-allhosts""" % self.hostname
    hosts.close()

    return True


  def configure_hardware(self):
    """reconfiguring several packages which depends on the hardware system in
    which has been installed on and need some automatic configurations to get
    work."""

    self.chrex('mount', '-t', 'proc', 'proc', '/proc')
    self.chrex('mount', '-t', 'sysfs', 'sysfs', '/sys')

    misc.ex('cp', '/etc/X11/xorg.conf', os.path.join(self.target, 'etc/X11/xorg.conf') )
    packages = ['gnome-panel', 'linux-image-' + self.kernel_version]

    try:
        for package in packages:
            self.copy_debconf(package)
            self.reconfigure(package)
    finally:
        self.chrex('umount', '/proc')
        self.chrex('umount', '/sys')
    return True


  def configure_network(self):
    """setting network configuration into installed system from live system data. It's
    provdided by setup-tool-backends."""

    conf = subprocess.Popen(['/usr/share/setup-tool-backends/scripts/network-conf',
        '--platform', 'ubuntu-5.04', '--get'], stdout=subprocess.PIPE)
    subprocess.Popen(['chroot', self.target, '/usr/share/setup-tool-backends/scripts/network-conf', 
        '--platform', 'ubuntu-5.04', '--set'], stdin=conf.stdout)
    return True


  def configure_bootloader(self):
    """configuring and installing boot loader into installed hardware system."""

    import re

    target_dev = self.mountpoints.keys()[self.mountpoints.values().index('/')]
    distro = self.distro.capitalize()

    misc.ex('mount', '/proc', '--bind', self.target + '/proc')
    misc.ex('mount', '/sys', '--bind', self.target + '/sys')
    misc.ex('mount', '/dev', '--bind', self.target + '/dev')

    if not os.path.exists(self.target + '/boot/grub'):
          os.mkdir(self.target + '/boot/grub')

    #/target/etc/mtab creation - temporary bugfix for buggy grub-install
    mtab = open(os.path.join(self.target,'etc/mtab'), 'w')
    print >>mtab, '%s\t%s\t%s\t%s\t%s' % (target_dev, '/', 'auto', 'defaults', '0 0')
    mtab.close()

    #grub-install it's enough, because it calls grub-shell with setup command
    device_regex = re.compile(r'/dev/[a-z]+')
    device = device_regex.search(target_dev).group()
    if not os.path.exists ( device ) or os.path.isdir ( device ):
      device = target_dev
    self.chrex ('rm', '-f', '/boot/grub/device.map')
    self.chrex ('grub-install', device )

    # creates grub menu.lst on target
    self.chrex ('rm', '-f', '/boot/grub/menu.lst')
    self.chrex('update-grub', '-y')
    misc.ex('umount', '-f', self.target + '/proc')
    misc.ex('umount', '-f', self.target + '/sys')
    misc.ex('umount', '-f', self.target + '/dev')
    return True


  def chrex(self, *args):
    """executes commands on chroot system (provided by *args)."""

    msg = ''
    for word in args:
      msg += str(word) + ' '
    if not misc.ex('chroot', self.target, *args):
      misc.post_log('error', 'chroot' + msg)
      return False
    misc.post_log('info', 'chroot' + msg)
    return True


  def copy_debconf(self, package):
    """setting debconf database into installed system."""

    targetdb = os.path.join(self.target, 'var/cache/debconf/config.dat')
    misc.ex('debconf-copydb', 'configdb', 'targetdb', '-p', '^%s/' % package,
            '--config=Name:targetdb', '--config=Driver:File','--config=Filename:' + targetdb)


  def set_debconf(self, owner, question, value):
    dccomm = subprocess.Popen(['chroot', self.target, 'debconf-communicate', '-fnoninteractive', owner],
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    dc = debconf.Debconf(read=dccomm.stdout, write=dccomm.stdin)
    dc.set(question, value)
    dc.fset(question, 'seen', 'true')
    dccomm.stdin.close()
    dccomm.wait()


  def reconfigure(self, package):
    """executes a dpkg-reconfigure into installed system to each package which
    provided by args."""

    self.chrex('dpkg-reconfigure', '-fnoninteractive', package)


if __name__ == '__main__':
  from Queue import Queue
  queue = Queue ()
  vars = misc.get_var()
  config = Config(vars)
  config.run(queue)
  print 101

# vim:ai:et:sts=2:tw=80:sw=2:
