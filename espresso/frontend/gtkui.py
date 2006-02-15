# -*- coding: utf-8 -*-
#
# «gtkui» - interfaz de usuario GTK
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006 Canonical Ltd.
#
# Autores (Authors):
#
# - Javier Carranza <javier.carranza#interactors._coop>
# - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
# - Antonio Olmo Titos <aolmo#emergya._info>
# - Gumer Coronel Pérez <gcoronel#emergya._info>
# - Colin Watson <cjwatson@ubuntu.com>
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
##################################################################################

""" U{pylint<http://logilab.org/projects/pylint>} mark: -28.40!!! (bad
        indentation and accesses to undefined members) """

from sys import stderr
import pygtk
pygtk.require('2.0')

import gobject
import gtk.glade
import os
import time
import glob
import subprocess
import thread
import xml.sax.saxutils
import Queue

from gettext import bindtextdomain, textdomain, install

from espresso import filteredcommand
from espresso.backend import *
from espresso.validation import *
from espresso.misc import *
from espresso.components import usersetup, partman, partman_commit

# Define Espresso global path
PATH = '/usr/share/espresso'

# Define glade path
GLADEDIR = os.path.join(PATH, 'glade')

# Define locale path
LOCALEDIR = "/usr/share/locale"


class Wizard:

    def __init__(self, distro):
        # declare attributes
        self.distro = distro
        self.hostname = ''
        self.fullname = ''
        self.name = ''
        self.manual_choice = None
        self.password = ''
        self.mountpoints = {}
        self.part_labels = {' ' : ' '}
        self.current_page = None
        self.dbfilter = None
        self.progress_min = 0
        self.progress_max = 100
        self.progress_cur = 0

        # To get a "busy mouse":
        self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)

        # useful dicts to manage UI data
        self.entries = {
                                        'hostname' : 0,
                                        'fullname' : 0,
                                        'username' : 0,
                                        'password' : 0,
                                        'verified_password' : 0
                                        }

        # set custom language
        self.set_locales()

        # If automatic partitioning fails, it may be disabled toggling on this variable:
        self.discard_automatic_partitioning = False

        # load the interface
        self.glade = gtk.glade.XML('%s/liveinstaller.glade' % GLADEDIR)

        # get widgets
        for widget in self.glade.get_widget_prefix(""):
            setattr(self, widget.get_name(), widget)

        self.customize_installer()


    def run(self):
        """run the interface."""

        # show interface
        # TODO cjwatson 2005-12-20: Disabled for now because this segfaults in
        # current dapper (https://bugzilla.ubuntu.com/show_bug.cgi?id=20338).
        #self.show_browser()
        self.show_intro()
        self.live_installer.window.set_cursor(None)

        # Resizing labels according to screen resolution
        for widget in self.glade.get_widget_prefix(""):
            if widget.__class__ == gtk.Label and widget.get_name()[-6:-1] == 'label':
                msg = self.resize_text(widget, widget.get_name()[-1:])
                if msg != '':
                    widget.set_markup(msg)

        # Declare SignalHandler
        self.glade.signal_autoconnect(self)

        # Start the interface
        self.current_page = 0
        while self.current_page is not None:
            if self.current_page == 1:
                self.dbfilter = usersetup.UserSetup(self)
            elif self.current_page == 2:
                self.dbfilter = partman.Partman(self)
            else:
                self.dbfilter = None

            if self.dbfilter is not None:
                self.dbfilter.start(auto_process=True)
            gtk.main()

            if self.current_page is not None:
                self.process_step()


    def customize_installer(self):
        """Initial UI setup."""

        PIXMAPSDIR = os.path.join(GLADEDIR, 'pixmaps', self.distro)

        # set pixmaps
        if ( gtk.gdk.get_default_root_window().get_screen().get_width() > 1024 ):
            logo = os.path.join(PIXMAPSDIR, "logo_1280.jpg")
            photo = os.path.join(PIXMAPSDIR, "photo_1280.jpg")
        else:
            logo = os.path.join(PIXMAPSDIR, "logo_1024.jpg")
            photo = os.path.join(PIXMAPSDIR, "photo_1024.jpg")
        if not os.path.exists(logo):
            logo = None
        if not os.path.exists(photo):
            photo = None

        self.logo_image0.set_from_file(logo)
        self.logo_image1.set_from_file(logo)
        self.photo1.set_from_file(photo)
        self.logo_image21.set_from_file(logo)
        self.logo_image22.set_from_file(logo)
        self.logo_image23.set_from_file(logo)

        self.live_installer.show()
        self.live_installer.window.set_cursor(self.watch)

        # set initial bottom bar status
        self.back.hide()
        self.next.set_label('gtk-go-forward')


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

        import gtkmozembed

        widget = gtkmozembed.MozEmbed()
        local_uri = os.path.join(PATH, 'htmldocs/', self.distro, 'index.html')

        # Loading branding if htmldocs/ brand exists. In other hand Ubuntu Project
        #     website is loaded
        try:
            widget.load_url("file://" + local_uri)
        except:
            widget.load_url("http://www.ubuntu.com/")
        widget.get_location()
        self.browser_vbox.add(widget)
        widget.show()


    def show_intro(self):
        """Show some introductory text, if available."""

        intro = os.path.join(PATH, 'htmldocs', self.distro, 'intro.txt')

        if os.path.isfile(intro):
            widget = gtk.Label()
            widget.set_line_wrap(True)
            intro_file = open(intro)
            widget.set_markup(intro_file.read().rstrip('\n'))
            intro_file.close()
            self.browser_vbox.add(widget)
            widget.show()


    def resize_text (self, widget, type):
        """set different text sizes from screen resolution."""

        if widget.__class__ == str :
            msg = widget
        elif isinstance (widget, list):
            msg = '\n'.join (widget)
        else:
            msg = widget.get_text()

        if ( gtk.gdk.get_default_root_window().get_screen().get_width() > 1024 ):
            if ( type in    ['1', '4'] ):
                msg = '<big>' + msg + '</big>'
            elif ( type == '2' ):
                msg = '<big><b>' + msg + '</b></big>'
            elif ( type == '3' ):
                msg = '<span font_desc="22">' + msg + '</span>'
        else:
            if type != '4':
                msg = ''
        return msg

    # Methods

    def gparted_loop(self):
        """call gparted and embed it into glade interface."""

        pre_log('info', 'gparted_loop()')
        # Save pid to kill gparted when install process starts
        self.gparted_subp = part.call_gparted(self.embedded)


    def get_sizes(self):
        """return a dictionary with skeleton { partition : size }
        from /proc/partitions ."""

        # parsing /proc/partitions and getting size data
        size = {}
        for line in open('/proc/partitions'):
            try:
                size[line.split()[3]] = int(line.split()[2])
            except:
                continue
        return size


    def set_size_msg(self, widget):
        """return a string message with size value about
        the partition target by widget argument."""

        # widget is studied in a different manner depending on object type
        if widget.__class__ == str:
            size = float(self.size[widget.split('/')[2]])
        else:
            size = float(self.size[self.part_labels.keys()[self.part_labels.values().index(widget.get_active_text())].split('/')[2]])

        if size > 1024*1024:
            msg = '%.0f Gb' % (size/1024/1024)
        elif size > 1024:
            msg = '%.0f Mb' % (size/1024)
        else:
            msg = '%.0f Kb' % size
        return msg


    def get_default_partition_selection(self, size):
        """return a dictionary with a skeleton { mountpoint : device }
        as a default partition selection. The first partition with max size
        and ext3 fs will be root, and the first partition it finds as swap
        will be marked as the swap selection."""

        # ordering a list from size dict ( { device : size } ), from higher to lower
        size_ordered, selection = [], {}
        for value in size.values():
            if not size_ordered.count(value):
                size_ordered.append(value)
        size_ordered.sort()
        size_ordered.reverse()

        # getting filesystem dict ( { device : fs } )
        device_list = get_filesystems()

        # building an initial mountpoint preselection dict. Assigning only
        # preferred partitions for each mountpoint (the highest ext3 partition
        # to '/' and the first swap partition to swap).
        if len(device_list.items()) != 0:
            root, swap = 0, 0
            for size_selected in size_ordered:
                partition = size.keys()[size.values().index(size_selected)]
                try:
                    fs = device_list['/dev/%s' % partition]
                except:
                    continue
                if swap == 1 and root == 1:
                    break
                elif fs == 'ext3' and size_selected > 1024:
                    if root == 0:
                        selection['/'] = '/dev/%s' % partition
                        root = 1
                elif fs == 'swap':
                    selection['swap'] = '/dev/%s' % partition
                    swap = 1
                else:
                    continue
        return selection


    def show_partitions(self, widget):
        """write all values in this widget (GtkComboBox) from local
        partitions values."""

        from espresso import misc
        import gobject

        # setting GtkComboBox partition values from get_partition return.
        self.partitions = []
        partition_list = get_partitions()
        treelist = gtk.ListStore(gobject.TYPE_STRING)

        # the first element is empty to allow deselect a preselected device
        treelist.append([' '])
        for index in partition_list:
            index = '/dev/' + index
            self.part_labels[index] = misc.part_label(index)
            treelist.append([self.part_labels[index]])
            self.partitions.append(index)
        widget.set_model(treelist)


    def progress_loop(self):
        """prepare, copy and config the system in the core install process."""

        pre_log('info', 'progress_loop()')

        self.install_window.show()

        # Setting Normal cursor
        self.install_window.window.set_cursor(None)

        def wait_thread(queue):
            """wait thread for copy process."""

            cp = copy.Copy(self.mountpoints)
            cp.run(queue)
            queue.put('101')

        # Starting copy process
        queue = Queue.Queue()
        thread.start_new_thread(wait_thread, (queue,))

        # setting progress bar status while copy process is running
        while True:
            try:
                msg = str(queue.get_nowait())
                # copy process is ended when '101' is pushed
                if msg.startswith('101'):
                    break
                self.set_progress(msg)
            except Queue.Empty:
                pass
            # refreshing UI
            if gtk.events_pending():
                while gtk.events_pending():
                    gtk.main_iteration()
            else:
                time.sleep(0.1)

        def wait_thread(queue):
            """wait thread for config process."""

            cf = config.Config(self)
            cf.run(queue)
            queue.put('101')

        # Starting config process
        queue = Queue.Queue()
        thread.start_new_thread(wait_thread, (queue,))

        # setting progress bar status while config process is running
        while True:
            try:
                msg = str(queue.get_nowait())
                # config process is ended when '101' is pushed
                if msg.startswith('101'):
                    break
                self.set_progress(msg)
            except Queue.Empty:
                pass
            # refreshing UI
            if gtk.events_pending():
                while gtk.events_pending():
                    gtk.main_iteration()
            else:
                time.sleep(0.1)

        # umounting self.mountpoints (mountpoints user selection)
        umount = copy.Copy(self.mountpoints)
        umount.umount_target()

        self.install_window.hide()
        self.finished_dialog.show()


    def __reboot(self, *args):
        """reboot the system after installing process."""

        os.system("reboot")
        self.quit()


    def set_progress(self, msg):
        """set values on progress bar widget."""

        num , text = get_progress(msg)
        self.install_progress_bar.set_fraction (num / 100.0)
        self.install_progress_bar.set_text('%d%%' % num)
        self.install_progress_label.set_text(text)


    def show_error(self, msg):
        """show warning message on Identification screen where validation
        doesn't work properly."""

        self.warning_info.set_markup(msg)


    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        gtk.main_quit()


    # Callbacks
    def on_cancel_clicked(self, widget):
        self.warning_dialog.show()


    def on_cancelbutton_clicked(self, widget):
        self.warning_dialog.hide()


    def on_exitbutton_clicked(self, widget):
        self.current_page = None
        self.quit()


    def on_warning_dialog_close(self, widget):
        self.warning_dialog.hide()


    def on_list_changed(self, widget):
        """check if partition/mountpoint pair is filled and show the next pair
        on mountpoint screen. Also size label associated with partition combobox
        is changed dynamically to show the size partition."""

        list_partitions, list_mountpoints, list_sizes, list_partitions_labels, list_mountpoints_labels, list_sizes_labels = [], [], [], [], [], []

        # building widget and name_widget lists to query and modify the original widget status
        for widget_it in self.glade.get_widget('vbox_partitions').get_children()[1:]:
            list_partitions.append(widget_it)
            list_partitions_labels.append(widget_it.get_name())
        for widget_it in self.glade.get_widget('vbox_mountpoints').get_children()[1:]:
            list_mountpoints.append(widget_it)
            list_mountpoints_labels.append(widget_it.get_name())
        for widget_it in self.glade.get_widget('vbox_sizes').get_children()[1:]:
            list_sizes.append(widget_it)
            list_sizes_labels.append(widget_it.get_name())

        # showing new partition and mountpoint widgets if they are needed. Assigning
        #     a new value to gtklabel size.
        if widget.get_active_text() not in ['', None]:
            if widget.__class__ == gtk.ComboBox:
                index = list_partitions_labels.index(widget.get_name())
            elif widget.__class__ == gtk.ComboBoxEntry:
                index = list_mountpoints_labels.index(widget.get_name())

            if list_partitions[index].get_active_text() is not None and \
               list_mountpoints[index].get_active_text() != "" and \
               len(get_partitions()) >= index+1:
                list_partitions[index+1].show()
                list_mountpoints[index+1].show()
                list_sizes[index+1].show()
            if list_partitions[index].get_active_text() == ' ':
                list_sizes[index].set_text('')
            elif list_partitions[index].get_active_text() != None:
                list_sizes[index].set_text(self.set_size_msg(list_partitions[index]))


    def info_loop(self, widget):
        """check if all entries from Identification screen are filled. Callback
        defined in glade file."""

        # each entry is saved as 1 when it's filled and as 0 when it's empty. This
        #     callback is launched when these widgets are modified.
        counter = 0
        if widget.get_text() != '':
            self.entries[widget.get_name()] = 1
        else:
            self.entries[widget.get_name()] = 0

        if len(filter(lambda v: v == 1, self.entries.values())) == 5:
            self.next.set_sensitive(True)

    def read_stdout(self, source, condition):
        """read msgs from queues to set progress on progress bar label.
        '101' message finishes this process returning False."""

        msg = source.readline()
        if msg.startswith('101'):
            print "read_stdout finished"
            return False
        self.set_progress(msg)
        return True


    def on_next_clicked(self, widget):
        """Callback to control the installation process between steps."""

        if self.dbfilter is not None:
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            gtk.main_quit()


    def process_step(self):
        """Process and validate the results of this step."""

        # setting actual step
        step = self.steps.get_current_page()
        pre_log('info', 'Step_before = %d' % step)

        # Welcome
        if step == 0:
            self.next.set_label('gtk-go-forward')
            self.next.set_sensitive(False)
            self.steps.next_page()
        # Identification
        elif step == 1:
            self.process_identification()
        # Automatic partitioning
        elif step == 2:
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == 3:
            self.gparted_to_mountpoints()
        # Mountpoints
        elif step == 4:
            self.mountpoints_to_progress()

        step = self.steps.get_current_page()
        pre_log('info', 'Step_after = %d' % step)


    def process_identification (self):
        """Processing identification step tasks."""

        from espresso import validation
        error_msg = ['\n']
        error = 0

        # Validation stuff

        # checking hostname entry
        for result in validation.check_hostname(self.hostname.get_property('text')):
            if result == 1:
                error_msg.append("· El <b>nombre del equipo</b> tiene tamaño incorrecto (permitido entre 3 y 18 caracteres).\n")
            elif result == 2:
                error_msg.append("· El <b>nombre del equipo</b> contiene espacios en blanco (no están permitidos).\n")
            elif result == 3:
                error_msg.append("· El <b>nombre del equipo</b> contiene carácteres incorrectos (sólo letras y números están permitidos).\n")

        # showing warning message is error is set
        if len(error_msg) > 1:
            self.show_error(self.resize_text(''.join(error_msg), '4'))
        else:
            # showing next step and destroying mozembed widget to
            # release memory
            self.browser_vbox.destroy()
            self.back.show()
            self.steps.next_page()


    def process_autopartitioning(self):
        """Processing automatic partitioning step tasks."""

        while gtk.events_pending ():
            gtk.main_iteration ()

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        if self.manual_choice is None or \
           self.get_autopartition_choice() == self.manual_choice:
            self.gparted_loop()

            self.steps.next_page()

        else:
            # TODO cjwatson 2006-01-10: extract mountpoints from partman
            self.live_installer.hide()

            while gtk.events_pending():
                gtk.main_iteration()

            self.progress_loop()


    def gparted_to_mountpoints(self):
        """Processing gparted to mountpoints step tasks."""

        print >>self.gparted_subp.stdin, "apply"
        gparted_reply = self.gparted_subp.stdout.readline().rstrip('\n')
        if not gparted_reply.startswith('0 '):
            return

        # Shut down gparted
        self.gparted_subp.stdin.close()
        self.gparted_subp.wait()
        self.gparted_subp = None

        # Setting items into partition Comboboxes
        for widget in self.glade.get_widget('vbox_partitions').get_children()[1:]:
            self.show_partitions(widget)
        self.size = self.get_sizes()

        # building mountpoints preselection
        self.default_partition_selection = self.get_default_partition_selection(self.size)

        # Setting a default partition preselection
        if len(self.default_partition_selection.items()) == 0:
            self.next.set_sensitive(False)
        else:
            count = 0
            mp = { 'swap' : 0, '/' : 1 }

            # Setting default preselection values into ComboBox
            # widgets and setting size values. In addition, next row
            # is showed if they're validated.
            for j, k in self.default_partition_selection.items():
                if count == 0:
                    self.partition1.set_active(self.partitions.index(k)+1)
                    self.mountpoint1.set_active(mp[j])
                    self.size1.set_text(self.set_size_msg(k))
                    if ( len(get_partitions()) > 1 ):
                        self.partition2.show()
                        self.mountpoint2.show()
                    count += 1
                elif count == 1:
                    self.partition2.set_active(self.partitions.index(k)+1)
                    self.mountpoint2.set_active(mp[j])
                    self.size2.set_text(self.set_size_msg(k))
                    if ( len(get_partitions()) > 2 ):
                        self.partition3.show()
                        self.mountpoint3.show()
                    count += 1

        self.steps.next_page()


    def mountpoints_to_progress(self):
        """Processing mountpoints to progress step tasks."""

        # Validating self.mountpoints
        error_msg = ['\n']

        # creating self.mountpoints list only if the pairs { device :
        # mountpoint } are selected.
        list = []
        list_partitions = []
        list_mountpoints = []

        # building widget lists to build dev_mnt dict ( { device :
        # mountpoint } )
        for widget in self.glade.get_widget('vbox_partitions').get_children()[1:]:
            if widget.get_active_text() not in [None, ' ']:
                list_partitions.append(widget)
        for widget in self.glade.get_widget('vbox_mountpoints').get_children()[1:]:
            if widget.get_active_text() != "":
                list_mountpoints.append(widget)
        # Only if partitions cout or mountpoints count selected are the same,
        #     dev_mnt is built.
        if len(list_partitions) == len(list_mountpoints):
            dev_mnt = dict( [ (list_partitions[i], list_mountpoints[i]) for i in range(0,len(list_partitions)) ] )

            for dev, mnt in dev_mnt.items():
                if dev.get_active_text() is not None \
                   and mnt.get_active_text() != "":
                    self.mountpoints[self.part_labels.keys()[self.part_labels.values().index(dev.get_active_text())]] = mnt.get_active_text()

        # Processing validation stuff
        elif len(list_partitions) > len(list_mountpoints):
            error_msg.append("· Punto de montaje vacío.\n\n")
        elif len(list_partitions) < len(list_mountpoints):
            error_msg.append("· Partición sin seleccionar.\n\n")

        gvm_automount_drives = '/desktop/gnome/volume_manager/automount_drives'
        gvm_automount_media = '/desktop/gnome/volume_manager/automount_media'
        gconf_dir = 'xml:readwrite:%s' % os.path.expanduser('~/.gconf')
        gconf_previous = {}
        for gconf_key in (gvm_automount_drives, gvm_automount_media):
            subp = subprocess.Popen(['gconftool-2', '--config-source', gconf_dir,
                                                             '--get', gconf_key],
                                                            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            gconf_previous[gconf_key] = subp.communicate()[0].rstrip('\n')
            if gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                                 '--type', 'bool', 'false'])

        if partman_commit.PartmanCommit(self).run_command(auto_process=True) != 0:
                return

        for gconf_key in (gvm_automount_drives, gvm_automount_media):
            if gconf_previous[gconf_key] == '':
                subprocess.call(['gconftool-2', '--unset', gconf_key])
            elif gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                                 '--type', 'bool', gconf_previous[gconf_key]])

        # Checking duplicated devices
        for widget in self.glade.get_widget('vbox_partitions').get_children()[1:]:
            if widget.get_active_text() != None:
                list.append(widget.get_active_text())

        for check in list:
            if list.count(check) > 1:
                error_msg.append("· Dispositivos duplicados.\n\n")
                break

        # Processing more validation stuff
        if len(self.mountpoints) > 0:
            for check in check_mountpoint(self.mountpoints, self.size):
                if check == 1:
                    error_msg.append("· No se encuentra punto de montaje '/'.\n\n")
                elif check == 2:
                    error_msg.append("· Puntos de montaje duplicados.\n\n")
                elif check == 3:
                    try:
                        swap = self.mountpoints.values().index('swap')
                        error_msg.append("· Tamaño insuficiente para la partición '/' (Tamaño mínimo: %d Mb).\n\n" % MINIMAL_PARTITION_SCHEME['root'])
                    except:
                        error_msg.append("· Tamaño insuficiente para la partición '/' (Tamaño mínimo: %d Mb).\n\n" % (MINIMAL_PARTITION_SCHEME['root'] + MINIMAL_PARTITION_SCHEME['swap']*1024))
                elif check == 4:
                    error_msg.append("· Carácteres incorrectos para el punto de montaje.\n\n")

        # showing warning messages
        if len(error_msg) > 1:
            self.msg_error2.set_text(self.resize_text(''.join(error_msg), '4'))
            self.msg_error2.show()
            self.img_error2.show()
        else:
            self.live_installer.hide()

            # refreshing UI
            while gtk.events_pending():
                gtk.main_iteration()

            # Starting installation core process
            self.progress_loop()


    def on_back_clicked(self, widget):
        """Callback to set previous screen."""

        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()

        # Enabling next button
        self.next.set_sensitive(True)
        # Setting actual step
        step = self.steps.get_current_page()

        if step == 2:
            self.back.hide()
        elif step == 3:
            print >>self.gparted_subp.stdin, "undo"
            self.gparted_subp.stdin.close()
            self.gparted_subp.wait()
            self.gparted_subp = None
        elif step == 4:
            self.gparted_loop()

        if step is not 6:
            self.steps.prev_page()

    def on_drives_changed (self, foo):

        """When a different drive is selected, it is necessary to
           update the chekboxes to reflect the set of permited
           operations on the new drive."""

        # TODO cjwatson 2006-01-10: update for partman
        return

        model = self.drives.get_model ()

        if len (model) > 0:
            current = self.drives.get_active ()

            if -1 != current:
                selected_drive = self.__assistant.get_drives () [current]

                if not selected_drive ['large_enough']:
                    self.freespace.set_sensitive (False)
                    self.recycle.set_sensitive (False)
                    self.manually.set_sensitive (False)
                    self.partition_message.set_markup (self.resize_text(
                        '<span>La unidad que ha seleccionado es <b>demasiado ' +
                        'pequeña</b> para instalar el sistema en él.\n\nPor favor, ' +
                        'seleccione un disco duro de más capacidad.</span>', '4'))
                else:
                    self.manually.set_sensitive (True)

                    if not self.__assistant.only_manually ():

                        if not self.discard_automatic_partitioning:

##                             if selected_drive.has_key (''):

                            self.freespace.set_sensitive (True)

                        if selected_drive.has_key ('linux_before'):

                            if selected_drive ['linux_before'] is not None:
                                self.recycle.set_sensitive (True)

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
##                 message = str (selected_drive ['info'])
##                 self.partition_message.set_text (message)

        if selected_drive ['large_enough']:
            self.on_freespace_toggled (self.freespace)
            self.on_recycle_toggled (self.recycle)
            self.on_manually_toggled (self.manually)


    def on_new_size_scale_format_value (self, widget, value):
        # TODO cjwatson 2006-01-09: get minsize/maxsize through to here
        return '%d%%' % value


    # Public method "on_steps_switch_page" _____________________________________
    def on_steps_switch_page (self, foo, bar, current):

        self.current_page = current

        # Populate the drives combo box the first time that page #2 is shown.
        if 2 == current and False:
            # TODO cjwatson 2006-01-10: update for partman

            # To set a "busy mouse":
            self.live_installer.window.set_cursor (self.watch)

##             while gtk.events_pending ():
##                 gtk.main_iteration ()

            # To set a normal mouse again:
            self.live_installer.window.set_cursor (None)

            for i in self.__assistant.get_drives ():
                self.drives.append_text ('%s' % i ['label'])

            model = self.drives.get_model ()

            if len (model) > 0:
                self.drives.set_active (0)


    def on_autopartition_resize_toggled (self, widget):
        """Update autopartitioning screen when the resize button is
        selected."""

        if widget.get_active():
            self.confirmation_checkbutton.show()
            self.confirmation_checkbutton.set_active(False)
            self.next.set_sensitive(False)
            self.new_size_vbox.set_sensitive(True)
        else:
            self.new_size_vbox.set_sensitive(False)


    def on_autopartition_manual_toggled (self, widget):
        """Update autopartitioning screen when the manual button is
        selected."""

        if widget.get_active():
            self.confirmation_checkbutton.hide()
            self.confirmation_checkbutton.set_active(False)
            self.next.set_sensitive(True)


    def on_autopartition_button_toggled (self, widget):
        """Update autopartitioning screen when any button other than
        resize or manual is selected."""

        if widget.get_active():
            self.confirmation_checkbutton.show()
            self.confirmation_checkbutton.set_active(False)
            self.next.set_sensitive(False)


    def on_confirmation_checkbutton_toggled (self, widget):

        """Change 'active' property of 'next' button when this check
        box is changed."""

        if self.confirmation_checkbutton.get_active ():
            self.next.set_sensitive (True)
        else:
            self.next.set_sensitive (False)

##     def on_abort_dialog_close (self, widget):

##         """ Disable automatic partitioning and reset partitioning method step. """

##         stderr.write ('\non_abort_dialog_close.\n\n')

##         self.discard_automatic_partitioning = True
##         self.on_drives_changed (None)

    def on_abort_ok_button_clicked (self, widget):

        """ Close this dialog. """

        self.abort_dialog.hide ()


    # Callbacks provided to components.

    def watch_debconf_fd (self, from_debconf, process_input):
        gobject.io_add_watch(from_debconf,
                                                 gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                                                 self.watch_debconf_fd_helper, process_input)


    def watch_debconf_fd_helper (self, source, cb_condition, callback):
        debconf_condition = 0
        if (cb_condition & gobject.IO_IN) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_IN
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)


    def debconf_progress_start (self, progress_min, progress_max, progress_title):
        self.debconf_progress_dialog.set_transient_for(self.live_installer)
        self.debconf_progress_dialog.set_title(progress_title)
        self.progress_title.set_markup(
            '<b>' + xml.sax.saxutils.escape(progress_title) + '</b>')
        self.progress_bar.set_fraction(0)
        self.progress_bar.set_text('0%')
        self.progress_min = progress_min
        self.progress_max = progress_max
        self.progress_cur = progress_min
        self.debconf_progress_dialog.show()

    def debconf_progress_set (self, progress_val):
        self.progress_cur = progress_val
        fraction = (float(self.progress_cur - self.progress_min) /
                                (self.progress_max - self.progress_min))
        self.progress_bar.set_fraction(fraction)
        self.progress_bar.set_text('%s%%' % int(fraction * 100))

    def debconf_progress_step (self, progress_inc):
        self.debconf_progress_set(self.progress_cur + progress_inc)

    def debconf_progress_info (self, progress_info):
        self.progress_info.set_markup(
            '<i>' + xml.sax.saxutils.escape(progress_info) + '</i>')

    def debconf_progress_stop (self):
        self.debconf_progress_dialog.hide()


    def debconffilter_done (self, dbfilter):
        # TODO cjwatson 2006-02-10: handle dbfilter.status
        if dbfilter == self.dbfilter:
            gtk.main_quit()


    def set_autopartition_choices (self, choices, resize_choice, manual_choice):
        for child in self.autopartition_vbox.get_children():
            self.autopartition_vbox.remove(child)

        self.manual_choice = manual_choice
        firstbutton = None
        for choice in choices:
            button = gtk.RadioButton(firstbutton, choice, False)
            if firstbutton is None:
                firstbutton = button
            self.autopartition_vbox.add(button)
            if choice == resize_choice:
                self.on_autopartition_resize_toggled(button)
                button.connect('toggled', self.on_autopartition_resize_toggled)
            elif choice == manual_choice:
                self.on_autopartition_manual_toggled(button)
                button.connect('toggled', self.on_autopartition_manual_toggled)
            else:
                self.on_autopartition_button_toggled(button)
                button.connect('toggled', self.on_autopartition_button_toggled)
        if firstbutton is not None:
            firstbutton.set_active(True)

        self.autopartition_vbox.show_all()


    def get_autopartition_choice (self):
        for button in self.autopartition_vbox.get_children():
            if button.get_active():
                return button.get_label()


    def set_autopartition_resize_min_percent (self, min_percent):
        self.new_size_scale.set_range(min_percent, 100)


    def get_autopartition_resize_percent (self):
        return self.new_size_scale.get_value()


    def get_hostname (self):
        return self.hostname


    def get_mountpoints (self):
        return dict(self.mountpoints)


    def confirm_partitioning_dialog (self, title, description):
        dialog = gtk.MessageDialog(self.live_installer, gtk.DIALOG_MODAL,
                                                             gtk.MESSAGE_QUESTION, gtk.BUTTONS_YES_NO, title)
        dialog.format_secondary_text(description)
        response = dialog.run()
        dialog.hide()
        if response == gtk.RESPONSE_YES:
            return True
        else:
            return False


    def error_dialog (self, msg):
        # TODO: cancel button as well if capb backup
        dialog = gtk.MessageDialog(self.live_installer, gtk.DIALOG_MODAL,
                                                             gtk.MESSAGE_ERROR, gtk.BUTTONS_OK, msg)
        dialog.run()
        dialog.hide()


    def refresh (self):
        while gtk.events_pending():
            gtk.main_iteration()


    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        gtk.main()


    # Return control to the next level up.
    def quit_main_loop (self):
        gtk.main_quit()


if __name__ == '__main__':
    w = Wizard('ubuntu')
    w.run()

