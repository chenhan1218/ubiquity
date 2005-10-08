# -*- coding: utf-8 -*-

import os
import time, gobject
import glob

from gettext import bindtextdomain, textdomain, install

from ue.backend import *
from ue.validation import *
from ue.misc import *

# Define Ubuntu Express global path
PATH = '/usr/share/ubuntu-express'

# Define locale path
LOCALEDIR = "/usr/share/locale"

class Wizard:

  def __init__(self, distro):
    # declare attributes
    self.distro = distro
    self.pid = False
    self.info = {}
    self.parse('/etc/config.cfg',self.info)
   
    # Start a timer to see how long the user runs this program
    self.start = time.time()
    
    # set custom language
    self.set_locales()
    
    
  def run(self):
    from ue import validation
    error_msg = ['\n']
    error = 0
    result = validation.check_username(self.info['username'])
    if ( result == 1 ):
      error_msg.append("· username contains dots (they're not allowed).\n")
      error = 1
    elif ( result == 2 ):
      error_msg.append("· username contains uppercase characters (they're not allowed).\n")
      error = 1
    elif ( result == 3 ):
      error_msg.append("· username wrong length (allowed between 3 and 24 chars).\n")
      error = 1
    elif ( result == 4 ):
      error_msg.append("· username contains white spaces (they're not allowed).\n")
      error = 1
    elif ( result in [5, 6] ):
      error_msg.append("· username is already taken or prohibited.\n")
      error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    result = validation.check_password(self.info['password'], self.info['password'])
    if ( result in [1,2] ):
      error_msg.append("· password wrong length (allowed between 4 and 16 chars).\n")
      error = 1
    elif ( result == 3 ):
      error_msg.append("· passwords don't match.\n")
      error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    result = validation.check_hostname(self.info['hostname'])
    if ( result == 1 ):
      error_msg.append("· hostname wrong length (allowed between 3 and 18 chars).\n")
      error = 1
    elif ( result == 2 ):
      error_msg.append("· hostname contains white spaces (they're not allowed).\n")
      error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    result = validation.check_mountpoint(self.mountpoint1.get_active_text())
    if ( result[0] is not '/' ):
       error_msg.append("· mountpoint must start with '/').\n")
       error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    self.progress_loop()
    self.clean_up()


  def set_locales(self):
    """internationalization config. Use only once."""
    
    domain = self.distro + '-installer'
    bindtextdomain(domain, LOCALEDIR)
    textdomain(domain)
    install(domain, LOCALEDIR, unicode=1)


  # Methods
  def progress_loop(self):
    pre_log('info', 'progress_loop()')
    self.set_vars_file()
    # Set timeout objects
    path = '/usr/lib/python2.4/site-packages/ue/backend/'
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'copy.py')
      gobject.io_add_watch(source,gobject.IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'config.py')
      gobject.io_add_watch(source,gobject.IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    self.steps.next_page()


  def clean_up(self):
    ex('rm','-f','/cdrom/META/META.squashfs')
    post_log('info','Cleaned up')


  def set_progress(self, msg):
    num , text = get_progress(msg)
    post_log('%d: %s' % (set_percentage(num/100.0), set_text(text)))


  def parse(name, dict):
    for line in open(name).readlines():
      line = line.strip()
      if line[0] == '#':
        continue
      for word in line.split():
        if '=' in word:
          name, val = word.split('=', 1)
          if name == 'mountpoints':
            mountpoints = {}
            for each in val.split(';'):
              mountpoint, device = each.split(':')
              mountpoints[mountpoint] = device
            val = mountpoints
          dict[name] = val
 
 
  def set_vars_file(self):
    from ue import misc
    misc.set_var(self.info)


  def show_error(self, msg):
    post_log('error', msg)
    print "ERROR: " + msg

  def quit(self):
    if self.pid:
      os.kill(self.pid, 9)
    # Tell the user how much time they used
    post_log('info', 'You wasted %.2f seconds with this installation' %
                      (time.time()-self.start))


  def read_stdout(self, source, condition):
    msg = source.readline()
    if msg.startswith('101'):
      return False
    self.set_progress(msg)
    return True

if __name__ == '__main__':
  distro = open('/etc/lsb-release').readline().strip().split('=')[1].lower()
  w = Wizard(distro)
  w.run()


# vim:ai:et:sts=2:tw=80:sw=2:
