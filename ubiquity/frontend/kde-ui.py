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

UIDIR = '/usr/lib/ubiquity/ubiquity/frontend'

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
        uic.loadUi("%s/liveinstaller.ui" % UIDIR, self)

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

        self.advanceddialog = QDialog(self.userinterface)
        uic.loadUi("%s/advanceddialog.ui" % UIDIR, self.advanceddialog)

        # declare attributes
        self.distro = distro
        self.current_layout = None
        self.release_notes_url_template = None
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
        self.summary_device = None
        self.popcon = None
        self.installing = False
        self.returncode = 0
        self.language_questions = ('live_installer', 'welcome_heading_label',
                                   'welcome_text_label', 'release_notes_label',
                                   'release_notes_url', 'step_label',
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

        self.map_vbox = QVBoxLayout(self.userinterface.map_frame)
        self.map_vbox.setMargin(0)

        self.customize_installer()

        self.translate_widgets()

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

        dialog = QDialog(self.userinterface)
        uic.loadUi("%s/crashdialog.ui" % UIDIR, dialog)
        dialog.beastie_url.setOpenExternalLinks(True)
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
        self.app.connect(self.userinterface.back, SIGNAL("clicked()"), self.on_back_clicked)
        self.app.connect(self.userinterface.cancel, SIGNAL("clicked()"), self.on_cancel_clicked)
        self.app.connect(self.userinterface.keyboardlayoutview, SIGNAL("itemSelectionChanged()"), self.on_keyboard_layout_selected)
        self.app.connect(self.userinterface.keyboardvariantview, SIGNAL("itemSelectionChanged()"), self.on_keyboard_variant_selected)

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

        self.app.connect(self.userinterface.language_treeview, SIGNAL("itemSelectionChanged()"), self.on_language_treeview_selection_changed)

        self.app.connect(self.userinterface.timezone_city_combo, SIGNAL("activated(int)"), self.tzmap.city_combo_changed)

        self.app.connect(self.userinterface.advanced_button, SIGNAL("clicked()"), self.on_advanced_button_clicked)

        # Start the interface
        if got_intro:
            global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
            for step in BREADCRUMB_STEPS:
                BREADCRUMB_STEPS[step] += 1
            BREADCRUMB_STEPS["stepWelcome"] = 1
            BREADCRUMB_MAX_STEP += 1
            first_step = "stepWelcome"
        else:
            first_step = "stepLanguage"
        self.set_current_page(WIDGET_STACK_STEPS[first_step])

        while self.current_page is not None:
            if not self.installing:
                # Make sure any started progress bars are stopped.
                while self.progress_position.depth() != 0:
                    self.debconf_progress_stop()

            self.backup = False
            current_name = self.step_name(self.current_page)
            old_dbfilter = self.dbfilter
            if current_name == "stepLanguage":
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
                self.dbfilter = None

            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                self.allow_change_step(False)
                self.dbfilter.start(auto_process=True)
            else:
                self.allow_change_step(not self.installing)

            self.app.exec_()

            if self.installing:
                self.progress_loop()
            elif self.current_page is not None and not self.backup:
                self.process_step()
            self.app.processEvents()

        return self.returncode

    def customize_installer(self):
        """Initial UI setup."""

        self.userinterface.setWindowIcon(QIcon("/usr/share/icons/crystalsvg/64x64/apps/ubiquity.png"))
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

        try:
            release_notes = open('/cdrom/.disk/release_notes_url')
            self.release_notes_url_template = release_notes.read().rstrip('\n')
            release_notes.close()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.userinterface.release_notes_label.hide()
            self.userinterface.release_notes_url.hide()

        self.tzmap = TimezoneMap(self)
        self.tzmap.tzmap.show()

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

        self.translate_widget(parentWidget, self.locale)
        if parentWidget.children() != None:
            for widget in parentWidget.children():
                self.translate_widget(widget, self.locale)
                self.translate_widget_children(widget)

    def translate_widget(self, widget, lang):
        #FIXME needs translations for Next, Back and Cancel

        text = get_string(widget.objectName(), lang)

        if widget.objectName() == "next":
            text = get_string("continue", lang) + " >"
        elif widget.objectName() == "back":
            text = "< " + get_string("go_back", lang)
        elif str(widget.objectName()) == "UbiquityUIBase":
            text = get_string("live_installer", lang)

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
            elif ('group_label' in name or
                  name in ('drives_label', 'partition_method_label',
                           'mountpoint_label', 'size_label', 'device_label',
                           'format_label')):
                widget.setText("<strong>" + text + "</strong>")
            elif name == 'release_notes_url':
                if self.release_notes_url_template is not None:
                    url = self.release_notes_url_template.replace(
                        '${LANG}', lang.split('.')[0])
                    widget.setText('<a href="%s">%s</a>' % (url, text))
            else:
                widget.setText(text)

        elif isinstance(widget, QPushButton):
            widget.setText(text)

        elif isinstance(widget, QWidget) and str(widget.objectName()) == "UbiquityUIBase":
            widget.setWindowTitle(text)
        else:
            print "WARNING: unknown widget: " + widget.objectName()

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

    def step_name(self, step_index):
        if step_index < 0:
            step_index = 0
        return str(self.userinterface.widgetStack.widget(step_index).objectName())

    def set_current_page(self, current):
        widget = self.userinterface.widgetStack.widget(current)
        if self.userinterface.widgetStack.currentWidget() == widget:
            # self.userinterface.widgetStack.raiseWidget() will do nothing.
            # Update state ourselves.
            self.on_steps_switch_page(current)
        else:
            self.userinterface.widgetStack.setCurrentWidget(widget)
            self.on_steps_switch_page(current)

    def qtparted_loop(self):
        """call qtparted and embed it into the interface."""

        syslog.syslog('qtparted_loop()')

        disable_swap()

        if self.embed is not None:
            self.qtparted_vbox.removeWidget(self.embed)
            del self.embed
        self.embed = QX11EmbedContainer(self.userinterface.qtparted_frame)

        self.qtparted_subp = subprocess.Popen(
            ['log-output', '-t', 'ubiquity', '--pass-stdout',
             '/usr/sbin/qtparted', '--installer'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, close_fds=True)
        qtparted_winid = self.qtparted_subp.stdout.readline().rstrip('\n')
        self.qtparted_vbox.addWidget(self.embed)
        ##FIXME causes segfault, not sure why
        ##self.embed.embedClient( int(qtparted_winid) )
        #nasty cludge, we need qtparted to output a line when it's done settings up its window so we can resize then
        #uncomment when new version of qt is in the archive
        ##qtparted_reply = self.qtparted_subp.stdout.readline().rstrip('\n')
        ##if qtparted_reply.startswith('STARTED'):
        ##   self.userinterface.qtparted_frame.resize(self.userinterface.qtparted_frame.width()-1,self.userinterface.qtparted_frame.height())

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

    def add_mountpoint_table_row(self):
        """Add a new empty row to the mountpoints table."""
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

        ##FIXME use non-stock messagebox to customise button text
        #quitAnswer = QMessageBox.question(self.userinterface, titleText, quitText, rebootButtonText, quitButtonText)
        quitAnswer = QMessageBox.question(self.userinterface, titleText, quitText)

        if quitAnswer == 0:
            self.reboot()

    def reboot(self, *args):
        """reboot the system after installing process."""

        self.returncode = 10
        self.quit()

    def do_reboot(self):
        """Callback for main program to actually reboot the machine."""

        ex('dcop', 'ksmserver', 'ksmserver', 'logout',
           # ShutdownConfirmNo, ShutdownTypeReboot, ShutdownModeForceNow
           '0', '1', '2')

    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

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

    def on_list_changed(self, textID):
        """check if partition/mountpoint pair is filled and show the next pair
        on mountpoint screen. Also size label associated with partition combobox
        is changed dynamically to show the size partition."""
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
                if partition in self.qtparted_fstype:
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

    def on_hostname_insert_text(self):
        self.hostname_edited = (self.userinterface.hostname.text() != '')

    def on_next_clicked(self):
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
            self.dbfilter.ok_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def on_keyboard_layout_selected(self):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            if layout is not None:
                self.current_layout = layout
                self.dbfilter.change_layout(layout)

    def on_keyboard_variant_selected(self):
        if isinstance(self.dbfilter, console_setup.ConsoleSetup):
            layout = self.get_keyboard()
            variant = self.get_keyboard_variant()
            if layout is not None and variant is not None:
                self.dbfilter.apply_keyboard(layout, variant)

    def process_step(self):
        """Process and validate the results of this step."""

        # setting actual step
        step_num = self.get_current_page()
        step = self.step_name(step_num)
        syslog.syslog('Step_before = %s' % step)

        if step.startswith("stepPart"):
            self.previous_partitioning_page = step_num

        # Welcome
        if step == "stepWelcome":
            self.set_current_page(WIDGET_STACK_STEPS["stepLanguage"])
        # Language
        elif step == "stepLanguage":
            self.translate_widgets()
            self.set_current_page(WIDGET_STACK_STEPS["stepLocation"])
            self.userinterface.back.show()
            self.allow_go_forward(self.get_timezone() is not None)
        # Location
        elif step == "stepLocation":
            self.set_current_page(WIDGET_STACK_STEPS["stepKeyboardConf"])
        # Keyboard
        elif step == "stepKeyboardConf":
            self.set_current_page(WIDGET_STACK_STEPS["stepUserInfo"])
            #self.steps.next_page()
            self.info_loop(None)
        # Identification
        elif step == "stepUserInfo":
            self.process_identification()
        # Automatic partitioning
        elif step == "stepPartAuto":
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == "stepPartAdvanced":
            self.qtparted_to_mountpoints()
        # Mountpoints
        elif step == "stepPartMountpoints":
            self.mountpoints_to_summary()
        # Ready to install
        elif step == "stepReady":
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

    def process_identification (self):
        """Processing identification step tasks."""

        error_msg = []
        error = 0

        # Validation stuff

        # checking hostname entry
        hostname = self.userinterface.hostname.text()
        for result in validation.check_hostname(unicode(hostname)):
            if result == validation.HOSTNAME_LENGTH:
                error_msg.append("The hostname must be between 2 and 63 characters long.")
            elif result == validation.HOSTNAME_BADCHAR:
                error_msg.append("The hostname may only contain letters, digits, hyphens, and dots.")
            elif result == validation.HOSTNAME_BADHYPHEN:
                error_msg.append("The hostname may not start or end with a hyphen.")

        # showing warning message is error is set
        if len(error_msg) != 0:
            self.userinterface.hostname_error_reason.setText("\n".join(error_msg))
            self.userinterface.hostname_error_reason.show()
        else:
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])

    def process_autopartitioning(self):
        """Processing automatic partitioning step tasks."""

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

    def qtparted_crashed(self):
        pass
        """qtparted crashed. Ask the user if they want to continue."""
        # TODO cjwatson 2006-07-18: i18n
        text = ('The advanced partitioner (qtparted) crashed. Further '
                'information may be found in /var/log/syslog, or by '
                'running qtparted directly. Do you want to try the '
                'advanced partitioner again, return to automatic '
                'partitioning, or quit this installer?')
        #FIXME QMessageBox seems to have lost the ability to set custom labels
        # so for now we have to get by with these not-entirely meaningful stock labels
        answer = QMessageBox.warning(self.userinterface, 'QTParted crashed',
                                     text, QMessageBox.Retry, QMessageBox.Reset, QMessageBox.Close)
        if answer == QMessageBox.Reset:
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])
        elif answer == QMessageBox.Close:
            self.current_page = None
            self.quit()
        else:
            self.qtparted_loop()

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
            qtparted_reply = self.qtparted_subp.stdout.readline()
            if not qtparted_reply:
                break
            qtparted_reply = qtparted_reply.rstrip('\n')
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
            if isinstance(child, QGridLayout) or isinstance(child, QVBoxLayout):
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
                    self.mountpoint_widgets[-1].setCurrentIndex(self.mountpoint_choices.index(mountpoint))
                else:
                    self.mountpoint_widgets[-1].addItem(mountpoint)
                    self.mountpoint_widgets[-1].setCurrentIndex(self.mountpoint_widgets[-1].count() - 1)
                self.size_widgets[-1].setText(self.set_size_msg(partition))
                self.partition_widgets[-1].setCurrentIndex(self.partition_choices.index(partition))
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

    def mountpoints_to_summary(self):
        """Processing mountpoints to summary step tasks."""

        # Validating self.mountpoints
        error_msg = []

        mountpoints = {}
        for i in range(len(self.mountpoint_widgets)):
            mountpoint_value = unicode(self.mountpoint_widgets[i].currentText())
            partition_value = unicode(self.partition_widgets[i].currentText())
            if partition_value is not None:
                if partition_value in self.part_devices:
                    partition_id = self.part_devices[partition_value]
                else:
                    partition_id = partition_value
            else:
                partition_id = None
            format_value = self.format_widgets[i].isChecked()
            fstype = None
            if partition_id in self.qtparted_fstype:
                fstype = self.qtparted_fstype[partition_id]

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
                    # TODO cjwatson 2006-09-26: Replace None with flags once
                    # qtparted can export the list of flags set on formatted
                    # filesystems (or just ignore until
                    # ubiquity-advanced-partitioner happens!).
                    mountpoints[partition_id] = \
                        (mountpoint_value, format_value, fstype, None)
        else:
            self.mountpoints = mountpoints
        syslog.syslog('mountpoints: %s' % self.mountpoints)

        # Checking duplicated devices
        partitions = [w.currentText() for w in self.partition_widgets]

        for check in partitions:
            if check in (None, '', ' '):
                continue
            if partitions.count(check) > 1:
                error_msg.append("A partition is assigned to more than one "
                                 "mount point.")
                break

        # Processing more validation stuff
        if len(self.mountpoints) > 0:
            # Supplement filesystem types from qtparted FORMAT instructions
            # with those detected from the disk.
            validate_mountpoints = dict(self.mountpoints)
            validate_filesystems = get_filesystems(self.qtparted_fstype)
            for device, (path, format, fstype,
                         flags) in validate_mountpoints.items():
                if fstype is None and device in validate_filesystems:
                    validate_mountpoints[device] = \
                        (path, format, validate_filesystems[device], None)
            # Check for some special-purpose partitions detected by partman.
            if self.auto_mountpoints is not None:
                for device, mountpoint in self.auto_mountpoints.iteritems():
                    if device in validate_mountpoints:
                        continue
                    if not mountpoint.startswith('/'):
                        validate_mountpoints[device] = \
                            (mountpoint, False, None, None)

            for check in validation.check_mountpoint(validate_mountpoints,
                                                     self.size):
                if check == validation.MOUNTPOINT_NOROOT:
                    error_msg.append(get_string(
                        'partman-target/no_root', self.locale))
                elif check == validation.MOUNTPOINT_DUPPATH:
                    error_msg.append("Two file systems are assigned the same "
                                     "mount point.")
                elif check == validation.MOUNTPOINT_BADSIZE:
                    for mountpoint, format, fstype, flags in \
                            self.mountpoints.itervalues():
                        if mountpoint == 'swap':
                            min_root = MINIMAL_PARTITION_SCHEME['root']
                            break
                    else:
                        min_root = (MINIMAL_PARTITION_SCHEME['root'] +
                                    MINIMAL_PARTITION_SCHEME['swap'])
                    error_msg.append("The partition assigned to '/' is too "
                                     "small (minimum size: %d Mb)." % min_root)
                elif check == validation.MOUNTPOINT_BADCHAR:
                    error_msg.append(get_string(
                        'partman-basicfilesystems/bad_mountpoint',
                        self.locale))
                elif check == validation.MOUNTPOINT_XFSROOT:
                    error_msg.append("XFS may not be used on the filesystem "
                                     "containing /boot. Either use a "
                                     "different filesystem for / or create a "
                                     "non-XFS filesystem for /boot.")
                elif check == validation.MOUNTPOINT_XFSBOOT:
                    error_msg.append("XFS may not be used on the /boot "
                                     "filesystem. Use a different filesystem "
                                     "type for /boot.")
                elif check == validation.MOUNTPOINT_UNFORMATTED:
                    error_msg.append("Filesystems used by the system (/, "
                                     "/boot, /usr, /var) must be reformatted "
                                     "for use by this installer. Other "
                                     "filesystems (/home, /media/*, "
                                     "/usr/local, etc.) may be used without "
                                     "reformatting.")
                elif check == validation.MOUNTPOINT_NEEDPOSIX:
                    error_msg.append("FAT and NTFS filesystems may not be "
                                     "used on filesystems used by the system "
                                     "(/, /boot, /home, /usr, /var, etc.). "
                                     "It is usually best to mount them "
                                     "somewhere under /media/.")
                elif check == validation.MOUNTPOINT_NONEWWORLD:
                    error_msg.append(get_string(
                        'partman-newworld/no_newworld',
                        'extended:%s' % self.locale))

        # showing warning messages
        self.userinterface.mountpoint_error_reason.setText("\n".join(error_msg))
        if len(error_msg) != 0:
            self.userinterface.mountpoint_error_reason.show()
            self.userinterface.mountpoint_error_image.show()
            return
        else:
            self.userinterface.mountpoint_error_reason.hide()
            self.userinterface.mountpoint_error_image.hide()

        self.manual_partitioning = True
        self.set_current_page(WIDGET_STACK_STEPS["stepReady"])

    def on_back_clicked(self):
        """Callback to set previous screen."""

        if not self.allowed_change_step:
            return

        self.allow_change_step(False)

        self.backup = True

        # Enabling next button
        self.allow_go_forward(True)
        # Setting actual step
        step = self.step_name(self.get_current_page())
        self.userinterface.setCursor(QCursor(Qt.WaitCursor))

        changed_page = False

        if str(step) == "stepLocation":
            self.userinterface.back.hide()
        elif str(step) == "stepPartAuto":
            self.set_current_page(WIDGET_STACK_STEPS["stepUserInfo"])
            changed_page = True
        elif str(step) == "stepPartAdvanced":
            if self.qtparted_subp is not None:
                try:
                    print >>self.qtparted_subp.stdin, "undo"
                    print >>self.qtparted_subp.stdin, "exit"
                except IOError:
                    pass
                self.qtparted_subp.stdin.close()
                self.qtparted_subp.wait()
                self.qtparted_subp = None
                if self.embed is not None:
                    self.qtparted_vbox.removeWidget(self.embed)
                    del self.embed
                    self.embed = None
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])
            changed_page = True
        elif str(step) == "stepPartMountpoints":
            self.qtparted_loop()
        elif str(step) == "stepReady":
            self.userinterface.next.setText("Next >")
            self.set_current_page(self.previous_partitioning_page)
            changed_page = True

        if not changed_page:
            self.set_current_page(self.get_current_page() - 1)

        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def selected_language (self):
        selection = self.userinterface.language_treeview.selectedItems()
        if len(selection) == 1:
            value = unicode(selection[0].text())
            return self.language_choice_map[value][1]
        else:
            return ''

    def on_language_treeview_selection_changed (self):
        lang = self.selected_language()
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            for widget in (self.userinterface, self.userinterface.welcome_heading_label, self.userinterface.welcome_text_label, self.userinterface.release_notes_label, self.userinterface.release_notes_url, self.userinterface.next, self.userinterface.back, self.userinterface.cancel, self.userinterface.step_label):
                self.translate_widget(widget, lang)

    def on_steps_switch_page(self, newPageID):
        self.current_page = newPageID
        self.translate_widget(self.userinterface.step_label, self.locale)
        syslog.syslog('switched to page %s' % self.step_name(newPageID))

    def on_autopartition_toggled (self, choice, enable):
        """Update autopartitioning screen when the resize button is
        selected."""

        if choice in self.autopartition_extras:
            self.autopartition_extras[choice].setEnabled(enable)

    def watch_debconf_fd (self, from_debconf, process_input):
        self.debconf_fd_counter = 0
        self.socketNotifierRead = QSocketNotifier(from_debconf, QSocketNotifier.Read, self.app)
        self.app.connect(self.socketNotifierRead, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_read)

        self.socketNotifierWrite = QSocketNotifier(from_debconf, QSocketNotifier.Write, self.app)
        self.app.connect(self.socketNotifierWrite, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_write)

        self.socketNotifierException = QSocketNotifier(from_debconf, QSocketNotifier.Exception, self.app)
        self.app.connect(self.socketNotifierException, SIGNAL("activated(int)"), self.watch_debconf_fd_helper_exception)

        self.debconf_callbacks[from_debconf] = process_input
        self.current_debconf_fd = from_debconf

    def watch_debconf_fd_helper_read (self, source):
        self.debconf_fd_counter += 1
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_IN
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_write(self, source):
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_OUT
        self.debconf_callbacks[source](source, debconf_condition)

    def watch_debconf_fd_helper_exception(self, source):
        debconf_condition = 0
        debconf_condition |= filteredcommand.DEBCONF_IO_ERR
        self.debconf_callbacks[source](source, debconf_condition)

    def debconf_progress_start (self, progress_min, progress_max, progress_title):
        if self.progress_cancelled:
            return False

        if progress_title is None:
            progress_title = ""
        total_steps = progress_max - progress_min
        if self.progressDialogue is None:
            self.progressDialogue = QProgressDialog('', "Cancel", 0, total_steps, self.userinterface)
            self.progressDialogue.setWindowModality(Qt.WindowModal);
            self.cancelButton = QPushButton("Cancel", self.progressDialogue)
            self.cancelButton.hide()
            self.progressDialogue.setCancelButton(self.cancelButton)
        elif self.progress_position.depth() == 0:
            self.progressDialogue.setMaximum(total_steps)

        self.progress_position.start(progress_min, progress_max,
                                     progress_title)
        self.progressDialogue.setWindowTitle(progress_title)
        self.debconf_progress_set(0)
        self.progressDialogue.setLabel(QLabel(''))
        self.progressDialogue.show()
        return True

    def debconf_progress_set (self, progress_val):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            return False
        self.progress_position.set(progress_val)
        fraction = self.progress_position.fraction()
        self.progressDialogue.setValue(
            int(fraction * self.progressDialogue.maximum()))
        return True

    def debconf_progress_step (self, progress_inc):
        self.progress_cancelled = self.progressDialogue.wasCanceled()
        if self.progress_cancelled:
            return False
        self.progress_position.step(progress_inc)
        fraction = self.progress_position.fraction()
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

    def on_progress_cancel_button_clicked (self, button):
        self.progress_cancelled = True

    def debconffilter_done (self, dbfilter):
        ##FIXME in Qt 4 without this disconnect it calls watch_debconf_fd_helper_read once more causing
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
                self.app.exit()

    def set_language_choices (self, choices, choice_map):
        self.language_choice_map = dict(choice_map)
        self.userinterface.language_treeview.clear()
        for choice in choices:
            QListWidgetItem(QString(unicode(choice)), self.userinterface.language_treeview)

    def set_language (self, language):
        counter = 0
        max = self.userinterface.language_treeview.count()
        while counter < max:
            selection = self.userinterface.language_treeview.item(counter)
            if selection is None:
                value = "C"
            else:
                value = unicode(selection.text())
            if value == language:
                selection.setSelected(True)
                self.userinterface.language_treeview.scrollToItem(selection)
                break
            counter += 1

    def get_language (self):
        items = self.userinterface.language_treeview.selectedItems()
        if len(items) == 1:
            value = unicode(items[0].text())
            return self.language_choice_map[value][0]
        else:
            return 'C'

    def set_timezone (self, timezone):
        self.tzmap.set_tz_from_name(timezone)

    def get_timezone (self):
        return self.tzmap.get_selected_tz_name()

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

    def set_auto_mountpoints(self, auto_mountpoints):
        self.auto_mountpoints = auto_mountpoints

    def set_autopartition_choices (self, choices, extra_options,
                                   resize_choice, manual_choice):
        children = self.userinterface.autopartition_frame.children()
        for child in children:
            if isinstance(child, QVBoxLayout) or isinstance(child, QButtonGroup):
                pass
            else:
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

            #Qt changes the string by adding accelarators, 
            #so keep pristine string here as is returned later to partman
            self.autopartition_buttongroup_texts[id] = choice
            if firstbutton is None:
                firstbutton = button
            self.autopartition_vbox.addWidget(button)

            if choice in extra_options:
                indent_hbox = QHBoxLayout()
                self.autopartition_vbox.addLayout(indent_hbox)
                indent_hbox.addSpacing(10)
                if choice == resize_choice:
                    new_size_hbox = QHBoxLayout()
                    indent_hbox.addLayout(new_size_hbox)
                    new_size_label = QLabel("New partition size:", self.userinterface.autopartition_frame)
                    new_size_hbox.addWidget(new_size_label)
                    self.translate_widget(new_size_label, self.locale)
                    new_size_hbox.addWidget(new_size_label)
                    new_size_label.show()
                    new_size_scale_vbox = QVBoxLayout()
                    new_size_hbox.addLayout(new_size_scale_vbox)
                    self.new_size_value = QLabel(self.userinterface.autopartition_frame)
                    new_size_scale_vbox.addWidget(self.new_size_value)
                    self.new_size_value.show()
                    self.new_size_scale = QSlider(Qt.Horizontal, self.userinterface.autopartition_frame)
                    self.new_size_scale.setMaximum(100)
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
                        self.new_size_scale.setMinimum(min_percent)
                        self.new_size_scale.setMaximum(100)
                        self.new_size_scale.setValue(
                            int((min_percent + 100) / 2))
                    self.autopartition_extras[choice] = self.new_size_scale
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
                    if extra_firstbutton is not None:
                        extra_firstbutton.setChecked(True)
                    self.autopartition_extra_buttongroup[choice] = \
                        disk_buttongroup
                    self.autopartition_extra_buttongroup_texts[choice] = \
                        disk_buttongroup_texts
                    disk_frame.show()
                    extraIdCounter += 1
                    self.autopartition_extras[choice] = disk_frame

            # TODO cjwatson 2006-12-09: The lambda never seems to get
            # called? Make sure not to disable things until this is fixed.
            #self.on_autopartition_toggled(choice, button.isChecked())
            #self.app.connect(button, SIGNAL('toggled(bool)'),
            #                 lambda enable:
            #                     self.on_autopartition_toggled(choice, enable))

            button.show()
            idCounter += 1
        if firstbutton is not None:
            firstbutton.setChecked(True)

        # make sure we're on the autopartitioning page
        self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])

    def get_autopartition_choice (self):
        id = self.autopartition_buttongroup.checkedId()
        choice = unicode(self.autopartition_buttongroup_texts[id])

        if choice == self.resize_choice:
            # resize choice should have been hidden otherwise
            assert self.new_size_scale is not None
            return choice, self.new_size_scale.value()
        elif (choice != self.manual_choice and
              choice in self.autopartition_extra_buttongroup):
            disk_id = self.autopartition_extra_buttongroup[choice].checkedId()
            disk_texts = self.autopartition_extra_buttongroup_texts[choice]
            return choice, unicode(disk_texts[disk_id])
        else:
            return choice, None

    def get_hostname (self):
        return unicode(self.userinterface.hostname.text())

    def get_mountpoints (self):
        return dict(self.mountpoints)

    def set_keyboard_choices(self, choices):
        self.userinterface.keyboardlayoutview.clear()
        for choice in sorted(choices):
            QListWidgetItem(QString(unicode(choice)), self.userinterface.keyboardlayoutview)

        if self.current_layout is not None:
            self.set_keyboard(self.current_layout)

    def set_keyboard (self, layout):
        self.current_layout = layout

        counter = 0
        max = self.userinterface.keyboardlayoutview.count()
        while counter < max:
            selection = self.userinterface.keyboardlayoutview.item(counter)
            if unicode(selection.text()) == layout:
                selection.setSelected(True)
                self.userinterface.keyboardlayoutview.scrollToItem(selection)
                break
            counter += 1

    def get_keyboard (self):
        items = self.userinterface.keyboardlayoutview.selectedItems()
        if len(items) == 1:
            return unicode(items[0].text())
        else:
            return None

    def set_keyboard_variant_choices(self, choices):
        self.userinterface.keyboardvariantview.clear()
        for choice in sorted(choices):
            QListWidgetItem(QString(unicode(choice)), self.userinterface.keyboardvariantview)

    def set_keyboard_variant(self, variant):
        counter = 0
        max = self.userinterface.keyboardvariantview.count()
        while counter < max:
            selection = self.userinterface.keyboardvariantview.item(counter)
            if unicode(selection.text()) == variant:
                selection.setSelected(True)
                self.userinterface.keyboardvariantview.scrollToItem(selection)
                break
            counter += 1

    def get_keyboard_variant(self):
        items = self.userinterface.keyboardvariantview.selectedItems()
        if len(items) == 1:
            return unicode(items[0].text())
        else:
            return None

    def set_summary_text (self, text):
        i = text.find("\n")
        while i != -1:
            text = text[:i] + "<br>" + text[i+1:]
            i = text.find("\n")
        self.userinterface.ready_text.setText(text)

    def set_summary_device (self, device):
        if device is not None:
            if not device.startswith('(') and not device.startswith('/dev/'):
                device = '/dev/%s' % device
        self.summary_device = device

    def get_summary_device (self):
        return self.summary_device

    def set_popcon (self, participate):
        self.popcon = participate

    def get_popcon (self):
        return self.popcon

    def on_advanced_button_clicked (self):
        display = False
        summary_device = self.get_summary_device()
        if summary_device is not None:
            display = True
            self.advanceddialog.bootloader_group_label.show()
            self.advanceddialog.grub_device_label.show()
            self.advanceddialog.grub_device_entry.show()
            self.advanceddialog.grub_device_entry.setText(summary_device)
        else:
            self.advanceddialog.bootloader_group_label.hide()
            self.advanceddialog.grub_device_label.hide()
            self.advanceddialog.grub_device_entry.hide()
        if self.popcon is not None:
            display = True
            self.advanceddialog.popcon_group_label.show()
            self.advanceddialog.popcon_checkbutton.show()
            self.advanceddialog.popcon_checkbutton.setChecked(self.popcon)
        else:
            self.advanceddialog.popcon_group_label.hide()
            self.advanceddialog.popcon_checkbutton.hide()
        if not display:
            return

        response = self.advanceddialog.exec_()
        if response == QDialog.Accepted:
            self.set_summary_device(
                unicode(self.advanceddialog.grub_device_entry.text()))
            self.set_popcon(self.advanceddialog.popcon_checkbutton.isChecked())

    def return_to_autopartitioning (self):
        """If the install progress bar is up but still at the partitioning
        stage, then errors can safely return us to autopartitioning.
        """
        if self.installing and self.current_page is not None:
            # Go back to the autopartitioner and try again.
            #self.live_installer.show()
            self.set_current_page(WIDGET_STACK_STEPS["stepPartAuto"])
            nextText = get_string("continue", self.locale) + " >"
            self.userinterface.next.setText(nextText)
            self.backup = True
            self.installing = False

    def error_dialog (self, title, msg, fatal=True):
        self.allow_change_step(True)
        # TODO: cancel button as well if capb backup
        QMessageBox.warning(self.userinterface, title, msg, QMessageBox.Ok)
        if fatal:
            self.return_to_autopartitioning()

    def question_dialog (self, title, msg, option_templates):
        # I doubt we'll ever need more than three buttons.
        assert len(option_templates) <= 3, option_templates

        self.allow_change_step(True)
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

        #FIXME qt 4 seems to have lost the ability to set a custom message on the buttons for stock dialogues
        #response = QMessageBox.question(self.userinterface, title, msg,
        #                                *buttons)
        response = QMessageBox.question(self.userinterface, title, msg, QMessageBox.Ok, QMessageBox.Cancel)

        """
        if response < 0:
            return None
        elif response == 0:
            return option_templates[len(buttons) - 1]
        else:
            return option_templates[response - 1]
        """
        
        if response < 0:
            return None
        elif response == QMessageBox.Ok:
            return option_templates[len(buttons) - 1]
        else:
            return option_templates[response - 1]

    def refresh (self):
        self.app.processEvents()

    # Run the UI's main loop until it returns control to us.
    def run_main_loop (self):
        self.allow_change_step(True)
        #self.app.exec_()   ##FIXME Qt 4 won't allow nested main loops, here it just returns directly
        self.mainLoopRunning = True
        while self.mainLoopRunning:    # nasty, but works OK
            self.app.processEvents()

    # Return control to the next level up.
    def quit_main_loop (self):
        #self.app.exit()
        self.mainLoopRunning = False

    # returns the current wizard page
    def get_current_page(self):
      return self.userinterface.widgetStack.indexOf(self.userinterface.widgetStack.currentWidget())

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

    def update_new_size_label(self, value):
        if self.new_size_value is None:
            return
        if self.resize_max_size is not None:
            size = value * self.resize_max_size / 100
            text = '%d%% (%s)' % (value, format_size(size))
        else:
            text = '%d%%' % value
        self.new_size_value.setText(text)
 
    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

class TimezoneMap(object):
    def __init__(self, frontend):
        self.frontend = frontend
        self.tzdb = ubiquity.tz.Database()
        #self.tzmap = ubiquity.emap.EMap()
        self.tzmap = MapWidget(self.frontend.userinterface.map_frame)
        self.frontend.map_vbox.addWidget(self.tzmap)
        self.tzmap.show()
        self.update_timeout = None
        self.point_selected = None
        self.point_hover = None
        self.location_selected = None

        timezone_city_combo = self.frontend.userinterface.timezone_city_combo
        self.timezone_city_index = {}  #map human readable city name to Europe/London style zone
        self.city_index = []  # map cities to indexes for the combo box

        prev_continent = ''
        for location in self.tzdb.locations:
            #self.tzmap.add_point("", location.longitude, location.latitude,
            #                     NORMAL_RGBA)
            zone_bits = location.zone.split('/')
            if len(zone_bits) == 1:
                continue
            continent = zone_bits[0]
            if continent != prev_continent:
                timezone_city_combo.addItem('')
                self.city_index.append('')
                timezone_city_combo.addItem("--- %s ---" % continent)
                self.city_index.append("--- %s ---" % continent)
                prev_continent = continent
            human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
            timezone_city_combo.addItem(human_zone)
            self.timezone_city_index[human_zone] = location.zone
            self.city_index.append(human_zone)
            self.tzmap.cities[human_zone] = [location.latitude, location.longitude]

        self.frontend.app.connect(self.tzmap, SIGNAL("cityChanged"), self.cityChanged)
        self.mapped()

    def set_city_text(self, name):
        """ Gets a long name, Europe/London """
        timezone_city_combo = self.frontend.userinterface.timezone_city_combo
        count = timezone_city_combo.count()
        found = False
        i = 0
        zone_bits = name.split('/')
        human_zone = '/'.join(zone_bits[1:]).replace('_', ' ')
        while not found and i < count:
            if str(timezone_city_combo.itemText(i)) == human_zone:
                timezone_city_combo.setCurrentIndex(i)
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
        """ Gets a long name, Europe/London """

        (longitude, latitude) = (0.0, 0.0)

        for location in self.tzdb.locations:
            if location.zone == name:
                (longitude, latitude) = (location.longitude, location.latitude)
                break
        else:
            return

        self.location_selected = location
        self.set_city_text(self.location_selected.zone)
        self.set_zone_text(self.location_selected)
        self.frontend.allow_go_forward(True)

        if name == None or name == "":
            return

    def get_tz_from_name(self, name):
        if len(name) != 0:
            return self.timezone_city_index[name]
        else:
            return None

    def city_combo_changed(self, index):
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
        return True

    def mapped(self):
        if self.update_timeout is None:
            self.update_timeout = QTimer()
            self.frontend.app.connect(self.update_timeout, SIGNAL("timeout()"), self.timeout)
            self.update_timeout.start(100)

    def cityChanged(self):
        self.frontend.userinterface.timezone_city_combo.setCurrentIndex(self.city_index.index(self.tzmap.city))
        self.city_combo_changed(self.frontend.userinterface.timezone_city_combo.currentIndex())
        self.frontend.allow_go_forward(True)

class CityIndicator(QLabel):
    def __init__(self, parent, name="cityindicator"):
        QLabel.__init__(self, parent)
        self.setMouseTracking(True)
        self.setMargin(1)
        self.setIndent(0)
        self.setAutoFillBackground(True)
        self.setLineWidth(1)
        self.setFrameStyle(QFrame.Box | QFrame.Plain)
        self.setPalette(QToolTip.palette())
        self.setText("CityIndicator")

    def mouseMoveEvent(self, mouseEvent):
        mouseEvent.ignore()

    def setText(self, text):
        """ implement auto resize """
        QLabel.setText(self, text)
        self.adjustSize()

class MapWidget(QWidget):
    def __init__(self, parent, name="mapwidget"):
        QWidget.__init__(self, parent)
        self.setObjectName(name)
        self.setAutoFillBackground(True)
        self.imagePath = "/usr/share/ubiquity/pixmaps/world_map-960.png"
        image = QImage(self.imagePath);
        pixmapUnscaled = QPixmap(self.imagePath);
        pixmap = pixmapUnscaled.scaled( QSize(self.width(), self.height()) )
        palette = QPalette()
        palette.setBrush(self.backgroundRole(), QBrush(pixmap))
        self.setPalette(palette)
        self.cities = {}
        self.cities['Edinburgh'] = [self.coordinate(False, 55, 50, 0), self.coordinate(True, 3, 15, 0)]
        self.timer = QTimer(self)
        self.connect(self.timer, SIGNAL("timeout()"), self.updateCityIndicator)
        self.setMouseTracking(True)

        self.cityIndicator = CityIndicator(self)
        self.cityIndicator.setText("")
        self.cityIndicator.hide()

    def paintEvent(self, paintEvent):
        ##FIXME this is slow, need to buffer the output.
        painter = QPainter(self)
        for city in self.cities:
            self.drawCity(self.cities[city][0], self.cities[city][1], painter)

    def drawCity(self, lat, long, painter):
        point = self.getPosition(lat, long, self.width(), self.height())
        painter.setPen(QPen(QColor(250,100,100), 1))
        painter.drawPoint(point.x(), point.y()-1)
        painter.drawPoint(point.x()-1, point.y())
        painter.drawPoint(point.x(), point.y())
        painter.drawPoint(point.x()+1, point.y())
        painter.drawPoint(point.x(), point.y()+1)
        painter.setPen(QPen(QColor(0,0,0), 1))
        painter.drawPoint(point.x(), point.y()-2)
        painter.drawPoint(point.x()-1, point.y()-1)
        painter.drawPoint(point.x()+1, point.y()-1)
        painter.drawPoint(point.x()-2, point.y())
        painter.drawPoint(point.x()+2, point.y())
        painter.drawPoint(point.x()-1, point.y()+1)
        painter.drawPoint(point.x()+1, point.y()+1)
        painter.drawPoint(point.x(), point.y()+2)

    def getPosition(self, la, lo, w, h):
        x = (w * (180.0 + lo) / 360.0)
        y = (h * (90.0 - la) / 180.0)

        return QPoint(int(x),int(y))

    def coordinate(self, neg, d, m, s):
        if neg:
            return - (d + m/60.0 + s/3600.0)
        else :
            return d + m/60.0 + s/3600.0

    def getNearestCity(self, w, h, x, y):
        result = None
        dist = 1.0e10
        for city in self.cities:
            pos = self.getPosition(self.cities[city][0], self.cities[city][1], self.width(), self.height())

            d = (pos.x()-x)*(pos.x()-x) + (pos.y()-y)*(pos.y()-y)
            if d < dist:
                dist = d
                self.where = pos
                result = city
        return result

    def mouseMoveEvent(self, mouseEvent):
        self.x = mouseEvent.pos().x()
        self.y = mouseEvent.pos().y()
        if not self.timer.isActive():
            self.timer.setSingleShot(True)
            self.timer.start(25)

    def updateCityIndicator(self):
        city = self.getNearestCity(self.width(), self.height(), self.x, self.y)
        if city is None:
            return
        self.cityIndicator.setText(city)
        movePoint = self.getPosition(self.cities[city][0], self.cities[city][1], self.width(), self.height())
        self.cityIndicator.move(movePoint.x(), movePoint.y() - self.cityIndicator.height())
        self.cityIndicator.show()

    def mouseReleaseEvent(self, mouseEvent):
        pos = mouseEvent.pos()

        city = self.getNearestCity(self.width(), self.height(), pos.x(), pos.y());
        if city is None:
            return
        elif city == "Edinburgh":
            self.city = "London"
        else:
            self.city = city
        self.emit(SIGNAL("cityChanged"), ())

    def resizeEvent(self, resizeEvent):
        image = QImage(self.imagePath);
        pixmapUnscaled = QPixmap(self.imagePath);
        pixmap = pixmapUnscaled.scaled( QSize(self.width(), self.height()), Qt.IgnoreAspectRatio, Qt.SmoothTransformation)
        palette = QPalette()
        palette.setBrush(self.backgroundRole(), QBrush(pixmap))
        self.setPalette(palette)
