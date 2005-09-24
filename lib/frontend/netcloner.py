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
    self.checked_partitions = False
    self.pid = False
    self.hostname = ''
    self.fullname = ''
    self.name = ''
    self.password = ''
    self.gparted = False
    self.entries = {
                    'hostname' : 0,
                    'fullname' : 0, 
                    'username' : 0,
                    'password' : 0,
                    'verified_password' : 0
                    }
   
    # Start a timer to see how long the user runs this program
    self.start = time.time()
    
    # set custom language
    self.set_locales()
    
    
  def run(self):
    pass


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


  def set_progress(self, msg):
    num , text = get_progress(msg)
    self.progressbar.set_percentage(num/100.0)
    self.progressbar.set_text(text)
    
  def parse(name, dict):
    for line in open(name).readlines():
      line = line.strip()
      if line[0] == '#':
        continue
      for word in line.split():
        if '=' in word:
          name, val = word.split('=', 1)
          dict[name] = val
 
 
  def set_vars_file(self):
    from ue import fmisc
    vars = {}
    attribs = ['hostname','fullname','username','password']
    try:
      for name in attribs:
        var = getattr(self, name)
        vars[name] = var.get_text()
      vars['mountpoints'] = self.mountpoints
    except:
      pre_log('error', 'Missed attrib to write to /tmp/vars')
      self.quit()
    else:
      fmisc.set_var(vars)


  def show_error(self, msg):
    pass

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


  def on_next_clicked(self, widget):
    step = self.steps.get_current_page()
    pre_log('info', 'Step_before = %d' % step)
    # From Welcome to Info
    if step == 0:
      self.next.set_label('gtk-go-forward')
      self.next.set_sensitive(False)
      self.help.show()
      self.steps.next_page()
    # From Info to Part1
    elif step == 1:
      from ue import validation
      error_msg = ['\n']
      error = 0
      for result in validation.check_username(self.username.get_property('text')):
        if ( result == 1 ):
          error_msg.append("· <b>username</b> contains dots (they're not allowed).\n")
          error = 1
        elif ( result == 2 ):
          error_msg.append("· <b>username</b> contains uppercase characters (they're not allowed).\n")
          error = 1
        elif ( result == 3 ):
          error_msg.append("· <b>username</b> wrong length (allowed between 3 and 24 chars).\n")
          error = 1
        elif ( result == 4 ):
          error_msg.append("· <b>username</b> contains white spaces (they're not allowed).\n")
          error = 1
        elif ( result in [5, 6] ):
          error_msg.append("· <b>username</b> is already taken or prohibited.\n")
          error = 1
      for result in validation.check_password(self.password.get_property('text'), self.verified_password.get_property('text')):
        if ( result in [1,2] ):
          error_msg.append("· <b>password</b> wrong length (allowed between 4 and 16 chars).\n")
          error = 1
        elif ( result == 3 ):
          error_msg.append("· <b>passwords</b> don't match.\n")
          error = 1
      for result in validation.check_hostname(self.hostname.get_property('text')):
        if ( result == 1 ):
          error_msg.append("· <b>hostname</b> wrong length (allowed between 3 and 18 chars).\n")
          error = 1
        elif ( result == 2 ):
          error_msg.append("· <b>hostname</b> contains white spaces (they're not allowed).\n")
          error = 1
      if ( error == 1 ):
        self.show_error(''.join(error_msg))
      else:
        self.gparted_loop()
        self.browser_vbox.destroy()
        self.help.hide()
        #self.next.set_sensitive(False)
        self.steps.set_current_page(3)
        #self.back.show()
        #if not self.checked_partitions:
        #  if not self.check_partitions():
        #    return          
        #self.steps.next_page()
    # From Part1 to part2
    elif step == 2 and self.gparted:
      self.next.set_sensitive(False)
      self.gparted_loop()
      self.steps.next_page()
    # From Part1 to Progress
    elif step == 2 and not self.gparted:
      self.progress_loop()
      self.steps.set_current_page(5)
    # From Part2 to Progress
    elif step == 3:
      for widget in [self.partition1, self.partition2, self.partition3,
      self.partition4, self.partition5, self.partition6, self.partition7,
      self.partition8, self.partition9, self.partition10 ]:
        self.show_partitions(widget)
      self.steps.next_page()
    elif step == 4:
      error_msg = ['\n']
      error = 0
      for result in validation.check_mountpoint(self.mountpoint1.get_active_text()):
        if ( result[0] is not '/' ):
           error_msg.append("· <b>mountpoint</b> must start with '/').\n")
           error = 1
      if ( error == 1 ):
        self.show_error(''.join(error_msg))
      else:
        self.steps.next_page()
    elif step == 4:
      self.embedded.destroy()
      self.next.set_sensitive(False)
      self.progress_loop()
      self.steps.next_page()
    # From Progress to Finish
    elif step == 5:
      self.next.set_label('Finish and Reboot')
      self.next.connect('clicked', lambda *x: gtk.main_quit())
      self.back.set_label('Just Finish')
      self.back.connect('clicked', lambda *x: gtk.main_quit())
      self.next.set_sensitive(True)
      self.back.show()
      self.cancel.hide()
      self.steps.next_page()
    
    step = self.steps.get_current_page()
    pre_log('info', 'Step_after = %d' % step)


if __name__ == '__main__':
  w = Wizard('ubuntu')
  w.run()


# vim:ai:et:sts=2:tw=80:sw=2:
