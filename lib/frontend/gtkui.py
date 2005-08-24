#!/usr/bin/python

import pygtk
pygtk.require('2.0')

import gtk.glade
import gtkmozembed
import os
import time, gobject
import glob

from gettext import bindtextdomain, textdomain, install

from ue.backend import *
from ue.validation import *
from ue.misc import *

# Define Ubuntu Express global path
PATH = '/usr/share/ubuntu-express'

# Define glade path
GLADEDIR = os.path.join(PATH, 'glade')

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
    # just for testings
    self.mountpoints = {'/'     : '/dev/hda1',
                        'swap'  : '/dev/hda2',
                        '/home' : '/dev/hda3'}
    self.gparted = False
    PIXMAPSDIR = os.path.join(GLADEDIR, 'pixmaps', distro)
    self.entries = {'hostname' : 0, 'fullname' : 0, 'username' : 0, 'password' : 0, 'verified_password' : 0}
    self.install_image = 0
    self.total_images=glob.glob("%s/snapshot*.png" % PIXMAPSDIR)
    self.total_messages=open("%s/messages.txt" % PIXMAPSDIR).readlines()
    
    # Start a timer to see how long the user runs this program
    self.start = time.time()
    
    
    # set custom language
    self.set_locales()
    
    # load the interface
    self.glade = gtk.glade.XML('%s/liveinstaller.glade' % GLADEDIR)
    
    # get widgets
    for widget in self.glade.get_widget_prefix(""):
      setattr(self, widget.get_name(), widget)
     
    # set initial status
    self.back.hide()
    self.help.hide()
    self.next.set_label('gtk-media-next')
    
    # set pixmaps
    self.logo_image.set_from_file(os.path.join(PIXMAPSDIR, "logo.png"))
    self.logo_image1.set_from_file(os.path.join(PIXMAPSDIR, "logo.png"))
    self.logo_image2.set_from_file(os.path.join(PIXMAPSDIR, "logo.png"))
    self.logo_image3.set_from_file(os.path.join(PIXMAPSDIR, "logo.png"))
    self.logo_image4.set_from_file(os.path.join(PIXMAPSDIR, "logo.png"))
    self.user_image.set_from_file(os.path.join(PIXMAPSDIR, "users.png"))
    self.lock_image.set_from_file(os.path.join(PIXMAPSDIR, "lockscreen_icon.png"))
    self.host_image.set_from_file(os.path.join(PIXMAPSDIR, "nameresolution_id.png"))
    self.installing_image.set_from_file(os.path.join(PIXMAPSDIR, "snapshot1.png"))
    
    # set fullscreen mode
    self.live_installer.fullscreen()
    self.live_installer.show()


  def run(self):
    # show interface
    self.show_browser()
    
    # Declare SignalHandler
    self.glade.signal_autoconnect(self)
    gtk.main()

  def set_locales(self):
    """internationalization config. Use only once."""
    
    domain = self.distro + '-installer'
    bindtextdomain(domain, LOCALEDIR)
    gtk.glade.bindtextdomain(domain, LOCALEDIR )
    gtk.glade.textdomain(domain)
    textdomain(domain)
    install(domain, LOCALEDIR, unicode=1)

  def show_browser(self):
    """Embed Mozilla widget into a vbox."""
    
    widget = gtkmozembed.MozEmbed()
    local_uri = os.path.join(PATH, 'htmldocs/', self.distro, 'index.html')
    try:
      widget.load_url("file://" + local_uri)
    except:
      widget.load_url("http://www.ubuntulinux.org/")
    widget.get_location()
    self.browser_vbox.add(widget)
    widget.show()

  # Methods
  def check_partitions(self):
    #FIXME: Check if it's possible to run the partman-auto
    # if not, will run the Gparted
    
    #self.mountpoints = {'/'     : '/dev/hda1',
    #                    'swap'  : '/dev/hda2',
    #                    '/home' : '/dev/hda3'}
                   
    self.mountpoints = None
    self.mountpoints = part.call_autoparted()
    if self.mountpoints is None:
      self.help.hide()
      self.steps.next_page()
      self.gparted_loop()
      return False
    return True


  def gparted_loop(self):
    pre_log('info', 'gparted_loop()')
    self.mountpoints = None
    self.mountpoints = part.call_gparted(self.embedded)
    if self.mountpoints is None:
      self.checked_partitions = False
      return False
    else:
      self.checked_partitions = True
      return True


  def progress_loop(self):
    pre_log('info', 'progress_loop()')
    path = os.path.dirname(os.path.realpath(os.curdir))
    path = os.path.join(path, 'backend')
    ex(path + 'format.py')
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'copy.py')
      io_add_watch(source,IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'config.py')
      io_add_watch(source,IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    
  def set_progress(self, msg):
    num , text = get_progress(msg)
    self.progressbar.set_percentage(num/100.0)
    self.progressbar.set_text(text)
    
  def read_stdout(self, source, condition):
    msg = source.readline()
    if msg.startswith('Exit'):
      return False
    set_progress(msg)
    return True

  def set_vars_file(self):
    from ue import misc
    vars = {}
    attribs = ['hostname','fullname','name','password']
    try:
      for name in attribs:
        var = getattr(self, name)
        vars[name] = var.get_text()
      vars['mountpoints'] = self.mountpoints
    except:
      pre_log('error', 'Missed attrib to write to /tmp/vars')
      self.quit()      
    else:
      misc.set_var(vars)

  def quit(self):
    if self.pid:
      os.kill(self.pid, 9)
    # Tell the user how much time they used
    post_log('info', 'You wasted %.2f seconds with this installation' %
                      (time.time()-self.start))
    
    gtk.main_quit()
 

  # Callbacks
  def on_cancel_clicked(self, widget):
    self.quit()

  def on_live_installer_delete_event(self, widget):
    self.quit()

  def info_loop(self, widget):
    counter = 0
    if (widget.get_text() is not '' ):
      self.entries[widget.get_name()] = 1
    else:
      self.entries[widget.get_name()] = 0
    for k, v in self.entries.items():
      if ( v == 1 ):
        counter+=1
    if (counter == 5 ):
      self.next.set_sensitive(True)

  def images_loop(self):
    self.install_image+=1
    step = self.install_image % len(self.total_images) -1
    self.installing_image.set_from_file(self.total_images[step])
    self.installing_text.get_buffer().set_text(self.total_messages[step])
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
      self.browser_vbox.destroy()
      self.back.hide()
      self.help.hide()
      self.gparted_loop()
      self.steps.set_current_page(3)
      #self.back.show()
      #if not self.checked_partitions:
      #  if not self.check_partitions():
      #    return          
      #self.steps.next_page()
    # From Part1 to part2
    elif step == 2 and self.gparted:
      self.back.hide()
      self.help.hide()
      self.steps.next_page()
      self.gparted_loop()
    # From Part1 to Progress
    elif step == 2 and not self.gparted:
      self.back.hide()
      self.help.hide()
      self.set_vars_file()
      self.progress_loop()
      # Set timeout objects
      self.timeout_images = gobject.timeout_add(60000, self.images_loop)
      self.steps.set_current_page(4)
    # From Part2 to Progress
    elif step == 3:
      self.embedded.destroy()
      self.back.hide()
      self.help.hide()
      self.set_vars_file()
      self.progress_loop()
      # Set timeout objects
      self.timeout_images = gobject.timeout_add(60000, self.images_loop)
      self.steps.next_page()
    # From Progress to Finish
    elif step == 4:
      self.next.set_label('Finish and Reboot')
      self.next.connect('clicked', lambda *x: gtk.main_quit())
      self.back.set_label('Just Finish')
      self.back.connect('clicked', lambda *x: gtk.main_quit())
      self.back.show()
      self.cancel.hide()
      self.steps.next_page()
      
    step = self.steps.get_current_page()
    pre_log('info', 'Step_after = %d' % step)

  def on_back_clicked(self, widget):
    step = self.steps.get_current_page()
    if step == 2:
      self.back.hide()
    
    if step is not 5:
      self.steps.prev_page()


  def on_gparted_clicked(self, widget):
    if self.gparted:
      self.gparted = False
    else:
      self.gparted = True


if __name__ == '__main__':
  w = Wizard('ubuntu')
  w.run()


# vim:ai:et:sts=2:tw=80:sw=2:
