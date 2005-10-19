#!/usr/bin/python
# -*- coding: utf-8 -*-

from ue import misc, settings

import debconf, os
import subprocess

class Config:

  def __init__(self, vars):
    """Initial attributes."""

    # We get here the current kernel version
    self.kernel_version = open('/proc/sys/kernel/osrelease').readline().strip()
    # FIXME: Hack (current kernel loaded on liveCD doesn't work on installed systems)
    self.kernel_version = '2.6.12-9-386'
    self.distro = open('/etc/lsb-release').readline().strip().split('=')[1].lower()
    self.target = '/target/'
    # Getting vars: fullname, username, password, hostname
    # and mountpoints
    for var in vars.keys():
      setattr(self,var,vars[var])


  def run(self, queue):
    """Run configuration stage. These are the last steps to launch in live
    installer."""

    #queue.put('92 92% Configurando sistema locales')
    #misc.post_log('info', 'Configuring distro')
    #if self.get_locales():
    #  queue.put('92 92% Sistema locales configurado')
    #  misc.post_log('info', 'Configured distro')
    #else:
    #  misc.post_log('error', 'Configuring distro')
    #  return False
    queue.put('93 93% Configurando sistema de particiones en disco')
    misc.post_log('info', 'Configuring distro')
    if self.configure_fstab():
      queue.put('93 93% Sistema de particiones en disco configurado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    #queue.put('94 94% Configurando zona horaria')
    #misc.post_log('info', 'Configuring distro')
    #if self.configure_timezone():
    #  queue.put('94 94% Zona horaria configurada')
    #  misc.post_log('info', 'Configured distro')
    #else:
    #  misc.post_log('error', 'Configuring distro')
    #  return False
    queue.put('95 95% Creando usuario')
    misc.post_log('info', 'Configuring distro')
    if self.configure_user():
      queue.put('95 95% Usuario creado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('96 96% Configurando hardware')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hardware():
      queue.put('96 96% Hardware configurado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('97 97% Configurando red')
    misc.post_log('info', 'Configuring distro')
    if self.configure_network():
      queue.put('97 97% Red configurada')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('98 98% Bautizando ordenador')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hostname():
      queue.put('98 98% Ordenador bautizado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('99 99% Configurando sistema de arranque')
    misc.post_log('info', 'Configuring distro')
    if self.configure_bootloader():
      queue.put('100 100% Instalación finalizada')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False


  def get_locales(self):
    """set timezone and keymap attributes from debconf. It uses the same values
    the user have selected on live system.

    get_locales() -> timezone, keymap, locales"""

    debconf.runFrontEnd()
    db = debconf.Debconf()

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
            passno = 1
            options = 'defaults,errors=remount-ro'
            filesystem = 'ext3'
        elif path == 'swap':
            swap = 1
            passno = 0
            filesystem = 'swap'
            options = 'sw'
            path = 'none'
        else:
            passno = 2
            filesystem = 'ext3'
            options = 'defaults'

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

    self.chrex('passwd', '-l', 'root')
    #self.set_debconf('passwd', 'passwd/username', self.username)
    #self.set_debconf('passwd', 'passwd/user-fullname', self.fullname)
    #self.set_debconf('passwd', 'passwd/user-password', self.password)
    #self.set_debconf('passwd', 'passwd/user-password-again', self.password)
    #self.reconfigure('passwd')
    self.chrex('useradd', '-u', '1001', '-d', '/home/' + self.username, '-s',
        '/bin/bash', '-c', self.fullname, self.username)
    passwd = subprocess.Popen(['echo', self.username + ':' + self.password],
        stdout=subprocess.PIPE)
    subprocess.Popen(['chroot', self.target, 'chpasswd', '--md5'], stdin=passwd.stdout)
    self.chrex('deluser', 'guada')
    self.chrex('rm', '-rf', '/home/guada')
    self.chrex('mkdir', '/home/%s' % self.username)
    self.chrex('adduser', self.username, 'admin')
    try:
      self.chrex('/usr/local/sbin/adduser.local')
    except Exception, e:
      print e

    # Copying skel

    def visit (arg, dirname, names):
      for name in names:
        oldname = os.path.join (dirname, name)
        for pattern in str(dirname).split('/')[2:]:
          dir = os.path.join('', pattern)
        newname = os.path.join (self.target, 'home/%s/' % self.username, dir, name)
        if ( os.path.isdir(oldname) ):
          os.mkdir(newname)
        else:
          os.system('cp ' + oldname + ' ' + newname)

    os.path.walk('/etc/skel/', visit, None)

    self.chrex('chown', '-R', self.username, '/home/%s' % self.username)

    return True


  def configure_hostname(self):
    """setting hostname into installed system from data got along the installation
    process."""

    fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
    print >>fp, self.hostname
    fp.close()
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

    files = ['/etc/lilo.conf', '/boot/grub/menu.lst','/etc/grub.conf',
             '/boot/grub/grub.conf']
    TEST = '/mnt/test/'
    target_dev = self.mountpoints.keys()[self.mountpoints.values().index('/')]
    grub_dev = misc.grub_dev(target_dev)
    distro = self.distro.capitalize()
    proc_file = open('/proc/partitions').readlines()
    parts, grub_conf = [], []

    #if os.path.exists(target + '/boot/grub/menu.lst'):
    #  grub_file = open(os.path.join(target, 'boot/grub/menu.lst'), 'r')
    #  it = grub_entries(grub_file)
    #  for i_index, i in enumerate(it):
    #    if ( ''.join(i).startswith('title') ):
    #      #i[1] = 'root\t\t(%s)\n' % grub_dev
    #      grub_conf.append(i)

    for entry in proc_file[2:]:
        dev = entry.split()
        if len(dev[3]) == 4:
            parts.append(dev[3])
    misc.ex('mkdir', TEST)
    for part in parts:
        if misc.ex('mount', '/dev/' + part , TEST):
            for file in files:
                if os.path.exists(TEST + file):
                    grub_file = open(os.path.join(TEST, file))
                    it = misc.grub_entries(grub_file)
                    for i_index, i in enumerate(it):
                      if ( ''.join(i).startswith('title') ):
                        grub_conf.append(i)

            grub_file.close()
            misc.ex('umount', TEST)
    # The new boot
    #self.chex('/usr/sbin/mkinitrd')
    misc.ex('mount', '/proc', '--bind', self.target + '/proc')
    misc.ex('mount', '/sys', '--bind', self.target + '/sys')

    # For the Grub
    first_elem = []
    first_elem.append('fallback 0\n')
    first_elem.append('timeout 30\n')
    first_elem.append('default 1\n')
    first_elem.append('\n')
    #first_elem.append('\n')
    #first_elem.append('title %s, memtest86+\n' % distro)
    #first_elem.append('root (%s)\n' % grub_dev)
    #first_elem.append('kernel (%s)/boot/memtest86+.bin\n' % grub_dev)
    #first_elem.append('\n')
    first_elem.append('title %s, kernel %s\n' % (self.distro, self.kernel_version))
    first_elem.append('root (%s)\n' % grub_dev)
    first_elem.append('kernel (%s)/boot/vmlinuz-%s root=%s ro splash quiet\n' % (grub_dev, self.kernel_version, target_dev))
    first_elem.append('initrd (%s)/boot/initrd.img-%s\n' % (grub_dev, self.kernel_version))
    first_elem.append('savedefault\n')
    first_elem.append('\n')

    grub_conf.reverse()
    grub_conf.append(first_elem)
    grub_conf.reverse()

    menu = open(os.path.join(target + '/boot/grub/menu.lst'), 'w')
    for list_a in grub_conf:
      for elem in list_a:
        menu.write(''.join(elem))
    menu.close()

    misc.ex('grub-install', '--root-directory=' + self.target, target_dev)
    grub_conf = open('/tmp/grub.conf', 'w')

    grub_conf.write('\n \
root (%s)\n \
setup (%s)\n \
quit \n \
' % (grub_dev, grub_dev[:3]))
    grub_conf.close()

    conf = subprocess.Popen(['cat', '/tmp/grub.conf'], stdout=subprocess.PIPE)
    grub_apply = subprocess.Popen(['chroot', self.target, 'grub', '--batch',
        '--device-map=/boot/grub/device.map',
        '--config-file=/boot/grub/menu.lst'], stdin=conf.stdout)

    # For the Yaboot
    #if not os.path.exists(self.target + '/etc/yaboot.conf'):
    #    misc.make_yaboot_header(self.target, target_dev)
    #yaboot_conf = open(self.target + '/etc/yaboot.conf', 'a')
    #yaboot_conf.write(' \
    #default=%s \
    #\
    #image=/boot/vmlinux-%s \
    #  label=%s \
    #  read-only \
    #  initrd=/boot/initrd.img-%s \
    #  append="quiet splash" \
    #' % (distro, self.kernel_version, distro, self.kernel_version) )

    #yaboot_conf.close()

    #conf = subprocess.Popen(['/usr/share/setup-tool-backends/scripts/boot-conf',
    #    '--platform', 'ubuntu-5.04', '--get'], stdout=subprocess.PIPE)
    #subprocess.Popen(['chroot', self.target, '/usr/share/setup-tool-backends/scripts/boot-conf', 
    #    '--set'], stdin=conf.stdout)
    misc.ex('umount', '-f', self.target + '/proc')
    misc.ex('umount', '-f', self.target + '/sys')
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
