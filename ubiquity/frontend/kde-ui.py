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

import sys
#from qt import *
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
#from kdeui import *
#from kdecore import *
#from kio import KRun
#import kdedesigner
##from ubiquity.frontend.liveinstaller import Ui_UbiquityUIBase
#FIXMEfrom ubiquity.frontend.crashdialog import CrashDialog

import os
import datetime
import subprocess
import math
import traceback
import syslog

import gettext

try:
    from debconf import DebconfCommunicator
except ImportError:
    from ubiquity.debconfcommunicator import DebconfCommunicator

from ubiquity import filteredcommand, validation
from ubiquity.misc import *
from ubiquity.settings import *
from ubiquity.components import console_setup, language, timezone, usersetup, \
                                partman_auto, partman_commit, summary, install
import ubiquity.tz
import ubiquity.progressposition

# Define global path
PATH = '/usr/share/ubiquity'

# Define locale path
LOCALEDIR = "/usr/share/locale"

BREADCRUMB_STEPS = {
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "stepUserInfo": 4,
    "stepPartAuto": 5,
    "stepPartAdvanced": 5,
    "stepPartMountpoints": 5,
    "stepReady": 6
}
BREADCRUMB_MAX_STEP = 6

WIDGET_STACK_STEPS = {
    "stepWelcome": 0,
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "stepUserInfo": 4,
    "stepPartAuto": 5,
    "stepPartAdvanced": 6,
    "stepPartMountpoints": 7,
    "stepReady": 8
}

class UbiquityUI(QWidget):

    def __init__(self):
        QWidget.__init__(self)
        uic.loadUi("ubiquity/frontend/liveinstaller.ui", self)
#        Ui_UbiquityUIBase.__init__(self)

    def setWizard(self, wizardRef):
        self.wizard = wizardRef

    def closeEvent(self, event):
        self.wizard.on_cancel_clicked()

class Wizard:

    def __init__(self, distro):
        sys.excepthook = self.excepthook

        #about=KAboutData("kubuntu-ubiquity","Installer","0.1","Live CD Installer for Kubuntu",KAboutData.License_GPL,"(c) 2006 Canonical Ltd", "http://wiki.kubuntu.org/KubuntuUbiquity", "jriddell@ubuntu.com")
        #about.addAuthor("Jonathan Riddell", None,"jriddell@ubuntu.com")
        #KCmdLineArgs.init(["./installer"],about)

        #self.app = KApplication()

        self.app = QApplication([])

        self.userinterface = UbiquityUI()
        self.userinterface.setWizard(self)
        #self.app.setMainWidget(self.userinterface)
        self.userinterface.show()

        # declare attributes
        self.distro = distro
        self.current_layout = None
        self.password = ''
        self.hostname_edited = False
        self.auto_mountpoints = None
        self.resize_min_size = None
        self.resize_max_size = None
        self.resize_choice = None
        self.manual_choice = None
        self.manual_partitioning = False
        self.new_size_value = None
        self.new_size_scale = None
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
        self.progressDialogue = None
        self.progress_position = ubiquity.progressposition.ProgressPosition()
        self.progress_cancelled = False
        self.previous_partitioning_page = None
        # TODO cjwatson 2006-09-04: replace this by a button
        self.summary_device = ''
        self.installing = False
        self.returncode = 0
        self.language_questions = ('live_installer', 'welcome_heading_label',
                                   'welcome_text_label', 'step_label',
                                   'cancel', 'back', 'next')
        self.allowed_change_step = True
        self.allowed_go_forward = True
        self.mainLoopRunning = False

        self.laptop = ex("laptop-detect")
        self.qtparted_subp = None

        # set default language
        dbfilter = language.Language(self, DebconfCommunicator('ubiquity',
                                                               cloexec=True))
        dbfilter.cleanup()
        dbfilter.db.shutdown()

        self.debconf_callbacks = {}    # array to keep callback functions needed by debconf file descriptors

        self.translate_widgets()

        self.map_vbox = QVBoxLayout(self.userinterface.map_frame)

        self.customize_installer()

        self.autopartition_vbox = QVBoxLayout(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup = QButtonGroup(self.userinterface.autopartition_frame)
        self.autopartition_buttongroup_texts = {}
        self.autopartition_extras = {}
        self.autopartition_extra_buttongroup = {}
        self.autopartition_extra_buttongroup_texts = {}

        self.qtparted_vbox = QVBoxLayout(self.userinterface.qtparted_frame)
        self.embed = None

        self.mount_vbox = QVBoxLayout(self.userinterface.mountpoint_frame_parent)
        #self.mountpoint_scrollview = QScrollView(self.userinterface.mountpoint_frame_parent)
        self.mountpoint_scrollview = QScrollArea(self.userinterface.mountpoint_frame_parent)
        self.mount_vbox.addWidget(self.mountpoint_scrollview)
        self.mountpoint_scrollview.setWidgetResizable(True)
        self.userinterface.mountpoint_frame = QFrame(self.mountpoint_scrollview)
        self.userinterface.mountpoint_frame.setFrameShape(QFrame.NoFrame)
        self.userinterface.mountpoint_frame.setFrameShadow(QFrame.Plain)
        self.mountpoint_scrollview.setFrameShape(QFrame.NoFrame)
        self.mountpoint_scrollview.setFrameShadow(QFrame.Plain)
        #self.mountpoint_scrollview.addChild(self.userinterface.mountpoint_frame)
        self.mountpoint_scrollview.setWidget(self.userinterface.mountpoint_frame)
        self.userinterface.mountpoint_frame.resize(100, 100)
        self.mountpoint_vbox = QVBoxLayout(self.userinterface.mountpoint_frame)
        self.mountpoint_table = QGridLayout()
        self.mountpoint_vbox.addLayout(self.mountpoint_table)
        self.mountpoint_vbox.addStretch()

        summary_vbox = QVBoxLayout(self.userinterface.summary_frame)
        ##FIXMEself.ready_text = UbiquityTextEdit(self, self.userinterface.summary_frame)
        ##self.ready_text.setReadOnly(True)
        ##self.ready_text.setTextFormat(Qt.RichText)
        ##summary_vbox.addWidget(self.ready_text)

    def excepthook(self, exctype, excvalue, exctb):
        """Crash handler."""

        if (issubclass(exctype, KeyboardInterrupt) or
            issubclass(exctype, SystemExit)):
            return

        tbtext = ''.join(traceback.format_exception(exctype, excvalue, exctb))
        syslog.syslog(syslog.LOG_ERR,
                      "Exception in KDE frontend (invoking crash handler):")
        for line in tbtext.split('\n'):
            syslog.syslog(syslog.LOG_ERR, line)
        print >>sys.stderr, ("Exception in KDE frontend"
                             " (invoking crash handler):")
        print >>sys.stderr, tbtext

        #dialog = CrashDialog(self.userinterface)
        dialog = QDialog(self.userinterface)
        uic.loadUi("ubiquity/frontend/crashdialog.ui", dialog)
        ##FIXMEdialog.connect(dialog.beastie_url, SIGNAL("leftClickedURL(const QString&)"), self.openURL)
        dialog.crash_detail.setText(tbtext)
        dialog.exec_()
        sys.exit(1)

    def openURL(self, url):
        #need to run this else kdesu can't run Konqueror
        ex('su', 'ubuntu', 'xhost', '+localhost')
        KRun.runURL(KURL(url), "text/html")

    def run(self):
        """run the interface."""

        if os.getuid() != 0:
                title = ('This installer must be run with administrative privileges, and cannot continue without them.')
                result = QMessageBox.critical(self.userinterface, "Must be root", title)

                sys.exit(1)

        # show interface
        # TODO cjwatson 2005-12-20: Disabled for now because this segfaults in
        # current dapper (https://bugzilla.ubuntu.com/show_bug.cgi?id=20338).
        #self.show_browser()
        got_intro = self.show_intro()
        self.allow_change_step(True)

        # Declare SignalHandler
        self.app.connect(self.userinterface.next, SIGNAL("clicked()"), self.on_next_clicked)
        """
        self.app.connect(self.userinterface.back, SIGNAL("clicked()"), self.on_back_clicked)
        self.app.connect(self.userinterface.cancel, SIGNAL("clicked()"), self.on_cancel_clicked)
        #self.app.connect(self.userinterface.widgetStack, SIGNAL("aboutToShow(int)"), self.on_steps_switch_page)
        self.app.connect(self.userinterface.keyboardlayoutview, SIGNAL("selectionChanged()"), self.on_keyboard_layout_selected)
        self.app.connect(self.userinterface.keyboardvariantview, SIGNAL("selectionChanged()"), self.on_keyboard_variant_selected)

        """
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
        """

        self.app.connect(self.userinterface.language_treeview, SIGNAL("selectionChanged()"), self.on_language_treeview_selection_changed)

        self.app.connect(self.userinterface.timezone_time_adjust, SIGNAL("clicked()"), self.on_timezone_time_adjust_clicked)

        self.app.connect(self.userinterface.timezone_city_combo, SIGNAL("activated(int)"), self.tzmap.city_combo_changed)
        """

        # Start the interface
        if got_intro:
            print "got intro"
            global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
            for step in BREADCRUMB_STEPS:
                BREADCRUMB_STEPS[step] += 1
            BREADCRUMB_STEPS["stepWelcome"] = 1
            BREADCRUMB_MAX_STEP += 1
            first_step = "stepWelcome"
        else:
            print "not got_intro"
            first_step = "stepLanguage"
        self.set_current_page(WIDGET_STACK_STEPS[first_step])

        while self.current_page is not None:
            if not self.installing:
                # Make sure any started progress bars are stopped.
                while self.progress_position.depth() != 0:
                    self.debconf_progress_stop()

            self.backup = False
            current_name = self.step_name(self.current_page)
            print "name: " + current_name + " page: " + str(self.current_page)
            old_dbfilter = self.dbfilter
            if current_name == "stepLanguage":
                print "setting dbfilter to stepLanguage"
                self.dbfilter = language.Language(self)
            elif current_name == "stepLocation":
                self.dbfilter = timezone.Timezone(self)
            elif current_name == "stepKeyboardConf":
                self.dbfilter = console_setup.ConsoleSetup(self)
            elif current_name == "stepUserInfo":
                self.dbfilter = usersetup.UserSetup(self)
            elif current_name == "stepPartAuto":
                self.dbfilter = partman_auto.PartmanAuto(self)
            elif current_name == "stepReady":
                self.dbfilter = summary.Summary(self, self.manual_partitioning)
            else:
                print "no dbfilter"
                self.dbfilter = None

            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                self.allow_change_step(False)
                print "starting dbfilter"
                self.dbfilter.start(auto_process=True)
            else:
                self.allow_change_step(not self.installing)

            print "EXEC in run()"
            #self.mainLoopRunning = True
            self.app.exec_()
            #self.mainLoopRunning = False
            print "EXEC in run() done"

            if self.installing:
                self.progress_loop()
            elif self.current_page is not None and not self.backup:
                self.process_step()
            self.app.processEvents()

        return self.returncode

    def customize_installer(self):
        """Initial UI setup."""

        #iconLoader = KIconLoader()
        #icon = iconLoader.loadIcon("system", KIcon.Small)
        #self.userinterface.logo_image.setPixmap(icon)
        self.userinterface.back.hide()

        """

        PIXMAPSDIR = os.path.join(PATH, 'pixmaps', self.distro)

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

        ##FIXMEself.tzmap = TimezoneMap(self)
        #self.tzmap.tzmap.show()

    def translate_widgets(self, parentWidget=None):
        if self.locale is None:
            languages = []
        else:
            languages = [self.locale]
        get_translations(languages=languages,
                         core_names=['ubiquity/text/%s' % q
                                     for q in self.language_questions])

        self.translate_widget_children(parentWidget)

    def translate_widget_children(self, parentWidget=None):
        if parentWidget == None:
            parentWidget = self.userinterface

        if parentWidget.children() != None:
            for widget in parentWidget.children():
                self.translate_widget(widget, self.locale)
                self.translate_widget_children(widget)

    def translate_widget(self, widget, lang):
        #print "translate_widget" + widget.objectName()
        #FIXME how to do in KDE?  use kstdactions?
        #if isinstance(widget, gtk.Button) and widget.get_use_stock():
        #    widget.set_label(widget.get_label())

        text = get_string(widget.objectName(), lang)

        if widget.objectName() == "next":
            ##FIXMEtext = get_string("continue", lang) + " >"
            text = "Next >"
        elif widget.objectName() == "back":
            ##FIXEtext = "< " + get_string("go_back", lang)
            text = "< Back"
        if text is None:
            return

        if isinstance(widget, QLabel):
            name = widget.objectName()

            if name == 'step_label':
                global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
                curstep = '?'
                if self.current_page is not None:
                    current_name = self.step_name(self.current_page)
                    if current_name in BREADCRUMB_STEPS:
                        curstep = str(BREADCRUMB_STEPS[current_name])
                text = text.replace('${INDEX}', curstep)
                text = text.replace('${TOTAL}', str(BREADCRUMB_MAX_STEP))

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

        ##FIXME
        elif isinstance(widget, QWidget) and widget.objectName() == UbiquityUIBase:
            widget.setCaption(text)

    def set_current_page(self, current):
        print "set_current_page to " + str(current)
        widget = self.userinterface.widgetStack.widget(current)
        if self.userinterface.widgetStack.currentWidget() == widget:
            # self.userinterface.widgetStack.raiseWidget() will do nothing.
            # Update state ourselves.
            self.on_steps_switch_page(current)
        else:
            #self.userinterface.widgetStack.raiseWidget(widget)
            self.userinterface.widgetStack.setCurrentWidget(widget)
            self.on_steps_switch_page(current)

    def on_steps_switch_page(self, newPageID):
        print "on_steps_switch_page, setting to: " + str(newPageID)
        self.current_page = newPageID
        ##FIXMEself.translate_widget(self.userinterface.step_label, self.locale)
        syslog.syslog('switched to page %s' % self.step_name(newPageID))

    def step_name(self, step_index):
        if step_index < 0:
            step_index = 0
        #return WIDGET_STACK_STEPS[step_index]
        return str(self.userinterface.widgetStack.widget(step_index).objectName())

    def allow_change_step(self, allowed):
        if allowed:
            cursor = QCursor(Qt.ArrowCursor)
        else:
            cursor = QCursor(Qt.WaitCursor)
        self.userinterface.setCursor(cursor)
        self.userinterface.back.setEnabled(allowed)
        self.userinterface.next.setEnabled(allowed and self.allowed_go_forward)
        self.allowed_change_step = allowed

    def allow_go_forward(self, allowed):
        self.userinterface.next.setEnabled(allowed and self.allowed_change_step)
        self.allowed_go_forward = allowed

    def show_intro(self):
        """Show some introductory text, if available."""

        intro = os.path.join(PATH, 'intro.txt')

        if os.path.isfile(intro):
            intro_file = open(intro)
            text = ""
            for line in intro_file:
                text = text + line + "<br>"
            self.userinterface.introLabel.setText(text)
            intro_file.close()
            return True
        else:
            return False

    def progress_loop(self):
        """prepare, copy and config the system in the core install process."""

        syslog.syslog('progress_loop()')

        self.current_page = None

        self.debconf_progress_start(
            0, 100, get_string('ubiquity/install/title', self.locale))
        self.debconf_progress_region(0, 15)

        ex('dcop', 'kded', 'kded', 'unloadModule', 'medianotifier')

        dbfilter = partman_commit.PartmanCommit(self, self.manual_partitioning)
        if dbfilter.run_command(auto_process=True) != 0:
            # TODO cjwatson 2006-09-03: return to partitioning?
            return

        ex('dcop', 'kded', 'kded', 'loadModule', 'medianotifier')

        self.debconf_progress_region(15, 100)

        dbfilter = install.Install(self)
        ret = dbfilter.run_command(auto_process=True)
        if ret != 0:
            self.installing = False
            if ret == 3:
                # error already handled by Install
                sys.exit(ret)
            elif os.path.exists('/var/lib/ubiquity/install.trace'):
                tbfile = open('/var/lib/ubiquity/install.trace')
                realtb = tbfile.read()
                tbfile.close()
                raise RuntimeError, ("Install failed with exit code %s\n%s" %
                                     (ret, realtb))
            else:
                raise RuntimeError, ("Install failed with exit code %s; see "
                                     "/var/log/syslog" % ret)

        while self.progress_position.depth() != 0:
            self.debconf_progress_stop()

        # just to make sure
        self.progressDialogue.hide()

        self.installing = False
        quitText = "<qt>" + get_string("finished_label", self.locale) + "</qt>"
        rebootButtonText = get_string("reboot_button", self.locale)
        quitButtonText = get_string("quit_button", self.locale)
        titleText = get_string("finished_dialog", self.locale)

        quitAnswer = QMessageBox.question(self.userinterface, titleText, quitText, rebootButtonText, quitButtonText)

        if quitAnswer == 0:
            self.reboot()

    def debconf_progress_start (self, progress_min, progress_max, progress_title):
        if self.progress_cancelled:
            return False

        if progress_title is None:
            progress_title = ""
        total_steps = progress_max - progress_min
        if self.progressDialogue is None:
            #self.progressDialogue = QProgressDialog('', "Cancel", total_steps, self.userinterface, "progressdialog", True)
            self.progressDialogue = QProgressDialog('', "Cancel", 0, total_steps, self.userinterface)
            self.progressDialogue.setWindowModality(Qt.WindowModal);
            self.cancelButton = QPushButton("Cancel", self.progressDialogue)
            self.cancelButton.hide()
            self.progressDialogue.setCancelButton(self.cancelButton)
        elif self.progress_position.depth() == 0:
            #self.progressDialogue.setTotalSteps(total_steps)
            self.progressDialogue.setMaximum(total_steps)

        self.progress_position.start(progress_min, progress_max,
                                     progress_title)
        self.progressDialogue.setWindowTitle(progress_title)
        self.debconf_progress_set(0)
        #self.progressDialogue.setLabelText('')
        self.progressDialogue.setLabel(QLabel(''))
        self.progressDialogue.show()
        return True

    def debconf_progress_set (self, progress_val):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            return False
        self.progress_position.set(progress_val)
        fraction = self.progress_position.fraction()
        #self.progressDialogue.setProgress(
        self.progressDialogue.setValue(
            int(fraction * self.progressDialogue.maximum()))
        return True

    def debconf_progress_step (self, progress_inc):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            return False
        self.progress_position.step(progress_inc)
        fraction = self.progress_position.fraction()
        #self.progressDialogue.setProgress(
        self.progressDialogue.setValue(
            int(fraction * self.progressDialogue.maximum()))
        return True

    def debconf_progress_info (self, progress_info):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            return False
        self.progressDialogue.setLabel(QLabel(progress_info))
        return True

    def debconf_progress_stop (self):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            self.progress_cancelled = False
            return False
        self.progress_position.stop()
        if self.progress_position.depth() == 0:
            self.progressDialogue.hide()
        else:
            self.progressDialogue.setWindowTitle(self.progress_position.title())
        return True

    def debconf_progress_region (self, region_start, region_end):
        self.progress_position.set_region(region_start, region_end)

    def debconf_progress_cancellable (self, cancellable):
        if cancellable:
            self.cancelButton.show()
        else:
            self.cancelButton.hide()
            self.progress_cancelled = False

    def on_next_clicked(self):
        print "on_next_clicked"
        """Callback to control the installation process between steps."""

        if not self.allowed_change_step or not self.allowed_go_forward:
            return

        self.allow_change_step(False)

        step = self.step_name(self.get_current_page())
        if step == "stepKeyboardConf":
            self.userinterface.fullname_error_image.hide()
            self.userinterface.fullname_error_reason.hide()
            self.userinterface.username_error_image.hide()
            self.userinterface.username_error_reason.hide()
            self.userinterface.password_error_image.hide()
            self.userinterface.password_error_reason.hide()
            self.userinterface.hostname_error_image.hide()
            self.userinterface.hostname_error_reason.hide()

        if self.dbfilter is not None:
            print "dbfilter is not none"
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            print "EXITED in on_next_clicked"
            self.app.exit()

    # returns the current wizard page
    def get_current_page(self):
      return self.userinterface.widgetStack.indexOf(self.userinterface.widgetStack.currentWidget())

    def process_step(self):
        """Process and validate the results of this step."""

        # setting actual step
        step_num = self.get_current_page()
        step = self.step_name(step_num)
        print step
        syslog.syslog('Step_before = %s' % step)

        if step.startswith("stepPart"):
            self.previous_partitioning_page = step_num

        print "process_step: " + step
        # Welcome
        if step == str("stepWelcome"):
            print "setting page to stepLanguage"
            self.set_current_page(WIDGET_STACK_STEPS["stepLanguage"])
        # Language
        elif step == str("stepLanguage"):
            self.translate_widgets()
            self.set_current_page(WIDGET_STACK_STEPS["stepLocation"])
            self.userinterface.back.show()
            ##FIXMEself.allow_go_forward(self.get_timezone() is not None)
        # Location
        elif step == str("stepLocation"):
            self.set_current_page(WIDGET_STACK_STEPS["stepKeyboardConf"])
        # Keyboard
        elif step == str("stepKeyboardConf"):
            self.set_current_page(WIDGET_STACK_STEPS["stepUserInfo"])
            #self.steps.next_page()
            self.info_loop(None)
        # Identification
        elif step == str("stepUserInfo"):
            self.process_identification()
        # Automatic partitioning
        elif step == str("stepPartAuto"):
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == str("stepPartAdvanced"):
            self.qtparted_to_mountpoints()
        # Mountpoints
        elif step == str("stepPartMountpoints"):
            print "in step == str(stepPartMountpoints)"
            self.mountpoints_to_summary()
        # Ready to install
        elif step == str("stepReady"):
            # FIXME self.live_installer.hide()
            self.current_page = None
            self.installing = True
            self.progress_loop()
            return

        step = self.step_name(self.get_current_page())
        syslog.syslog('Step_after = %s' % step)

        if step == "stepReady":
            installText = get_string("live_installer", self.locale)
            self.userinterface.next.setText(installText)

    def set_language_choices (self, choices, choice_map):
        print "set_language_choices"
        self.language_choice_map = dict(choice_map)
        self.userinterface.language_treeview.clear()
        for choice in choices:
            QListWidgetItem(QString(unicode(choice)), self.userinterface.language_treeview)
            #self.userinterface.language_treeview.insertItem( KListViewItem(self.userinterface.language_treeview, QString(unicode(choice))) )

    def set_language (self, language):
        counter = 0
        max = self.userinterface.language_treeview.count()
        while counter < max:
            selection = self.userinterface.language_treeview.item(counter)
            if selection is None:
                value = "C"
            else:
                value = unicode(selection.text())
                #value = selection.text()
                #print unicode("value: ")
                #print value
                print str(counter)
            if value == language:
                selection.setSelected(True)
                #self.userinterface.language_treeview.setSelected(iterator.current(), True)
                self.userinterface.language_treeview.scrollToItem(selection)
                #self.userinterface.language_treeview.ensureItemVisible(iterator.current())
                break
            counter += 1

    def get_language (self):
        print "get_language"
        items = self.userinterface.language_treeview.selectedItems()
        if len(items) == 1:
            value = unicode(items[0].text())
            print "language: " + value
            print "returning " + self.language_choice_map[value][0]
            return self.language_choice_map[value][0]
        else:
            return 'C'

    def set_timezone (self, timezone):
        ##FIXMEself.tzmap.set_tz_from_name(timezone)
        pass

    def get_timezone (self):
        print "get_timezone"
        return "London"
        ##return self.tzmap.get_selected_tz_name()

    def set_keyboard_choices(self, choices):
        self.userinterface.keyboardlayoutview.clear()
        for choice in sorted(choices):
            QListWidgetItem(QString(unicode(choice)), self.userinterface.keyboardlayoutview)
            #self.userinterface.keyboardlayoutview.insertItem( KListViewItem(self.userinterface.keyboardlayoutview, choice) )

        if self.current_layout is not None:
            self.set_keyboard(self.current_layout)

    def set_keyboard (self, layout):
        print "set_keyboard: " + layout
        self.current_layout = layout

        counter = 0
        max = self.userinterface.keyboardlayoutview.count()
        while counter < max:
            selection = self.userinterface.keyboardlayoutview.item(counter)
            if unicode(selection.text()) == layout:
                print "selecting keyboard item"
                selection.setSelected(True)
                self.userinterface.keyboardlayoutview.scrollToItem(selection)
                break
            counter += 1

    def get_keyboard (self):
        print "get_keyboard"
        items = self.userinterface.keyboardlayoutview.selectedItems()
        if len(items) == 1:
            return unicode(items[0].text())
        else:
            return None

    def set_keyboard_variant_choices(self, choices):
        self.userinterface.keyboardvariantview.clear()
        for choice in sorted(choices):
            QListWidgetItem(QString(unicode(choice)), self.userinterface.keyboardvariantview)
            #self.userinterface.keyboardvariantview.insertItem( KListViewItem(self.userinterface.keyboardvariantview, choice) )

    def set_keyboard_variant(self, variant):
        counter = 0
        max = self.userinterface.keyboardvariantview.count()
        while counter < max:
            selection = self.userinterface.keyboardvariantview.item(counter)
            print "item: " + selection.text()
            if unicode(selection.text()) == variant:
                print "selecting keyboard item"
                selection.setSelected(True)
                self.userinterface.keyboardvariantview.scrollToItem(selection)
                break
            counter += 1

    def get_keyboard_variant(self):
        print "get_keyboard_variant"
        items = self.userinterface.keyboardvariantview.selectedItems()
        if len(items) == 1:
            print "returning " + unicode(items[0].text())
            return unicode(items[0].text())
        else:
            return None

    def on_hostname_insert_text(self):
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

    def info_loop(self, widget):
        """check if all entries from Identification screen are filled."""

        if (widget is not None and widget.objectName() == 'username' and
            not self.hostname_edited):
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
            self.userinterface.hostname.blockSignals(True)
            self.userinterface.hostname.setText(unicode(widget.text()) + hostname_suffix)
            self.userinterface.hostname.blockSignals(False)

        complete = True
        for name in ('username', 'password', 'verified_password', 'hostname'):
            if getattr(self.userinterface, name).text() == '':
                complete = False
        self.allow_go_forward(complete)

    def set_fullname(self, value):
        self.userinterface.fullname.setText(unicode(value, "UTF-8"))

    def get_fullname(self):
        return unicode(self.userinterface.fullname.text())

    def set_username(self, value):
        self.userinterface.username.setText(unicode(value, "UTF-8"))

    def get_username(self):
        return unicode(self.userinterface.username.text())

    def get_password(self):
        return unicode(self.userinterface.password.text())

    def get_verified_password(self):
        return unicode(self.userinterface.verified_password.text())

    def username_error(self, msg):
        self.userinterface.username_error_reason.setText(msg)
        self.userinterface.username_error_image.show()
        self.userinterface.username_error_reason.show()

    def password_error(self, msg):
        self.userinterface.password_error_reason.setText(msg)
        self.userinterface.password_error_image.show()
        self.userinterface.password_error_reason.show()


    def process_identification (self):
        """Processing identification step tasks."""

        error_msg = []
        error = 0

        # Validation stuff

        # checking hostname entry
        hostname = self.userinterface.hostname.text()
        for result in validation.check_hostname(unicode(hostname)):
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
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])

    def set_auto_mountpoints(self, auto_mountpoints):
        self.auto_mountpoints = auto_mountpoints

    def set_autopartition_choices (self, choices, extra_options,
                                   resize_choice, manual_choice):
        children = self.userinterface.autopartition_frame.children()
        for child in children:
            if isinstance(child, QVBoxLayout) or isinstance(child, QButtonGroup):
                pass
            else:
                print "child: " + str(child)
                self.autopartition_vbox.removeWidget(child)
                child.hide()

        self.resize_choice = resize_choice
        self.manual_choice = manual_choice
        firstbutton = None
        idCounter = 0
        for choice in choices:
            button = QRadioButton(choice, self.userinterface.autopartition_frame)
            self.autopartition_buttongroup.addButton(button, idCounter)
            id = self.autopartition_buttongroup.id(button)
            print "id: " + str(id) + " " + button.text()

            #Qt changes the string by adding accelarators, 
            #so keep pristine string here as is returned later to partman
            self.autopartition_buttongroup_texts[id] = choice
            if firstbutton is None:
                firstbutton = button
            self.autopartition_vbox.addWidget(button)

            if choice in extra_options:
                #indent_hbox = QHBoxLayout(self.autopartition_vbox)
                indent_hbox = QHBoxLayout()
                self.autopartition_vbox.addLayout(indent_hbox)
                indent_hbox.addSpacing(10)
                if choice == resize_choice:
                    new_size_hbox = QHBoxLayout(indent_hbox)
                    new_size_label = QLabel("New partition size:", new_size_hbox)
                    self.translate_widget(new_size_label, self.locale)
                    new_size_hbox.addWidget(new_size_label)
                    new_size_label.show()
                    new_size_scale_vbox = QVBoxLayout(new_size_hbox)
                    self.new_size_value = QLabel(new_size_scale_vbox)
                    new_size_scale_vbox.addWidget(self.new_size_value)
                    self.new_size_value.show()
                    self.new_size_scale = QSlider(Qt.Horizontal,
                                                  new_size_scale_vbox)
                    self.new_size_scale.setMaxValue(100)
                    self.new_size_scale.setSizePolicy(QSizePolicy.Expanding,
                                                      QSizePolicy.Minimum)
                    self.app.connect(self.new_size_scale,
                                     SIGNAL("valueChanged(int)"),
                                     self.update_new_size_label)
                    new_size_scale_vbox.addWidget(self.new_size_scale)
                    self.new_size_scale.show()
                    self.resize_min_size, self.resize_max_size = \
                        extra_options[choice]
                    if (self.resize_min_size is not None and
                        self.resize_max_size is not None):
                        min_percent = int(math.ceil(
                            100 * self.resize_min_size / self.resize_max_size))
                        self.new_size_scale.setMinValue(min_percent)
                        self.new_size_scale.setMaxValue(100)
                        self.new_size_scale.setValue(
                            int((min_percent + 100) / 2))
                elif choice != manual_choice:
                    disk_frame = QFrame(self.userinterface.autopartition_frame)
                    indent_hbox.addWidget(disk_frame)
                    disk_vbox = QVBoxLayout(disk_frame)
                    disk_buttongroup = QButtonGroup(disk_frame)
                    disk_buttongroup_texts = {}
                    extra_firstbutton = None
                    extraIdCounter = 0
                    for extra in extra_options[choice]:
                        if extra == '':
                            disk_vbox.addSpacing(10)
                        else:
                            extra_button = QRadioButton(
                                extra, disk_frame)
                            disk_buttongroup.addButton(extra_button, extraIdCounter)
                            extra_id = disk_buttongroup.id(extra_button)
                            # Qt changes the string by adding accelerators,
                            # so keep the pristine string here to be
                            # returned to partman later.
                            disk_buttongroup_texts[extra_id] = extra
                            if extra_firstbutton is None:
                                extra_firstbutton = extra_button
                            disk_vbox.addWidget(extra_button)
                    self.autopartition_extra_buttongroup[choice] = \
                        disk_buttongroup
                    self.autopartition_extra_buttongroup_texts[choice] = \
                        disk_buttongroup_texts
                    disk_frame.show()
                    extraIdCounter += 1
                self.autopartition_extras[choice] = indent_hbox
            self.on_autopartition_toggled(choice, button.isChecked())
            self.app.connect(button, SIGNAL('toggled(bool)'),
                             lambda enable:
                                 self.on_autopartition_toggled(choice, enable))

            button.show()
            idCounter += 1
        if firstbutton is not None:
            firstbutton.setChecked(True)

        # make sure we're on the autopartitioning page
        self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])

    def on_autopartition_toggled (self, choice, enable):
        """Update autopartitioning screen when the resize button is
        selected."""

        if choice in self.autopartition_extras:
            self.autopartition_extras[choice].setEnabled(enable)

    def get_autopartition_choice (self):
        #id = self.autopartition_buttongroup.selectedId()
        id = self.autopartition_buttongroup.checkedId()
        print "autopartition_buttongroup_texts: " + str(self.autopartition_buttongroup_texts)
        print "id: " + str(id)
        choice = unicode(self.autopartition_buttongroup_texts[id])
        print "get_autopartition_choice choice: " + choice

        if choice == self.resize_choice:
            # resize choice should have been hidden otherwise
            assert self.new_size_scale is not None
            return choice, self.new_size_scale.value()
        elif (choice != self.manual_choice and
              choice in self.autopartition_extra_buttongroup):
            disk_id = self.autopartition_extra_buttongroup[choice].checkedId()
            disk_texts = self.autopartition_extra_buttongroup_texts[choice]
            return choice, unicode(disk_texts[id])
        else:
            return choice, None

    def process_autopartitioning(self):
        """Processing automatic partitioning step tasks."""

        ##FIXME, why is this here? jr
        self.app.processEvents()

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        choice = self.get_autopartition_choice()[0]
        if self.manual_choice is None or choice == self.manual_choice:
            self.qtparted_loop()
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAdvanced"])
        else:
            # TODO cjwatson 2006-01-10: extract mountpoints from partman
            self.manual_partitioning = False
            self.set_current_page(WIDGET_STACK_STEPS["stepReady"])

    def qtparted_loop(self):
        """call qtparted and embed it into the interface."""

        syslog.syslog('qtparted_loop()')

        disable_swap()

        if self.embed is not None:
            self.qtparted_vbox.removeWidget(self.embed)
            del self.embed
        #self.embed = QXEmbed(self.userinterface.qtparted_frame, "embed")
        #self.embed.setProtocol(QXEmbed.XPLAIN)
        self.embed = QX11EmbedContainer(self.userinterface.qtparted_frame)

        self.qtparted_subp = subprocess.Popen(
            ['log-output', '-t', 'ubiquity', '--pass-stdout',
             '/usr/sbin/qtparted', '--installer'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
        qtparted_winid = self.qtparted_subp.stdout.readline().rstrip('\n')
        print "embedding " + qtparted_winid
        self.qtparted_vbox.addWidget(self.embed)
        ##FIXME causes segfault, not sure why
        ##self.embed.embedClient( int(qtparted_winid) )
        #nasty cludge, we need qtparted to output a line when it's done settings up its window so we can resize then
        #uncomment when new version of qt is in the archive
        ##qtparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        ##if qtparted_reply.startswith('STARTED'):
        ##   self.userinterface.qtparted_frame.resize(self.userinterface.qtparted_frame.width()-1,self.userinterface.qtparted_frame.height())

    def qtparted_to_mountpoints(self):
        """Processing qtparted to mountpoints step tasks."""

        self.qtparted_fstype = {}

        if self.qtparted_subp is None:
            self.qtparted_crashed()
            return

        try:
            print >>self.qtparted_subp.stdin, "apply"
        except IOError:
            # Shut down qtparted
            self.qtparted_subp.stdin.close()
            self.qtparted_subp.wait()
            self.qtparted_subp = None
            self.qtparted_crashed()
            return

        # read qtparted output of format "- FORMAT /dev/hda2 linux-swap"
        qtparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        while not qtparted_reply.startswith('0 ') and not qtparted_reply.startswith('1 '):
            syslog.syslog('qtparted replied: %s' % qtparted_reply)
            if qtparted_reply.startswith('- '):
                words = qtparted_reply[2:].strip().split()
                if words[0].lower() == 'format' and len(words) >= 3:
                    self.qtparted_fstype[words[1]] = words[2]
            qtparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        syslog.syslog('qtparted replied: %s' % qtparted_reply)

        if qtparted_reply.startswith('1 '):
            # Cancel
            return

        # Shut down qtparted
        self.qtparted_subp.stdin.close()
        self.qtparted_subp.wait()
        self.qtparted_subp = None
        if self.embed is not None:
            self.qtparted_vbox.removeWidget(self.embed)
            del self.embed
            self.embed = None

        if not qtparted_reply.startswith('0 '):
            # something other than OK or Cancel
            return

        children = self.userinterface.mountpoint_frame.children()
        for child in children:
            ##FIXME not qlabel
            if isinstance(child, QGridLayout) or isinstance(child, QVBoxLayout)  or isinstance(child, QLabel):
                pass
            else:
                self.mountpoint_table.removeWidget(child)
                del child

        mountText = "<b>" + get_string("mountpoint_label", self.locale) + "</b>"
        sizeText = "<b>" + get_string("size_label", self.locale) + "</b>"
        partitionText = "<b>" + get_string("device_label", self.locale) + "</b>"
        reformatText = "<b>" + get_string("format_label", self.locale) + "</b>"

        mountLabel = QLabel(mountText, self.userinterface.mountpoint_frame)
        sizeLabel = QLabel(sizeText, self.userinterface.mountpoint_frame)
        partitionLabel = QLabel(partitionText, self.userinterface.mountpoint_frame)
        reformatLabel = QLabel(reformatText, self.userinterface.mountpoint_frame)
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

        # Reinitialise the mountpoints table.
        self.mountpoint_widgets = []
        self.size_widgets = []
        self.partition_widgets = []
        self.format_widgets = []

        self.add_mountpoint_table_row()

        # Try to get some default mountpoint selections.
        self.size = get_sizes()
        selection = get_default_partition_selection(
            self.size, self.qtparted_fstype, self.auto_mountpoints)

        # Setting a default partition preselection
        if len(selection.items()) == 0:
            self.allow_go_forward(False)
        else:
            # Setting default preselection values into ComboBox widgets and
            # setting size values. In addition, the next row is shown if
            # they're validated.
            for mountpoint, partition in selection.items():
                if partition.split('/')[2] not in self.size:
                    syslog.syslog(syslog.LOG_WARNING,
                                  "No size available for partition %s; "
                                  "skipping" % partition)
                    continue
                if partition not in self.partition_choices:
                    # TODO cjwatson 2006-05-27: I don't know why this might
                    # happen, but it does
                    # (https://launchpad.net/bugs/46910). Figure out why. In
                    # the meantime, ignoring this partition is better than
                    # crashing.
                    syslog.syslog(syslog.LOG_WARNING,
                                  "Partition %s not in /proc/partitions?" %
                                  partition)
                    continue
                if mountpoint in self.mountpoint_choices:
                    ##FIXMEself.mountpoint_widgets[-1].setCurrentItem(self.mountpoint_choices.index(mountpoint))
                    pass
                else:
                    ##FIXMEself.mountpoint_widgets[-1].setCurrentText(mountpoint)
                    pass
                self.size_widgets[-1].setText(self.set_size_msg(partition))
                ##FIXMEself.partition_widgets[-1].setCurrentItem(self.partition_choices.index(partition))
                if (mountpoint in ('swap', '/', '/usr', '/var', '/boot') or
                    partition in self.qtparted_fstype):
                    self.format_widgets[-1].setChecked(True)
                else:
                    self.format_widgets[-1].setChecked(False)
                if partition not in self.qtparted_fstype:
                    self.format_widgets[-1].setEnabled(True)
                if len(get_partitions()) > len(self.partition_widgets):
                    self.add_mountpoint_table_row()
                else:
                    break

        # We defer connecting up signals until now to avoid the changed
        # signal firing while we're busy populating the table.
        """  Not needed for KDE
        for mountpoint in self.mountpoint_widgets:
            self.app.connect(mountpoint, SIGNAL("activated(int)"), self.on_list_changed)
        for partition in self.partition_widgets:
            self.app.connect(partition, SIGNAL("activated(int)"), self.on_list_changed)
        """

        self.userinterface.mountpoint_error_reason.hide()
        self.userinterface.mountpoint_error_image.hide()

        self.set_current_page(WIDGET_STACK_STEPS["stepPartMountpoints"])

    def add_mountpoint_table_row(self):
        """Add a new empty row to the mountpoints table."""
        print "add_mountpoint_table_row"
        mountpoint = QComboBox(self.userinterface.mountpoint_frame)
        mountpoint.setEditable(True)
        for mp in self.mountpoint_choices:
            mountpoint.insertItem(999, mp)
        size = QLabel(self.userinterface.mountpoint_frame)
        partition = QComboBox(self.userinterface.mountpoint_frame)
        for part in self.partition_choices:
            if part in self.part_labels:
                partition.insertItem(999, self.part_labels[part])
            else:
                partition.insertItem(999, part)
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

        ##FIXME
        ##self.app.connect(mountpoint, SIGNAL("activated(int)"), self.on_list_changed)
        ##self.app.connect(partition, SIGNAL("activated(int)"), self.on_list_changed)

    def set_size_msg(self, widget):
        """return a string message with size value about
        the partition target by widget argument."""

        # widget is studied in a different manner depending on object type
        if widget.__class__ == str:
            size = float(self.size[widget.split('/')[2]])
        elif unicode(widget.currentText()) in self.part_devices:
            size = float(self.size[self.part_devices[unicode(widget.currentText())].split('/')[2]])
        else:
            # TODO cjwatson 2006-07-31: Why isn't it in part_devices? This
            # indicates a deeper problem somewhere, but for now we'll just
            # try our best to ignore it.
            return ''

        if size > 1024*1024:
            msg = '%.0f Gb' % (size/1024/1024)
        elif size > 1024:
            msg = '%.0f Mb' % (size/1024)
        else:
            msg = '%.0f Kb' % size
        return msg

    def watch_debconf_fd (self, from_debconf, process_input):
        print "watch_debconf_fd"
        self.debconf_fd_counter = 0
        self.socketNotifierRead = QSocketNotifier(from_debconf, QSocketNotifier.Read, self.app)
        self.app.connect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)

        self.socketNotifierWrite = QSocketNotifier(from_debconf, QSocketNotifier.Write, self.app)
        self.app.connect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)

        self.socketNotifierException = QSocketNotifier(from_debconf, QSocketNotifier.Exception, self.app)
        self.app.connect(self.socketNotifierException, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_exception)

        self.debconf_callbacks[from_debconf] = process_input
        self.current_debconf_fd = from_debconf
        """
        gobject.io_add_watch(from_debconf,
                                                 gobject.IO_IN | gobject.IO_ERR | gobject.IO_HUP,
                                                 self.watch_debconf_fd_helper, process_input)
        """

    def watch_debconf_fd_helper_read (self, source):
        #print "watch_debconf_fd_helper_read"
        self.debconf_fd_counter += 1
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_IN
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_write(self, source):
        print "watch_debconf_fd_helper_write"
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_OUT
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_exception(self, source):
        print "watch_debconf_fd_helper_exception"
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        self.debconf_callbacks[source](source, debconf_condition)

    def debconffilter_done (self, dbfilter):
        ##FIXME without this disconnect it would call another watch_debconf_fd_helper_read causing
        ## a crash after the keyboard stage.  No idea why.
        self.app.disconnect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)
        # TODO cjwatson 2006-02-10: handle dbfilter.status
        if dbfilter is None:
            name = 'None'
        else:
            name = dbfilter.__class__.__name__
        if self.dbfilter is None:
            currentname = 'None'
        else:
            currentname = self.dbfilter.__class__.__name__
        syslog.syslog(syslog.LOG_DEBUG,
                      "debconffilter_done: %s (current: %s)" %
                      (name, currentname))
        if dbfilter == self.dbfilter:
            self.dbfilter = None
            if isinstance(dbfilter, summary.Summary):
                # The Summary component is just there to gather information,
                # and won't call run_main_loop() for itself.
                self.allow_change_step(True)
            else:
                print "EXITED in debconffilter_done"
                self.app.exit()

    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        self.allow_change_step(True)
        print "EXEC in run_main_loop"
        #self.app.exec_()   ##FIXME Qt 4 won't allow nested main loops, here it just returns directly
        self.mainLoopRunning = True
        while self.mainLoopRunning:    # kludge, but works OK
            #print "mainLoopRunning loop"
            self.app.processEvents()
        print "EXEC in run_main_loop done"

    # Return control to the next level up.
    def quit_main_loop (self):
        print "EXITED in quit_main_loop"
        #self.app.exit()
        self.mainLoopRunning = False

    def on_cancel_clicked(self):
        warning_dialog_label = get_string("warning_dialog_label", self.locale)
        abortTitle = get_string("warning_dialog", self.locale)
        continueButtonText = get_string("continue", self.locale)
        response = QMessageBox.question(self.userinterface, abortTitle, warning_dialog_label, abortTitle, continueButtonText)
        if response == 0:
            if self.qtparted_subp is not None:
                try:
                    print >>self.qtparted_subp.stdin, "exit"
                except IOError:
                    pass
            self.current_page = None
            self.quit()
            return True
        else:
            return False

    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

    def refresh (self):
        self.app.processEvents()
        """
        while gtk.events_pending():
            gtk.main_iteration()
        """
