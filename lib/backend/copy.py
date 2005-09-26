#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import subprocess
from ue import misc


class Copy:

  def __init__(self, mountpoints):
    self.source = '/source'
    self.target = '/target'
    self.mountpoints = mountpoints

  def run(self, queue):
    queue.put( '3 Preparing the target in the disc')
    misc.pre_log('info', 'Mounting target')
    if self.mount_target():
      queue.put( '3 Prepared the target in the disc')
      misc.pre_log('info', 'Mounted target')
    else:
      misc.pre_log('error', 'Mounting target')
      return False
      
    queue.put( '4 Getting the distro to copy')
    misc.pre_log('info', 'Mounting source')
    if self.mount_source():
      queue.put( '5 Got the distro to copy')
      misc.pre_log('info', 'Mounted source')
    else:
      misc.pre_log('error', 'Mounting source')
      return False
      
    queue.put( '6 Copying the distro files to the disc')
    misc.pre_log('info', 'Copying distro')
    if self.copy_all(queue):
      queue.put( '90 Copied the distro files to the disc')
      misc.pre_log('info', 'Copied distro')
    else:
      misc.pre_log('error', 'Copying distro')
      return False
      
    queue.put( '91 Copying the logs files to the disc')
    misc.pre_log('info', 'Copying logs files')
    if self.copy_logs():
      queue.put( '92 Copied the logs files to the disc')
      misc.post_log('info', 'Copied logs files')
    else:
      misc.pre_log('error', 'Copying logs files')
      return False
      
    queue.put( '93 Releasing the copied distro image')
    misc.post_log('info', 'Umounting source')
    if self.unmount_source():
      queue.put( '94 Released the copied distro image')
      misc.post_log('info', 'Umounted source')
    else:
      misc.post_log('error', 'Umounting source')
      return False
     

  def mount_target(self):
    if not os.path.isdir(self.target):
      try:
        os.mkdir(self.target)
      except Exception, e:
        print e
    try:
      misc.ex('mount', self.mountpoints.keys()[self.mountpoints.values().index('/')], self.target)
    except Exception, e:
      misc.ex('mkfs.ext3', self.mountpoints.keys()[self.mountpoints.values().index('/')])
      misc.ex('mount', self.mountpoints.keys()[self.mountpoints.values().index('/')], self.target)

    for device, path in self.mountpoints.items():
      if path in ('/', 'swap'):
          continue
      path = os.path.join(self.target, path[1:])
      os.mkdir(path)
      try:
        misc.ex('mount', device, path)
      except Exception, e:
        print e
    return True

  def umount_target(self):
    if not os.path.isdir(self.target):
      try:
        os.mkdir(self.target)
      except Exception, e:
        print e
    misc.ex('umount', self.mountpoints.keys()[self.mountpoints.values().index('/')], self.target)

    ordered_list = []
    for device, path in self.mountpoints.items():
      if path in ('swap',):
          continue

      path = os.path.join(self.target, path[1:])
      ordered_list.append((len(path), device, path))

    ordered_list.reverse()
    for length, device, path in  ordered_list:
      misc.ex('umount -f', device, path)
    return True

  def copy_all(self, queue):
    files = []
    total_size = 0
    
    misc.pre_log('info','Recolecting files to copy')
    for dirpath, dirnames, filenames in os.walk(self.source):
      sourcepath = dirpath[len(self.source)+1:]
      if sourcepath.startswith('etc'):
        queue.put( 7)
      elif sourcepath.startswith('home'):
        queue.put( 8)
      elif sourcepath.startswith('media'):
        queue.put( 10)
      elif sourcepath.startswith('usr/doc'):
        queue.put( 11)
      elif sourcepath.startswith('usr/local'):
        queue.put( 13)
      elif sourcepath.startswith('usr/src'):
        queue.put( 15)
      elif sourcepath.startswith('var/backups'):
        queue.put( 16)
      elif sourcepath.startswith('var/tmp'):
        queue.put( 17)


      for name in dirnames + filenames:
        relpath = os.path.join(sourcepath, name)
        fqpath = os.path.join(self.source, dirpath, name)

        if os.path.isfile(fqpath):
          size = os.path.getsize(fqpath)
          total_size += size	
          files.append((relpath, size))
        else:
          files.append((relpath, None))

    misc.pre_log('info','About to start copying')

    copy = subprocess.Popen(['cpio', '-d0mp', self.target],
        cwd = self.source,
        stdin = subprocess.PIPE)

    copied_bytes = 0
    for path, size in files:
      copy.stdin.write(path + '\0')
      misc.pre_log('info', path)
      if size is not None:
        copied_bytes += size
      per = (copied_bytes * 100) / total_size
      # Adjusting the percentage
      per = (per*73/100)+17
      queue.put("%s Copiando /%s" %(per, path))
    
    copy.stdin.close()
    copy.wait()
    return True
    
  def copy_logs(self):

    distro = open ('/etc/lsb-release').readline ().strip ().split ('=') [1].lower ()
    log_file = '/var/log/' + distro + '-express'

    try:
      misc.ex('cp', '-a', log_file,
              os.path.join(self.target, log_file))
    except IOError, error:
      misc.pre_log('error', error)
      return False

    return True

  def mount_source(self):
    from os import path
    self.dev = ''
    files = ['/cdrom/casper/filesystem.cloop', '/cdrom/META/META.squashfs']
    for f in files:
      if path.isfile(f) and path.splitext(f)[1] == '.cloop':
    	file = f
        self.dev = '/dev/cloop1'
      elif path.isfile(f) and path.splitext(f)[1] == '.squashfs':
    	file = f
    	self.dev = '/dev/loop3'

    if self.dev == '':
      return False

    misc.ex('losetup', self.dev, file)
    if not os.path.isdir(self.source):
      try:
        os.mkdir(self.source)
      except Exception, e:
        print e
      misc.pre_log('info', 'mkdir %s' % self.source)
    try:
      misc.ex('mount', self.dev, self.source)
    except Exception, e:
      print e
    return True

  def unmount_source(self):
    if not misc.ex('umount', self.source):
      return False
    if not misc.ex('losetup', '-d', self.dev):
      return False
    return True


if __name__ == '__main__':
  mountpoints = misc.get_var()['mountpoints']
  copy = Copy(mountpoints)
  copy.run()

# vim:ai:et:sts=2:tw=80:sw=2:
