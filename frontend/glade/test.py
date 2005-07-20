#!/usr/bin/python

import pygtk # for testing GTK version number
pygtk.require ('2.0')
import gtk
import glade

def main():
 # load the interface
 main_window = gtk.glade.XML('liveinstaller.glade')
 
 main_window.get_widget('bienvenida').show()
 main_window.get_widget('final').show()

 # connect the signals in the interface
 main_window.signal_autoconnect(GladeHandlers.__dict__)

 gtk.main()

class GladeHandlers:

  # Funciones para manejar los eventos de glade
  def on_frontend_installer_cancel(self):
    gtk.main_quit()
 
  def on_live_installer_delete_event(self, widget, event, data=None):
    gtk.main_quit()

if __name__ == '__main__':
 main()
