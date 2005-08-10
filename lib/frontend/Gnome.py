#!/usr/bin/python

import gtk.glade
import gnome.ui
import gtkmozembed
import subprocess
from sys import exit
from pango import FontDescription
from gettext import bindtextdomain, textdomain, install
from locale import setlocale, LC_ALL

from UE.part import call_autoparted, call_gparted
from UE.validation import *


# Define Ubuntu Express global path
PATH = '/usr/share/ubuntu-express'

# Define glade path
GLADEDIR = PATH + '/glade'

# Define locale path
LOCALEDIR = GLADEDIR + '/locale'


class Wizard:
  '''
  Gnome Frontend
  
  This is a wizard interface to interact with the user and the 
  main program. It has some basic methods:
  - set_progress()
  - get_info()
  - get_partitions()
  '''
  
  def __init__(self, distro):
    # set custom language
    self.set_locales(distro[0])
    
    # load the interface
    self.main_window = gtk.glade.XML('%s/liveinstaller.glade' % GLADEDIR)
    
    # declare attributes
    self.distro = distro
    
    self.druid = self.main_window.get_widget('frontend_installer')
    self.druid.set_buttons_sensitive(0,1,1,1)
    
    self.welcome = self.main_window.get_widget('welcome')
    self.step1 = self.main_window.get_widget('step1')
    self.step2 = self.main_window.get_widget('step2')
    self.step3 = self.main_window.get_widget('step3')
    self.final = self.main_window.get_widget('final')
    
    self.live_installer = self.main_window.get_widget('live_installer')
    self.browser_vbox = self.main_window.get_widget('browser_vbox')
    self.embedded = self.main_window.get_widget('embedded')
    
    self.installing_text = self.main_window.get_widget('installing_text')
    self.installing_image = self.main_window.get_widget('installing_image')
    self.installing_title = self.main_window.get_widget('installing_title')
    self.progressbar = self.main_window.get_widget('progressbar')
    self.final_title = self.main_window.get_widget('final_title')
    
    self.user_image = self.main_window.get_widget('user_image')
    self.lock_image = self.main_window.get_widget('lock_image')
    self.host_image = self.main_window.get_widget('host_image')
    self.logo_image = self.main_window.get_widget('logo_image')
    self.logo_image1 = self.main_window.get_widget('logo_image1')
    self.logo_image2 = self.main_window.get_widget('logo_image2')
    self.logo_image3 = self.main_window.get_widget('logo_image3')
    
    
    self.fullname = self.main_window.get_widget('fullname')
    self.username = self.main_window.get_widget('username')
    self.password = self.main_window.get_widget('password')
    self.verified_password = self.main_window.get_widget('verified_password')
    self.hostname = self.main_window.get_widget('hostname')
    
    # set style
    self.installer_style()
    
    # show interface
    self.show_browser()
    
    # FIXME: Temporaly call here the gparted
    data = call_gparted(self.main_window)
    
    # Declare SignalHandler
    self.main_window.signal_autoconnect(self)
    gtk.main()

  def set_locales(self, distro):
    """internationalization config. Use only once."""
    
    final_localedir = LOCALEDIR + '/' + distro
    bindtextdomain("liveinstaller", final_localedir)
    gtk.glade.bindtextdomain("liveinstaller", final_localedir )
    gtk.glade.textdomain("liveinstaller")
    textdomain("liveinstaller")
    install("liveinstaller", final_localedir, unicode=1)

  def show_browser(self):
    """Embed Mozilla widget into Druid."""
    
    widget = gtkmozembed.MozEmbed()
    try:
      widget.load_url("file://" + PATH + '/htmldocs/' + self.distro[0] + '/index.html')
    except:
      widget.load_url("http://www.gnome.org/")
    widget.get_location()
    self.browser_vbox.add(widget)
    widget.show()

  def installer_style(self):
    """Set installer screen styles."""
    
    # set screen styles
    self.welcome.set_property('background', self.distro[1])
    self.step1.set_property('background', self.distro[1])
    self.step2.set_property('background', self.distro[1])
    self.step3.set_property('background', self.distro[1])
    self.final.set_property('background', self.distro[1])
  #  self.installing_title.modify_font(FontDescription('Helvetica 30'))
  #  self.installing_title.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.distro[1]))
  #  self.installing_text.modify_font(FontDescription('Helvetica 12'))
  #  self.installing_text.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.distro[1]))
  #  self.final_title.modify_font(FontDescription('Helvetica 30'))
  #  self.final_title.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse(self.distro[1]))
    
    # set pixmaps
    self.logo_image.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "logo.png"))
    self.logo_image1.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "logo.png"))
    self.logo_image2.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "logo.png"))
    self.logo_image3.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "logo.png"))
    self.user_image.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "users.png"))
    self.lock_image.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "lockscreen_icon.png"))
    self.host_image.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "nameresolution_id.png"))
    self.installing_image.set_from_file("%s/pixmaps/%s/%s" %(GLADEDIR, self.distro[0], "snapshot1.png"))
    
    # set fullscreen mode
    self.live_installer.fullscreen()
    self.live_installer.show()

  def get_info(self):
    '''get_info() -> [hostname, fullname, name, password]

    Get from the Debconf database the information about
    hostname and user. Return a list with those values.
    '''
    #FIXME: We need here a loop. We've to wait until the user press the 'next' button
    info = []
    info.append(self.fullname.get_property('text'))
    info.append(self.username.get_property('text'))
    pass1 = self.password.get_property('text')
    pass2 = self.verified_password.get_property('text')
    if pass1 == pass2:
      #FIXME: This is a crappy check. We need use the lib for that.
      info.append(pass1)
    else:
      #FIXME: If the pass is wrong we must warn about it
      info.append(pass1)
    info.append(self.hostname.get_property('text'))
    # FIXME: self.step not declared yet
    #while self.step < 1:
    #  info = self.info
    
    return info

  def set_progress(self, num, msg="", image=""):
    '''set_progress(num, msg='') -> none

    Put the progress bar in the 'num' percent and if
    there is any value in 'msg', this method print it.
    '''
    """ - Set value attribute to progressbar widget.
        - Modifies Splash Ad Images from distro usage.
        - Modifies Ad texts about distro images. """

    self.progressbar.set_percentage(num/100.0)
    if ( msg != "" ):
      gtk.TextBuffer.set_text(self.installing_text.get_buffer(), msg)
      self.installing_image.set_from_file("%s/pixmaps/%s/%s" % (GLADEDIR, self.distro[0], image))

  def get_partitions(self):
    '''get_partitions() -> dict {'mount point' : 'dev'}

    Get the information to be able to partitioning the disk.
    Partitioning the disk and return a dict with the pairs
    mount point and device.
    At least, there must be 2 partitions: / and swap.
    '''
    #FIXME: We've to put here the autopartitioning stuff
    
    # This is just a example info.
    # We should take that info from the debconf
    # Something like:
    # re = self.db.get('express/mountpoints')
    # for path, dev in re:
    #   mountpoints[path] = dev
    mountpoints = {'/'     : '/dev/hda1',
                   'swap'  : '/dev/hda2',
                   '/home' : '/dev/hda3'}
                   
    #mountpoints = call_autoparted()
    #if mountpoints is None:
    #    mountpoints = call_graphicparted('/usr/bin/gparted')

    return mountpoints

  def on_frontend_installer_cancel(self, widget):
    gtk.main_quit()

  def on_live_installer_delete_event(self, widget):
    raise Signals("on_live_installer_delete_event")

  def on_step1_next(self, widget, data):
    self.info = []
    self.info.append(self.main_window.get_widget('hostname').get_property('text'))
    self.info.append(self.main_window.get_widget('fullname').get_property('text'))
    self.info.append(self.main_window.get_widget('username').get_property('text'))
    pass1 = self.main_window.get_widget('password').get_property('text')
    pass2 = self.main_window.get_widget('verified_password').get_property('text')
    check = check_password(pass1, pass2)
    self.pass_alert = self.main_window.get_widget('pass_alert')
    print check
    if  check == 0:
      self.info.append(pass1)
    elif check == 1:
      self.pass_alert.set_text('Wrong size!')
      self.info.append(pass1)
    elif check == 2:
      self.pass_alert.set_text('The passwords doesn\'t match!')
      self.info.append(pass1)

    self.step = 2


if __name__ == '__main__':
  # Guadalinex HexColor style #087021
  # Ubuntu HexColor style #9F6C49
  w = Wizard(['ubuntu', '#9F6C49'])
  [hostname, fullname, name, password] = w.get_info()
  print '''
  Hostname: %s
  User Full name: %s
  Username: %s
  Password: %s
  Mountpoints : %s
  ''' % (hostname, fullname, name, password, w.get_partitions())

# vim:ai:et:sts=2:tw=80:sw=2:
