# -*- coding: UTF-8 -*-
#
# Copyright (C) 2006 Canonical Ltd.
#
# Author:
#   Jonathan Riddell <jriddell@ubuntu.com>
#
# This file is part of Ubiquity.
#
# Ubiquity is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free
# Software Foundation; either version 2 of the License, or at your option)
# any later version.
#
# Ubiquity is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or
# FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for
# more details.
#
# You should have received a copy of the GNU General Public License along
# with Ubiquity; if not, write to the Free Software Foundation, Inc., 51
# Franklin St, Fifth Floor, Boston, MA  02110-1301  USA
##################################################################################

print "importing kde-ui"

import sys
from qt import *
from kdeui import *
from kdecore import *
from kio import KRun
#import kdedesigner
from ubiquity.frontend.liveinstaller import UbiquityUIBase
from ubiquity.frontend.crashdialog import CrashDialog

import os
import time
import datetime
import glob
import subprocess
import traceback
import xml.sax.saxutils

import gettext

import debconf
try:
    from debconf import DebconfCommunicator
except ImportError:
    from ubiquity.debconfcommunicator import DebconfCommunicator

from ubiquity import filteredcommand, validation
from ubiquity.misc import *
from ubiquity.settings import *
from ubiquity.components import language, kbd_chooser, timezone, usersetup, \
                                partman, partman_commit, summary, install
import ubiquity.tz
import ubiquity.progressposition

# Define global path
PATH = '/usr/share/ubiquity'

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

class UbiquityUI(UbiquityUIBase):
    
    def setWizard(self, wizardRef):
        self.wizard = wizardRef

    def closeEvent(self, event):
        print "closing!"
        self.wizard.on_cancel_clicked()

class Wizard:

    def __init__(self, distro):
        print "  init(distro)"
        sys.excepthook = self.excepthook

        about=KAboutData("kubuntu-ubiquity","Installer","0.1","Live CD Installer for Kubuntu",KAboutData.License_GPL,"(c) 2006 Canonical Ltd", "http://wiki.kubuntu.org/KubuntuUbiquity", "jriddell@ubuntu.com")
        about.addAuthor("Jonathan Riddell", None,"jriddell@ubuntu.com")
        KCmdLineArgs.init(["./installer"],about)
        
        self.app = KApplication()
        
        self.userinterface = UbiquityUI(None, "Ubiquity")
        self.userinterface.setWizard(self)
        self.app.setMainWidget(self.userinterface)
        self.userinterface.show()
        
        # declare attributes
        self.distro = distro
        self.current_keyboard = None
        self.manual_choice = None
        self.password = ''
        self.hostname_edited = False
        self.mountpoint_widgets = []
        self.size_widgets = []
        self.partition_widgets = []
        self.format_widgets = []
        self.mountpoint_choices = ['', 'swap', '/', '/home',
                                   '/boot', '/usr', '/var']
        self.partition_choices = []
        self.mountpoints = {}
        self.part_labels = {' ' : ' '}
        self.part_devices = {' ' : ' '}
        self.current_page = None
        self.dbfilter = None
        self.locale = None
        self.progress_position = ubiquity.progressposition.ProgressPosition()
        self.progress_cancelled = False
        self.previous_partitioning_page = None
        self.installing = False
        self.returncode = 0
        self.language_questions = ('live_installer', 'welcome_heading_label',
                                   'welcome_text_label', 'cancel', 'back',
                                   'next')

        devnull = open('/dev/null', 'w')
        self.laptop = subprocess.call(["laptop-detect"], stdout=devnull,
                                      stderr=subprocess.STDOUT) == 0
        devnull.close()
        self.qtparted_subp = None

        # set default language
        dbfilter = language.Language(self, DebconfCommunicator('ubiquity',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()

        self.debconf_callbacks = {}    # array to keep callback functions needed by debconf file descriptors
    
        # To get a "busy mouse":
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))
    
        # If automatic partitioning fails, it may be disabled toggling on this variable:
        self.discard_automatic_partitioning = False
        
        # TODO jr 2006-04-19: sometimes causes pykde crash when creating
        # kdialogs
        self.translate_widgets()

        self.customize_installer()
        
        self.part_disk_vbox = QVBoxLayout(self.userinterface.part_disk_frame)
        self.part_disk_buttongroup = QButtonGroup(self.userinterface.part_disk_frame)
        self.part_disk_buttongroup_texts = {}
        
        self.autopartition_vbox = QVBoxLayout(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup = QButtonGroup(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup_texts = {}
        
        self.qtparted_vbox = QVBoxLayout(self.userinterface.qtparted_frame)
        self.embed = QXEmbed(self.userinterface.qtparted_frame, "embed")
        self.embed.setProtocol(QXEmbed.XPLAIN)
        print "init end"

    def excepthook(self, exctype, excvalue, exctb):
        """Crash handler."""

        if (issubclass(exctype, KeyboardInterrupt) or
            issubclass(exctype, SystemExit)):
            return

        tbtext = ''.join(traceback.format_exception(exctype, excvalue, exctb))
        print >>sys.stderr, ("Exception in KDE frontend"
                             " (invoking crash handler):")
        print >>sys.stderr, tbtext
        dialog = CrashDialog(self.userinterface)
        dialog.connect(dialog.beastie_url, SIGNAL("leftClickedURL(const QString&)"), self.openURL)
        dialog.crash_detail.setText(tbtext)
        dialog.exec_loop()
        sys.exit(1)

    def openURL(self, url):
        print "openURL(self, url):" + str(url)
        #need to run this else kdesu can't run Konqueror
        subprocess.call(['su', 'ubuntu', 'xhost', '+localhost'])
        KRun.runURL(KURL(url), "text/html")

    def run(self):
        """run the interface."""
        print "  run()"

        if os.getuid() != 0:
                print "uid != 0"
                title = ('This installer must be run with administrative privileges, and cannot continue without them.')
                result = QMessageBox.critical(self.userinterface, "Must be root", title)

                sys.exit(1)

        # show interface
        # TODO cjwatson 2005-12-20: Disabled for now because this segfaults in
        # current dapper (https://bugzilla.ubuntu.com/show_bug.cgi?id=20338).
        #self.show_browser()
        self.show_intro()
        self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
    
        # Declare SignalHandler
        self.app.connect(self.userinterface.next, SIGNAL("clicked()"), self.on_next_clicked)
        self.app.connect(self.userinterface.back, SIGNAL("clicked()"), self.on_back_clicked)
        self.app.connect(self.userinterface.cancel, SIGNAL("clicked()"), self.on_cancel_clicked)
        self.app.connect(self.userinterface.widgetStack, SIGNAL("aboutToShow(int)"), self.on_steps_switch_page)
        self.app.connect(self.userinterface.keyboardlistview, SIGNAL("selectionChanged()"), self.on_keyboard_selected)
        
        self.app.connect(self.userinterface.fullname, SIGNAL("textChanged(const QString &)"), self.on_fullname_changed)
        self.app.connect(self.userinterface.username, SIGNAL("textChanged(const QString &)"), self.on_username_changed)
        self.app.connect(self.userinterface.password, SIGNAL("textChanged(const QString &)"), self.on_password_changed)
        self.app.connect(self.userinterface.verified_password, SIGNAL("textChanged(const QString &)"), self.on_verified_password_changed)
        self.app.connect(self.userinterface.hostname, SIGNAL("textChanged(const QString &)"), self.on_hostname_changed)
        self.app.connect(self.userinterface.hostname, SIGNAL("textChanged(const QString &)"), self.on_hostname_insert_text)
        
        self.app.connect(self.userinterface.fullname, SIGNAL("selectionChanged()"), self.on_fullname_changed)
        self.app.connect(self.userinterface.username, SIGNAL("selectionChanged()"), self.on_username_changed)
        self.app.connect(self.userinterface.password, SIGNAL("selectionChanged()"), self.on_password_changed)
        self.app.connect(self.userinterface.verified_password, SIGNAL("selectionChanged()"), self.on_verified_password_changed)
        self.app.connect(self.userinterface.hostname, SIGNAL("selectionChanged()"), self.on_hostname_changed)
        
        self.app.connect(self.userinterface.language_treeview, SIGNAL("selectionChanged()"), self.on_language_treeview_selection_changed)

        self.app.connect(self.userinterface.timezone_time_adjust, SIGNAL("clicked()"), self.on_timezone_time_adjust_clicked)

        self.app.connect(self.userinterface.timezone_city_combo, SIGNAL("activated(int)"), self.tzmap.city_combo_changed)

        self.app.connect(self.userinterface.new_size_scale, SIGNAL("valueChanged(int)"), self.update_new_size_label)
        # Start the interface
        self.set_current_page(0)
        while self.current_page is not None:
            if not self.installing:
                # Make sure any started progress bars are stopped.
                while self.progress_position.depth() != 0:
                    print "removing a progress position in run: " + str(self.progress_position.depth())
                    self.debconf_progress_stop()

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
                self.userinterface.setCursor(QCursor(Qt.WaitCursor))
                self.dbfilter.start(auto_process=True)
            else:
                self.userinterface.next.setEnabled(True)
                if not (current_name == "stepIntro" or current_name == "stepLanguage"):
                    self.userinterface.back.setEnabled(True)
                self.userinterface.setCursor(QCursor(Qt.ArrowCursor))

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
        """Initial UI setup."""

        #iconLoader = KIconLoader()
        #icon = iconLoader.loadIcon("system", KIcon.Small)
        #self.userinterface.logo_image.setPixmap(icon)
        self.userinterface.back.setEnabled(False)

        self.update_new_size_label(self.userinterface.new_size_scale.value())
        """

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

        self.logo_image.set_from_file(logo)
        self.photo.set_from_file(photo)
        """

        self.tzmap = TimezoneMap(self)
        #self.tzmap.tzmap.show()

    def translate_widgets(self, parentWidget=None):
        print "  translate_widgets(self, parentWidget=None):"
        if self.locale is None:
            languages = []
        else:
            languages = [self.locale]
        get_translations(languages=languages,
                         core_names=['ubiquity/text/%s' % q
                                     for q in self.language_questions])

        self.translate_widget_chidren(parentWidget)

    def translate_widget_chidren(self, parentWidget=None):
        print "  translate_widget_chidren(self, parentWidget=None):"
        if parentWidget == None:
            parentWidget = self.userinterface

        for widget in parentWidget.children():
            self.translate_widget(widget, self.locale)
            self.translate_widget_chidren(widget)

    def translate_widget(self, widget, lang):

        print "  translate_widget(self, widget, lang)"
        
        #FIXME how to do in KDE?  use kstdactions?
        #if isinstance(widget, gtk.Button) and widget.get_use_stock():
        #    widget.set_label(widget.get_label())

        text = get_string('ubiquity/text/%s' % widget.name(), lang)
        if text is None:
            return

        if isinstance(widget, QLabel):
            name = widget.name()
            if 'heading_label' in name:
                widget.setText("<h2>" + text + "</h2>")
            elif 'extra_label' in name:
                widget.setText("<em>" + text + "</em>")
            elif name in ('drives_label', 'partition_method_label',
                          'mountpoint_label', 'size_label', 'device_label',
                          'format_label'):
                widget.setText("<strong>" + text + "</strong>")
            else:
                widget.setText(text)

        elif isinstance(widget, QPushButton):
            widget.setText(text)

        elif isinstance(widget, QWidget) and widget.name() == UbiquityUI:
            widget.setCaption(text)

    def show_intro(self):
        """Show some introductory text, if available."""
        print "  show_intro()"
    
        #intro = os.path.join(PATH, 'htmldocs', self.distro, 'intro.txt')
        intro = "/usr/share/ubiquity/htmldocs/ubuntu/intro.txt"
    
        if os.path.isfile(intro):
            intro_file = open(intro)
            text = ""
            for line in intro_file:
                text = text + line + "<br>"
            self.userinterface.introLabel.setText(text)
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

        disable_swap()

        self.qtparted_subp = subprocess.Popen(
            ['/usr/sbin/qtparted', '--installer'], stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
        qtparted_winid = self.qtparted_subp.stdout.readline().rstrip('\n')
        self.embed.embed( int(qtparted_winid) )
        self.qtparted_vbox.addWidget(self.embed)
        #nasty cludge, we need qtparted to output a line when it's done settings up its window so we can resize then
        QTimer.singleShot(5000, self.resize_qtparted)
        #uncomment when new version of qt is in the archive
        #qtparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        #if qtparted_reply.startswith('STARTED'):
            #self.userinterface.qtparted_frame.resize(self.userinterface.qtparted_frame.width()-1,self.userinterface.qtparted_frame.height())

    def resize_qtparted(self):
        print "  resize_qtparted"
        self.userinterface.qtparted_frame.resize(self.userinterface.qtparted_frame.width()-1,self.userinterface.qtparted_frame.height())

    def set_size_msg(self, widget):
        """return a string message with size value about
        the partition target by widget argument."""

        # widget is studied in a different manner depending on object type
        if widget.__class__ == str:
            size = float(self.size[widget.split('/')[2]])
        else:
            size = float(self.size[self.part_devices[str(widget.currentText())].split('/')[2]])

        if size > 1024*1024:
            msg = '%.0f Gb' % (size/1024/1024)
        elif size > 1024:
            msg = '%.0f Mb' % (size/1024)
        else:
            msg = '%.0f Kb' % size
        print "msg: " + msg
        return msg

    def add_mountpoint_table_row(self):
        print "  add_mountpoint_table_row(self):"
        """Add a new empty row to the mountpoints table."""
        mountpoint = QComboBox(self.userinterface.mountpoint_frame)
        mountpoint.setEditable(True)
        for mp in self.mountpoint_choices:
            mountpoint.insertItem(mp)
        size = QLabel(self.userinterface.mountpoint_frame)
        partition = QComboBox(self.userinterface.mountpoint_frame)
        for part in self.partition_choices:
            if part in self.part_labels:
                partition.insertItem(self.part_labels[part])
            else:
                partition.insertItem(part)
        format = QCheckBox(self.userinterface.mountpoint_frame)
        format.setEnabled(False)

        row = len(self.mountpoint_widgets) + 1
        self.mountpoint_widgets.append(mountpoint)
        self.size_widgets.append(size)
        self.partition_widgets.append(partition)
        self.format_widgets.append(format)

        #self.mountpoint_table.resize(row + 1, 4)
        self.mountpoint_table.addWidget(mountpoint, row, 0)
        self.mountpoint_table.addWidget(size, row, 1)
        self.mountpoint_table.addWidget(partition, row, 2)
        self.mountpoint_table.addWidget(format, row, 3)
        mountpoint.show()
        size.show()
        partition.show()
        format.show()

        self.app.connect(mountpoint, SIGNAL("activated(int)"), self.on_list_changed)
        self.app.connect(partition, SIGNAL("activated(int)"), self.on_list_changed)

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
            print "removing a progress position in progress_loop: " + str(self.progress_position.depth())
            self.debconf_progress_stop()

        # just to make sure
        self.progressDialogue.hide()
        #FIXME jr self.debconf_progress_window.hide()

        self.installing = False
        quitText = """Kubuntu is now installed on your computer. You need to restart the computer in order to use it. You can continue to use this live CD, although any changes you make or documents you save will not be preserved.\n\nMake sure to remove the CD when restarting the computer, otherwise it will start back up using this live CD rather than the newly-installed system."""
        
        quitAnswer = QMessageBox.question(self.userinterface, "Finished", quitText, "Quit", "Reboot")

        if quitAnswer == 1:
            self.reboot();

    def reboot(self, *args):
        print "  reboot(self, *args):"
        """reboot the system after installing process."""

        self.returncode = 10
        self.quit()


    def do_reboot(self):
        print "  do_reboot(self):"
        """Callback for main program to actually reboot the machine."""

        # can't seem to be able to call dcop from kdesu (even if I su back to ubuntu user)
        #if (os.path.exists("/usr/bin/ksmserver") and
        #    os.path.exists("/usr/bin/dcop")):
        #    subprocess.call(["dcop", "ksmserver", "ksmserver", "logout", "1", "1", "1"])
        #else:
        subprocess.call(["reboot"])

    def quit(self):
        print "  quit(self):"
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

    def on_cancel_clicked(self):
        print "  on_cancel_clicked(self, widget):"
        
        response = QMessageBox.question(self.userinterface, "Abort?", "Do you really want to abort the installation now?", "Quit", "Continue")
        if response == 0:
            if self.qtparted_subp is not None:
                print >>self.qtparted_subp.stdin, "exit"
            self.current_page = None
            self.quit()
            return True
        else:
            return False

    def on_list_changed(self, textID):
        print "  on_list_changed(self, widget):"
        """check if partition/mountpoint pair is filled and show the next pair
        on mountpoint screen. Also size label associated with partition combobox
        is changed dynamically to show the size partition."""
        
        """

        if widget.get_active_text() not in ['', None]:
            if widget in self.partition_widgets:
                index = self.partition_widgets.index(widget)
            elif widget in self.mountpoint_widgets:
                index = self.mountpoint_widgets.index(widget)
            else:
                return
        """

        index = 0
        while index < len(self.partition_widgets):

            #set size widget
            partition_text = unicode(self.partition_widgets[index].currentText())
            if partition_text == ' ':
                self.size_widgets[index].setText('')
            elif partition_text != None:
                self.size_widgets[index].setText(self.set_size_msg(self.partition_widgets[index]))

            # Does the Reformat checkbox make sense?
            if (partition_text == ' ' or
                partition_text not in self.part_devices):
                self.format_widgets[index].setEnabled(False)
                self.format_widgets[index].setChecked(False)
            else:
                partition = self.part_devices[partition_text]
                if partition in self.gparted_fstype:
                    self.format_widgets[index].setEnabled(False)
                    self.format_widgets[index].setChecked(True)
                else:
                    self.format_widgets[index].setEnabled(True)

            #add new row if partitions list is long enough and last row validates
            if len(get_partitions()) > len(self.partition_widgets):
                for i in range(len(self.partition_widgets)):
                    partition = self.partition_widgets[i].currentText()
                    mountpoint = self.mountpoint_widgets[i].currentText()
                    if partition is None or mountpoint == "":
                        break
                else:
                    # All table rows have been filled; create a new one.
                    self.add_mountpoint_table_row()
            index += 1

    def info_loop(self, widget):
        print "  info_loop(self, widget):"
        """check if all entries from Identification screen are filled."""

        if widget.name() == 'username' and not self.hostname_edited:
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
            self.userinterface.hostname.blockSignals(True)
            self.userinterface.hostname.setText(unicode(widget.text()) + hostname_suffix)
            self.userinterface.hostname.blockSignals(False)

        complete = True
        for name in ('fullname', 'username', 'password', 'verified_password',
                     'hostname'):
            if getattr(self.userinterface, name).text() == '':
                complete = False
        self.userinterface.next.setEnabled(complete)

    def on_hostname_insert_text(self):
        print "  on_hostname_insert_text(self):"
        self.hostname_edited = True

    def on_fullname_changed(self):
        self.info_loop(self.userinterface.fullname)

    def on_username_changed(self):
        self.info_loop(self.userinterface.username)

    def on_password_changed(self):
        self.info_loop(self.userinterface.password)

    def on_verified_password_changed(self):
        self.info_loop(self.userinterface.verified_password)

    def on_hostname_changed(self):
        self.info_loop(self.userinterface.hostname)

    def on_next_clicked(self):
        print "  on_next_clicked(self):"
        """Callback to control the installation process between steps."""

        step = self.step_name(self.get_current_page())
        print "step: " + step
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))
        self.userinterface.next.setEnabled(False)
        self.userinterface.back.setEnabled(False)
        if step == "stepKeyboardConf":
            print "is stepUserInfo"
            self.userinterface.fullname_error_image.hide()
            self.userinterface.fullname_error_reason.hide()
            self.userinterface.username_error_image.hide()
            self.userinterface.username_error_reason.hide()
            self.userinterface.password_error_image.hide()
            self.userinterface.password_error_reason.hide()
            self.userinterface.hostname_error_image.hide()
            self.userinterface.hostname_error_reason.hide()
        print "if stepuserinfo done ***"

        if self.dbfilter is not None:
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def on_keyboard_selected(self):
        print "  on_keyboard_selected(self):"
        keyboard = self.get_keyboard()
        if keyboard is not None:
            kbd_chooser.apply_keyboard(keyboard)

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
            self.userinterface.back.setEnabled(True)
        # Location
        elif step == "stepLocation":
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepKeyboardConf"])
        # Keyboard
        elif step == "stepKeyboardConf":
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepUserInfo"])
            #self.steps.next_page()
            # XXX: Actually do keyboard config here
            self.userinterface.next.setEnabled(False)
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
        print "  process_identification (self):"
        """Processing identification step tasks."""

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
                error_msg.append("The hostname may only contain letters, digits, and hyphens.")

        # showing warning message is error is set
        if len(error_msg) != 0:
            self.userinterface.hostname_error_reason.setText("\n".join(error_msg))
            self.userinterface.hostname_error_reason.show()
        else:
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

    def gparted_to_mountpoints(self):
        """Processing gparted to mountpoints step tasks."""

        self.gparted_fstype = {}
        
        print >>self.qtparted_subp.stdin, "apply"

        """
        # read gparted output of format "- FORMAT /dev/hda2 linux-swap"
        gparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        while gparted_reply.startswith('- '):
            pre_log('info', 'gparted replied: %s' % gparted_reply)
            words = gparted_reply[2:].strip().split()
            if words[0].lower() == 'format' and len(words) >= 3:
                self.gparted_fstype[words[1]] = words[2]
            gparted_reply = self.gparted_subp.stdout.readline().rstrip('\n')
        

        if not gparted_reply.startswith('0 '):
            return
        """

        # Shut down gparted
        self.qtparted_subp.stdin.close()
        self.qtparted_subp.wait()
        self.qtparted_subp = None

        self.mountpoint_table = QGridLayout(self.userinterface.mountpoint_frame, 2, 4, 11, 6)
        mountLabel = QLabel("<b>Mount Point</b>", self.userinterface.mountpoint_frame)
        sizeLabel = QLabel("<b>Size</b>", self.userinterface.mountpoint_frame)
        partitionLabel = QLabel("<b>Partition</b>", self.userinterface.mountpoint_frame)
        reformatLabel = QLabel("<b>Reformat?</b>", self.userinterface.mountpoint_frame)
        self.mountpoint_table.addWidget(mountLabel, 0, 0)
        self.mountpoint_table.addWidget(sizeLabel, 0, 1)
        self.mountpoint_table.addWidget(partitionLabel, 0, 2)
        self.mountpoint_table.addWidget(reformatLabel, 0, 3)

        # Set up list of partition names for use in the mountpoints table.
        self.partition_choices = []
        # The first element is empty to allow deselecting a partition.
        self.partition_choices.append(' ')
        for partition in get_partitions():
            partition = '/dev/' + partition
            label = part_label(partition)
            self.part_labels[partition] = label
            self.part_devices[label] = partition
            self.partition_choices.append(partition)

        # Initialise the mountpoints table.
        if len(self.mountpoint_widgets) == 0:
            self.add_mountpoint_table_row()
            

            # Try to get some default mountpoint selections.
            self.size = get_sizes()
            selection = get_default_partition_selection(
                self.size, self.gparted_fstype)

            # Setting a default partition preselection
            if len(selection.items()) == 0:
                self.userinterface.next.setEnabled(False)
            else:
                mp = { 'swap' : 0, '/' : 1 }

                # Setting default preselection values into ComboBox
                # widgets and setting size values. In addition, next row
                # is showed if they're validated.
                for mountpoint, partition in selection.items():
                    count = 0
                    while count < self.mountpoint_widgets[-1].count():
                        if self.mountpoint_widgets[-1].text(count) == mp[mountpoint]:
                            self.mountpoint_widgets[-1].setCurrentItem(count)
                        count += 1
                    self.size_widgets[-1].setText(self.set_size_msg(partition))
                    count = 0
                    while count < self.partition_widgets[-1].count():
                        if self.partition_widgets[-1].text(count) == self.partition_choices.index(partition):
                            self.partition_widgets[-1].setCurrentItem(count)
                        count += 1
                    if (mountpoint in ('swap', '/', '/usr', '/var', '/boot') or
                        partition in self.gparted_fstype):
                        self.format_widgets[-1].setChecked(True)
                    else:
                        self.format_widgets[-1].setChecked(False)
                    if partition not in self.gparted_fstype:
                        self.format_widgets[-1].setEnabled(True)
                    if len(get_partitions()) > len(self.partition_widgets):
                        self.add_mountpoint_table_row()
                    else:
                        break

            # We defer connecting up signals until now to avoid the changed
            # signal firing while we're busy populating the table.
            """
            for mountpoint in self.mountpoint_widgets:
                self.app.connect(mountpoint, SIGNAL("activated(int)"), self.on_list_changed)
            for partition in self.partition_widgets:
                self.app.connect(partition, SIGNAL("activated(int)"), self.on_list_changed)
            """

        self.userinterface.mountpoint_error_reason.hide()
        self.userinterface.mountpoint_error_image.hide()

        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartMountpoints"])

    def show_partitions(self, widget):
        print "  show_partitions(self, widget): " + widget.name()
        """write all values in this widget (GtkComboBox) from local
        partitions values."""

        from ubiquity import misc

        self.partitions = []
        partition_list = get_partitions()

        # the first element is empty to allow deselect a preselected device
        widget.clear()
        widget.insertItem(" ")
        for index in partition_list:
            print "partition:" + index
            index = '/dev/' + index
            label = misc.part_label(index)
            self.part_labels[index] = label
            self.part_devices[label] = index
            widget.insertItem(self.part_labels[index])
            self.partitions.append(index)

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
        """Processing mountpoints to summary step tasks."""

        # Validating self.mountpoints
        error_msg = []

        mountpoints = {}
        for i in range(len(self.mountpoint_widgets)):
            mountpoint_value = str(self.mountpoint_widgets[i].currentText())
            partition_value = str(self.partition_widgets[i].currentText())
            if partition_value is not None:
                partition_id = self.part_devices[partition_value]
            else:
                partition_id = None
            format_value = self.format_widgets[i].isChecked()
            fstype = None
            if partition_id in self.gparted_fstype:
                fstype = self.gparted_fstype[partition_id]

            if mountpoint_value == "":
                if partition_value in (None, ' '):
                    continue
                else:
                    error_msg.append(
                        "No mount point selected for %s." % partition_value)
                    break
            else:
                if partition_value in (None, ' '):
                    error_msg.append(
                        "No partition selected for %s." % mountpoint_value)
                    break
                else:
                    mountpoints[partition_id] = (mountpoint_value,
                                                 format_value, fstype)
        else:
            self.mountpoints = mountpoints
        pre_log('info', 'mountpoints: %s' % self.mountpoints)

        # Checking duplicated devices
        partitions = [w.currentText() for w in self.partition_widgets]

        for check in partitions:
            if partitions.count(check) > 1:
                error_msg.append("A partition is assigned to more than one "
                                 "mount point.")
                break

        # Processing more validation stuff
        if len(self.mountpoints) > 0:
            for check in validation.check_mountpoint(self.mountpoints,
                                                     self.size):
                if check == validation.MOUNTPOINT_NOROOT:
                    error_msg.append(get_string(
                        'partman-target/no_root', self.locale))
                elif check == validation.MOUNTPOINT_DUPPATH:
                    error_msg.append("Two file systems are assigned the same "
                                     "mount point.")
                elif check == validation.MOUNTPOINT_BADSIZE:
                    for mountpoint, format, fstype in \
                            self.mountpoints.itervalues():
                        if mountpoint == 'swap':
                            min_root = MINIMAL_PARTITION_SCHEME['root']
                            break
                    else:
                        min_root = (MINIMAL_PARTITION_SCHEME['root'] +
                                    MINIMAL_PARTITION_SCHEME['swap'] * 1024)
                    error_msg.append("The partition assigned to '/' is too "
                                     "small (minimum size: %d Mb)." % min_root)
                elif check == validation.MOUNTPOINT_BADCHAR:
                    error_msg.append(get_string(
                        'partman-basicfilesystems/bad_mountpoint',
                        self.locale))

        # showing warning messages
        self.userinterface.mountpoint_error_reason.setText("\n".join(error_msg))
        if len(error_msg) != 0:
            self.userinterface.mountpoint_error_reason.show()
            self.userinterface.mountpoint_error_image.show()
            return
        else:
            self.userinterface.mountpoint_error_reason.hide()
            self.userinterface.mountpoint_error_image.hide()
        
        """

        gvm_automount_drives = '/desktop/gnome/volume_manager/automount_drives'
        gvm_automount_media = '/desktop/gnome/volume_manager/automount_media'
        gconf_dir = 'xml:readwrite:%s' % os.path.expanduser('~/.gconf')
        gconf_previous = {}
        for gconf_key in (gvm_automount_drives, gvm_automount_media):
            subp = subprocess.Popen(['gconftool-2', '--config-source',
                                     gconf_dir, '--get', gconf_key],
                                    stdout=subprocess.PIPE,
                                    stderr=subprocess.PIPE)
            gconf_previous[gconf_key] = subp.communicate()[0].rstrip('\n')
            if gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                 '--type', 'bool', 'false'])
        """

        if partman_commit.PartmanCommit(self).run_command(auto_process=True) != 0:
            return

        """
        for gconf_key in (gvm_automount_drives, gvm_automount_media):
            if gconf_previous[gconf_key] == '':
                subprocess.call(['gconftool-2', '--unset', gconf_key])
            elif gconf_previous[gconf_key] != 'false':
                subprocess.call(['gconftool-2', '--set', gconf_key,
                                 '--type', 'bool', gconf_previous[gconf_key]])
        """

        # Since we've successfully committed partitioning, the install
        # progress bar should now be displayed, so we can go straight on to
        # the installation now.
        self.progress_loop()

    def on_back_clicked(self):
        print "  on_back_clicked(self, widget):"
        """Callback to set previous screen."""

        self.backup = True

        # Enabling next button
        self.userinterface.next.setEnabled(True)
        # Setting actual step
        step = self.step_name(self.get_current_page())
        print "step: " + step
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))
        
        changed_page = False

        if step == "stepLocation":
            self.userinterface.back.setEnabled(False)
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
            self.userinterface.next.setText("Next >")
        if not changed_page:
            self.userinterface.widgetStack.raiseWidget(self.get_current_page() - 1)
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def on_language_treeview_selection_changed (self):
        print "  on_language_treeview_selection_changed (self, selection):"
        selection = self.userinterface.language_treeview.selectedItem()
        print "selection: " + str(selection)
        if selection is not None:
            print "selection is not None"
            value = unicode(selection.text(0))
            lang = self.language_choice_map[value][1]
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            for widget in (self.userinterface, self.userinterface.welcome_heading_label, self.userinterface.welcome_text_label, self.userinterface.next, self.userinterface.back, self.userinterface.cancel):
                print "translating widget"
                self.translate_widget(widget, lang)

    def on_timezone_time_adjust_clicked (self):
        print "  on_timezone_time_adjust_clicked (self):"
        #invisible = gtk.Invisible()
        #invisible.grab_add()
        time_admin_env = dict(os.environ)
        tz = self.tzmap.get_selected_tz_name()
        if tz is not None:
            time_admin_env['TZ'] = tz
        time_admin_subp = subprocess.Popen(["kcmshell", "clock"], env=time_admin_env)
        #gobject.child_watch_add(time_admin_subp.pid, self.on_time_admin_exit,
        #                        invisible)

    # returns the current wizard page
    def get_current_page(self):
      return self.userinterface.widgetStack.id(self.userinterface.widgetStack.visibleWidget())

    def on_steps_switch_page(self, newPageID):
        print "  on_steps_switch_page(title): " + str(self.get_current_page()) + " " + str(newPageID)

        self.set_current_page(newPageID)
        current_name = self.step_name(self.get_current_page())

    def on_autopartition_resize_toggled (self, enable):
        print "  on_autopartition_resize_toggled (self, widget):"
        """Update autopartitioning screen when the resize button is
        selected."""

        self.userinterface.new_size_frame.setEnabled(enable)
        self.userinterface.new_size_scale.setEnabled(enable)
        
    def update_new_size_label(self, value):
        self.userinterface.new_size_value.setText(str(value) + "%")
        ##     def on_abort_dialog_close (self, widget):

        ##         """ Disable automatic partitioning and reset partitioning method step. """

        ##         sys.stderr.write ('\non_abort_dialog_close.\n\n')

        ##         self.discard_automatic_partitioning = True
        ##         self.on_drives_changed (None)


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
            total_steps = progress_max - progress_min
            self.progressDialogue = QProgressDialog(progress_title, "Cancel", total_steps, self.userinterface, "progressdialog", True)
            #self.progressDialogue = KProgressDialog(self.userinterface, "progressdialog", progress_title, "", True)
            # FIXME jr self.debconf_progress_window.set_title(progress_title)
        
        #self.progressDialogue.setLabelText(progress_title)

        self.progress_position.start(progress_min, progress_max)
        self.debconf_progress_set(0)
        self.progressDialogue.show()
        return True

    def debconf_progress_set (self, progress_val):
        print "  debconf_progress_set (self, progress_val):"
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        self.progress_position.set(progress_val)
        self.progressDialogue.setProgress(progress_val)
        #fraction = self.progress_position.fraction()
        #self.progress_bar.set_fraction(fraction)
        #self.progress_bar.set_text('%s%%' % int(fraction * 100))
        return True

    def debconf_progress_step (self, progress_inc):
        print "  debconf_progress_step (self, progress_inc): " + str(progress_inc)
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        self.progress_position.step(progress_inc)
        newValue = self.progressDialogue.progress() + progress_inc
        self.progressDialogue.setProgress(newValue)
        return True

    def debconf_progress_info (self, progress_info):
        print "  debconf_progress_info (self, progress_info):"
        self.progress_cancelled = self.progressDialogue.wasCancelled()
        if self.progress_cancelled:
            return False
        self.progressDialogue.setLabelText(progress_info)
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
            #FIXME jr self.progressDialogue.showCancelButton(True)
            pass
        else:
            #self.progressDialogue.showCancelButton(False)
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

    def set_language_choices (self, choices, choice_map):
        print "  set_language_choices (self, choices, choice_map):"
        self.language_choice_map = dict(choice_map)
        self.userinterface.language_treeview.clear()
        for choice in choices:
            self.userinterface.language_treeview.insertItem( KListViewItem(self.userinterface.language_treeview, QString(unicode(choice))) )

    def set_language (self, language):
        print "  set_language (self, language): " #+ language
        iterator = QListViewItemIterator(self.userinterface.language_treeview)
        while iterator.current():
            #print "text: " + unicode(iterator.current().text(0))
            #if unicode(str(iterator.current().text(0).ascii()), 'utf-8') == language:
            selection = iterator.current()
            if selection is None:
                value = "C"
            else:
                value = unicode(selection.text(0))
            if value == language:
                self.userinterface.language_treeview.setSelected(iterator.current(), True)
                break
            iterator += 1

    def get_language (self):
        print "  get_language (self):"
        selection = self.userinterface.language_treeview.selectedItem()
        if selection is None:
            print "returning C"
            return 'C'
        else:
            value = unicode(selection.text(0))
            print "returning: " + self.language_choice_map[value][0]
            return self.language_choice_map[value][0]

    def set_timezone (self, timezone):
        print "  set_timezone (self, timezone): " + timezone + "<<"
        self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        print "  get_timezone (self):"
        return self.tzmap.get_selected_tz_name()

    def set_fullname(self, value):
        print "  set_fullname(self, value):"
        self.userinterface.fullname.setText(unicode(value, "UTF-8"))

    def get_fullname(self):
        print "  get_fullname(self):"
        return unicode(self.userinterface.fullname.text())

    def set_username(self, value):
        print "  set_username(self, value):"
        self.userinterface.username.setText(unicode(value, "UTF-8"))

    def get_username(self):
        print "  get_username(self):"
        return unicode(self.userinterface.username.text())
  
    def get_password(self):
        print "  get_password(self):"
        return unicode(self.userinterface.password.text())
  
    def get_verified_password(self):
        print "  get_verified_password(self):"
        return unicode(self.userinterface.verified_password.text())

    def username_error(self, msg):
        print "  username_error(self, msg):"
        self.userinterface.username_error_reason.setText(msg)
        self.userinterface.username_error_image.show()
        self.userinterface.username_error_reason.show()

    def password_error(self, msg):
        print "  password_error(self, msg):"
        self.userinterface.password_error_reason.setText(msg)
        self.userinterface.password_error_image.show()
        self.userinterface.password_error_reason.show()

    def set_disk_choices (self, choices, manual_choice):
        print "  set_disk_choices (self, choices, manual_choice):"
        children = self.userinterface.part_disk_frame.children()
        for child in children:
            if isinstance(child, QVBoxLayout):
                pass
            else:
                print child.name()
                print str(child)
                self.part_disk_vbox.remove(child)
                child.hide()

        self.manual_choice = manual_choice
        firstbutton = None
        for choice in choices:
            if choice == '':
                pass  #FIXME add a spacer
            else:
                button = QRadioButton(choice, self.userinterface.part_disk_frame)
                self.part_disk_buttongroup.insert(button)
                id = self.part_disk_buttongroup.id(button)
                #Qt changes the string by adding accelarators, 
                #so keep pristine string here as is returned later to partman
                self.part_disk_buttongroup_texts[id] = choice
                if firstbutton is None:
                    firstbutton = button
                self.part_disk_vbox.addWidget(button)
                button.show()

        if firstbutton is not None:
            firstbutton.setChecked(True)

        # make sure we're on the disk selection page
        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartDisk"])

        return True

    def get_disk_choice (self):
        print "  get_disk_choice (self): "
        id = self.part_disk_buttongroup.id( self.part_disk_buttongroup.selected() )
        return unicode(self.part_disk_buttongroup_texts[id])

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

    def get_autopartition_choice (self):
        print "  get_autopartition_choice (self): "
        id = self.autopartition_buttongroup.id( self.autopartition_buttongroup.selected() )
        return unicode(self.autopartition_buttongroup_texts[id])

    def set_autopartition_resize_min_percent (self, min_percent):
        print "  set_autopartition_resize_min_percent (self, min_percent):"
        self.userinterface.new_size_scale.setMinValue(min_percent)
        self.userinterface.new_size_scale.setMaxValue(100)

    def get_autopartition_resize_percent (self):
        print "  get_autopartition_resize_percent (self):"
        return self.userinterface.new_size_scale.value()

    def get_hostname (self):
        return unicode(self.userinterface.hostname.text())

    def get_mountpoints (self):
        return dict(self.mountpoints)

    def confirm_partitioning_dialog (self, title, description):
        print "  confirm_partitioning_dialog (self, title, description):"
        # TODO cjwatson 2006-03-10: Duplication of page logic; I think some
        # of this can go away once we reorganise page handling not to invoke
        # a main loop for each page.
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))
        self.userinterface.next.setText("Install") # TODO i18n
        self.previous_partitioning_page = self.get_current_page()
        self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepReady"])

        save_dbfilter = self.dbfilter
        save_backup = self.backup
        self.dbfilter = summary.Summary(self, description)
        self.backup = False

        # Since the partitioner is still running, we need to use a different
        # database to run the summary page. Fortunately, nothing we set in
        # the summary script needs to persist, so we can just use a
        # throwaway database.
        save_replace, save_override = None, None
        if 'DEBCONF_DB_REPLACE' in os.environ:
            save_replace = os.environ['DEBCONF_DB_REPLACE']
        if 'DEBCONF_DB_OVERRIDE' in os.environ:
            save_override = os.environ['DEBCONF_DB_OVERRIDE']
        os.environ['DEBCONF_DB_REPLACE'] = 'configdb'
        os.environ['DEBCONF_DB_OVERRIDE'] = 'Pipe{infd:none outfd:none}'
        self.dbfilter.run_command(auto_process=True)
        if save_replace is None:
            del os.environ['DEBCONF_DB_REPLACE']
        else:
            os.environ['DEBCONF_DB_REPLACE'] = save_replace
        if save_override is None:
            del os.environ['DEBCONF_DB_OVERRIDE']
        else:
            os.environ['DEBCONF_DB_OVERRIDE'] = save_override

        self.dbfilter = save_dbfilter

        if self.current_page is None:
            print "current page none, install cancelled"
            # installation cancelled; partman should return ASAP after this
            return False

        if self.backup:
            self.userinterface.widgetStack.raiseWidget(self.previous_partitioning_page)
            self.userinterface.next.setText("Next >")
            return False
        # TODO should this not just force self.backup = False?
        self.backup = save_backup

        # The user said OK, so we're going to start the installation proper
        # now. We therefore have to put up the installation progress bar,
        # return control to partman to do the partitioning in a region of
        # that, and then let whatever started partman drop through to
        # progress_loop.
        # Yes, the control flow is pretty tortuous here. Sorry!

        #self.live_installer.hide()
        self.current_page = None
        self.debconf_progress_start(
            0, 100, get_string('ubiquity/install/title', self.locale))
        self.debconf_progress_region(0, 15)
        self.installing = True

        return True


    def set_keyboard_choices(self, choicemap):
        print "  set_keyboard_choices(self, choicemap):"
        self.keyboard_choice_map = choicemap
        choices = choicemap.keys()

        self.userinterface.keyboardlistview.clear()
        for choice in sorted(choices):
            self.userinterface.keyboardlistview.insertItem( KListViewItem(self.userinterface.keyboardlistview, choice) )

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
            return None
        else:
            value = unicode(selection.text(0))
            return self.keyboard_choice_map[value]

    def set_summary_text (self, text):
        print "  set_summary_text (self, text):"
        self.userinterface.ready_text.setText(text)

    def return_to_autopartitioning (self):
        """Return from the install progress bar to autopartitioning."""
        if self.installing:
            # Go back to the autopartitioner and try again.
            # TODO self.previous_partitioning_page
            #self.live_installer.show()
            self.userinterface.widgetStack.raiseWidget(WIDGET_STACK_STEPS["stepPartDisk"])
            self.userinterface.next.setText("Next >")
            self.backup = True
            self.installing = False

    def error_dialog (self, msg):
        print "  error_dialog (self, msg):"
        self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
        # TODO: cancel button as well if capb backup
        QMessageBox.warning(self.userinterface, "Error", msg, QMessageBox.Ok)
        self.return_to_autopartitioning()

    def question_dialog (self, title, msg, option_templates):
        print "  question_dialog (self, title, msg, option_templates):"

        # I doubt we'll ever need more than three buttons.
        assert len(option_templates) <= 3, option_templates

        self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
        buttons = []
        for option_template in option_templates:
            text = get_string(option_template, self.locale)
            if text is None:
                text = option_template
            buttons.append(text)
        # Convention for option_templates is to have the affirmative action
        # last; KDE convention is to have it first.
        affirmative = buttons.pop()
        buttons.insert(0, affirmative)

        response = QMessageBox.question(self.userinterface, title, msg,
                                        *buttons)

        if response < 0:
            return None
        elif response == 0:
            return option_templates[len(buttons) - 1]
        else:
            return option_templates[response - 1]

    def refresh (self):
        print "  refresh (self):"
        self.app.processEvents(1)
        """
        while gtk.events_pending():
            gtk.main_iteration()
        """
    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        print "  run_main_loop()"
        self.userinterface.setCursor(QCursor(Qt.ArrowCursor))
        self.userinterface.next.setEnabled(True)
        step = self.step_name(self.get_current_page())
        if not (step == "stepIntro" or step == "stepLanguage"):
            self.userinterface.back.setEnabled(True)
        self.app.exec_loop()

    # Return control to the next level up.
    def quit_main_loop (self):
        print "  quit_main_loop()"
        self.app.exit()


class TimezoneMap(object):
    def __init__(self, frontend):
        print "  TimezoneMap.__init__(self, frontend):"
        self.frontend = frontend
        self.tzdb = ubiquity.tz.Database()
        #self.tzmap = ubiquity.emap.EMap()
        self.update_timeout = None
        self.point_selected = None
        self.point_hover = None
        self.location_selected = None

        """
        zoom_in_file = os.path.join(GLADEDIR, 'pixmaps', self.frontend.distro,
                                    'zoom-in.png')
        if os.path.exists(zoom_in_file):
            display = self.frontend.live_installer.get_display()
            pixbuf = gtk.gdk.pixbuf_new_from_file(zoom_in_file)
            self.cursor_zoom_in = gtk.gdk.Cursor(display, pixbuf, 10, 10)
        else:
            self.cursor_zoom_in = None

        self.tzmap.add_events(gtk.gdk.LEAVE_NOTIFY_MASK |
                              gtk.gdk.VISIBILITY_NOTIFY_MASK)

        self.frontend.timezone_map_window.add(self.tzmap)
        """

        timezone_city_combo = self.frontend.userinterface.timezone_city_combo
        self.timezone_city_index = {}  #map human readable city name to Europe/London style zone

        prev_continent = ''
        for location in self.tzdb.locations:
            #self.tzmap.add_point("", location.longitude, location.latitude,
            #                     NORMAL_RGBA)
            zone_bits = location.zone.split('/')
            if len(zone_bits) == 1:
                continue
            continent = zone_bits[0]
            if continent != prev_continent:
                timezone_city_combo.insertItem('')
                timezone_city_combo.insertItem("--- %s ---" % continent)
                prev_continent = continent
            human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
            timezone_city_combo.insertItem(human_zone)
            self.timezone_city_index[human_zone] = location.zone

        #self.tzmap.connect("map-event", self.mapped)
        #self.tzmap.connect("unmap-event", self.unmapped)
        #self.tzmap.connect("motion-notify-event", self.motion)
        #self.tzmap.connect("button-press-event", self.button_pressed)
        #self.tzmap.connect("leave-notify-event", self.out_map)

        #timezone_city_combo.connect("changed", self.city_changed)
        self.mapped()

    def set_city_text(self, name):
        """ Gets a long name, Europe/London """
        print "  set_city_text(self, name): " + name
        timezone_city_combo = self.frontend.userinterface.timezone_city_combo
        count = timezone_city_combo.count()
        found = False
        i = 0
        zone_bits = name.split('/')
        human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
        while not found and i < count:
            if str(timezone_city_combo.text(i)) == human_zone:
                timezone_city_combo.setCurrentItem(i)
                found = True
            i += 1

    def set_zone_text(self, location):
        offset = location.utc_offset
        if offset >= datetime.timedelta(0):
            minuteoffset = int(offset.seconds / 60)
        else:
            minuteoffset = int(offset.seconds / 60 - 1440)
        if location.zone_letters == 'GMT':
            text = location.zone_letters
        else:
            text = "%s (GMT%+d:%02d)" % (location.zone_letters,
                                         minuteoffset / 60, minuteoffset % 60)
        self.frontend.userinterface.timezone_zone_text.setText(text)
        translations = gettext.translation('iso_3166',
                                           languages=[self.frontend.locale],
                                           fallback=True)
        self.frontend.userinterface.timezone_country_text.setText(translations.ugettext(location.human_country))
        self.update_current_time()

    def update_current_time(self):
        if self.location_selected is not None:
            now = datetime.datetime.now(self.location_selected.info)
            self.frontend.userinterface.timezone_time_text.setText(unicode(now.strftime('%X'), "utf-8"))

    def set_tz_from_name(self, name):
        print "  set_tz_from_name(self, name): " + name
        """ Gets a long name, Europe/London """

        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        #if self.point_selected is not None:
        #    self.tzmap.point_set_color_rgba(self.point_selected, NORMAL_RGBA)

        #self.point_selected = self.tzmap.get_closest_point(longitude, latitude,
        #                                                   False)


        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)

        if name == None or name == "":
            return

    def get_tz_from_name(self, name):
        print "  set_tz_from_name(self, name): " + name
        return self.timezone_city_index[name]

    def city_combo_changed(self, index):
        print "  city_combo_changed"
        city = str(self.frontend.userinterface.timezone_city_combo.currentText())
        try:
            zone = self.timezone_city_index[city]
        except KeyError:
            return
        self.set_tz_from_name(zone)

    def get_selected_tz_name(self):
        name = str(self.frontend.userinterface.timezone_city_combo.currentText())
        return self.get_tz_from_name(name)

    def timeout(self):
        self.update_current_time()
        """

        if self.point_selected is None:
            return True

        if self.point_selected.get_color_rgba() == SELECTED_1_RGBA:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_2_RGBA)
        else:
            self.tzmap.point_set_color_rgba(self.point_selected,
                                            SELECTED_1_RGBA)
        """

        return True

    def mapped(self):
        if self.update_timeout is None:
            self.update_timeout = QTimer()
            self.frontend.app.connect(self.update_timeout, SIGNAL("timeout()"), self.timeout)
            self.update_timeout.start(100)
