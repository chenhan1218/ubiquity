#!/usr/bin/python
#

import gtk.glade
import gnome.ui
import gtkmozembed
import subprocess
from sys import exit, path
#from posix import system
from pango import FontDescription
from gettext import bindtextdomain, textdomain, install
from locale import setlocale, LC_ALL

PATH = path[0]

# Define glade path
GLADEDIR = PATH + '/glade'

# Define locale path
LOCALEDIR = GLADEDIR + '/locale'

class Wizard:
  '''
  This is a wizard interface to interact with the user and the 
  main program. It has some basic methods:
  - set_progress()
  - get_info()
  - get_partitions()
  '''
  def __init__(self):
    # set custom language
    self.set_locales()
    
    # load the interface
    self.main_window = gtk.glade.XML('%s/liveinstaller.glade' % GLADEDIR)
    self.show_browser()
    self.show_end()
    
    # set style
    self.installer_style()
    
    # plug/socket implementation (Gparted integration)
    socket = gtk.Socket()
    socket.show()
    self.main_window.get_widget('embedded').add(socket)
    Wid = str(socket.get_id())
    subprocess.Popen(['/usr/bin/gparted', Wid], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    
    # Declare SignalHandler
    self.main_window.signal_autoconnect(self)
    gtk.main()

  def set_locales(self):
    """internationalization config. Use only once."""
    
    bindtextdomain("Gnome.py", LOCALEDIR )
    gtk.glade.bindtextdomain("Gnome.py", LOCALEDIR )
    gtk.glade.textdomain("Gnome.py")
    textdomain("Gnome.py")
    install("Gnome.py", LOCALEDIR, unicode=1)

  def show_browser(self):
    """Embed Mozilla widget into Druid."""
    
    widget = gtkmozembed.MozEmbed()
    widget.load_url("http://www.gnome.org/")
    widget.get_location()
    self.main_window.get_widget('browser').add(widget)
    widget.show()

  def installer_style(self):
    """Set installer screen styles."""
    
    # set screen styles
    self.main_window.get_widget('installing_title').modify_font(FontDescription('Helvetica 30'))
    self.main_window.get_widget('installing_title').modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    self.main_window.get_widget('installing_text').modify_font(FontDescription('Helvetica 12'))
    self.main_window.get_widget('installing_text').modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    
    # set fullscreen mode
    self.main_window.get_widget('live_installer').fullscreen()
    self.main_window.get_widget('live_installer').show()

  def show_end(self):
    """show and design end page."""
    
    final = self.main_window.get_widget('final')
    final.set_bg_color(gtk.gdk.color_parse("#087021"))
    final.set_logo(gtk.gdk.pixbuf_new_from_file("%s/pixmaps/logo.png" % GLADEDIR))
    final.modify_font(FontDescription('Helvetica 14'))
    final.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    final.show()

  def get_info(self):
    '''get_info() -> [hostname, fullname, name, password]

    Get from the Debconf database the information about
    hostname and user. Return a list with those values.
    '''
    #FIXME: We need here a loop. We've to wait until the user press the 'next' button
    info = []
    #info.append(self.main_window.get_widget('fullname').get_property('text'))
    info.append(self.main_window.get_widget('username').get_property('text'))
    pass1 = self.main_window.get_widget('password').get_property('text')
    pass2 = self.main_window.get_widget('verify_password').get_property('text')
    if pass1 == pass2:
      #FIXME: This is a crappy check. We need use the lib for that.
      info.append(pass1)
    else:
      #FIXME: If the pass is wrong we must warn about it
      info.append(pass1)
    info.append(self.main_window.get_widget('hostname').get_property('text'))
    return info

  def set_progress(self, num, msg="", image=""):
    '''set_progress(num, msg='') -> none

    Put the progress bar in the 'num' percent and if
    there is any value in 'msg', this method print it.
    '''
    """ - Set value attribute to progressbar widget.
        - Modifies Splash Ad Images from distro usage.
        - Modifies Ad texts about distro images. """

    self.main_window.get_widget('progressbar').set_percentage(num/100.0)
    #self.main_window.get_widget('progressbar').set_pulse_step(num/100.0)
    if ( msg != "" ):
      gtk.TextBuffer.set_text(self.main_window.get_widget('installing_text').get_buffer(), msg)
      self.main_window.get_widget('installing_image').set_from_file("%s/pixmaps/%s" % (GLADEDIR, image))

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
    return mountpoints

  def on_frontend_installer_cancel(self, widget):
    gtk.main_quit()

  def on_live_installer_delete_event(self, widget):
    raise Signals("on_live_installer_delete_event")

if __name__ == '__main__':
  w = Wizard()
  hostname, fullname, name, password = w.get_info()
  print '''
  Hostname: %s
  User Full name: %s
  Username: %s
  Password: %s
  Mountpoints : %s
  ''' % (hostname, fullname, name, password, w.get_partitions())

# vim:ai:et:sts=2:tw=80:sw=2:
