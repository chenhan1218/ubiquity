#!/usr/bin/python
# -*- coding: utf-8 -*-

# Last modified by A. Olmo on 4 oct 2005.

import os
import subprocess
import time
from ue import misc
from sys import stderr

class Copy:

  def __init__(self, mountpoints):
    self.source = '/source'
    self.target = '/target'
    self.mountpoints = mountpoints

  def run(self, queue):
    queue.put( '3 Preparando el directorio de instalación')
    misc.pre_log('info', 'Mounting target')
    if self.mount_target():
      queue.put( '3 Directorio de instalación listo')
      misc.pre_log('info', 'Mounted target')
    else:
      misc.pre_log('error', 'Mounting target')
      return False
      
    queue.put( '4 Obteniendo la distribución a copiar')
    misc.pre_log('info', 'Mounting source')
    if self.mount_source():
      queue.put( '5 Distribución obtenida')
      misc.pre_log('info', 'Mounted source')
    else:
      misc.pre_log('error', 'Mounting source')
      return False
      
    queue.put( '6 Preparando la copia a disco')
    misc.pre_log('info', 'Copying distro')
    if self.copy_all(queue):
      queue.put( '90 Ficheros copiados')
      misc.pre_log('info', 'Copied distro')
    else:
      misc.pre_log('error', 'Copying distro')
      return False
      
    queue.put( '91 Copiando registros de instalación al disco')
    misc.pre_log('info', 'Copying logs files')
    if self.copy_logs():
      queue.put( '92 Registros de instalación listos')
      misc.post_log('info', 'Copied logs files')
    else:
      misc.pre_log('error', 'Copying logs files')
      return False
      
    queue.put( '93 Desmontando la imagen original de la copia')
    misc.post_log('info', 'Umounting source')
    if self.unmount_source():
      queue.put( '94 Imagen de la copia desmontada')
      misc.post_log('info', 'Umounted source')
    else:
      misc.post_log('error', 'Umounting source')
      return False
     

  def mount_target(self):

#    stderr.write ('PuntosDeMontaje: ' + str (self.mountpoints) + '\n')

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
      try:
        os.mkdir(path)
      except Exception, e:
        print e
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
        queue.put( '7 Recorriendo /etc' )
      elif sourcepath.startswith('home'):
        queue.put( '8 Recorriendo /home' )
      elif sourcepath.startswith('media'):
        queue.put( '10 Recorriendo /media' )
      elif sourcepath.startswith('usr/doc'):
        queue.put( '11 Recorriendo /usr/doc' )
      elif sourcepath.startswith('usr/local'):
        queue.put( '13 Recorriendo /usr/local' )
      elif sourcepath.startswith('usr/src'):
        queue.put( '15 Recorriendo /usr/src' )
      elif sourcepath.startswith('var/backups'):
        queue.put( '16 Recorriendo /var/backups' )
      elif sourcepath.startswith('var/tmp'):
        queue.put( '17 Recorriendo /var/tmp' )


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

    copied_bytes, counter = 0, 0
    for path, size in files:
      copy.stdin.write(path + '\0')
      misc.pre_log('info', path)
      if ( size != None ):
        copied_bytes += size
      per = (copied_bytes * 100) / total_size
      # Adjusting the percentage
      per = (per*73/100)+17
      if ( counter != per and per == 33 ):
        time_start = time.time()
      if ( counter != per and per >= 35 ):
        counter = per
        time_left = (time.time()-time_start)*57/(counter - 33) - (time.time()-time_start)
        minutes, seconds = time_left/60, time_left - int(time_left/60)*60
        queue.put("%s Copiando %s%% - Queda %02d:%02d - [%s]" % (per, per, minutes, seconds, path))
      elif ( counter != per and per < 35 ):
        counter = per
        queue.put("%s Copiando %s%% - [%s]" % (per, per, path))
    
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

