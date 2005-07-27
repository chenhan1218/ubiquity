#!/usr/bin/python
#

import gtk.glade
import gnome.ui
import gtkmozembed
from pango import FontDescription
from gobject import TYPE_STRING
from os import path, walk
from gettext import bindtextdomain, textdomain, install
from locale import setlocale, LC_ALL
from re import search

# Define locale path
DIR = './locale'

# Define timezones path
DIRNAME = '/usr/share/zoneinfo/'

class FrontendInstaller:

  def __init__(self):
    # set custom language
    self.set_locales()
    
    # load the interface
    self.main_window = gtk.glade.XML('liveinstaller.glade')
    self.show_browser()
    self.show_end()
    
    # set style
    self.installer_style()
    
    # Declare SignalHandler
    self.main_window.signal_autoconnect(GladeHandlers.__dict__)

  def set_locales(self):
    # internationalization config
    bindtextdomain("frontend.py", DIR )
    gtk.glade.bindtextdomain("frontend.py", DIR )
    gtk.glade.textdomain("frontend.py")
    textdomain("frontend.py")
    install("frontend.py", DIR, unicode=1)

  def show_browser(self):
    widget = gtkmozembed.MozEmbed()
    widget.load_url("http://www.gnome.org/")
    widget.get_location()
    self.main_window.get_widget('vbox1').add(widget)
    widget.show()

  def installer_style(self):
    # set screen styles
    self.main_window.get_widget('installing_title').modify_font(FontDescription('Helvetica 30'))
    self.main_window.get_widget('installing_title').modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    self.main_window.get_widget('installing_text').modify_font(FontDescription('Helvetica 16'))
    self.main_window.get_widget('installing_text').modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    
    # set fullscreen mode
    self.main_window.get_widget('live_installer').fullscreen()
    self.main_window.get_widget('live_installer').show()
    
# show and design end page
  def show_start(self):
    welcome = self.main_window.get_widget('welcome')
    welcome.show()
    welcome.set_bg_color(gtk.gdk.color_parse("#087021"))
    welcome.set_logo(gtk.gdk.pixbuf_new_from_file("pixmaps/logo.png"))

  def show_end(self):
    final = self.main_window.get_widget('final')
    final.set_bg_color(gtk.gdk.color_parse("#087021"))
    final.set_logo(gtk.gdk.pixbuf_new_from_file("pixmaps/logo.png"))
    final.modify_font(FontDescription('Helvetica 14'))
    final.modify_fg(gtk.STATE_NORMAL, gtk.gdk.color_parse("#087021"))
    final.show()

  def main(self):
    gtk.main()

  def set_installing_text(self, title, text):
    # change text screens during the installation process
    self.main_window.get_widget('installing_title').set_text(title)
    self.main_window.get_widget('installing_text').set_text(text)
    
#  def get_language(self):
#    return self.main_window.get_widget('language').get_active_text()
#
#  def get_timezone(self):
#    return self.main_window.get_widget('timezone').get_active_text()

  def get_username(self):
    return self.main_window.get_widget('username').get_property('text')

  def get_password(self):
    return self.main_window.get_widget('password').get_property('text')

  def get_hostname(self):
    return self.main_window.get_widget('hostname').get_property('text')

  def set_progress(self, value):
    self.main_window.get_widget('progressbar').set_percentage(value)

# Events Handler
class GladeHandlers:
  def on_frontend_installer_cancel(self):
    gtk.main_quit()
  
  def on_live_installer_delete_event(self, widget):
    gtk.main_quit()

if __name__ == '__main__':
  installer = FrontendInstaller()
  installer.main()
