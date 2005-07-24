#!/usr/bin/python

#import pygtk # for testing GTK version number
#pygtk.require ('2.0')
import gtk.glade
import gettext
import gnome.ui

DIR = './locale'

gettext.bindtextdomain("test.py", DIR )
gtk.glade.bindtextdomain("test.py", DIR )
gtk.glade.textdomain("test.py")
gettext.textdomain("test.py")
gettext.install("test.py",DIR,unicode=1)

def main():
 # load the interface
 main_window = gtk.glade.XML('liveinstaller.glade')
 
 main_window.get_widget('welcome').show_all()
 main_window.get_widget('final').show_all()

 main_window.get_widget('welcome').set_bg_color(gtk.gdk.color_parse("#087021"))
 main_window.get_widget('welcome').set_logo(gtk.gdk.pixbuf_new_from_file("pixmaps/logo.png"))
 main_window.get_widget('final').set_bg_color(gtk.gdk.color_parse("#087021"))
 main_window.get_widget('final').set_logo(gtk.gdk.pixbuf_new_from_file("pixmaps/logo.png"))

 main_window.signal_autoconnect(GladeHandlers.__dict__)

 gtk.main()

class GladeHandlers:

  # Funciones para manejar los eventos de glade
  def on_frontend_installer_cancel(self):
    gtk.main_quit()
 
  def on_live_installer_delete_event(self, widget):
    gtk.main_quit()

if __name__ == '__main__':
 main()
