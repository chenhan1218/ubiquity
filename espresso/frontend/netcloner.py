# -*- coding: utf-8 -*-

import os
import time, gobject
import glob

from gettext import bindtextdomain, textdomain, install

from espresso.backend import *
from espresso.validation import *
from espresso.misc import *

from Queue import Queue
import thread

# Define Espresso global path
PATH = '/usr/share/espresso'

# Define locale path
LOCALEDIR = "/usr/share/locale"

class Wizard:

  def __init__(self, distro):
    # declare attributes
    self.distro = distro
    self.pid = False
    self.info = {}
    self.per = 0
    self.parse('/etc/config.cfg',self.info)
   
    # Start a timer to see how long the user runs this program
    self.start = time.time()
    
    # set custom language
    self.set_locales()
    
    
  def run(self):
    from espresso import validation
    error_msg = ['\n']
    error = 0
    result = validation.check_hostname(self.info['hostname'])
    if ( result == 1 ):
      error_msg.append("· hostname wrong length (allowed between 3 and 18 chars).\n")
      error = 1
    elif ( result == 2 ):
      error_msg.append("· hostname contains white spaces (they're not allowed).\n")
      error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    if ( '/' not in self.info['mountpoints'].values() ):
       error_msg.append("· mountpoint must start with '/').\n")
       error = 1
    if ( error == 1 ):
      self.show_error(''.join(error_msg))
    self.progress_loop()
    self.clean_up()
    self.__reboot()


  def set_locales(self):
    """internationalization config. Use only once."""
    
    domain = self.distro + '-installer'
    bindtextdomain(domain, LOCALEDIR)
    textdomain(domain)
    install(domain, LOCALEDIR, unicode=1)


  # Methods
  def progress_loop(self):

    mountpoints = self.info['mountpoints']

    def copy_thread(queue):
      """copy thread for copy process."""
      pre_log('info', 'Copying the system...')
      cp = copy.Copy(mountpoints)
      if not cp.run(queue):
        pre_log('error','fail the copy fase')
        self.quit()
      else:
        pre_log('info', 'Copy: ok')
      queue.put('101')
      
    def config_thread(queue):
      """config thread for config process."""
      pre_log('info', 'Configuring the system...')
      cf = config.Config(self, self.info)
      if not cf.run(queue):
        pre_log('error','fail the configure fase')
        self.quit()
      else:
        pre_log('info', 'Configure: ok')
      queue.put('101')

    for function in [copy_thread,config_thread]:
      # Starting config process
      queue = Queue()
      thread.start_new_thread(function, (queue,))
      
      # setting progress bar status while config process is running
      while True:
        msg = str(queue.get())
        # config process is ended when '101' is pushed
        if msg.startswith('101'):
          break
        self.set_progress(msg)

    # umounting self.mountpoints (mounpoints user selection)
    umount = copy.Copy(mountpoints)
    umount.umount_target()


  def clean_up(self):
    ex('rm','-f','/cdrom/META/META.squashfs')
    post_log('info','Cleaned up')


  def set_progress(self, msg):
    num , text = get_progress(msg)
    if num == self.per:
      return True
    post_log('info','%d: %s' % ((num/100.0), text))
    print '%d: %s' % ((num/100.0), text)
    self.per = num
    return True


  def parse(self,name, dict):
    for line in open(name).readlines():
      line = line.strip()
      if line[0] == '#':
        continue
      for word in line.split():
        if '=' in word:
          name, val = word.split('=', 1)
          if name == 'mountpoints':
            mountpoints = {}
            for each in val.split('-'):
              mountpoint, device = each.split(':')
              mountpoints[device] = mountpoint
            val = mountpoints
          dict[name] = val
 
 
  def set_vars_file(self):
    from espresso import misc
    misc.set_var(self.info)


  def show_error(self, msg):
    from sys import stderr
    pre_log('error', msg)
    print >>stderr, "ERROR: " + msg


  def quit(self):
    if self.pid:
      os.kill(self.pid, 9)
    # Tell the user how much time they used
    post_log('info', 'You wasted %.2f seconds with this installation' %
                      (time.time()-self.start))


  def __reboot(self, *args):
    """reboot the system after installing process."""

    os.system("reboot")
    self.quit()


  def read_stdout(self, source, condition):
    msg = source.readline()
    if msg.startswith('101'):
      return False
    self.set_progress(msg)
    return True


  def run_main_loop(self):
    pass


  def quit_main_loop(self):
    pass


if __name__ == '__main__':
  distro = misc.distribution().lower()
  w = Wizard(distro)
  w.run()


# vim:ai:et:sts=2:tw=80:sw=2:
