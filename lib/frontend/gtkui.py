#!/usr/bin/python

import pygtk
pygtk.require('2.0')

import gtk.glade
import gtkmozembed
import os

from gettext import bindtextdomain, textdomain, install

from ue.backend.part import call_autoparted, call_gparted
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
    self.info = []
    self.gparted = False
    PIXMAPSDIR = os.path.join(GLADEDIR, distro)
    
    # set custom language
    self.set_locales()
    
    # load the interface
    self.glade = gtk.glade.XML('%s/liveinstaller.glade' % GLADEDIR)
    
    # get widgets
    for widget in glade.get_widget_prefix(""):
      setattr(self, widget, self.glade.get_widget(widget))
     
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
    self.mountpoints = call_autoparted()
    if self.mountpoints is None:
      self.mountpoints = call_gparted(self.glade)
    if self.mountpoints is None:
      self.checked_partitions = False
      return False
    else:
      self.checked_partitions = True
      return True


  def info_loop(self):
    pass


  def progress_loop(self):
    # Use get_progress(str) -> [NUM, MSG]
    pass

  def set_vars_file(self):
    from ue import misc
    vars = {}
    attribs = ['hostname','fullname','name','password','mountpoints']
    for var in attribs:
      vars[var] = getattr(self, var)
    misc.set_var(vars)
 

  # Callbacks
  def on_cancel_clicked(self, widget):
    gtk.main_quit()

  def on_live_installer_delete_event(self, widget):
    gtk.main_quit()

  def on_next_clicked(self, widget):
    step = self.steps.get_current_page()
    if step == 0:
      self.next.set_label('gtk-go-forward')
      self.help.show()
    elif step == 1:
      self.browser_vbox.destroy()
      if not self.checked_partitions:
        self.check_partitions()
      self.info_loop()
      self.back.show()
    elif step == 2:
      self.embedded.destroy()
      self.back.hide()
      self.help.hide()
      self.set_vars_file()
    elif step == 3:
      self.embedded.destroy()
      self.back.hide()
      self.help.hide()
      self.set_vars_file()
      self.progress_loop()
    elif step == 4:
      self.next.set_label('Finish and Reboot')
      self.next.connect('clicked', lambda *x: gtk.main_quit())
      self.back.set_label('Just Finish')
      self.back.connect('clicked', lambda *x: gtk.main_quit())
      self.back.show()
      self.cancel.hide()
      
    if step in [0, 1, 3, 4]:
      self.steps.next_page()
    elif step == 2 and self.gparted:
      self.steps.next_page()
    elif step == 2 and not self.gparted:
      self.steps.set_current_page(4)

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
