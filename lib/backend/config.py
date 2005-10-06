#!/usr/bin/python
# -*- coding: utf-8 -*-

from ue import misc

import debconf, os
import subprocess

class Config:

  def __init__(self, vars):
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
    queue.put('96 96% Bautizando ordenador')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hostname():
      queue.put('96 96% Ordenador bautizado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('97 97% Configurando hardware')
    misc.post_log('info', 'Configuring distro')
    if self.configure_hardware():
      queue.put('97 97% Hardware configurado')
      misc.post_log('info', 'Configured distro')
    else:
      misc.post_log('error', 'Configuring distro')
      return False
    queue.put('98 98% Configurando red')
    misc.post_log('info', 'Configuring distro')
    if self.configure_network():
      queue.put('98 98% Red configurada')
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
      '''get_locales() -> timezone, keymap, locales

      Get the timezone, keymap and locales from the
      Debconf database and return them.
      '''
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
      fstab = open(os.path.join(self.target,'etc/fstab'), 'w')
      print >>fstab, 'proc\t/proc\tproc\tdefaults\t0\t0\nsysfs\t/sys\tsysfs\tdefaults\t0\t0'
      for device, path in self.mountpoints.items():
          if path == '/':
              passno = 1
          elif path == 'swap':
              swap = 1
              passno = 0
          else:
              passno = 2

          if path != 'swap':
            filesystem = 'ext3'
            options = 'defaults'
          else:
            filesystem = 'swap'
            options = 'sw'
            path = 'none'

          print >>fstab, '%s\t%s\t%s\t%s\t%d\t%d' % (device, path, filesystem, options, 0, passno)
      if ( swap != 1 ):
        print >>fstab, '/swapfile\tnone\tswap\tsw\t0\t0'
        os.system("dd if=/dev/zero of=%s/swapfile bs=1024 count=262144" % self.target)
        os.system("mkswap %s/swapfile" % self.target)
      fstab.close()
      return True


  def configure_timezone(self):
      # tzsetup ignores us if these exist
      for tzfile in ('etc/timezone', 'etc/localtime'):
          path = os.path.join(self.target, tzfile)
          if os.path.exists(path):
              os.unlink(path)

      self.set_debconf('base-config', 'tzconfig/preseed_zone', self.timezone)
      self.chrex('tzsetup', '-y')
      return True


  def configure_keymap(self):
      self.set_debconf('debian-installer', 'debian-installer/keymap', self.keymap)
      self.chrex('install-keymap', self.keymap)
      return True


  def configure_user(self):
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
      self.chrex('rm', '-rf', '/home/guada')
      self.chrex('mkdir', '/home/%s' % self.username)
      self.chrex('adduser', self.username, 'admin')
      try:
        self.chrex('/usr/local/sbin/adduser.local')
      except Exception, e:
        print e

      #SKEL

      def visit (arg, dirname, names):
        for name in names:
          oldname = os.path.join (dirname, name)
          for pattern in str(dirname).split('/')[2:]:
            dir = os.path.join('', pattern)
          newname = os.path.join (self.target, '/home/%s/' % self.username, dir, name)
          if ( os.path.isdir(oldname) ):
            os.mkdir(newname)
          else:
            os.system('cp ' + oldname + ' ' + newname)

      os.path.walk('/etc/skel/', visit, None)

      #os.system ("cp -a /etc/skel/* " + os.path.join (self.target, 'home/%s' % self.username))
      #os.system ("cp -a /etc/skel/.[0-Z]* " + os.path.join (self.target, 'home/%s' % self.username))
      self.chrex('chown', '-R', self.username, '/home/%s' % self.username)

      return True


  def configure_hostname(self):
      fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
      print >>fp, self.hostname
      fp.close()
      return True


  def configure_hardware(self):
      self.chrex('mount', '-t', 'proc', 'proc', '/proc')
      self.chrex('mount', '-t', 'sysfs', 'sysfs', '/sys')

      packages = ['gnome-panel', 'xserver-xorg', 'linux-image-' + self.kernel_version]

      try:
          for package in packages:
              self.copy_debconf(package)
              self.reconfigure(package)
      finally:
          self.chrex('umount', '/proc')
          self.chrex('umount', '/sys')
      return True


  def configure_network(self):
      conf = subprocess.Popen(['/usr/share/setup-tool-backends/scripts/network-conf',
          '--platform', 'ubuntu-5.04', '--get'], stdout=subprocess.PIPE)
      subprocess.Popen(['chroot', self.target, '/usr/share/setup-tool-backends/scripts/network-conf', 
          '--platform', 'ubuntu-5.04', '--set'], stdin=conf.stdout)
      return True


  def configure_bootloader(self):
      # Copying the old boot config
      files = ['/etc/lilo.conf', '/boot/grub/menu.lst','/etc/grub.conf',
               '/boot/grub/grub.conf']
      TEST = '/mnt/test/'
      target_dev = self.mountpoints.keys()[self.mountpoints.values().index('/')]
      grub_dev = misc.grub_dev(target_dev)
      distro = self.distro.capitalize()
      proc_file = open('/proc/partitions').readlines()
      parts = []

      for entry in proc_file[2:]:
          dev = entry.split()
          if len(dev[3]) == 4:
              parts.append(dev[3])
      misc.ex('mkdir', TEST)
      for part in parts:
          if misc.ex('mount', '/dev/' + part , TEST):
              for file in files:
                  if os.path.exists(TEST + file):
                      misc.ex('cp', TEST + file, self.target + file)

              misc.ex('umount', TEST)
      # The new boot
      #self.chex('/usr/sbin/mkinitrd')
      misc.ex('mount', '/proc', '--bind', self.target + '/proc')
      misc.ex('mount', '/sys', '--bind', self.target + '/sys')
      # For the Grub
      grub_conf = open(self.target + '/boot/grub/menu.lst', 'w')
      grub_conf.write('\n \
fallback 0\n \
timeout 30\n \
default 1\n \
\n \
title %s\n \
root (%s)\n \
kernel (%s)/boot/vmlinuz-%s root=%s ro splash quiet\n \
initrd (%s)/boot/initrd.img-%s\n \
' % \
      (distro, grub_dev, grub_dev, self.kernel_version, target_dev, grub_dev, self.kernel_version) )

      grub_conf.close()

      try:
        misc.ex('grub-install', '--root-directory=' + self.target, target_dev)
      except Exception, e:
        grub_conf = open('/tmp/grub.conf', 'w')

        grub_target_dev = int(target_dev[8:]) -1
        grub_conf.write('\n \
root (hd0,%s)\n \
setup (hd0)\n \
quit ' % grub_target_dev)
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
    msg = ''
    for word in args:
      msg += str(word) + ' '
    if not misc.ex('chroot', self.target, *args):
      misc.post_log('error', 'chroot' + msg)
      return False
    misc.post_log('info', 'chroot' + msg)
    return True


  def copy_debconf(self, package):
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
          self.chrex('dpkg-reconfigure', '-fnoninteractive', package)


if __name__ == '__main__':
  from Queue import Queue
  queue = Queue ()
  vars = misc.get_var()
  config = Config(vars)
  config.run(queue)
  print 101

# vim:ai:et:sts=2:tw=80:sw=2:
