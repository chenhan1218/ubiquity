#!/usr/bin/python
# -*- coding: utf-8 -*-

from espresso import misc
from espresso.components import usersetup_apply
from espresso.settings import *

import os
import platform
import debconf
try:
  from debconf import DebconfCommunicator
except ImportError:
  from espresso.debconfcommunicator import DebconfCommunicator
import subprocess

class Config:

  def __init__(self, frontend):
    """Initial attributes."""

    self.frontend = frontend
    self.kernel_version = platform.release()
    self.target = '/target/'


  def run(self, queue):
    """Run configuration stage. These are the last steps to launch in live
    installer."""

    queue.put('91 91% Configuring installed system')
    misc.post_log('info', 'Configuring distro')
    if self.run_target_config_hooks():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('92 92% Configuring system locales')
    misc.post_log('info', 'Configuring distro')
    if self.get_locales():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('93 93% Configuring mount points')
    misc.post_log('info', 'Configuring distro')
    if self.configure_fstab():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    #queue.put('94 94% Configure time zone')
    #misc.post_log('info', 'Configuring distro')
    #if self.configure_timezone():
    #  misc.post_log('info', 'Configured distro')
    #else:
    #  misc.post_log('error', 'Configuring distro')
    #  return False
    queue.put('95 95% Creating user')
    misc.post_log('info', 'Configuring distro')
    if self.configure_user():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('96 96% Configuring hardware')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hardware():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('97 97% Configuring network')
    misc.post_log('info', 'Configuring distro')
    if self.configure_network():
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('98 98% Setting computer name')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hostname():
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


  def run_target_config_hooks(self):
    """Run hook scripts from /usr/lib/espresso/target-config. This allows
    casper to hook into us and repeat bits of its configuration in the
    target system."""

    hookdir = '/usr/lib/espresso/target-config'

    if os.path.isdir(hookdir):
      for hookentry in os.listdir(hookdir):
        # Exclude hooks containing '.', so that *.dpkg-* et al are avoided.
        if '.' in hookentry:
          continue

        hook = os.path.join(hookdir, hookentry)
        if not os.access(hook, os.X_OK):
          continue
        # Errors are ignored at present, although this may change.
        subprocess.call(hook)

    return True


  def get_locales(self):
    """set timezone and keymap attributes from debconf. It uses the same values
    the user have selected on live system.

    get_locales() -> timezone, keymap, locales"""

    db = DebconfCommunicator('espresso')

    try:
      self.timezone = db.get('time/zone')
      if self.timezone == '':
          self.timezone = db.get('tzconfig/choose_country_zone_multiple')
    except debconf.DebconfError:
      if os.path.islink('/etc/localtime'):
        self.timezone = os.readlink('/etc/localtime')
        if self.timezone.startswith('/usr/share/zoneinfo/'):
          self.timezone = self.timezone[len('/usr/share/zoneinfo/'):]
      elif os.path.exists('/etc/timezone'):
        self.timezone = open('/etc/timezone').readline().strip()
      else:
        self.timezone = None

    try:
      self.keymap = db.get('debian-installer/keymap')
    except debconf.DebconfError:
      self.keymap = None

    try:
      self.locales = db.get('locales/default_environment_locale')
      if self.locales == 'None':
        self.locales = None
    except debconf.DebconfError:
      self.locales = None

    db.shutdown()

    return True


  def configure_fstab(self):
    """create and configure /etc/fstab depending on our installation selections.
    It creates a swapfile instead of swap partition if it isn't defined along the
    installation process. """

    swap = 0
    fstab = open(os.path.join(self.target,'etc/fstab'), 'w')
    print >>fstab, 'proc\t/proc\tproc\tdefaults\t0\t0\nsysfs\t/sys\tsysfs\tdefaults\t0\t0'
    for device, path in self.frontend.get_mountpoints().items():
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

    if self.timezone is not None:
      # tzsetup ignores us if these exist
      for tzfile in ('etc/timezone', 'etc/localtime'):
          path = os.path.join(self.target, tzfile)
          if os.path.exists(path):
              os.unlink(path)

      self.set_debconf('d-i', 'time/zone', self.timezone)
      self.chrex('tzsetup')

    return True


  def configure_keymap(self):
    """set keymap on installed system (which was obtained from get_locales)."""

    if self.keymap is not None:
      self.set_debconf('d-i', 'debian-installer/keymap', self.keymap)
      self.chrex('install-keymap', self.keymap)

    return True


  def configure_user(self):
    """create the user selected along the installation process into the installed
    system. Default user from live system is deleted and skel for this new user is
    copied to $HOME."""

    dbfilter = usersetup_apply.UserSetupApply(self.frontend)
    return (dbfilter.run_command(auto_process=True) == 0)


  def configure_hostname(self):
    """setting hostname into installed system from data got along the installation
    process."""

    fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
    print >>fp, self.frontend.get_hostname()
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
ff02::3 ip6-allhosts""" % self.frontend.get_hostname()
    hosts.close()

    return True


  def configure_hardware(self):
    """reconfiguring several packages which depends on the hardware system in
    which has been installed on and need some automatic configurations to get
    work."""

    self.chrex('mount', '-t', 'proc', 'proc', '/proc')
    self.chrex('mount', '-t', 'sysfs', 'sysfs', '/sys')

    packages = ['linux-image-' + self.kernel_version]

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

    misc.ex('mount', '--bind', '/proc', self.target + '/proc')
    misc.ex('mount', '--bind', '/dev', self.target + '/dev')

    try:
      from espresso.components import grubinstaller
      dbfilter = grubinstaller.GrubInstaller(self.frontend)
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
  config = Config(None)
  config.run(queue)
  print 101

# vim:ai:et:sts=2:tw=80:sw=2:
