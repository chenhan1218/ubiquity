#!/usr/bin/python

import gtk
import subprocess

def call_autoparted():
  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> null
  '''

  mountpoints = {'/'     : '/dev/hda1',
                 'swap'  : '/dev/hda2',
                 '/home' : '/dev/hda3'}
                   
  return mountpoints

def call_gparted(main_window):
  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> null
  '''
  # plug/socket implementation (Gparted integration)
  socket = gtk.Socket()
  socket.show()
  main_window.get_widget('embedded').add(socket)
  Wid = str(socket.get_id())
  subprocess.Popen(['/usr/local/bin/gparted', Wid], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
  

  mountpoints = {'/'     : '/dev/hda1',
                 'swap'  : '/dev/hda2',
                 '/home' : '/dev/hda3'}
                   
  return mountpoints

# vim:ai:et:sts=2:tw=80:sw=2:

