# -*- coding: utf-8 -*-

# «gtkui» - interfaz de usuario GTK
# 
# Copyright (C) 2005 Junta de Andalucía
# 
# Autor/es (Author/s):
# 
# - Javier Carranza <javier.carranza#interactors._coop>
# - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
# - Antonio Olmo Titos <aolmo#emergya._info>
# 
# Este fichero es parte del instalador en directo de Guadalinex 2005.
# 
# El instalador en directo de Guadalinex 2005 es software libre. Puede
# redistribuirlo y/o modificarlo bajo los términos de la Licencia Pública
# General de GNU según es publicada por la Free Software Foundation, bien de la
# versión 2 de dicha Licencia o bien (según su elección) de cualquier versión
# posterior. 
# 
# El instalador en directo de Guadalinex 2005 se distribuye con la esperanza de
# que sea útil, pero SIN NINGUNA GARANTÍA, incluso sin la garantía MERCANTIL
# implícita o sin garantizar la CONVENIENCIA PARA UN PROPÓSITO PARTICULAR. Véase
# la Licencia Pública General de GNU para más detalles.
# 
# Debería haber recibido una copia de la Licencia Pública General junto con el
# instalador en directo de Guadalinex 2005. Si no ha sido así, escriba a la Free
# Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA 02110-1301
# USA.
# 
# -------------------------------------------------------------------------
# 
# This file is part of Guadalinex 2005 live installer.
# 
# Guadalinex 2005 live installer is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License, or
# at your option) any later version.
# 
# Guadalinex 2005 live installer is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
# 
# You should have received a copy of the GNU General Public License along with
# Guadalinex 2005 live installer; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

""" U{pylint<http://logilab.org/projects/pylint>} mark: -29.27!!! (bad
    indentation and accesses to undefined members) """

# Last modified by A. Olmo on 16 sep 2005.

import pygtk
pygtk.require('2.0')

import gtk.glade
import gtkmozembed
import os
import time, gobject
import glob
from ue.backend.peez2 import *

from gettext import bindtextdomain, textdomain, install

# Next line changed by A. Olmo on 15 sep 2005:
# from ue.fbackend import *
from ue.backend import *

from ue.validation import *
from ue.fmisc import *

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
    self.gparted = False
    self.entries = {
                    'hostname' : 0,
                    'fullname' : 0, 
                    'username' : 0,
                    'password' : 0,
                    'verified_password' : 0
                    }
    # images stuff
    self.install_image = 0
    PIXMAPSDIR = os.path.join(GLADEDIR, 'pixmaps', distro)
    self.total_images   = glob.glob("%s/snapshot*.png" % PIXMAPSDIR)
    self.total_messages = open("%s/messages.txt" % PIXMAPSDIR).readlines()
                        
    # just for testings
    #self.mountpoints = {
    #                    '/'     : '/dev/hda1',
    #                    'swap'  : '/dev/hda2',
    #                    '/home' : '/dev/hda3'
    #                    }
    self.mountpoints = {}
    
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

    for widget in [self.partition1, self.partition2, self.partition3,
    self.partition4, self.partition5, self.partition6, self.partition7,
    self.partition8, self.partition9, self.partition10 ]:
      self.show_partitions(widget)

    # Next lines for debugging purposes only:
#    self.steps.set_current_page (2)

    #self.gparted_loop()

    # Peez2 stuff initialization:
    self.__assistant = None

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

  def check_partitions (self, drive, progress_bar):

    #FIXME: Check if it's possible to run the automatic partition through
    # "peez2". If not, will run the Gparted

    result = False

    result = part.call_autoparted (self.__assistant, drive, progress_bar)

    if not result:
      self.help.hide ()
      self.steps.next_page ()
      self.gparted_loop ()

    return result

  def gparted_loop(self):
    pre_log('info', 'gparted_loop()')
    #self.mountpoints = None
    #self.mountpoints = part.call_gparted(self.embedded)
    self.gparted_pid = part.call_gparted(self.embedded)
    self.next.set_sensitive(True)
    if self.mountpoints is None:
      self.checked_partitions = False
      return False
    else:
      self.checked_partitions = True
      #self.next.set_sensitive(True)
      return True

  def get_partitions(self):
    import re, subprocess

    partition_table_pipe = subprocess.Popen(['/sbin/fdisk', '-l'], stdout=subprocess.PIPE)
    partition_table = partition_table_pipe.communicate()[0]
    regex = re.compile(r'/dev/[a-z]+[0-9]+.*')
    partition = regex.findall(partition_table)

    return partition

  def show_partitions(self, widget):
    partition_list = self.get_partitions()
    treelist = gtk.ListStore(gobject.TYPE_STRING)
    for index in partition_list:
      treelist.append([index.split()[0]])
    widget.set_model(treelist)

  def progress_loop(self):
    pre_log('info', 'progress_loop()')
    self.set_vars_file()
    # Set timeout objects
    self.timeout_images = gobject.timeout_add(60000, self.images_loop)
    path = '/usr/lib/python2.4/site-packages/ue/backend/'
    ex(path + 'format.py')
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'copy.py')
      gobject.io_add_watch(source,gobject.IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    self.pid = os.fork()
    if self.pid == 0:
      source = ret_ex(path + 'config.py')
      gobject.io_add_watch(source,gobject.IO_IN,self.read_stdout)
    os.waitpid(self.pid, 0)
    self.steps.next_page()


  def set_progress(self, msg):
    num , text = get_progress(msg)
    self.progressbar.set_percentage(num/100.0)
    self.progressbar.set_text(text)


  def set_vars_file(self):
    from ue import misc
    vars = {}
    attribs = ['hostname','fullname','username','password']
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


  def show_error(self, msg):
    self.warning_info.set_markup(msg)
    self.warning_image.set_from_icon_name('gtk-dialog-warning', gtk.ICON_SIZE_DIALOG)

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


  def on_list_changed(self, widget):
    if ( widget.get_active_text() is not "" ):
      if ( widget.get_name() in ['partition1', 'mountpoint1'] and
      self.partition1.get_active_text() != "" and
      self.mountpoint1.get_active_text() != "" ):
        self.partition2.show()
        self.mountpoint2.show()
        self.mountpoints[self.partition1.get_active_text()] = self.mountpoint1.get_active_text()
      elif ( widget.get_name() in ['partition2', 'mountpoint2'] and
      self.partition2.get_active_text() != "" and
      self.mountpoint2.get_active_text() != "" ):
        self.partition3.show()
        self.mountpoint3.show()
        self.mountpoints[self.partition2.get_active_text()] = self.mountpoint2.get_active_text()
      elif ( widget.get_name() in ['partition3', 'mountpoint3'] and
      self.partition3.get_active_text() != "" and
      self.mountpoint3.get_active_text() != "" ):
        self.partition4.show()
        self.mountpoint4.show()
        self.mountpoints[self.partition3.get_active_text()] = self.mountpoint3.get_active_text()
      elif ( widget.get_name() in ['partition4', 'mountpoint4'] and
      self.partition4.get_active_text() != "" and
      self.mountpoint4.get_active_text() != "" ):
        self.partition5.show()
        self.mountpoint5.show()
        self.mountpoints[self.partition4.get_active_text()] = self.mountpoint4.get_active_text()
      elif ( widget.get_name() in ['partition5', 'mountpoint5'] and
      self.partition5.get_active_text() != "" and
      self.mountpoint5.get_active_text() != "" ):
        self.partition6.show()
        self.mountpoint6.show()
        self.mountpoints[self.partition5.get_active_text()] = self.mountpoint5.get_active_text()
      elif ( widget.get_name() in ['partition6', 'mountpoint6'] and
      self.partition6.get_active_text() != "" and
      self.mountpoint6.get_active_text() != "" ):
        self.partition7.show()
        self.mountpoint7.show()
        self.mountpoints[self.partition6.get_active_text()] = self.mountpoint6.get_active_text()
      elif ( widget.get_name() in ['partition7', 'mountpoint7'] and
      self.partition7.get_active_text() != "" and
      self.mountpoint7.get_active_text() != "" ):
        self.partition8.show()
        self.mountpoint8.show()
        self.mountpoints[self.partition7.get_active_text()] = self.mountpoint7.get_active_text()
      elif ( widget.get_name() in ['partition8', 'mountpoint8'] and
      self.partition8.get_active_text() != "" and
      self.mountpoint8.get_active_text() != "" ):
        self.partition9.show()
        self.mountpoint9.show()
        self.mountpoints[self.partition8.get_active_text()] = self.mountpoint8.get_active_text()
      elif ( widget.get_name() in ['partition9', 'mountpoint9'] and
      self.partition9.get_active_text() != "" and
      self.mountpoint9.get_active_text() != "" ):
        self.partition10.show()
        self.mountpoint10.show()
        self.mountpoints[self.partition9.get_active_text()] = self.mountpoint9.get_active_text()
      elif ( widget.get_name() in ['partition10', 'mountpoint10'] and
      self.partition10.get_active_text() != "" and
      self.mountpoint10.get_active_text() != "" ):
        self.mountpoints[self.partition10.get_active_text()] = self.mountpoint10.get_active_text()


  def on_key_press (self, widget, event):
    if ( event.keyval == gtk.gdk.keyval_from_name('Return') ) :
      if ( not self.help.get_property('has-focus')
        and not self.back.get_property('has-focus')
        and not self.cancel.get_property('has-focus') ):
        self.next.clicked()


  def on_warning_close(self, widget):
    self.warning_dialog.hide()


  def read_stdout(self, source, condition):
    msg = source.readline()
    if msg.startswith('101'):
      return False
    self.set_progress(msg)
    return True


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
    # From Info to Peez
    elif step == 1:
      from ue import validation
      error_msg = ['\n']
      error = 0
      for result in validation.check_username(self.username.get_property('text')):
        if ( result == 1 ):
          error_msg.append("· <b>username</b> contains dots (they're not allowed).\n")
          error = 1
        elif ( result == 2 ):
          error_msg.append("· <b>username</b> contains uppercase characters (they're not allowed).\n")
          error = 1
        elif ( result == 3 ):
          error_msg.append("· <b>username</b> wrong length (allowed between 3 and 24 chars).\n")
          error = 1
        elif ( result == 4 ):
          error_msg.append("· <b>username</b> contains white spaces (they're not allowed).\n")
          error = 1
        elif ( result in [5, 6] ):
          error_msg.append("· <b>username</b> is already taken or prohibited.\n")
          error = 1
      for result in validation.check_password(self.password.get_property('text'), self.verified_password.get_property('text')):
        if ( result in [1,2] ):
          error_msg.append("· <b>password</b> wrong length (allowed between 4 and 16 chars).\n")
          error = 1
        elif ( result == 3 ):
          error_msg.append("· <b>passwords</b> don't match.\n")
          error = 1
      for result in validation.check_hostname(self.hostname.get_property('text')):
        if ( result == 1 ):
          error_msg.append("· <b>hostname</b> wrong length (allowed between 3 and 18 chars).\n")
          error = 1
        elif ( result == 2 ):
          error_msg.append("· <b>hostname</b> contains white spaces (they're not allowed).\n")
          error = 1
      if ( error == 1 ):
        self.show_error(''.join(error_msg))
      else:
        self.gparted_loop()
        self.browser_vbox.destroy()
        self.help.hide()
        #self.next.set_sensitive(False)
        self.steps.set_current_page(2)
        #self.back.show()
        #if not self.checked_partitions:
        #  if not self.check_partitions():
        #    return          
        #self.steps.next_page()
    # From Peez to Gparted
    elif step == 2:
      self.freespace.set_active (False)
      self.recycle.set_active (False)
      self.manually.set_active (False)

      if self.freespace.get_active ():
        model = self.drives.get_model ()

        if len (model) > 0:
          current = self.drives.get_active ()

          if -1 != current:
            selected_drive = self.__assistant.get_drives () [current]
            self.check_partitions (selected_drive, self.partition_bar)

      elif self.recycle.get_active ():
        pass
      elif self.manually.get_active ():
        pass

      if self.gparted:
        self.next.set_sensitive(False)
        self.gparted_loop()
        self.steps.next_page()
      else:
#        self.progress_loop()
        self.steps.set_current_page(5)

    # From Gparted to Mountpoints
    elif step == 3:
      for widget in [self.partition1, self.partition2, self.partition3,
      self.partition4, self.partition5, self.partition6, self.partition7,
      self.partition8, self.partition9, self.partition10 ]:
        self.show_partitions(widget)
      self.steps.next_page()
    # From Mountpoints to Progress
    elif step == 4:
      #error_msg = ['\n']
      #error = 0
      #for result in validation.check_mountpoint(self.mountpoint1.get_active_text()):
      #  if ( result[0] is not '/' ):
      #     error_msg.append("· <b>mountpoint</b> must start with '/').\n")
      #     error = 1
      #if ( error == 1 ):
      #  self.show_error(''.join(error_msg))
      #else:
      self.steps.next_page()
      self.embedded.destroy()
      self.next.set_sensitive(False)
      os.kill(self.gparted_pid, 9)
      self.progress_loop()
    # From Progress to Finish
    elif step == 5:
      self.next.set_label('Finish and Reboot')
      self.next.connect('clicked', lambda *x: gtk.main_quit())
      self.back.set_label('Just Finish')
      self.back.connect('clicked', lambda *x: gtk.main_quit())
      self.next.set_sensitive(True)
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

  # Public method "on_drives_changed" ________________________________________

  def on_drives_changed (self, foo):

    """ When a different drive is selected, it is necessary to update the
        chekboxes to reflect the set of permited operations on the new
        drive. """

    model = self.drives.get_model ()

    if len (model) > 0:
      current = self.drives.get_active ()

      if -1 != current:
        selected_drive = self.__assistant.get_drives () [current]

        if not selected_drive ['large_enough']:
          self.freespace.set_sensitive (False)
          self.recycle.set_sensitive (False)
          self.manually.set_sensitive (False)
          self.partition_message.set_text ('Not enough space!')
        else:
          self.manually.set_sensitive (True)

          if selected_drive.has_key ('info'):

            if selected_drive ['info'].has_key ('linux'):

              if selected_drive ['info'] ['linux'] >= 2:
                self.recycle.set_sensitive (True)

            if selected_drive ['info'].has_key ('oks'):
              self.freespace.set_sensitive (True)

        # All options are disabled:
        self.freespace.set_active (False)
        self.recycle.set_active (False)
        self.manually.set_active (False)

        # "Next" button is sensitive:
        self.next.set_sensitive (True)

        # Only the first possible option (if any) is enabled:
        if self.freespace.get_property ('sensitive'):
          self.freespace.set_active (True)
        elif self.recycle.get_property ('sensitive'):
          self.recycle.set_active (True)
        elif self.manually.get_property ('sensitive'):
          self.manually.set_active (True)
        else:
          # If no option is possible, "Next" button should not be sensitive:
          self.next.set_sensitive (False)

        # Next lines for debugging purposes only:
        message = str (selected_drive ['info'])
        self.partition_message.set_text (message)

  # Public method "on_steps_switch_page" _____________________________________

  def on_steps_switch_page (self, foo, bar, current):

    """ Only to populate the drives combo box the first time that page #2 is
        shown. """

    if 2 == current and None == self.__assistant:

      # To set a "bussy mouse":
#       b = gtk.Button()
#       watch = gtk.gdk.Cursor (gtk.gdk.WATCH)
#       gdkwin = b.window
#       gdkwin.set_cursor (watch)
#       gtk.gdk.flush ()

      self.__assistant = Peez2 () # debug = False)

      for i in self.__assistant.get_drives ():
        self.drives.append_text ('%s' % i ['label'])

      model = self.drives.get_model ()

      if len (model) > 0:
        self.drives.set_active (0)

  # Public method "on_freespace_group_changed" _______________________________

  def on_freespace_group_changed (self):

    """ Update help message when a different radio button is selected. """

    if self.freespace.get_property ('active'):
      self.partition_message.set_text ('Auto')
    elif self.recycle.get_property ('active'):
      self.partition_message.set_text ('Reusar particiones')
    elif self.manually.get_property ('active'):
      self.partition_message.set_text ('Manual')
    else:
      self.partition_message.set_text ('[Sin selección]')

if __name__ == '__main__':
  w = Wizard('ubuntu')
  w.run()

# vim:ai:et:sts=2:tw=80:sw=2:

