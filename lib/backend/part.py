#!/usr/bin/python

# Last modified by Antonio Olmo <aolmo@emergya.info> on 5 august 2005.

from subprocess import *

def call_autoparted ():

  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> None
  '''

  result = None

  #   Needed command seemed to be 'autopartition'.
  #   Without args, starts automatically.
  #   If one argument is added, it targets this device
  #   to automatically partition.
  
  [input, output] = popen4 ('autopartition')

  return result

def call_gparted(main_window):
  '''call_autoparted() -> dict {'mount point' : 'dev'}
                       -> None
  '''
  import gtk
  import sys

  # plug/socket implementation (Gparted integration)
  socket = gtk.Socket()
  socket.show()
  main_window.get_widget('embedded').add(socket)
  Wid = str(socket.get_id())

  # TODO: rewrite next block.

  try:
    out = Popen(['/usr/bin/gparted', '-i', Wid], stdin=PIPE, stdout=PIPE,
                close_fds=True).stdout
  except:
    try:
      out = Popen(['/usr/local/bin/gparted', '-i', Wid], stdin=PIPE,
                  stdout=PIPE, close_fds=True).stdout
    except:
      main_window.get_widget('embedded').destroy()
      return None
    
  #FIXME:We need to know how the mounpoints are showed up
  # get the output last line 
  line = out.readlines()[-1].strip()
  
  return mountpoints

# vim:ai:et:sts=2:tw=80:sw=2:

