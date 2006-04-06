# -*- coding: utf8 -*-
#
# Copyright (C) 2006 Canonical Ltd.
#
# Espresso live installer is free software; you can redistribute it
# and/or modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
#
# Espresso live installer is distributed in the hope that it will be
# useful, but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General
# Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Guadalinex 2005 live installer; if not, write to the Free Software Foundation,
# Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
#
# Author:
#   Jonathan Riddell <jriddell@ubuntu.com>

print "importing kde-ui"

import sys
from qt import *
from kdeui import *
from kdecore import *
#import kdedesigner
from espresso.frontend.liveinstaller import EspressoUI

import os
import time
import datetime
import glob
import subprocess
import thread
import xml.sax.saxutils

import gettext

from espresso import filteredcommand, validation
from espresso.misc import *
from espresso.settings import *
from espresso.components import language, kbd_chooser, timezone, usersetup, \
                                partman, partman_commit, summary, install
import espresso.tz
import espresso.progressposition

# Define Espresso global path
PATH = '/usr/share/espresso'

# Define glade path
GLADEDIR = os.path.join(PATH, 'glade')

# Define locale path
LOCALEDIR = "/usr/share/locale"

BREADCRUMB_STEPS = {
    "stepWelcome": 1,
    "stepLanguage": 2,
    "stepLocation": 3,
    "stepKeyboardConf": 4,
    "stepUserInfo": 5,
    "stepPartDisk": 6,
    "stepPartAuto": 6,
    "stepPartAdvanced": 6,
    "stepPartMountpoints": 6,
    "stepReady": 7
}
BREADCRUMB_MAX_STEP = 7

WIDGET_STACK_STEPS = {
    "stepWelcome": 0,
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "stepUserInfo": 4,
    "stepPartDisk": 5,
    "stepPartAuto": 6,
    "stepPartAdvanced": 7,
    "stepPartMountpoints": 8,
    "stepReady": 9
}

class MyEspressoUI(EspressoUI):
    
    def setWizard(self, wizardRef):
        self.wizard = wizardRef

    def closeEvent(self, event):
        print "closing!"
        self.wizard.on_cancel_clicked3()

class Wizard:

    def __init__(self, distro):
        print "  init(distro)"
        about=KAboutData("kubuntu-espresso","Kubuntu Espresso","0.1","Live CD Installer for Kubuntu",KAboutData.License_GPL,"(c) 2006 Canonical Ltd", "http://wiki.kubuntu.org/KubuntuEspresso", "jriddell@ubuntu.com")
        about.addAuthor("Jonathan Riddell", None,"jriddell@ubuntu.com")
        KCmdLineArgs.init(["./installer"],about)
        
        self.app = KApplication()
        
        #self.userinterface = EspressoUI(None, "Espresso")
        self.userinterface = MyEspressoUI(None, "Espresso")
        self.userinterface.setWizard(self)
        self.app.setMainWidget(self.userinterface)
        self.userinterface.show()
        
        # declare attributes
        self.distro = distro
        self.current_keyboard = None
        self.hostname = ''
        self.fullname = ''
        self.name = ''
        self.manual_choice = None
        self.password = ''
        self.mountpoint_widgets = []
        self.size_widgets = []
        self.partition_widgets = []
        self.format_widgets = []
        self.mountpoint_choices = ['swap', '/', '/home',
                                   '/boot', '/usr', '/var']
        self.partition_choices = []
        self.mountpoints = {}
        self.part_labels = {' ' : ' '}
        self.part_devices = {' ' : ' '}
        self.current_page = None
        self.dbfilter = None
        self.locale = None
        self.progress_position = espresso.progressposition.ProgressPosition()
        self.progress_cancelled = False
        self.previous_partitioning_page = None
        self.installing = False
        self.returncode = 0
        self.translations = get_translations()

        self.debconf_callbacks = {}    # array to keep callback functions needed by debconf file descriptors
    
        # To get a "busy mouse":
        #FIXME self.watch = gtk.gdk.Cursor(gtk.gdk.WATCH)
    
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
        
        self.customize_installer()
        
        self.autopartition_vbox = QVBoxLayout(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup = QButtonGroup(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup_texts = {}
        
        self.qtparted_vbox = QVBoxLayout(self.userinterface.qtparted_frame)
        self.embed = QXEmbed(self.userinterface.qtparted_frame, "embed")
        self.embed.setProtocol(QXEmbed.XPLAIN)

    def run(self):
        """run the interface."""
        print "  run()"
        """
        if os.getuid() != 0:
                print "uid != 0"
                title = ('This installer must be run with administrative '
                        'privileges, and cannot continue without them.')
                KMessageBox.error(self.userinterface, title, "Must run as root")
                sys.exit(1)
        """
        # show interface
        # TODO cjwatson 2005-12-20: Disabled for now because this segfaults in
        # current dapper (https://bugzilla.ubuntu.com/show_bug.cgi?id=20338).
        #self.show_browser()
        self.show_intro()
        
        #FIXME self.live_installer.window.set_cursor(None)
    
        # Declare SignalHandler
        #FIXME self.glade.signal_autoconnect(self)
        self.app.connect(self.userinterface.nextButton, SIGNAL("clicked()"), self.on_next_clicked)
        self.app.connect(self.userinterface.backButton, SIGNAL("clicked()"), self.on_back_clicked)
        self.app.connect(self.userinterface.cancelButton, SIGNAL("clicked()"), self.on_cancel_clicked3)
        self.app.connect(self.userinterface.widgetStack, SIGNAL("aboutToShow(int)"), self.on_steps_switch_page)
        self.app.connect(self.userinterface.keyboardlistview, SIGNAL("selectionChanged()"), self.on_keyboard_selected)
        
    
        # Start the interface
        self.set_current_page(0)
        while self.current_page is not None:
            self.backup = False
            current_name = self.step_name(self.current_page)
            old_dbfilter = self.dbfilter
            if current_name == "stepLanguage":
                print "stepLanguage"
                self.dbfilter = language.Language(self)
            elif current_name == "stepLocation":
                self.dbfilter = timezone.Timezone(self)
            elif current_name == "stepKeyboardConf":
                self.dbfilter = kbd_chooser.KbdChooser(self)
            elif current_name == "stepUserInfo":
                print "stepUserInfo"
                self.dbfilter = usersetup.UserSetup(self)
            elif current_name in ("stepPartDisk", "stepPartAuto"):
                if isinstance(self.dbfilter, partman.Partman):
                    pre_log('info', 'reusing running partman')
                else:
                    self.dbfilter = partman.Partman(self)
            elif current_name == "stepReady":
                self.dbfilter = summary.Summary(self)
            else:
                print "no filter"
                self.dbfilter = None
    
            print "checking if dbfilter in not None"
            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                print "dbfilter.start"
                self.dbfilter.start(auto_process=True)
            print "mainloop"
            self.app.exec_loop()
            print "end mainloop"
    
            if self.installing:
                self.progress_loop()
            elif self.current_page is not None and not self.backup:
                print "process_step"
                self.process_step()
            print "end of while"
            self.app.processEvents(1)

	return self.returncode
    
    def customize_installer(self):
        """Customizing logo and images."""
        # images stuff
        print "  customize_installer()"
        """
        self.install_image = 0
        PIXMAPSDIR = os.path.join(GLADEDIR, 'pixmaps', self.distro)
        self.total_images   = glob.glob("%s/snapshot*.png" % PIXMAPSDIR)
        messages = open("%s/messages.txt" % PIXMAPSDIR)
        self.total_messages = map(lambda line: line.rstrip('\n'),
                                  messages.readlines())
        messages.close()
        """
        iconLoader = KIconLoader()
        icon = iconLoader.loadIcon("system", KIcon.Small)
        self.userinterface.logo_image.setPixmap(icon)
        self.userinterface.backButton.setEnabled(False)

        """
        # set pixmaps
        if ( gtk.gdk.get_default_root_window().get_screen().get_width() > 1024 ):
        self.logo_image0.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.logo_image1.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.photo1.set_from_file(os.path.join(PIXMAPSDIR, "photo_1280.jpg"))
        self.logo_image21.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.logo_image22.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.logo_image23.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.logo_image3.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        self.photo2.set_from_file(os.path.join(PIXMAPSDIR, "photo_1280.jpg"))
        self.logo_image4.set_from_file(os.path.join(PIXMAPSDIR, "logo_1280.jpg"))
        else:
        self.logo_image0.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.logo_image1.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.photo1.set_from_file(os.path.join(PIXMAPSDIR, "photo_1024.jpg"))
        self.logo_image21.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.logo_image22.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.logo_image23.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.logo_image3.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
        self.photo2.set_from_file(os.path.join(PIXMAPSDIR, "photo_1024.jpg"))
        self.logo_image4.set_from_file(os.path.join(PIXMAPSDIR, "logo_1024.jpg"))
    
        self.installing_image.set_from_file(os.path.join(PIXMAPSDIR, "snapshot1.png"))
        
        self.live_installer.show()
        self.live_installer.window.set_cursor(self.watch)
        
        self.tzmap = TimezoneMap(self)
        self.tzmap.tzmap.show()
    
        # set initial bottom bar status
        self.back.hide()
        self.next.set_label('gtk-go-forward')
        """

    def set_locales(self):
        """internationalization config. Use only once."""
        """gtk only, KDE handles this"""
        #actually just use gettext??
        print "  set_locales()"
        #domain = self.distro + '-installer'
        domain = "gtkui" + '-installer'
        gettext.bindtextdomain(domain, LOCALEDIR)
        gettext.textdomain(domain)
        gettext.install(domain, LOCALEDIR, unicode=1)
        pass

    def translate_widgets(self):
        print "translate_widgets(self): TODO"
        #for widget in self.glade.get_widget_prefix(""):
        #    self.translate_widget(widget, self.locale)

    def show_intro(self):
        """Show some introductory text, if available."""
        print "  show_intro()"
    
        #intro = os.path.join(PATH, 'htmldocs', self.distro, 'intro.txt')
        intro = "/usr/share/espresso/htmldocs/ubuntu/intro.txt"
    
        if os.path.isfile(intro):
            intro_file = open(intro)
            self.userinterface.introLabel.setText(intro_file.read().rstrip('\n'))
            intro_file.close()
    
    def step_name(self, step_index):
        print "  step_name(step_index) " + str(step_index)
        if step_index < 0:
            step_index = 0
        return self.userinterface.widgetStack.widget(step_index).name()

    def set_current_page(self, current):
        print "  set_current_page(self, current):"
        self.current_page = current
        current_name = self.step_name(current)
        label_text = "Step %s of %d"
        curstep = "<i>Unknown?</i>"
        if current_name in BREADCRUMB_STEPS:
            curstep = str(BREADCRUMB_STEPS[current_name])
        self.userinterface.lblStepNofM.setText(label_text % (curstep, BREADCRUMB_MAX_STEP))

    def gparted_loop(self):
        print "  gparted_loop(self):"
        """call gparted and embed it into glade interface."""

        pre_log('info', 'gparted_loop()')
        
        #label.show()
        self.qtparted_process = KProcess(self.app)
        self.qtparted_process.setExecutable("/usr/sbin/qtparted")
        self.qtparted_process.setArguments(["--installer"])
        self.app.connect(self.qtparted_process, SIGNAL("receivedStdout(KProcess*, char*, int)"), self.qtparted_stdout)
        self.app.connect(self.qtparted_process, SIGNAL("processExited(KProcess*)"), self.qtparted_exited)
        started = self.qtparted_process.start(KProcess.NotifyOnExit, KProcess.All)
        print "started: " + str(started)

        """

        socket = gtk.Socket()
        socket.show()
        self.embedded.add(socket)
        window_id = str(socket.get_id())

        # Save pid to kill gparted when install process starts
        self.gparted_subp = subprocess.Popen(
            ['gparted', '--installer', window_id],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
        """

    def on_next_clicked(self):
        """Callback to control the installation process between steps."""
        print "  on_next_clicked()"
    
        if self.dbfilter is not None:
            self.dbfilter.ok_handler()
        else:
            self.app.exit()

    def on_keyboard_selected(self):
        kbd_chooser.apply_keyboard(self.get_keyboard())

    def on_back_clicked(self):
        print "  on_back_clicked(self, widget):"
        """Callback to set previous screen."""

        self.backup = True

        # Enabling next button
        self.userinterface.nextButton.setEnabled(True)
        # Setting actual step
        step = self.step_name(self.get_current_page())
        print "step: " + step

        changed_page = False

        if step == "stepLocation":
            self.userinterface.backButton.setEnabled(False)
        elif step == "stepPartAdvanced":
            """ FIXME jr
            print >>self.gparted_subp.stdin, "undo"
            self.gparted_subp.stdin.close()
            self.gparted_subp.wait()
            self.gparted_subp = None
            self.steps.set_current_page(self.steps.page_num(self.stepPartDisk))
            changed_page = True
            """
            pass
        elif step == "stepPartMountpoints":
            self.gparted_loop()
        elif step == "stepReady":
            self.userinterface.nextButton.setText("Next >")
        if not changed_page:
            self.userinterface.widgetStack.raiseWidget(self.get_current_page() - 1)
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def process_step(self):
        """Process and validate the results of this step."""
        print "  process_step() "

        # setting actual step
        step = self.step_name(self.get_current_page())
        pre_log('info', 'Step_before = %s' % step)

        # Welcome
        if step == "stepWelcome":
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepLanguage"])
        # Language
        elif step == "stepLanguage":
            self.translate_widgets()
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepLocation"])
            self.userinterface.backButton.setEnabled(True)
        # Location
        elif step == "stepLocation":
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepKeyboardConf"])
        # Keyboard
        elif step == "stepKeyboardConf":
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepUserInfo"])
            #self.steps.next_page()
            # XXX: Actually do keyboard config here
            self.userinterface.nextButton.setEnabled(False)
        # Identification
        elif step == "stepUserInfo":
            self.process_identification()
        # Disk selection
        elif step == "stepPartDisk":
            self.process_disk_selection()
        # Automatic partitioning
        elif step == "stepPartAuto":
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == "stepPartAdvanced":
            self.gparted_to_mountpoints()
        # Mountpoints
        elif step == "stepPartMountpoints":
            self.mountpoints_to_summary()
        # Ready to install
        elif step == "stepReady":
            # FIXME self.live_installer.hide()
            self.progress_loop()

        step = self.step_name(self.get_current_page())
        pre_log('info', 'Step_after = %s' % step)

    
    def process_identification (self):
        """Processing identification step tasks."""
        print "  process_identification()"
    
        error_msg = []
        error = 0
    
        # Validation stuff
    
        # checking hostname entry
        hostname = self.userinterface.hostname.text()
        for result in validation.check_hostname(str(hostname)):
            if result == validation.HOSTNAME_LENGTH:
                error_msg.append("The hostname must be between 3 and 18 characters long.")
            elif result == validation.HOSTNAME_WHITESPACE:
                error_msg.append("The hostname may not contain spaces.")
            elif result == validation.HOSTNAME_BADCHAR:
                error_msg.append("The hostname may only contain letters and digits.")
    
        # showing warning message is error is set
        if len(error_msg) > 1:
            self.show_error(''.join(error_msg))
        else:
            # showing next step and destroying mozembed widget to release memory
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartDisk"])

    def process_disk_selection (self):
        print "  process_disk_selection (self):"
        """Process disk selection before autopartitioning. This step will be
        skipped if only one disk is present."""

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        choice = self.get_disk_choice()
        if self.manual_choice is None or choice == self.manual_choice:
            print " process_disk_selection going to gparted"
            self.gparted_loop()
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartAdvanced"])
        else:
            print " process_disk_selection going to auto"
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartAuto"])

    def process_autopartitioning(self):
        print "  process_autopartitioning(self):"
        """Processing automatic partitioning step tasks."""

        self.app.processEvents(1)

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        choice = self.get_autopartition_choice()
        if self.manual_choice is None or choice == self.manual_choice:
            self.gparted_loop()
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartAdvanced"])
        else:
            # TODO cjwatson 2006-01-10: extract mountpoints from partman
            # TODO jr kde-ify
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepReady"])
            ##self.next.set_label("Install") # TODO i18n

    def set_disk_choices (self, choices, manual_choice):
        # TODO cjwatson 2006-03-20: This method should set up a disk
        # selector UI with the given choices.
        return False

    def get_disk_choice (self):
        # TODO cjwatson 2006-03-20: This method should return the current
        # choice in the disk selector.
        return None

    def set_autopartition_choices (self, choices, resize_choice, manual_choice):
        print "  set_autopartition_choices (self, choices, resize_choice, manual_choice):"
        children = self.userinterface.autopartition_frame.children()
        for child in children:
            if isinstance(child, QVBoxLayout):
                pass
            else:
                print child.name()
                print str(child)
                self.autopartition_vbox.remove(child)
                child.hide()

        self.manual_choice = manual_choice
        firstbutton = None
        for choice in choices:
            button = QRadioButton(choice, self.userinterface.autopartition_frame)
            self.autopartition_buttongroup.insert(button)
            id = self.autopartition_buttongroup.id(button)
            
            #Qt changes the string by adding accelarators, 
            #so keep pristine string here as is returned later to partman
            self.autopartition_buttongroup_texts[id] = choice
            if firstbutton is None:
                firstbutton = button
            self.autopartition_vbox.addWidget(button)
            
            if choice == resize_choice:
                self.on_autopartition_resize_toggled(button.isChecked())
                self.app.connect(button, SIGNAL('toggled(bool)'), self.on_autopartition_resize_toggled)
            
            button.show()
        if firstbutton is not None:
            firstbutton.setChecked(True)

        # make sure we're on the autopartitioning page
        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartAuto"])

    def on_autopartition_resize_toggled (self, enable):
        print "  on_autopartition_resize_toggled (self, widget):"
        """Update autopartitioning screen when the resize button is
        selected."""

        self.userinterface.new_size_frame.setEnabled(enable)

        ##     def on_abort_dialog_close (self, widget):
        print "  on_abort_dialog_close (self, widget):"

        ##         """ Disable automatic partitioning and reset partitioning method step. """

        ##         sys.stderr.write ('\non_abort_dialog_close.\n\n')

        ##         self.discard_automatic_partitioning = True
        ##         self.on_drives_changed (None)


    def get_autopartition_choice (self):
        print "  get_autopartition_choice (self): " + str(self.autopartition_buttongroup.selected().text())
        id = self.autopartition_buttongroup.id( self.autopartition_buttongroup.selected() )
        return self.autopartition_buttongroup_texts[id]
  
    def set_autopartition_resize_min_percent (self, min_percent):
        print "  set_autopartition_resize_min_percent (self, min_percent):"
        self.new_size_scale.setMinValue(min_percent)
        self.new_size_scale.setMaxValue(100)

    def get_autopartition_resize_percent (self):
        print "  get_autopartition_resize_percent (self):"
        return self.new_size_scale.value()


    def get_mountpoints (self):
        return dict(self.mountpoints)

  
    def confirm_partitioning_dialog (self, title, description):
        # TODO merge with gtk
        print "  confirm_partitioning_dialog (self, title, description):" + title + " ... " + description
        response = KMessageBox.warningYesNo(self.userinterface, description, title)
        if response == KMessageBox.Yes:
            return True
        else:
            return False

    def set_keyboard_choices(self, choicemap):
        print "  set_keyboard_choices(self, choicemap):"
        self.keyboard_choice_map = choicemap
        choices = choicemap.keys()

        self.userinterface.keyboardlistview.clear()
        for choice in sorted(choices):
            self.userinterface.keyboardlistview.insertItem( QListViewItem(self.userinterface.keyboardlistview, choice) )

        if self.current_keyboard is not None:
            self.set_keyboard(self.current_keyboard)

    def set_keyboard (self, keyboard):
        print "  set_keyboard (self, keyboard): " + keyboard
        """
        Keyboard is the database name of the keyboard, so untranslated
        """

        self.current_keyboard = keyboard

        iterator = QListViewItemIterator(self.userinterface.keyboardlistview)
        while iterator.current():
            #print "text: " + unicode(iterator.current().text(0))
            #if unicode(str(iterator.current().text(0).ascii()), 'utf-8') == language:
            value = unicode(iterator.current().text(0))
            if self.keyboard_choice_map[value] == keyboard:
                self.userinterface.keyboardlistview.setSelected(iterator.current(), True)
                break
            iterator += 1

    def get_keyboard (self):
        print "  get_keyboard (self):"
        selection = self.userinterface.keyboardlistview.selectedItem()
        if selection is None:
            print "returning none"
            return None
        else:
            print "returning value: " + str(selection.text(0))
            value = unicode(selection.text(0))
            return self.keyboard_choice_map[value]

    def qtparted_stdout(self, proc, output, bufflen):
            print " qtparted_stdout " + output
            self.embed.embed( int(output) )
            self.embed.resize(250,250)
            self.qtparted_vbox.addWidget(self.embed)

    def qtparted_exited(self, proc):
        print "qtparted_exited"

    def gparted_to_mountpoints(self):
        print "  gparted_to_mountpoints(self):"
        """Processing gparted to mountpoints step tasks."""
        
        #I'm doing something wrong in qtparted that it isn't reading stdin
        self.qtparted_process.writeStdin("apply", 5)


        """
        print >>self.gparted_subp.stdin, "apply"
        gparted_reply = self.gparted_subp.stdout.readline().rstrip('\n')
        if not gparted_reply.startswith('0 '):
            return

        # Shut down gparted
        self.gparted_subp.stdin.close()
        self.gparted_subp.wait()
        self.gparted_subp = None
        """

        # Setting items into partition Comboboxes
        for widget in self.userinterface.stepPartMountpoints.children():
            if QString(widget.name()).contains("partition") > 0:
                self.show_partitions(widget)
        self.size = self.get_sizes()

        # building mountpoints preselection
        self.default_partition_selection = self.get_default_partition_selection(self.size)

        # Setting a default partition preselection
        if len(self.default_partition_selection.items()) == 0:
            self.userinterface.nextButton.setEnabled(False)
        else:
            count = 0
            mp = { 'swap' : 0, '/' : 1 }

            # Setting default preselection values into ComboBox
            # widgets and setting size values. In addition, next row
            # is showed if they're validated.
            for j, k in self.default_partition_selection.items():
                if count == 0:
                    self.userinterface.partition1.setCurrentItem(self.partitions.index(k)+1)
                    self.userinterface.mountpoint1.setCurrentItem(mp[j]) # FIXME combox has never been filled
                    self.userinterface.size1.setText(self.set_size_msg(k))
                    if ( len(get_partitions()) > 1 ):
                        self.userinterface.partition2.show()
                        self.userinterface.mountpoint2.show()
                    count += 1
                elif count == 1:
                    self.userinterface.partition2.setCurrentItem(self.partitions.index(k)+1)
                    self.userinterface.mountpoint2.setCurrentItem(mp[j])
                    self.userinterface.size2.setText(self.set_size_msg(k))
                    if ( len(get_partitions()) > 2 ):
                        self.userinterface.partition3.show()
                        self.userinterface.mountpoint3.show()
                    count += 1

        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartMountpoints"])

    def show_partitions(self, widget):
        print "  show_partitions(self, widget): " + widget.name()
        """write all values in this widget (GtkComboBox) from local
        partitions values."""

        from espresso import misc

        self.partitions = []
        partition_list = get_partitions()

        # the first element is empty to allow deselect a preselected device
        widget.insertItem(" ")
        for index in partition_list:
            index = '/dev/' + index
            label = misc.part_label(index)
            self.part_labels[index] = label
            self.part_devices[label] = index
            widget.insertItem(self.part_labels[index])
            self.partitions.append(index)

    def get_sizes(self):
        print "  get_sizes(self):"
        """return a dictionary with skeleton { partition : size }
        from /proc/partitions ."""

        # parsing /proc/partitions and getting size data
        size = {}
        partitions = open('/proc/partitions')
        for line in partitions:
            try:
                size[line.split()[3]] = int(line.split()[2])
            except:
                continue
        partitions.close()
        return size

    def get_default_partition_selection(self, size, fstype):
        print "  get_default_partition_selection(self, size):"
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
        device_list = get_filesystems(fstype)

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
                elif fs == 'linux-swap':
                    selection['swap'] = '/dev/%s' % partition
                    swap = 1
                else:
                    continue
        return selection

    def set_size_msg(self, widget):
        print "  set_size_msg(self, widget):"
        """return a string message with size value about
        the partition target by widget argument."""

        # widget is studied in a different manner depending on object type
        if widget.__class__ == str:
            size = float(self.size[widget.split('/')[2]])
        else:
            size = float(self.size[self.part_devices[widget.get_active_text()].split('/')[2]])

        if size > 1024*1024:
            msg = '%.0f Gb' % (size/1024/1024)
        elif size > 1024:
            msg = '%.0f Mb' % (size/1024)
        else:
            msg = '%.0f Kb' % size
        return msg

    def get_partition_widgets(self):
        widgets = []
        for widget in self.userinterface.stepPartMountpoints.children():
            if QString(widget.name()).contains("partition") > 0:
                widgets.append(widget)
        return widgets

    def get_mountpoint_widgets(self):
        widgets = []
        for widget in self.userinterface.stepPartMountpoints.children():
            if QString(widget.name()).contains("mountpoint") > 0:
                widgets.append(widget)
        return widgets

    def mountpoints_to_summary(self):
        print "  mountpoints_to_summary(self):"
        """Processing mountpoints to summary step tasks."""

        # Validating self.mountpoints
        error_msg = ['\n']

        # creating self.mountpoints list only if the pairs { device :
        # mountpoint } are selected.
        list = []
        list_partitions = []
        list_mountpoints = []

        # building widget lists to build dev_mnt dict ( { device :
        # mountpoint } )
        for widget in self.get_partition_widgets():
            if widget.currentText() not in [None, ' ']:
                list_partitions.append(widget)
        for widget in self.get_mountpoint_widgets():
            if widget.currentText() != "":
                list_mountpoints.append(widget)
        # Only if partitions cout or mountpoints count selected are the same,
        #     dev_mnt is built.
        if len(list_partitions) == len(list_mountpoints):
            dev_mnt = dict( [ (list_partitions[i], list_mountpoints[i]) for i in range(0,len(list_partitions)) ] )

            for dev, mnt in dev_mnt.items():
                if dev.currentText() is not None \
                   and mnt.currentText() != "":
                    foo = self.part_devices[str(dev.currentText())]
                    # TODO cjwatson 2006-03-08: Add UI to control whether
                    # the partition is to be formatted; hardcoded to True in
                    # the meantime.
                    # TODO cjwatson 2006-03-29: Extract desired filesystem
                    # type from qtparted; hardcoded to None (i.e. use
                    # current filesystem type or failing that ext3) in the
                    # meantime.
                    self.mountpoints[foo] = (mnt.currentText(), True, None)

        # Processing validation stuff
        elif len(list_partitions) > len(list_mountpoints):
            error_msg.append("· Punto de montaje vacío.\n\n")
        elif len(list_partitions) < len(list_mountpoints):
            error_msg.append("· Partición sin seleccionar.\n\n")
        """
        # turn off automount

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
        """

        if partman_commit.PartmanCommit(self).run_command(auto_process=True) != 0:
                return
        
        """
        #return gconf back to previous state

        for gconf_key in (gvm_automount_drives, gvm_automount_media):
            if gconf_previous[gconf_key] == '':
                subprocess.call(['gconftool-2', '--unset', gconf_key])
            elif gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                                 '--type', 'bool', gconf_previous[gconf_key]])
        """

        # Checking duplicated devices
        for widget in self.get_partition_widgets:
            if widget.currentText() != None:
                list.append(widget.currentText())

        for check in list:
            if list.count(check) > 1:
                error_msg.append("· Dispositivos duplicados.\n\n")
                break

        # Processing more validation stuff
        if len(self.mountpoints) > 0:
            for check in validation.check_mountpoint(self.mountpoints,
                                                     self.size):
                if check == validation.MOUNTPOINT_NOROOT:
                    error_msg.append("· No se encuentra punto de montaje '/'.\n\n")
                elif check == validation.MOUNTPOINT_DUPPATH:
                    error_msg.append("· Puntos de montaje duplicados.\n\n")
                elif check == validation.MOUNTPOINT_BADSIZE:
                    for mountpoint, format, fstype in \
                            self.mountpoints.itervalues():
                        if mountpoint == 'swap':
                            error_msg.append("· Tamaño insuficiente para la partición '/' (Tamaño mínimo: %d Mb).\n\n" % MINIMAL_PARTITION_SCHEME['root'])
                            break
                    else:
                        error_msg.append("· Tamaño insuficiente para la partición '/' (Tamaño mínimo: %d Mb).\n\n" % (MINIMAL_PARTITION_SCHEME['root'] + MINIMAL_PARTITION_SCHEME['swap']*1024))
                elif check == validation.MOUNTPOINT_BADCHAR:
                    error_msg.append("· Carácteres incorrectos para el punto de montaje.\n\n")

        # showing warning messages
        if len(error_msg) > 1:
            self.mountpoint_error_reason.setText(''.join(error_msg))
            self.mountpoint_error_reason.show()
            self.mountpoint_error_image.show()
        else:
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartReady"])

    # returns the current wizard page
    def get_current_page(self):
      return self.userinterface.widgetStack.id(self.userinterface.widgetStack.visibleWidget())

    """
    def show_error(self, msg):
      ""show warning message on Identification screen where validation
      doesn't work properly.""
      print "  show_error(msg)"

      self.userinterface.warning_info.setText(msg)
    """

    def on_steps_switch_page(self, newPageID):
        print "  on_steps_switch_page(title): " + str(self.get_current_page()) + " " + str(newPageID)

        self.set_current_page(newPageID)
        current_name = self.step_name(self.get_current_page())
        """

        for step in range(0, self.steps.get_n_pages()):
            breadcrumb = BREADCRUMB_STEPS[self.step_name(step)]
            if hasattr(self, breadcrumb):
                breadcrumblbl = getattr(self, breadcrumb)
                if breadcrumb == BREADCRUMB_STEPS[current_name]:
                    breadcrumblbl.set_attributes(BREADCRUMB_HIGHLIGHT)
                else:
                    breadcrumblbl.set_attributes(BREADCRUMB_NORMAL)
            else:
                pre_log('info', 'breadcrumb step %s missing' % breadcrumb)
        """

        # Populate the drives combo box the first time that page #2 is shown.
        if current_name == "stepPartAuto" and False:
            # TODO cjwatson 2006-01-10: update for partman

            # To set a "busy mouse":
            #JR self.live_installer.window.set_cursor (self.watch)

            ##             while gtk.events_pending ():
            ##                 gtk.main_iteration ()

            # To set a normal mouse again:
            #JR self.live_installer.window.set_cursor (None)

            for i in self.__assistant.get_drives ():
                self.drives.append_text ('%s' % i ['label'])

            model = self.drives.get_model ()

            if len (model) > 0:
                self.drives.set_active (0)

    def get_screen_width(self):
        print "  get_screen_width(): " + str(self.app.desktop().screenGeometry().width())
        return self.app.desktop().screenGeometry().width()

    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        print "  run_main_loop()"
        self.app.exec_loop()

    # Return control to the next level up.
    def quit_main_loop (self):
        print "  quit_main_loop()"
        self.app.exit()

    # Callbacks provided to components.

    def watch_debconf_fd (self, from_debconf, process_input):
        self.debconf_fd_counter = 0
        print "  watch_debconf_fd (self, from_debconf, process_input): " +  str(from_debconf) + " " + str(process_input)
        self.socketNotifierRead = QSocketNotifier(from_debconf, QSocketNotifier.Read, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)
        
        self.socketNotifierWrite = QSocketNotifier(from_debconf, QSocketNotifier.Write, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)

        self.socketNotifierException = QSocketNotifier(from_debconf, QSocketNotifier.Exception, self.app, "read-for-" + str(from_debconf))
        self.app.connect(self.socketNotifierException, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_exception)
        
        self.debconf_callbacks[from_debconf] = process_input
        self.current_debconf_fd = from_debconf
        """
        gobject.io_add_watch(from_debconf,
                                                 gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                                                 self.watch_debconf_fd_helper, process_input)
        """


    def watch_debconf_fd_helper_read (self, source):
        self.debconf_fd_counter += 1
        print "  watch_debconf_fd_helper_read (self, source): " + str(source) + " " + str(self.debconf_fd_counter)
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_IN
        #if (self.debconf_fd_counter == 25):
        #    print "adding HUP"
        #    debconf_condition |= filteredcommand.DEBCONF_IO_HUP
        self.debconf_callbacks[source](source, debconf_condition)
        """
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)
        """

    def watch_debconf_fd_helper_write(self, source):
        print "  watch_debconf_fd_helper_write(self, source): " + str(source)
        
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_OUT
        self.debconf_callbacks[source](source, debconf_condition)
        """
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)
        """

    def watch_debconf_fd_helper_exception(self, source):
        print "  watch_debconf_fd_helper_error(self, source): " + str(source)
        
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        self.debconf_callbacks[source](source, debconf_condition)
        """
        if (cb_condition & gobject.IO_ERR) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        if (cb_condition & gobject.IO_HUP) != 0:
            debconf_condition |= filteredcommand.DEBCONF_IO_HUP

        return callback(source, debconf_condition)
        """
	
    def debconf_progress_start (self, progress_min, progress_max, progress_title):
        print "  debconf_progress_start (self, progress_min, progress_max, progress_title) " + str(progress_min) + " " + str(progress_max)
        if self.progress_cancelled:
            return False
        """
        if self.current_page is not None:
            self.debconf_progress_window.set_transient_for(self.live_installer)
        else:
            self.debconf_progress_window.set_transient_for(None)
        """
        
        if self.progress_position.depth() == 0:
            self.progressDialogue = KProgressDialog(self.userinterface, "progressdialog", progress_title, "", True)
            # FIXME jr self.debconf_progress_window.set_title(progress_title)
        
        self.progressDialogue.setLabel(progress_title)

        bar = self.progressDialogue.progressBar()
        bar.setTotalSteps(progress_max - progress_min)
        self.progress_position.start(progress_min, progress_max)
        self.progressDialogue.show()
        return True

    def debconf_progress_set (self, progress_val):
        print "  debconf_progress_set (self, progress_val):"
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        self.progressDialogue.progressBar().setProgress(progress_val)
        return True

    def debconf_progress_step (self, progress_inc):
        print "  debconf_progress_step (self, progress_inc): " + str(progress_inc)
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        newValue = self.progressDialogue.progressBar().progress() + progress_inc
        self.progressDialogue.progressBar().setProgress(newValue)
        return True

    def debconf_progress_info (self, progress_info):
        print "  debconf_progress_info (self, progress_info):"
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        self.progressDialogue.setLabel(progress_info)
        return True

    def debconf_progress_stop (self):
        print "  debconf_progress_stop (self):"
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            self.progress_cancelled = False
            return False
        self.progress_position.stop()
        if self.progress_position.depth() == 0:
            self.progressDialogue.hide()
        return True

    def debconf_progress_region (self, region_start, region_end):
        print "  debconf_progress_region (self, region_start, region_end):"
        self.progress_position.set_region(region_start, region_end)

    def debconf_progress_cancellable (self, cancellable):
        print "  debconf_progress_cancellable (self, cancellable):"
        if cancellable:
            self.progressDialogue.showCancelButton(True)
        else:
            self.progressDialogue.showCancelButton(False)
            self.progress_cancelled = False

    def on_progress_cancel_button_clicked (self, button):
        print "  on_progress_cancel_button_clicked (self, button):"
        self.progress_cancelled = True

    def debconffilter_done (self, dbfilter):
        print "  debconffilter_done (self, dbfilter): " + str(self.current_debconf_fd)
        # TODO cjwatson 2006-02-10: handle dbfilter.status
        if dbfilter == self.dbfilter:
            self.dbfilter = None
            self.app.exit()

    def progress_loop(self):
        print "  progress_loop(self):"
        """prepare, copy and config the system in the core install process."""

        pre_log('info', 'progress_loop()')

        self.current_page = None

        if self.progress_position.depth() != 0:
            # A progress bar is already up for the partitioner. Use the rest
            # of it.
            (start, end) = self.progress_position.get_region()
            self.debconf_progress_region(end, 100)

        print "setting dbfilter"

        dbfilter = install.Install(self)
        print "dbfilter set"
        if dbfilter.run_command(auto_process=True) != 0:
            print "runcommand != 0"
            self.installing = False
            # TODO cjwatson 2006-02-27: do something nicer than just quitting
            self.quit()
        print "run_command good"

        while self.progress_position.depth() != 0:
            self.debconf_progress_stop()

        # just to make sure
        #FIXME jr self.debconf_progress_window.hide()

        self.installing = False
        quitText = """Ubuntu is now installed on your computer. You need to restart the computer in order to use it. You can continue to use this live CD, although any changes you make or documents you save will not be preserved.\n\nMake sure to remove the CD when restarting the computer, otherwise it will start back up using this live CD rather than the newly-installed system."""
        quitAnswer = KMessageBox.questionYesNo(self.userinterface, quitText, "Installation Complete", KGuiItem("Quit"), KGuiItem("reboot"))
        if quitAnswer == KMessageBox.No:
            self.reboot();

    def reboot(self, *args):
        print "  reboot(self, *args):"
        """reboot the system after installing process."""

        self.returncode = 10
        self.quit()


    def do_reboot(self):
        print "  do_reboot(self):"
        """Callback for main program to actually reboot the machine."""

        os.system("reboot")

    def quit(self):
        print "  quit(self):"
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

    def on_cancel_clicked3(self):
        print "  on_cancel_clicked(self, widget):"
        
        response = KMessageBox.warningContinueCancel(self.userinterface, "Do you really want to abort the installation now?", "Abort the Installation?", KGuiItem("Quit"))
        if response == KMessageBox.Continue:
            self.current_page = None
            self.quit()
            return True
        else:
            return False

    def set_summary_text (self, text):
        print "  set_summary_text (self, text):"
        self.userinterface.ready_text.setText(text)

    def error_dialog (self, msg):
        print "  error_dialog (self, msg):" + msg
        # TODO: cancel button as well if capb backup
        if self.current_page is not None:
            transient = self.userinterface
        else:
            transient = self.userinterface
            #transient = self.debconf_progress_dialog FIXME
        KMessageBox.error(transient, msg)

    def set_language_choices (self, choice_map):
        print "  set_language_choices (self, choice_map):"
        self.language_choice_map = dict(choice_map)
        self.userinterface.language_treeview.clear()
        for choice in sorted(self.language_choice_map):
            self.userinterface.language_treeview.insertItem( QListViewItem(self.userinterface.language_treeview, choice) )

    def set_language (self, language):
        print "  set_language (self, language):"
        #model = self.language_treeview.get_model()
        #iterator = model.iter_children(None)
        #while iterator is not None:
        #    if unicode(model.get_value(iterator, 0)) == language:
        #        self.language_treeview.get_selection().select_iter(iterator)
        #        break
        #    iterator = model.iter_next(iterator)
        
        # FIXME, can't change QString to unicode when in ascii, why is this
        # program in ascii??
        iterator = QListViewItemIterator(self.userinterface.language_treeview)
        while iterator.current():
            #print "text: " + unicode(iterator.current().text(0))
            #if unicode(str(iterator.current().text(0).ascii()), 'utf-8') == language:
            if unicode("English") == language:
                self.userinterface.language_treeview.setSelected(iterator.current(), True)
                break
            iterator += 1

    def get_language (self):
        print "  get_language (self):"
        selection = self.userinterface.language_treeview.selectedItem()
        #return unicode(selection.text(0))
        return unicode("English")

    def set_timezone (self, timezone):
        print "  set_timezone (self, timezone): " + timezone + "<<"
        #self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        print "  get_timezone (self):"
        return "Europe/London" #self.tzmap.get_selected_tz_name()

    def refresh (self):
        print "  refresh (self):"
        self.app.processEvents(1)
        """
        while gtk.events_pending():
            gtk.main_iteration()
        """

    def set_fullname(self, value):
      self.userinterface.fullname.setText(str(value))

    def get_fullname(self):
      return str(self.userinterface.fullname.text())
  
    def set_username(self, value):
      self.userinterface.fullname.setText(str(value))

    def get_username(self):
      return str(self.userinterface.username.text())
  
    def get_password(self):
      return str(self.userinterface.password.text())
  
    def get_verified_password(self):
      return str(self.userinterface.verified_password.text())

    def username_error(self, msg):
        print "username_error() fixme for kde"
        self.username_error_reason.set_text(msg)
        self.username_error_box.show()

    def password_error(self, msg):
        print "password_error() fixme for kde"
        self.password_error_reason.set_text(msg)
        self.password_error_box.show()


