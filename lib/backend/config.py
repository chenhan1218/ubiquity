#!/usr/bin/python

def get_locales(self):
    '''get_locales() -> timezone, keymap, locales
    
    Get the timezone, keymap and locales from the
    Debconf database and return them.
    '''
    debconf.runFrontEnd()
    db = debconf.Debconf()
    
    # We get here the current kernel version
    self.kernel_version = open('/proc/sys/kernel/osrelease').readline().strip()
    
    try:
      timezone = db.get('express/timezone')
      if timezone == '':
          timezone = db.get('tzconfig/choose_country_zone_multiple')
    except:
      timezone = open('/etc/timezone').readline().strip()
    keymap = db.get('debian-installer/keymap')
      
    locales = db.get('locales/default_environment_locale')
    return timezone, keymap, locales

def configure_fstab(self, mountpoints):
    fstab = open(os.path.join(self.target,'etc/fstab'), 'w')
    for path, device in mountpoints.items():
        if path == '/':
            passno = 1
        else:
            passno = 2

        filesystem = 'ext3'
        options = 'defaults'
        
        print >>fstab, '%s\t%s\t%s\t%s\t%d\t%d' % (device, path, filesystem, options, 0, passno)
    fstab.close()

def configure_timezone(self, timezone):
    # tzsetup ignores us if these exist
    for tzfile in ('etc/timezone', 'etc/localtime'):
        path = os.path.join(self.target, tzfile)
        if os.path.exists(path):
            os.unlink(path)

    self.set_debconf('base-config', 'tzconfig/preseed_zone', timezone)
    self.chrex('tzsetup', '-y')

def configure_keymap(self, keymap):
    self.set_debconf('debian-installer', 'debian-installer/keymap', keymap)
    self.chrex('install-keymap', keymap)

def configure_user(self, username, password, fullname):
    self.chrex('passwd', '-l', 'root')
    self.set_debconf('passwd', 'passwd/username', username)
    self.set_debconf('passwd', 'passwd/user-fullname', fullname)
    self.set_debconf('passwd', 'passwd/user-password', password)
    self.set_debconf('passwd', 'passwd/user-password-again', password)
    self.reconfigure('passwd')

def configure_hostname(self, hostname):
    fp = open(os.path.join(self.target, 'etc/hostname'), 'w')
    print >>fp, hostname
    fp.close()

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

def configure_network(self):
    self.ex('/usr/share/setup-tool-backends/scripts/network-conf','--get',
    '>',self.target + '/tmp/network.xml')
    self.chex('/usr/share/setup-tool-backends/scripts/network-conf','--set',
    '<','/tmp/network.xml')

def configure_bootloader(self, target_dev):
    # Copying the old boot config
    files = ['/etc/lilo.conf', '/boot/grub/menu.lst','/etc/grub.conf',
             '/boot/grub/grub.conf']
    TEST = '/mnt/test/'
    grub_dev = misc.grub_dev(target_dev)
    distro = self.distro.capitalize()
    proc_file = open('/proc/partitions').readlines()
    parts = []

    for entry in proc_file[2:]:
        dev = entry.split()
        if len(dev[3]) == 4:
            parts.append(dev[3])
    self.ex('mkdir', TEST)
    for part in parts:
        if self.ex('mount', '/dev/' + part , TEST):
            for file in files:
                if os.path.exists(TEST + file):
                    self.ex('cp', TEST + file, self.target + file)
                    
            self.ex('umount', TEST)

    # The new boot
    self.chex('/usr/sbin/mkinitrd')
    # For the Grub
    grub_conf = open(self.target + '/boot/grub/menu.lst', 'a')
    grub_conf.write(' \
    e %s \
    (%s) \
    el (%s)/vmlinuz-%s root=%s ro vga=791 quiet \
    rd (%s)/initrd.img-%s \
    default ' % \
    (distro, grub_dev, grub_dev, self.kernel_version, target_dev, grub_dev, self.kernel_version) )

    grub_conf.close()

    # For the Yaboot
    if not os.path.exists(self.target + '/etc/yaboot.conf'):
        #FIXME: finish this function
        #misc.make_yaboot_header(self.target)
        pass
    yaboot_conf = open(self.target + '/etc/yaboot.conf', 'a')
    yaboot_conf.write(' \
    =/boot/vmlinuz-%s \
    label=%s \
    root=%s \
    initrd=/boot/initrd.img-%s \
    append="root=%s ro vga=791 quiet" \
    read-only \
    ' % (self.kernel_version, distro, target_dev, self.kernel_version, target_dev) )

    yaboot_conf.close()

    self.ex('/usr/share/setup-tool-backends/scripts/boot-conf','--get',
    '>',self.target + '/tmp/boot.xml')
    self.chex('/usr/share/setup-tool-backends/scripts/boot-conf','--set',
    '<','/tmp/boot.xml')

def chrex(self, *args):
    self.ex('chroot', self.target, *args)

def copy_debconf(self, package):
    targetdb = os.path.join(self.target, 'var/cache/debconf/config.dat')
    self.ex('debconf-copydb', 'configdb', 'targetdb', '-p', '^%s/' % package,
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



# vim:ai:et:sts=2:tw=80:sw=2:
