#!/usr/bin/python

# Last modified by Antonio Olmo <aolmo@emergya.info> on 4 august 2005.

import gtk
import subprocess

def call_autoparted():
  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> None
  '''

  mountpoints = {'/'     : '/dev/hda1',
                 'swap'  : '/dev/hda2',
                 '/home' : '/dev/hda3'}
                   
  return mountpoints

def call_gparted(main_window):
  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> None
  '''
  mountpoints = {'/'     : '/dev/hda1',
                 'swap'  : '/dev/hda2',
                 '/home' : '/dev/hda3'}

  # plug/socket implementation (Gparted integration)
  socket = gtk.Socket()
  socket.show()
  main_window.get_widget('embedded').add(socket)
  Wid = str(socket.get_id())

  # TODO: rewrite next block.

  try:
    subprocess.Popen(['/usr/local/bin/gparted', Wid], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
  except:

    try:
      subprocess.Popen(['/usr/bin/gparted', Wid], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
    except:
      pass
  
  if stdin is not '':
    mountpoints = stdin
  
  return mountpoints

# vim:ai:et:sts=2:tw=80:sw=2:

