# -*- coding: utf-8; Mode: Python; indent-tabs-mode: nil; tab-width: 4 -*-
# -*- kate: indent-mode python; space-indent true; indent-width 4; backspace-indents true
#
# Copyright (C) 2006, 2007, 2008, 2009 Canonical Ltd.
#
# Author(s):
#   Jonathan Riddell <jriddell@ubuntu.com>
#   Mario Limonciello <superm1@ubuntu.com>
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

import sys
import os
import datetime
import subprocess
import math
import traceback
import syslog
import atexit
import signal
import gettext

# kde gui specifics
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from PyQt4 import uic
from PyKDE4.kdeui import *
from PyKDE4.kdecore import *

#import all our custome kde components
from ubiquity.frontend.kde_components.Timezone import *
from ubiquity.frontend.kde_components.PartitionBar import *
from ubiquity.frontend.kde_components.PartitionModel import *

import debconf

from ubiquity import filteredcommand, i18n, validation, parted_server
from ubiquity.misc import *
from ubiquity.components import console_setup, language, timezone, usersetup, \
                                partman, partman_commit, summary, install
import ubiquity.progressposition
from ubiquity.frontend.base import BaseFrontend

# Define global path
PATH = '/usr/share/ubiquity'

# Define locale path
LOCALEDIR = "/usr/share/locale"

#currently using for testing, will remove
UIDIR = os.path.join(PATH, 'qt')
    
##custom clickable label for minimizing the app
#class MinimizeIcon(QLabel):
    #def __init__(self, parent, ui):
        #QLabel.__init__(self, parent)
        
        #self.ui = ui        
        #self.setFixedSize(14,14)
        #self.setObjectName("minimize_label")
        #self.setCursor(Qt.PointingHandCursor)
        
    #def mouseReleaseEvent(self, qMouseEvent):
        #self.ui.showMinimized()
    
class UbiquityUI(QMainWindow):

    def __init__(self, parent = None):
        QMainWindow.__init__(self, parent)
        uic.loadUi(os.path.join(UIDIR, "app.ui"), self)
        
        distro_name = "Kubuntu"
        distro_release = ""
        
        ## setup the release and codename
        fp = open("/etc/lsb-release", 'r')
        
        for line in fp:
            if "DISTRIB_ID=" in line:
                name = str.strip(line.split("=")[1], '\n')
                if name != "Ubuntu":
                    distro_name = name
            elif "DISTRIB_CODENAME=" in line:
                distro_release = str.strip(line.split("=")[1], '\n')
                
        fp.close()
        
        self.distro_name_label.setText(distro_name)
        self.distro_release_label.setText(distro_release)
        
        self.minimize_button.clicked.connect(self.showMinimized)
        
        self.setWindowTitle("%s %s" % (distro_name, distro_release))

    def setWizard(self, wizardRef):
        self.wizard = wizardRef

    def closeEvent(self, event):
        if self.wizard.on_quit_clicked() == False:
            event.ignore()

class linkLabel(QLabel):

    def __init__(self, wizard, parent):
        QLabel.__init__(self, parent)
        self.wizard = wizard

    def mouseReleaseEvent(self, event):
        self.wizard.openReleaseNotes()

    def setText(self, text):
        QLabel.setText(self, text)
        self.resize(self.sizeHint())

class Wizard(BaseFrontend):

    def __init__(self, distro):
        BaseFrontend.__init__(self, distro)

        self.previous_excepthook = sys.excepthook
        sys.excepthook = self.excepthook

        appName     = "kubuntu-ubiquity"
        catalog     = ""
        programName = ki18n ("Installer")
        version     = "1.0"
        description = ki18n ("Live CD Installer for Kubuntu")
        license     = KAboutData.License_GPL
        copyright   = ki18n ("(c) 2006 Canonical Ltd")
        text        = ki18n ("none")
        homePage    = "http://wiki.kubuntu.org/KubuntuUbiquity"
        bugEmail    = "jriddell@ubuntu.com"
        
        about = KAboutData (appName, catalog, programName, version, description,
                            license, copyright, text, homePage, bugEmail)
        about.addAuthor(ki18n("Jonathan Riddell"), KLocalizedString() ,"jriddell@ubuntu.com")
        about.addAuthor(ki18n("Roman Shtylman"), KLocalizedString() ,"shtylman@gmail.com")
        KCmdLineArgs.init([""],about)
        
        #undo the drop, this is needed to play nice with kde
        os.setegid(0)
        os.seteuid(0)
        
        self.app = KApplication()
        self.app.setStyleSheet(file(os.path.join(UIDIR, "style.qss")).read())

        # put the privileges back
        drop_privileges()

        self.ui = UbiquityUI()
        
        # initially the steps widget is not visible
        # it becomes visible once the first step becomes active
        self.ui.steps_widget.setVisible(False)
        
        #if 'UBIQUITY_ONLY' in os.environ:
        self.ui.setWindowState(self.ui.windowState() ^ Qt.WindowFullScreen)
                
        self.ui.setWizard(self)
        #self.ui.setWindowFlags(Qt.Window | Qt.CustomizeWindowHint | Qt.WindowTitleHint | Qt.WindowMinMaxButtonsHint)
        
        #if hasattr(Qt, 'WindowCloseButtonHint'):
        #    self.ui.setWindowFlags(self.ui.windowFlags() | Qt.WindowCloseButtonHint)
           
        #center the shown window
        #rect = QApplication.instance().desktop().availableGeometry(self.ui);
        #self.ui.move(rect.center() - self.ui.rect().center());

        self.advanceddialog = QDialog(self.ui)
        uic.loadUi(os.path.join(UIDIR, "advanceddialog.ui"), self.advanceddialog)

        # declare attributes
        self.release_notes_url_template = None
        self.language_questions = (
            'live_installer',
            'welcome_heading_label', 
            'welcome_text_label',
            'oem_id_label',
            'release_notes_label',
            'release_notes_url',
            'step_label',
            'quit', 
            'back', 
            'next'
        )
                                   
        self.current_page = None
        self.first_seen_page = None
        self.allowed_change_step = True
        self.allowed_go_backward = True
        self.allowed_go_forward = True
        self.stay_on_page = False
        self.mainLoopRunning = False
        self.progressDialogue = None
        self.progress_position = ubiquity.progressposition.ProgressPosition()
        self.progress_cancelled = False
        self.resizePath = None
        self.resizeSize = None
        self.username_edited = False
        self.hostname_edited = False
        self.previous_partitioning_page = self.step_index("stepPartAuto")
        self.installing = False
        self.installing_no_return = False
        self.returncode = 0
        self.partition_bars = []
        self.disk_layout = None

        self.laptop = execute("laptop-detect")
        self.partition_tree_model = None
        
        #self.app.connect(self.ui.partition_list_treeview, SIGNAL("customContextMenuRequested(const QPoint&)"), self.partman_popup)
        #self.app.connect(self.ui.partition_list_treeview, SIGNAL("activated(const QModelIndex&)"), self.on_partition_list_treeview_activated)

        # set default language
        dbfilter = language.Language(self, self.debconf_communicator())
        dbfilter.cleanup()
        dbfilter.db.shutdown()

        self.debconf_callbacks = {}    # array to keep callback functions needed by debconf file descriptors

        self.customize_installer()

        #release_notes_layout = QHBoxLayout(self.ui.release_notes_frame)
        #self.release_notes_url = linkLabel(self, self.ui.release_notes_frame)
        #self.release_notes_url.setObjectName("release_notes_url")
        #self.release_notes_url.show()

        self.translate_widgets()
        
        self.autopartition_buttongroup = QButtonGroup(self.ui.autopart_selection_frame)
        self.autopartition_buttongroup_texts = {}
        self.autopartition_handlers = {}
        self.autopartition_extras = {}
        self.autopartition_extra_choices = {}
        self.autopartition_extra_choices_texts = {}
        
        iconLoader = KIconLoader()
        warningIcon = iconLoader.loadIcon("dialog-warning", KIconLoader.Desktop)
        self.ui.part_advanced_warning_image.setPixmap(warningIcon)
        self.ui.fullname_error_image.setPixmap(warningIcon)
        self.ui.username_error_image.setPixmap(warningIcon)
        self.ui.password_error_image.setPixmap(warningIcon)
        self.ui.hostname_error_image.setPixmap(warningIcon)

        self.forwardIcon = KIcon("go-next")
        self.ui.next.setIcon(self.forwardIcon)

        #Used for the last step
        self.applyIcon = KIcon("dialog-ok-apply")

        backIcon = KIcon("go-previous")
        self.ui.back.setIcon(backIcon)

        quitIcon = KIcon("dialog-close")
        self.ui.quit.setIcon(quitIcon)

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

        self.post_mortem(exctype, excvalue, exctb)

        if os.path.exists('/usr/share/apport/apport-qt'):
            self.previous_excepthook(exctype, excvalue, exctb)
        else:
            dialog = QDialog(self.ui)
            uic.loadUi("%s/crashdialog.ui" % UIDIR, dialog)
            dialog.beastie_url.setOpenExternalLinks(True)
            dialog.crash_detail.setText(tbtext)
            dialog.exec_()
            sys.exit(1)

    # Disable the KDE media notifier to avoid problems during partitioning.
    def disable_volume_manager(self):
        print "FIXME, medianotifier unload port to KDE 4"
        #execute('dcop', 'kded', 'kded', 'unloadModule', 'medianotifier')
        atexit.register(self.enable_volume_manager)

    def enable_volume_manager(self):
        print "FIXME, medianotifier unload port to KDE 4"
        #execute('dcop', 'kded', 'kded', 'loadModule', 'medianotifier')

    def openReleaseNotes(self):
        self.openURL(self.release_notes_url_template)

    def openURL(self, url):
        #need to run this else kdesu can't run Konqueror
        execute('su', '-c', 'xhost +localhost', 'ubuntu')
        execute('su', '-c', 'kfmclient openURL '+url, 'ubuntu')

    def run(self):
        """run the interface."""

        if os.getuid() != 0:
            title = ('This installer must be run with administrative '
                     'privileges, and cannot continue without them.')
            result = QMessageBox.critical(self.ui, "Must be root",
                                          title)
            sys.exit(1)

        self.disable_volume_manager()

        # show interface
        # TODO cjwatson 2005-12-20: Disabled for now because this segfaults in
        # current dapper (https://bugzilla.ubuntu.com/show_bug.cgi?id=20338).
        #self.show_browser()
        got_intro = self.show_intro()
        self.allow_change_step(True)
        
        # Declare SignalHandler
        self.ui.next.clicked.connect(self.on_next_clicked)
        self.ui.back.clicked.connect(self.on_back_clicked)
        self.ui.quit.clicked.connect(self.on_quit_clicked)
        
        self.ui.language_combobox.currentIndexChanged[str].connect(self.on_language_combobox_selection_changed)

        #use activated instead of changed because we only want to act when the user changes the selection
        #not when we are populating the combo box
        self.ui.keyboard_layout_combobox.activated.connect(self.on_keyboard_layout_selected)
        self.ui.keyboard_variant_combobox.activated.connect(self.on_keyboard_variant_selected)
        
        self.ui.fullname.textChanged[str].connect(self.on_fullname_changed)
        self.ui.username.textChanged[str].connect(self.on_username_changed)
        self.ui.password.textChanged[str].connect(self.on_password_changed)
        self.ui.verified_password.textChanged[str].connect(self.on_verified_password_changed)
        
        self.ui.hostname.textChanged[str].connect(self.on_hostname_changed)

        #self.app.connect(self.ui.fullname, SIGNAL("selectionChanged()"), self.on_fullname_changed)
        #self.app.connect(self.ui.username, SIGNAL("selectionChanged()"), self.on_username_changed)
        #self.app.connect(self.ui.password, SIGNAL("selectionChanged()"), self.on_password_changed)
        #self.app.connect(self.ui.verified_password, SIGNAL("selectionChanged()"), self.on_verified_password_changed)
        #self.app.connect(self.ui.hostname, SIGNAL("selectionChanged()"), self.on_hostname_changed)
        
        self.ui.advanced_button.clicked.connect(self.on_advanced_button_clicked)

        self.ui.partition_button_new_label.clicked[bool].connect(self.on_partition_list_new_label_activate)
        self.ui.partition_button_new.clicked[bool].connect(self.on_partition_list_new_activate)
        self.ui.partition_button_edit.clicked[bool].connect(self.on_partition_list_edit_activate)
        self.ui.partition_button_delete.clicked[bool].connect(self.on_partition_list_delete_activate)
        self.ui.partition_button_undo.clicked[bool].connect(self.on_partition_list_undo_activate)

        self.pagesindex = 0

        if 'UBIQUITY_AUTOMATIC' in os.environ:
            got_intro = False
            self.debconf_progress_start(0, pageslen,
                self.get_string('ubiquity/install/checking'))
            self.refresh()

        # Start the interface
        if got_intro:
            self.pages.insert(0, None) # for page index bookkeeping
            first_step = "stepWelcome"
        else:
            first_step = self.pagenames[0]
            self.ui.steps_widget.setVisible(True)
        
        self.set_current_page(self.step_index(first_step))
        
        if got_intro:
            self.app.exec_()
            self.pagesindex += 1
        
        pageslen = len(self.pages)
        while(self.pagesindex < pageslen):
            if self.current_page == None:
                break

            self.backup = False
            old_dbfilter = self.dbfilter
            self.dbfilter = self.pages[self.pagesindex](self)

            # Non-debconf steps are no longer possible as the interface is now
            # driven by whether there is a question to ask.
            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                self.allow_change_step(False)
                self.dbfilter.start(auto_process=True)
            self.app.exec_()

            if self.backup or self.dbfilter_handle_status():
                if self.installing:
                    self.progress_loop()
                elif self.current_page is not None and not self.backup:
                    self.process_step()
                    if not self.stay_on_page:
                        self.pagesindex = self.pagesindex + 1
                    if 'UBIQUITY_AUTOMATIC' in os.environ:
                        # if no debconf_progress, create another one, set start to pageindex
                        self.debconf_progress_step(1)
                        self.refresh()
                if self.backup:
                    if self.pagesindex > 0:
                        step = self.step_name(self.get_current_page())
                        if not step == "stepPartAdvanced": #Advanced will already have pagesindex pointing at first Paritioning page
                            self.pagesindex = self.pagesindex - 1

            self.app.processEvents()

            # needed to be here for --automatic as there might not be any
            # current page in the event all of the questions have been
            # preseeded.
            if self.pagesindex == pageslen:
                # Ready to install
                self.ui.hide()
                self.current_page = None
                self.installing = True
                self.progress_loop()
        return self.returncode

    def customize_installer(self):
        """Initial UI setup."""
        
        self.ui.setWindowIcon(KIcon("ubiquity"))
        self.allow_go_backward(False)

        if self.oem_config:
            self.ui.setWindowTitle(
                self.get_string('oem_config_title'))
            try:
                self.ui.oem_id_entry.setText(
                    self.debconf_operation('get', 'oem-config/id'))
            except debconf.DebconfError:
                pass
            self.ui.fullname.setText(
                'OEM Configuration (temporary user)')
            self.ui.fullname.setReadOnly(True)
            self.ui.fullname.setEnabled(False)
            self.ui.username.setText('oem')
            self.ui.username.setReadOnly(True)
            self.ui.username.setEnabled(False)
            self.username_edited = True
            if self.laptop:
                self.ui.hostname.setText('oem-laptop')
            else:
                self.ui.hostname.setText('oem-desktop')
            self.hostname_edited = True
            self.ui.login_pass.hide()
            self.ui.login_auto.hide()
            # The UserSetup component takes care of preseeding passwd/user-uid.
            execute_root('apt-install', 'oem-config-kde')
        else:
            self.ui.oem_id_label.hide()
            self.ui.oem_id_entry.hide()

        if self.oem_user_config:
            self.ui.setWindowTitle(
                self.get_string('oem_user_config_title'))
            self.ui.setWindowIcon(KIcon("preferences-system"))
            flags = self.ui.windowFlags() ^ Qt.WindowMinMaxButtonsHint
            if hasattr(Qt, 'WindowCloseButtonHint'):
                flags = flags ^ Qt.WindowCloseButtonHint
            self.ui.setWindowFlags(flags)
            self.ui.quit.hide()
        
        if not 'UBIQUITY_AUTOMATIC' in os.environ:
            self.ui.show()

        try:
            release_notes = open('/cdrom/.disk/release_notes_url')
            self.release_notes_url_template = release_notes.read().rstrip('\n')
            release_notes.close()
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.ui.release_notes_label.hide()
            self.ui.release_notes_frame.hide()
        
        # init the timezone map
        self.tzmap = TimezoneMap(self)
        #self.tzmap.setObjectName("tz_frame")
        self.ui.map_frame.layout().addWidget(self.tzmap)

        self.ui.password_debug_warning_label.setVisible(
            'UBIQUITY_DEBUG' in os.environ)

    def set_layout_direction(self, lang=None):
        if not lang:
            lang = self.locale
        # TODO: At the moment we have to special-case languages. This will
        # be easier to fix when we move to cdebconf and have the
        # debconf/text-direction template easily available.
        if lang.startswith('ar') or lang.startswith('he'):
            direction = Qt.RightToLeft
        else:
            direction = Qt.LeftToRight
        self.app.setLayoutDirection(direction)

    # translates widget text based on the object names
    def translate_widgets(self, parentWidget=None):
        if self.locale is None:
            languages = []
        else:
            languages = [self.locale]
        core_names = ['ubiquity/text/%s' % q for q in self.language_questions]
        core_names.append('ubiquity/text/oem_config_title')
        core_names.append('ubiquity/text/oem_user_config_title')
        for stock_item in ('cancel', 'close', 'go-back', 'go-forward',
                           'ok', 'quit'):
            core_names.append('ubiquity/imported/%s' % stock_item)
        i18n.get_translations(languages=languages, core_names=core_names)

        self.translate_widget_children(parentWidget)

        self.ui.partition_button_undo.setText(
            self.get_string('partman/text/undo_everything').replace('_', '&', 1))
        if self.release_notes_url_template is not None:
            url = self.release_notes_url_template.replace('${LANG}', self.locale.split('.')[0])
            text = self.get_string('release_notes_url')
            self.release_notes_url.setText('<a href="%s">%s</a>' % (url, text))

        self.set_layout_direction()

    def translate_widget_children(self, parentWidget=None):
        if parentWidget == None:
            parentWidget = self.ui

        self.translate_widget(parentWidget, self.locale)
        if parentWidget.children() != None:
            for widget in parentWidget.children():
                self.translate_widget_children(widget)

    def translate_widget(self, widget, lang):
        #FIXME needs translations for Next, Back and Cancel
        if not isinstance(widget, QWidget):
            return

        name = str(widget.objectName())
        
        text = self.get_string(name, lang)

        if str(name) == "UbiquityUIBase":
            text = self.get_string("live_installer", lang)

        if text is None:
            return

        if isinstance(widget, QLabel):
            if name == 'step_label':
                curstep = '?'
                for page in self.pages:
                    if self.dbfilter is page or (page and isinstance(self.dbfilter, page)):
                        curstep = str(self.pages.index(page) + 1)
                        break
                text = text.replace('${INDEX}', curstep)
                text = text.replace('${TOTAL}', str(len(self.pages)))
            elif name == 'welcome_text_label' and self.oem_user_config:
                text = self.get_string('welcome_text_oem_user_label', lang)

            if 'heading_label' in name:
                widget.setText("<h2>" + text + "</h2>")
            elif 'extra_label' in name:
                widget.setText("<small>" + text + "</small>")
            elif ('group_label' in name or 'warning_label' in name or
                  name in ('drives_label', 'partition_method_label')):
                widget.setText("<strong>" + text + "</strong>")
            elif name == 'release_notes_url':
                if self.release_notes_url_template is not None:
                    url = self.release_notes_url_template.replace(
                        '${LANG}', lang.split('.')[0])
                    widget.setText('<a href="%s">%s</a>' % (url, text))
            else:
                widget.setText(text)
                
        elif isinstance(widget, QAbstractButton):
            widget.setText(text.replace('_', '&', 1))

        elif isinstance(widget, QWidget) and str(name) == "UbiquityUIBase":
            if self.oem_config:
                text = self.get_string('oem_config_title', lang)
            elif self.oem_user_config:
                text = self.get_string('oem_user_config_title', lang)
            widget.setWindowTitle(text)

        else:
            print "WARNING: unknown widget: " + name
            print "Type: ", type(widget)

    def allow_change_step(self, allowed):
        if allowed:
            cursor = QCursor(Qt.ArrowCursor)
        else:
            cursor = QCursor(Qt.WaitCursor)
        self.ui.setCursor(cursor)
        self.ui.back.setEnabled(allowed and self.allowed_go_backward)
        self.ui.next.setEnabled(allowed and self.allowed_go_forward)
        self.allowed_change_step = allowed

    def allow_go_backward(self, allowed):
        self.ui.back.setEnabled(allowed and self.allowed_change_step)
        self.allowed_go_backward = allowed

    def allow_go_forward(self, allowed):
        self.ui.next.setEnabled(allowed and self.allowed_change_step)
        self.allowed_go_forward = allowed

    def dbfilter_handle_status(self):
        """If a dbfilter crashed, ask the user if they want to continue anyway.

        Returns True to continue, or False to try again."""

        if not self.dbfilter_status or self.current_page is None:
            return True

        syslog.syslog('dbfilter_handle_status: %s' % str(self.dbfilter_status))

        # TODO cjwatson 2007-04-04: i18n
        text = ('%s failed with exit code %s. Further information may be '
                'found in /var/log/syslog. Do you want to try running this '
                'step again before continuing? If you do not, your '
                'installation may fail entirely or may be broken.' %
                (self.dbfilter_status[0], self.dbfilter_status[1]))
        #FIXME QMessageBox seems to have lost the ability to set custom labels
        # so for now we have to get by with these not-entirely meaningful stock labels
        answer = QMessageBox.warning(self.ui,
                                     '%s crashed' % self.dbfilter_status[0],
                                     text, QMessageBox.Retry,
                                     QMessageBox.Ignore, QMessageBox.Close)
        self.dbfilter_status = None
        syslog.syslog('dbfilter_handle_status: answer %d' % answer)
        if answer == QMessageBox.Ignore:
            return True
        elif answer == QMessageBox.Close:
            self.quit()
        else:
            step = self.step_name(self.get_current_page())
            if str(step).startswith("stepPart"):
                self.set_current_page(self.step_index("stepPartAuto"))
            return False

    def show_intro(self):
        """Show some introductory text, if available."""

        if self.oem_user_config:
            return False

        intro = os.path.join(PATH, 'intro.txt')
        
        if os.path.isfile(intro):
            intro_file = open(intro)
            text = ""
            for line in intro_file:
                text = text + line + "<br>"
            self.ui.introLabel.setText(text)
            intro_file.close()
            return True
        else:
            return False

    def step_name(self, step_index):
        if step_index < 0:
            step_index = 0
        return str(self.ui.widgetStack.widget(step_index).objectName())

    def step_index(self, step_name):
        if hasattr(self.ui, step_name):
          step = getattr(self.ui, step_name)
          return self.ui.widgetStack.indexOf(step)
        else:
          return 0

    def set_page(self, n):
        self.run_automation_error_cmd()
        self.ui.show()
        
        activeSS = "color: %s; " % "#666666"
        inactiveSS = "color: %s; " % "#b3b3b3"
        currentSS = "color: %s; " % "#0088aa"
        
        #self.ui.dummy_active_step.styleSheet()
        #inactiveSS = self.ui.dummy_inactive_step.styleSheet()
        #currentSS = self.ui.dummy_current_step.styleSheet()
        
        #set all the steps active
        #each step will set its previous ones as inactive
        #this handles the abiliy to go back
        
        self.ui.languageStep.setStyleSheet(activeSS)
        self.ui.timezoneStep.setStyleSheet(activeSS)
        self.ui.keyboardStep.setStyleSheet(activeSS)
        self.ui.partitionStep.setStyleSheet(activeSS)
        self.ui.userInfoStep.setStyleSheet(activeSS)
        self.ui.summaryStep.setStyleSheet(activeSS)
        self.ui.installStep.setStyleSheet(activeSS)
        
        if n == 'Language':
            self.ui.steps_widget.setVisible(True)
            self.set_current_page(self.step_index("stepLanguage"))
            
            self.ui.languageStep.setStyleSheet(currentSS)
            
        elif n == 'Timezone':
            self.set_current_page(self.step_index("stepLocation"))
            
            self.ui.languageStep.setStyleSheet(inactiveSS)
            self.ui.timezoneStep.setStyleSheet(currentSS)
            
        elif n == 'ConsoleSetup':
            self.set_current_page(self.step_index("stepKeyboardConf"))
            
            self.ui.languageStep.setStyleSheet(inactiveSS)
            self.ui.timezoneStep.setStyleSheet(inactiveSS)
            self.ui.keyboardStep.setStyleSheet(currentSS)

        elif n == 'Partman':
            # Rather than try to guess which partman page we should be on,
            # we leave that decision to set_autopartitioning_choices and
            # update_partman.
            
            self.ui.languageStep.setStyleSheet(inactiveSS)
            self.ui.timezoneStep.setStyleSheet(inactiveSS)
            self.ui.keyboardStep.setStyleSheet(inactiveSS)
            self.ui.partitionStep.setStyleSheet(currentSS)
            
            return
        elif n == 'UserSetup':
            self.set_current_page(self.step_index("stepUserInfo"))
            
            self.ui.languageStep.setStyleSheet(inactiveSS)
            self.ui.timezoneStep.setStyleSheet(inactiveSS)
            self.ui.keyboardStep.setStyleSheet(inactiveSS)
            self.ui.partitionStep.setStyleSheet(inactiveSS)
            self.ui.userInfoStep.setStyleSheet(currentSS)
            
        elif n == 'Summary':
            self.set_current_page(self.step_index("stepReady"))
            self.ui.next.setText(self.get_string('install_button').replace('_', '&', 1))
            self.ui.next.setIcon(self.applyIcon)
            
            self.ui.languageStep.setStyleSheet(inactiveSS)
            self.ui.timezoneStep.setStyleSheet(inactiveSS)
            self.ui.keyboardStep.setStyleSheet(inactiveSS)
            self.ui.partitionStep.setStyleSheet(inactiveSS)
            self.ui.userInfoStep.setStyleSheet(inactiveSS)
            self.ui.summaryStep.setStyleSheet(currentSS)
            
        else:
            print >>sys.stderr, 'No page found for %s' % n
            return

        if not self.first_seen_page:
            self.first_seen_page = n
        if self.first_seen_page == self.pages[self.pagesindex].__name__:
            self.allow_go_backward(False)
        else:
            self.allow_go_backward(True)
    
    def set_current_page(self, current):
        widget = self.ui.widgetStack.widget(current)
        if self.ui.widgetStack.currentWidget() == widget:
            # self.ui.widgetStack.raiseWidget() will do nothing.
            # Update state ourselves.
            self.on_steps_switch_page(current)
        else:
            self.ui.widgetStack.setCurrentWidget(widget)
            self.on_steps_switch_page(current)

    def progress_loop(self):
        """prepare, copy and config the system in the core install process."""

        syslog.syslog('progress_loop()')

        self.current_page = None

        self.debconf_progress_start(
            0, 100, self.get_string('ubiquity/install/title'))
        self.debconf_progress_region(0, 15)

        if not self.oem_user_config:
            dbfilter = partman_commit.PartmanCommit(self)
            if dbfilter.run_command(auto_process=True) != 0:
                while self.progress_position.depth() != 0:
                    self.debconf_progress_stop()
                self.progressDialogue.hide()
                self.return_to_partitioning()
                return

        # No return to partitioning from now on
        self.installing_no_return = True

        self.debconf_progress_region(15, 100)

        dbfilter = install.Install(self)
        ret = dbfilter.run_command(auto_process=True)
        if ret != 0:
            self.installing = False
            if ret == 3:
                # error already handled by Install
                sys.exit(ret)
            elif (os.WIFSIGNALED(ret) and
                  os.WTERMSIG(ret) in (signal.SIGINT, signal.SIGKILL,
                                       signal.SIGTERM)):
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
        quitText = '<qt>%s</qt>' % self.get_string("finished_label")
        rebootButtonText = self.get_string("reboot_button")
        quitButtonText = self.get_string("quit_button")
        titleText = self.get_string("finished_dialog")

        ##FIXME use non-stock messagebox to customise button text
        #quitAnswer = QMessageBox.question(self.ui, titleText, quitText, rebootButtonText, quitButtonText)
        self.run_success_cmd()
        if self.oem_user_config:
            self.quit()
        elif not self.get_reboot_seen():
            if 'UBIQUITY_ONLY' in os.environ:
                quitText = self.get_string('ubiquity/finished_restart_only')
            messageBox = QMessageBox(QMessageBox.Question, titleText, quitText, QMessageBox.NoButton, self.ui)
            messageBox.addButton(rebootButtonText, QMessageBox.AcceptRole)
            if not 'UBIQUITY_ONLY' in os.environ:
                messageBox.addButton(quitButtonText, QMessageBox.RejectRole)
            quitAnswer = messageBox.exec_()

            if quitAnswer == 0:
                self.reboot()
        elif self.get_reboot():
            self.reboot()

    def reboot(self, *args):
        """reboot the system after installing process."""

        self.returncode = 10
        self.quit()

    def do_reboot(self):
        """Callback for main program to actually reboot the machine."""

        if 'DESKTOP_SESSION' in os.environ:
            execute('qdbus', 'org.kde.ksmserver', '/KSMServer', 'org.kde.KSMServerInterface.logout',
                    # ShutdownConfirmNo, ShutdownTypeReboot,
                    # ShutdownModeForceNow
                    '0', '1', '2')
        else:
            execute('reboot')

    def quit(self):
        """quit installer cleanly."""

        # exiting from application
        self.current_page = None
        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
        self.app.exit()

    def on_quit_clicked(self):
        warning_dialog_label = self.get_string("warning_dialog_label")
        abortTitle = self.get_string("warning_dialog")
        continueButtonText = self.get_string("continue")
        response = QMessageBox.question(self.ui, abortTitle, warning_dialog_label, abortTitle, continueButtonText)
        if response == 0:
            self.current_page = None
            self.quit()
            return True
        else:
            return False

    def info_loop(self, widget):
        """check if all entries from Identification screen are filled."""

        if (widget is not None and widget.objectName() == 'fullname' and
            not self.username_edited):
            self.ui.username.blockSignals(True)
            new_username = unicode(widget.text()).split(' ')[0]
            new_username = new_username.encode('ascii', 'ascii_transliterate')
            new_username = new_username.lower()
            self.ui.username.setText(new_username)
            self.ui.username.blockSignals(False)
        elif (widget is not None and widget.objectName() == 'username' and
              not self.hostname_edited):
            if self.laptop:
                hostname_suffix = '-laptop'
            else:
                hostname_suffix = '-desktop'
            self.ui.hostname.blockSignals(True)
            self.ui.hostname.setText(unicode(widget.text()).strip() + hostname_suffix)
            self.ui.hostname.blockSignals(False)

        complete = True
        for name in ('username', 'hostname'):
            if getattr(self.ui, name).text() == '':
                complete = False
        if not self.allow_password_empty:
            for name in ('password', 'verified_password'):
                if getattr(self.ui, name).text() == '':
                    complete = False
        self.allow_go_forward(complete)

    def on_next_clicked(self):
        """Callback to control the installation process between steps."""

        if not self.allowed_change_step or not self.allowed_go_forward:
            return

        self.allow_change_step(False)

        step = self.step_name(self.get_current_page())

        # Beware that 'step' is the step we're leaving, not the one we're
        # entering. At present it's a little awkward to define actions that
        # occur upon entering a page without unwanted side-effects when the
        # user tries to go forward but fails due to validation.
        if step == "stepPartAuto":
            self.ui.part_advanced_warning_message.clear()
            self.ui.part_advanced_warning_hbox.setVisible(False)
        if step in ("stepPartAuto", "stepPartAdvanced"):
            self.ui.fullname_error_image.hide()
            self.ui.fullname_error_reason.hide()
            self.ui.username_error_image.hide()
            self.ui.username_error_reason.hide()
            self.ui.password_error_image.hide()
            self.ui.password_error_reason.hide()
            self.ui.hostname_error_image.hide()
            self.ui.hostname_error_reason.hide()

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
                pass

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

        # Language
        elif step == "stepLanguage":
            self.translate_widgets()
        # Automatic partitioning
        elif step == "stepPartAuto":
            self.process_autopartitioning()
        # Advanced partitioning
        elif step == "stepPartAdvanced":
            ##if not 'UBIQUITY_MIGRATION_ASSISTANT' in os.environ:  #FIXME for migration-assistant
            self.info_loop(None)
            #else:
            #    self.set_current_page(self.steps.page_num(self.stepMigrationAssistant))
        # Identification
        elif step == "stepUserInfo":
            self.process_identification()

    def process_identification (self):
        """Processing identification step tasks."""

        error_msg = []
        error = 0

        # Validation stuff

        # checking hostname entry
        hostname = self.ui.hostname.text()
        for result in validation.check_hostname(unicode(hostname)):
            if result == validation.HOSTNAME_LENGTH:
                error_msg.append("The hostname must be between 1 and 63 characters long.")
            elif result == validation.HOSTNAME_BADCHAR:
                error_msg.append("The hostname may only contain letters, digits, hyphens, and dots.")
            elif result == validation.HOSTNAME_BADHYPHEN:
                error_msg.append("The hostname may not start or end with a hyphen.")
            elif result == validation.HOSTNAME_BADDOTS:
                error_msg.append('The hostname may not start or end with a dot, or contain the sequence "..".')

        # showing warning message is error is set
        if len(error_msg) != 0:
            self.ui.hostname_error_reason.setText("\n".join(error_msg))
            self.ui.hostname_error_reason.show()
            self.ui.hostname_error_image.show()
            self.stay_on_page = True
        else:
            self.stay_on_page = False

    def process_autopartitioning(self):
        """Processing automatic partitioning step tasks."""

        self.app.processEvents()

        # For safety, if we somehow ended up improperly initialised
        # then go to manual partitioning.
        #choice = self.get_autopartition_choice()[0]
        #if self.manual_choice is None or choice == self.manual_choice:
        #    self.set_current_page(self.step_index("stepPartAdvanced"))
        #else:
        #    self.set_current_page(self.step_index("stepUserInfo"))

    def on_back_clicked(self):
        """Callback to set previous screen."""

        if not self.allowed_change_step:
            return

        self.allow_change_step(False)

        self.backup = True
        self.stay_on_page = False

        # Enabling next button
        self.allow_go_forward(True)
        # Setting actual step
        step = self.step_name(self.get_current_page())
        self.ui.setCursor(QCursor(Qt.WaitCursor))

        changed_page = False

        if str(step) == "stepReady":
            self.ui.next.setText(self.get_string("next").replace('_', '&', 1))
            self.ui.next.setIcon(self.forwardIcon)
            self.translate_widget(self.ui.next, self.locale)

        if self.dbfilter is not None:
            self.dbfilter.cancel_handler()
            # expect recursive main loops to be exited and
            # debconffilter_done() to be called when the filter exits
        else:
            self.app.exit()

    def selected_language (self):
        selection = self.ui.language_combobox.selectedItems()
        if len(selection) == 1:
            value = unicode(selection[0].text())
            return self.language_choice_map[value][1]
        else:
            return ''
    
    def on_language_combobox_selection_changed (self, language):
        if language.isNull():
            return
            
        lang = self.language_choice_map[unicode(language)][1]
        if lang:
            # strip encoding; we use UTF-8 internally no matter what
            lang = lang.split('.')[0].lower()
            for widget in (
                self.ui, 
                self.ui.welcome_heading_label, 
                self.ui.welcome_text_label, 
                self.ui.oem_id_label, 
                self.ui.release_notes_label, 
                self.ui.release_notes_frame, 
                self.ui.next, 
                self.ui.back, 
                self.ui.quit
            ):
                self.translate_widget(widget, lang)
            self.set_layout_direction(lang)

    def on_steps_switch_page(self, newPageID):
        self.current_page = newPageID
        #self.translate_widget(self.ui.step_label, self.locale)
        syslog.syslog('switched to page %s' % self.step_name(newPageID))

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
        if progress_title is None:
            progress_title = ""
        total_steps = progress_max - progress_min
        if self.progressDialogue is None:
            skipText = self.get_string("progress_cancel_button")
            self.progressDialogue = QProgressDialog('', skipText, 0, total_steps, self.ui)
            self.progressDialogue.setWindowModality(Qt.WindowModal);
            self.cancelButton = QPushButton(skipText, self.progressDialogue)
            self.progressDialogue.setCancelButton(self.cancelButton)
            # This needs to be called after setCancelButton, otherwise that
            # function will cause the button to be shown again.
            self.cancelButton.hide()
        elif self.progress_position.depth() == 0:
            self.progressDialogue.setMaximum(total_steps)

        self.progress_position.start(progress_min, progress_max,
                                     progress_title)
        self.progressDialogue.setWindowTitle(progress_title)
        self.debconf_progress_set(0)
        self.progressDialogue.setLabel(QLabel(''))
        self.progressDialogue.show()

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
        self.progress_cancelled = False
        self.progress_position.stop()
        if self.progress_position.depth() == 0:
            self.progressDialogue.reset() # also hides dialog
        else:
            self.progressDialogue.setWindowTitle(self.progress_position.title())

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
        self.socketNotifierRead.activated.disconnect(self.watch_debconf_fd_helper_read)
        if BaseFrontend.debconffilter_done(self, dbfilter):
            self.app.exit()
            return True
        else:
            return False

    def set_language_choices (self, choices, choice_map):
        BaseFrontend.set_language_choices(self, choices, choice_map)
        self.ui.language_combobox.clear()
        for choice in choices:
            self.ui.language_combobox.addItem(QString(unicode(choice)))

    def set_language (self, language):
        index = self.ui.language_combobox.findText(QString(unicode(language)))
        if index < 0:
            self.ui.language_combobox.addItem("C")
        else:
            self.ui.language_combobox.setCurrentIndex(index)

    def get_language (self):
        lang = self.ui.language_combobox.currentText()
        if not lang.isNull():
            return self.language_choice_map[unicode(lang)][1]
        else:
            return 'C'

    def get_oem_id (self):
        return unicode(self.ui.oem_id_entry.text())

    def set_timezone (self, timezone):
        self.tzmap.set_timezone(timezone)

    def get_timezone (self):
        return self.tzmap.get_timezone()

    def set_keyboard_choices(self, choices):
        self.ui.keyboard_layout_combobox.clear();
        for choice in sorted(choices):
            self.ui.keyboard_layout_combobox.addItem(QString(unicode(choice)))

        if self.current_layout is not None:
            self.set_keyboard(self.current_layout)

    def set_keyboard (self, layout):
        index = self.ui.keyboard_layout_combobox.findText(QString(unicode(layout)))
        
        if index > -1:
            self.ui.keyboard_layout_combobox.setCurrentIndex(index)

    def get_keyboard (self):
        if self.ui.keyboard_layout_combobox.currentIndex() < 0:
            return None
            
        return unicode(self.ui.keyboard_layout_combobox.currentText())

    def set_keyboard_variant_choices(self, choices):
        self.ui.keyboard_variant_combobox.clear();
        for choice in sorted(choices):
            self.ui.keyboard_variant_combobox.addItem(QString(unicode(choice)))

    def set_keyboard_variant(self, variant):
        index = self.ui.keyboard_variant_combobox.findText(QString(unicode(variant)))
        
        if index > -1:
            self.ui.keyboard_variant_combobox.setCurrentIndex(index)

    def get_keyboard_variant(self):
        if self.ui.keyboard_variant_combobox.currentIndex() < 0:
            return None
            
        return unicode(self.ui.keyboard_variant_combobox.currentText())

    # provides the basic disk layout
    def set_disk_layout(self, layout):
        self.disk_layout = layout

    def set_autopartition_choices (self, choices, extra_options,
                                   resize_choice, manual_choice,
                                   biggest_free_choice):
        BaseFrontend.set_autopartition_choices(self, choices, extra_options,
                                               resize_choice, manual_choice,
                                               biggest_free_choice)

        # remove any previous autopartition selections
        for child in self.ui.autopart_selection_frame.children():
            if isinstance(child, QVBoxLayout) or isinstance(child, QButtonGroup):
                pass
            else:
                self.autopart_selection_frame.removeWidget(child)
                #child.hide()

        regain_privileges()
        pserv = parted_server.PartedServer()
        
        disks = {} #dictionary dev -> list of partitions
        for disk in pserv.disks():
            d = disks[disk] = []
            pserv.select_disk(disk)
            for partition in pserv.partitions():
                d.append(partition)
                
        # p_num, p_id, p_size, p_type, p_fs, p_path, p_name
        drop_privileges()
        
        def _on_extra_toggle(extra_bar_frames):
            def slot(index):
                for bf in extra_bar_frames:
                    bf.setVisible(False)
                    
                extra_bar_frames[index].setVisible(True)
                pass
            return slot
        
        # toggle for a choice
        def _on_choice_toggle(extra_frame, bar_frame):
            def slot(enable):
                self.ui.autopart_bar_frame.setVisible(False)
                
                if bar_frame:
                    bar_frame.setVisible(enable)
                    
                    #show the main bar frame if we need to
                    self.ui.autopart_bar_frame.setVisible(enable)
                        
                if extra_frame:
                    extra_frame.setEnabled(enable)
                    
            return slot
            
        # slot for when partition is resized on the bar
        def partitionResized(path, size):
            print path, size
            self.resizePath = path
            self.resizeSize = size
            
        def addBars(parent, before_bar, after_bar):
            frame = QWidget(parent)
            frame.setLayout(QVBoxLayout())
            frame.layout().setSpacing(0)
            
            frame.layout().addWidget(QLabel(self.get_string('ubiquity/text/partition_layout_before')))
            frame.layout().addWidget(before_bar)
            frame.layout().addWidget(QLabel(self.get_string('ubiquity/text/partition_layout_after')))
            frame.layout().addWidget(after_bar)
            
            parent.layout().addWidget(frame)
            return frame
        
            
        #track the first button to set it as the active one
        firstbutton = None
        
        idCounter = 0
        for choice in choices:
            button = QRadioButton(choice, self.ui.autopart_selection_frame)
            self.ui.autopart_selection_frame.layout().addWidget(button)
            self.autopartition_buttongroup.addButton(button, idCounter)
            id = self.autopartition_buttongroup.id(button)

            #Qt changes the string by adding accelerators,
            #so keep pristine string here as is returned later to partman
            self.autopartition_buttongroup_texts[id] = choice
            if firstbutton is None:
                firstbutton = button

            # make a new frames for bars to make hiding/showing multiple easier
            # this allows us to hide an entire main bullet with multiple sub bullets
            self.ui.autopart_bar_frame.setVisible(False)
            
            ## these three things are toggled by each option
            # extra options frame for the option
            frame = None
            bar_frame = QFrame(self.ui.autopart_bar_frame)
            bar_frame.setLayout(QVBoxLayout())
            bar_frame.layout().setSpacing(0)
            self.ui.autopart_bar_frame.layout().addWidget(bar_frame)
            
            # if we have more information about the choice
            # i.e. various hard drives to install onto
            if choice in extra_options:
                # label for the before device
                dev = None
                
                if choice == biggest_free_choice:
                    biggest_free_id = extra_options[choice]
                    dev = None
                    
                    #get the device so we can get more info from it
                    for disk in disks:
                        for p in disks[disk]:
                            if p[1] == biggest_free_id:
                                dev = disk
                                break
                        if dev:
                            break
                            
                    if dev:
                        #create partition bars for graphical before/after display
                        before_bar = PartitionsBar()
                        after_bar = PartitionsBar()
                        
                        for p in disks[dev]:
                            before_bar.addPartition(p[6], int(p[2]), int(p[0]), p[4], p[5])
                            if p[1] == biggest_free_id:
                                after_bar.addPartition('', int(p[2]), int(p[0]), 'auto', get_release_name())
                            else:
                                after_bar.addPartition(p[6], int(p[2]), int(p[0]), p[4], p[5])
                                
                        addBars(bar_frame, before_bar, after_bar)
                
                # install side by side/resize
                elif choice == resize_choice:
                    # information about what can be resized
                    extra = extra_options[choice]
                    for d in self.disk_layout:
                        disk = d
                        if disk.startswith('=dev='):
                            disk = disk[5:]
                        if "%s" % disk in extra[3]:
                            dev = d
                            break

                    min_size, max_size, orig_size, resize_path = extra_options[choice]
                    
                    # TODO use find_in_os_prober to give nice name
                    if dev:
                        before_bar = PartitionsBar()
                        after_bar = PartitionsBar()
                        
                        for p in disks[dev]:
                            before_bar.addPartition(p[6], int(p[2]), int(p[0]), p[4], p[5])
                            after_bar.addPartition(p[6], int(p[2]), int(p[0]), p[4], p[5])
                        
                        after_bar.setResizePartition(resize_path, 
                            min_size, max_size, orig_size, get_release_name())
                        
                        self.resizePath = after_bar.resize_part.path
                        self.resizeSize = after_bar.resize_part.size
                        
                        after_bar.partitionResized.connect(partitionResized)
                        
                        addBars(bar_frame, before_bar, after_bar)
                    
                #full disk install
                elif choice != manual_choice:
                    extra_choice_texts = {}
                    extraIdCounter = 0
                    
                    frame = QFrame(self.ui.autopart_selection_frame)
                    frame.setEnabled(False)
                    self.ui.autopart_selection_frame.layout().addWidget(frame)
                    
                    frame_layout = QHBoxLayout(frame)
                    self.extra_combo = QComboBox(frame)
                    
                    frame_layout.addSpacing(20)
                    frame_layout.addWidget(self.extra_combo)
                    frame_layout.addStretch(1)
                    
                    extra_bar_frames = []
                    extra_bar_frame = None
                    
                    for extra in extra_options[choice]:
                        #each extra choice needs to toggle a change in the before bar
                        #extra is just a string with a general description
                        #each extra choice needs to be a before/after bar option
                        if extra == '':
                            continue
                        
                        # add the extra disk to the combo box
                        self.extra_combo.addItem(extra)
                        
                        #find the device to make a partition bar out of it
                        dev = None
                        for d in self.disk_layout:
                            disk = d
                            if disk.startswith('=dev='):
                                disk = disk[5:]
                            if "(%s)" % disk in extra:
                                dev = d
                                break
                                
                        #add the bars if we found the device
                        if dev:
                            before_bar = PartitionsBar()
                            after_bar = PartitionsBar()
                        
                            for p in disks[dev]:
                                before_bar.addPartition(p[6], int(p[2]), p[0], p[4], p[5])
                                
                            release_name = get_release_name()
                            if before_bar.diskSize > 0:
                                after_bar.addPartition('', before_bar.diskSize, '', 'auto', release_name)
                            else:
                                after_bar.addPartition('', 1, '', 'auto', release_name)
                            
                            extra_bar_frame = addBars(bar_frame, before_bar, after_bar)
                            extra_bar_frame.setVisible(False)
                            
                        extra_bar_frames.append(extra_bar_frame)
                        
                        # Qt changes the string by adding accelerators,
                        # so keep the pristine string here to be
                        # returned to partman later.
                        extra_choice_texts[extraIdCounter] = extra
                        #if extra_firstbutton is None:
                        #    extra_firstbutton = extra_button
                        extraIdCounter += 1
                        
                    self.extra_combo.currentIndexChanged[int].connect(_on_extra_toggle(extra_bar_frames))
                    self.autopartition_extra_choices[choice] = extra_choice_texts
                    
                    #show the first item of the combo box
                    if len(extra_bar_frames) > 0 and extra_bar_frames[0]:
                        extra_bar_frames[0].setVisible(True)
                    
            bar_frame.setVisible(False)
            button.toggled[bool].connect(_on_choice_toggle(frame, bar_frame))

            button.show()
            idCounter += 1
            
        if firstbutton is not None:
            firstbutton.setChecked(True)

        # make sure we're on the autopartitioning page
        self.set_current_page(self.step_index("stepPartAuto"))

    def get_autopartition_choice (self):
        id = self.autopartition_buttongroup.checkedId()
        choice = unicode(self.autopartition_buttongroup_texts[id])

        if choice == self.resize_choice:
            # resize choice should have been hidden otherwise
            assert self.resizeSize is not None
            return choice, '%d B' % self.resizeSize
        elif (choice != self.manual_choice and 
            self.autopartition_extra_choices.has_key(choice)):
                
            extra_id = self.extra_combo.currentIndex()
            disk_texts = self.autopartition_extra_choices[choice]
            return choice, unicode(disk_texts[extra_id])
        else:
            return choice, None

    def installation_medium_mounted (self, message):
        self.ui.part_advanced_warning_message.setText(message)
        self.ui.part_advanced_warning_hbox.show()

    def update_partman (self, disk_cache, partition_cache, cache_order):
        #throwing away the old model if there is one
        self.partition_tree_model = PartitionModel(self, self.ui.partition_list_treeview)

        children = self.ui.partition_bar_frame.children()
        for child in children:
            if isinstance(child, PartitionsBar):
                self.partition_bar_vbox.removeWidget(child)
                child.hide()
                del child
        
        self.partition_bars = []
        partition_bar = None
        indexCount = -1
        for item in cache_order:
            if item in disk_cache:
                #the item is a disk
                self.partition_tree_model.append([item, disk_cache[item]], self)
                indexCount += 1
                partition_bar = PartitionsBar(self.ui.partition_bar_frame)
                self.partition_bars.append(partition_bar)
                self.partition_bar_vbox.addWidget(partition_bar)
            else:
                #the item is a partition, add it to the current bar
                partition = partition_cache[item]
                #add the new partition to our tree display
                self.partition_tree_model.append([item, partition], self)
                indexCount += 1
                
                #get data for bar display
                size = int(partition['parted']['size'])
                fs = partition['parted']['fs']
                path = partition['parted']['path'].replace("/dev/","")
                if fs == "free":
                    path = fs
                partition_bar.addPartition('name', size, indexCount, fs, path)
                
        #for barSignal in self.partition_bars:
        #    self.app.connect(barSignal, SIGNAL("clicked(int)"), self.partitionClicked)
        #    for barSlot in self.partition_bars:
        #        self.app.connect(barSignal, SIGNAL("clicked(int)"), barSlot.raiseFrames)
        
        self.ui.partition_list_treeview.setModel(self.partition_tree_model)
        self.app.disconnect(self.ui.partition_list_treeview.selectionModel(), 
            SIGNAL("selectionChanged(const QItemSelection&, const QItemSelection&)"), 
            self.on_partition_list_treeview_selection_changed)
        self.app.connect(self.ui.partition_list_treeview.selectionModel(), 
            SIGNAL("selectionChanged(const QItemSelection&, const QItemSelection&)"), 
            self.on_partition_list_treeview_selection_changed)

        # make sure we're on the advanced partitioning page
        self.set_current_page(self.step_index("stepPartAdvanced"))

    def partitionClicked(self, indexCounter):
        """ a partition in a partition bar has been clicked, select correct entry in list view """
        index = self.partition_tree_model.index(indexCounter,2)
        flags = self.ui.partition_list_treeview.selectionCommand(index)
        rect = self.ui.partition_list_treeview.visualRect(index)
        self.ui.partition_list_treeview.setSelection(rect, flags)

    def partman_create_dialog(self, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        self.create_dialog = QDialog(self.ui)
        uic.loadUi("%s/partition_create_dialog.ui" % UIDIR, self.create_dialog)
        self.app.connect(self.create_dialog.partition_create_use_combo, SIGNAL("currentIndexChanged(int)"), self.on_partition_create_use_combo_changed)
        self.translate_widget_children(self.create_dialog)

        # TODO cjwatson 2006-11-01: Because partman doesn't use a question
        # group for these, we have to figure out in advance whether each
        # question is going to be asked.

        if partition['parted']['type'] == 'pri/log':
            # Is there already a primary partition?
            for child in self.partition_tree_model.children():
                data = child.itemData
                otherpart = data[1]
                if (otherpart['dev'] == partition['dev'] and
                    'id' in otherpart and
                    otherpart['parted']['type'] == 'primary'):
                    self.create_dialog.partition_create_type_logical.setChecked(True)
                    break
            else:
                self.create_dialog.partition_create_type_primary.setChecked(True)
        else:
            self.create_dialog.partition_create_type_label.hide()
            self.create_dialog.partition_create_type_widget.hide()
        # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
        # partman expects.
        max_size_mb = int(partition['parted']['size']) / 1000000
        self.create_dialog.partition_create_size_spinbutton.setMaximum(max_size_mb)
        self.create_dialog.partition_create_size_spinbutton.setValue(max_size_mb)

        self.create_dialog.partition_create_place_beginning.setChecked(True)

        self.create_use_method_names = {}
        for method, name, description in self.dbfilter.create_use_as():
            self.create_use_method_names[description] = name
            self.create_dialog.partition_create_use_combo.addItem(description)
        if self.create_dialog.partition_create_use_combo.count() == 0:
            self.create_dialog.partition_create_use_combo.setEnabled(False)

        self.create_dialog.partition_create_mount_combo.clear()
        for mp, choice_c, choice in self.dbfilter.default_mountpoint_choices():
            ##FIXME gtk frontend has a nifty way of showing the user readable
            ##'choice' text in the drop down, but only selecting the 'mp' text
            self.create_dialog.partition_create_mount_combo.addItem(mp)
        self.create_dialog.partition_create_mount_combo.clearEditText()

        response = self.create_dialog.exec_()

        if (response == QDialog.Accepted and
            isinstance(self.dbfilter, partman.Partman)):
            if partition['parted']['type'] == 'primary':
                prilog = partman.PARTITION_TYPE_PRIMARY
            elif partition['parted']['type'] == 'logical':
                prilog = partman.PARTITION_TYPE_LOGICAL
            elif partition['parted']['type'] == 'pri/log':
                if self.create_dialog.partition_create_type_primary.isChecked():
                    prilog = partman.PARTITION_TYPE_PRIMARY
                else:
                    prilog = partman.PARTITION_TYPE_LOGICAL

            if self.create_dialog.partition_create_place_beginning.isChecked():
                place = partman.PARTITION_PLACE_BEGINNING
            else:
                place = partman.PARTITION_PLACE_END

            method_description = unicode(self.create_dialog.partition_create_use_combo.currentText())
            method = self.create_use_method_names[method_description]

            mountpoint = unicode(self.create_dialog.partition_create_mount_combo.currentText())

            self.allow_change_step(False)
            self.dbfilter.create_partition(
                devpart,
                str(self.create_dialog.partition_create_size_spinbutton.value()),
                prilog, place, method, mountpoint)

    def on_partition_create_use_combo_changed (self, combobox):
        if not hasattr(self, 'create_use_method_names'):
            return
        known_filesystems = ('ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'xfs',
                             'fat16', 'fat32', 'ntfs')
        text = unicode(self.create_dialog.partition_create_use_combo.currentText())
        if text not in self.create_use_method_names:
            return
        method = self.create_use_method_names[text]
        if method not in known_filesystems:
            self.create_dialog.partition_create_mount_combo.clearEditText()
            self.create_dialog.partition_create_mount_combo.setEnabled(False)
        else:
            self.create_dialog.partition_create_mount_combo.setEnabled(True)
            if isinstance(self.dbfilter, partman.Partman):
                self.create_dialog.partition_create_mount_combo.clear()
                for mp, choice_c, choice in \
                    self.dbfilter.default_mountpoint_choices(method):
                    self.create_dialog.partition_create_mount_combo.addItem(mp)

    def partman_edit_dialog(self, devpart, partition):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        self.edit_dialog = QDialog(self.ui)
        uic.loadUi("%s/partition_edit_dialog.ui" % UIDIR, self.edit_dialog)
        self.app.connect(self.edit_dialog.partition_edit_use_combo, SIGNAL("currentIndexChanged(int)"), self.on_partition_edit_use_combo_changed)
        self.translate_widget_children(self.edit_dialog)

        current_size = None
        if ('can_resize' not in partition or not partition['can_resize'] or
            'resize_min_size' not in partition or
            'resize_max_size' not in partition):
            self.edit_dialog.partition_edit_size_label.hide()
            self.edit_dialog.partition_edit_size_spinbutton.hide()
        else:
            # Yes, I know, 1000000 bytes is annoying. Sorry. This is what
            # partman expects.
            min_size_mb = int(partition['resize_min_size']) / 1000000
            cur_size_mb = int(partition['parted']['size']) / 1000000
            max_size_mb = int(partition['resize_max_size']) / 1000000
            # Bad things happen if the current size is out of bounds.
            min_size_mb = min(min_size_mb, cur_size_mb)
            max_size_mb = max(cur_size_mb, max_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setMinimum(min_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setMaximum(max_size_mb)
            self.edit_dialog.partition_edit_size_spinbutton.setSingleStep(1)
            self.edit_dialog.partition_edit_size_spinbutton.setValue(cur_size_mb)

            current_size = str(self.edit_dialog.partition_edit_size_spinbutton.value())

        self.edit_use_method_names = {}
        method_descriptions = {}
        self.edit_dialog.partition_edit_use_combo.clear()
        for script, arg, option in partition['method_choices']:
            self.edit_use_method_names[option] = arg
            method_descriptions[arg] = option
            self.edit_dialog.partition_edit_use_combo.addItem(option)
        current_method = self.dbfilter.get_current_method(partition)
        if current_method and current_method in method_descriptions:
            current_method_description = method_descriptions[current_method]
            index = self.edit_dialog.partition_edit_use_combo.findText(current_method_description)
            self.edit_dialog.partition_edit_use_combo.setCurrentIndex(index)

        if 'id' not in partition:
            self.edit_dialog.partition_edit_format_label.hide()
            self.edit_dialog.partition_edit_format_checkbutton.hide()
            current_format = False
        elif 'method' in partition:
            self.edit_dialog.partition_edit_format_label.show()
            self.edit_dialog.partition_edit_format_checkbutton.show()
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(
                'can_activate_format' in partition)
            current_format = (partition['method'] == 'format')
        else:
            self.edit_dialog.partition_edit_format_label.show()
            self.edit_dialog.partition_edit_format_checkbutton.show()
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(False)
            current_format = False
        self.edit_dialog.partition_edit_format_checkbutton.setChecked(
            current_format)

        self.edit_dialog.partition_edit_mount_combo.clear()
        if 'mountpoint_choices' in partition:
            for mp, choice_c, choice in partition['mountpoint_choices']:
                ##FIXME gtk frontend has a nifty way of showing the user readable
                ##'choice' text in the drop down, but only selecting the 'mp' text
                self.edit_dialog.partition_edit_mount_combo.addItem(mp)
        current_mountpoint = self.dbfilter.get_current_mountpoint(partition)
        if current_mountpoint is not None:
            index = self.edit_dialog.partition_edit_mount_combo.findText(current_method)
            if index != -1:
                self.edit_dialog.partition_edit_mount_combo.setCurrentIndex(index)
            else:
                self.edit_dialog.partition_edit_mount_combo.addItem(current_mountpoint)
                self.edit_dialog.partition_edit_mount_combo.setCurrentIndex(self.edit_dialog.partition_edit_mount_combo.count() - 1)

        response = self.edit_dialog.exec_()

        if (response == QDialog.Accepted and
            isinstance(self.dbfilter, partman.Partman)):
            size = None
            if current_size is not None:
                size = str(self.edit_dialog.partition_edit_size_spinbutton.value())

            method_description = unicode(self.edit_dialog.partition_edit_use_combo.currentText())
            method = self.edit_use_method_names[method_description]

            format = self.edit_dialog.partition_edit_format_checkbutton.isChecked()

            mountpoint = unicode(self.edit_dialog.partition_edit_mount_combo.currentText())

            if (current_size is not None and size is not None and
                current_size == size):
                size = None
            if method == current_method:
                method = None
            if format == current_format:
                format = None
            if mountpoint == current_mountpoint:
                mountpoint = None

            if (size is not None or method is not None or format is not None or
                mountpoint is not None):
                self.allow_change_step(False)
                edits = {'size': size, 'method': method,
                         'mountpoint': mountpoint}
                if format is not None:
                    edits['format'] = 'dummy'
                self.dbfilter.edit_partition(devpart, **edits)

    def on_partition_edit_use_combo_changed(self, combobox):
        if not hasattr(self, 'edit_use_method_names'):
            return
        # If the selected method isn't a filesystem, then selecting a mount
        # point makes no sense. TODO cjwatson 2007-01-31: Unfortunately we
        # have to hardcode the list of known filesystems here.
        known_filesystems = ('ext4', 'ext3', 'ext2', 'reiserfs', 'jfs', 'xfs',
                             'fat16', 'fat32', 'ntfs')
        text = unicode(self.edit_dialog.partition_edit_use_combo.currentText())
        if text not in self.edit_use_method_names:
            return
        method = self.edit_use_method_names[text]
        if method not in known_filesystems:
            self.edit_dialog.partition_edit_mount_combo.clearEditText()
            self.edit_dialog.partition_edit_mount_combo.setEnabled(False)
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(False)
        else:
            self.edit_dialog.partition_edit_mount_combo.setEnabled(True)
            self.edit_dialog.partition_edit_format_checkbutton.setEnabled(True)
            if isinstance(self.dbfilter, partman.Partman):
                self.edit_dialog.partition_edit_mount_combo.clear()
                for mp, choice_c, choice in \
                    self.dbfilter.default_mountpoint_choices(method):
                    self.edit_dialog.partition_edit_mount_combo.addItem(mp)

    def on_partition_list_treeview_selection_changed(self, selected, deselected):
        self.ui.partition_button_new_label.setEnabled(False)
        self.ui.partition_button_new.setEnabled(False)
        self.ui.partition_button_edit.setEnabled(False)
        self.ui.partition_button_delete.setEnabled(False)
        if not isinstance(self.dbfilter, partman.Partman):
            return

        indexes = self.ui.partition_list_treeview.selectedIndexes()
        if indexes:
            index = indexes[0]
            for bar in self.partition_bars:
                pass
                #TODO show the appropriate partition bar
                ##bar.selected(index)  ##FIXME find out row from index and call bar.selected on it
                #bar.raiseFrames()
            item = index.internalPointer()
            devpart = item.itemData[0]
            partition = item.itemData[1]
        else:
            devpart = None
            partition = None

        for action in self.dbfilter.get_actions(devpart, partition):
            if action == 'new_label':
                self.ui.partition_button_new_label.setEnabled(True)
            elif action == 'new':
                self.ui.partition_button_new.setEnabled(True)
            elif action == 'edit':
                self.ui.partition_button_edit.setEnabled(True)
            elif action == 'delete':
                self.ui.partition_button_delete.setEnabled(True)
        self.ui.partition_button_undo.setEnabled(True)

    def on_partition_list_treeview_activated(self, index):
        if not self.allowed_change_step:
            return
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]

        if 'id' not in partition:
            # Are there already partitions on this disk? If so, don't allow
            # activating the row to offer to create a new partition table,
            # to avoid mishaps.
            for child in self.partition_tree_model.children():
                data = child.itemData
                otherpart = data[1]
                if otherpart['dev'] == partition['dev'] and 'id' in otherpart:
                    break
            else:
                if not isinstance(self.dbfilter, partman.Partman):
                    return
                self.allow_change_step(False)
                self.dbfilter.create_label(devpart)
        elif partition['parted']['fs'] == 'free':
            if 'can_new' in partition and partition['can_new']:
                self.partman_create_dialog(devpart, partition)
        else:
            self.partman_edit_dialog(devpart, partition)

    def on_partition_list_new_label_activate(self, ticked):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]

        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.create_label(devpart)

    def on_partition_list_new_activate(self, ticked):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]
        self.partman_create_dialog(devpart, partition)

    def on_partition_list_edit_activate(self, ticked):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]
        partition = item.itemData[1]
        self.partman_edit_dialog(devpart, partition)

    def on_partition_list_delete_activate(self, ticked):
        selected = self.ui.partition_list_treeview.selectedIndexes()
        if not selected:
            return
        index = selected[0]
        item = index.internalPointer()
        devpart = item.itemData[0]

        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.delete_partition(devpart)

    def on_partition_list_undo_activate(self, ticked):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return
        self.allow_change_step(False)
        self.dbfilter.undo()

    def partman_popup (self, position):
        if not self.allowed_change_step:
            return
        if not isinstance(self.dbfilter, partman.Partman):
            return

        selected = self.ui.partition_list_treeview.selectedIndexes()
        if selected:
            index = selected[0]
            item = index.internalPointer()
            devpart = item.itemData[0]
            partition = item.itemData[1]
        else:
            devpart = None
            partition = None

        #partition_list_menu = gtk.Menu()
        partition_list_menu = QMenu(self.ui)
        for action in self.dbfilter.get_actions(devpart, partition):
            if action == 'new_label':
                new_label_item = partition_list_menu.addAction(
                    self.get_string('partition_button_new_label'))
                self.app.connect(new_label_item, SIGNAL("triggered(bool)"),
                                 self.on_partition_list_new_label_activate)
            elif action == 'new':
                new_item = partition_list_menu.addAction(
                    self.get_string('partition_button_new'))
                self.app.connect(new_item, SIGNAL("triggered(bool)"),
                                 self.on_partition_list_new_activate)
            elif action == 'edit':
                edit_item = partition_list_menu.addAction(
                    self.get_string('partition_button_edit'))
                self.app.connect(edit_item, SIGNAL("triggered(bool)"),
                                 self.on_partition_list_edit_activate)
            elif action == 'delete':
                delete_item = partition_list_menu.addAction(
                    self.get_string('partition_button_delete'))
                self.app.connect(delete_item, SIGNAL("triggered(bool)"),
                                 self.on_partition_list_delete_activate)
        if partition_list_menu.children():
            partition_list_menu.addSeparator()
        undo_item = partition_list_menu.addAction(
            self.get_string('partman/text/undo_everything'))
        self.app.connect(undo_item, SIGNAL("triggered(bool)"),
                         self.on_partition_list_undo_activate)

        partition_list_menu.exec_(QCursor.pos())

    def set_fullname(self, value):
        self.ui.fullname.setText(unicode(value, "UTF-8"))

    def get_fullname(self):
        return unicode(self.ui.fullname.text())

    def set_username(self, value):
        self.ui.username.setText(unicode(value, "UTF-8"))

    def get_username(self):
        return unicode(self.ui.username.text())

    def get_password(self):
        return unicode(self.ui.password.text())

    def get_verified_password(self):
        return unicode(self.ui.verified_password.text())

    def select_password(self):
        self.ui.password.selectAll()

    def set_auto_login(self, value):
        return self.ui.login_auto.setChecked(value)

    def get_auto_login(self):
        return self.ui.login_auto.isChecked()
    
    def set_encrypt_home(self, value):
        if value:
            syslog.syslog(syslog.LOG_WARNING,
                          "KDE frontend does not support home encryption yet")

    def get_encrypt_home(self):
        return False

    def username_error(self, msg):
        self.ui.username_error_reason.setText(msg)
        self.ui.username_error_image.show()
        self.ui.username_error_reason.show()

    def password_error(self, msg):
        self.ui.password_error_reason.setText(msg)
        self.ui.password_error_image.show()
        self.ui.password_error_reason.show()

    def get_hostname (self):
        return unicode(self.ui.hostname.text())

    def set_hostname (self, value):
        self.ui.hostname.setText(value)

    def set_summary_text (self, text):
        i = text.find("\n")
        while i != -1:
            text = text[:i] + "<br>" + text[i+1:]
            i = text.find("\n")
        self.ui.ready_text.setText(text)

    ## called to set all possible install locations for grub
    def set_grub_combo(self, options):
        ''' options gives us a possible list of install locations for the boot loader '''
        self.advanceddialog.grub_device_entry.clear()
        ''' options is from summary.py grub_options() '''
        for opt in options:
           self.advanceddialog.grub_device_entry.addItem(opt[0]);

    def on_advanced_button_clicked (self):
        self.translate_widget_children(self.advanceddialog)
        self.app.connect(self.advanceddialog.grub_enable, SIGNAL("stateChanged(int)"), self.toggle_grub)
        self.app.connect(self.advanceddialog.proxy_host_entry, SIGNAL("textChanged(const QString &)"), self.enable_proxy_spinbutton)
        display = False
        grub_en = self.get_grub()
        summary_device = self.get_summary_device()
        if grub_en is not None:
            self.advanceddialog.grub_enable.show()
            self.advanceddialog.grub_enable.setChecked(grub_en)
        else:
            self.advanceddialog.grub_enable.hide()
            summary_device = None
        if summary_device is not None:
            display = True
            self.advanceddialog.bootloader_group_label.show()
            self.advanceddialog.grub_device_label.show()
            self.advanceddialog.grub_device_entry.show()
            
            # if the combo box does not yet have the target install device, add it
            # select current device
            target = summary.find_grub_target()
            index = self.advanceddialog.grub_device_entry.findText(target)
            if (index == -1):
                self.advanceddialog.grub_device_entry.addItem(target)
                index = self.advanceddialog.grub_device_entry.count() - 1
            
            # select the target device
            self.advanceddialog.grub_device_entry.setCurrentIndex(index)
            
            self.advanceddialog.grub_device_entry.setEnabled(grub_en)
            self.advanceddialog.grub_device_label.setEnabled(grub_en)
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

        display = True
        if self.http_proxy_host:
            self.advanceddialog.proxy_port_spinbutton.setEnabled(True)
            self.advanceddialog.proxy_host_entry.setText(unicode(self.http_proxy_host))
        else:
            self.advanceddialog.proxy_port_spinbutton.setEnabled(False)
        self.advanceddialog.proxy_port_spinbutton.setValue(self.http_proxy_port)

        if not display:
            return

        response = self.advanceddialog.exec_()
        if response == QDialog.Accepted:
            if summary_device is not None:
                self.set_summary_device(
                    unicode(self.advanceddialog.grub_device_entry.currentText()))
            self.set_popcon(self.advanceddialog.popcon_checkbutton.isChecked())
            self.set_grub(self.advanceddialog.grub_enable.isChecked())
            self.set_proxy_host(unicode(self.advanceddialog.proxy_host_entry.text()))
            self.set_proxy_port(self.advanceddialog.proxy_port_spinbutton.value())

    def enable_proxy_spinbutton(self):
        self.advanceddialog.proxy_port_spinbutton.setEnabled(self.advanceddialog.proxy_host_entry.text() != '')

    def toggle_grub(self):
        grub_en = self.advanceddialog.grub_enable.isChecked()
        self.advanceddialog.grub_device_entry.setEnabled(grub_en)
        self.advanceddialog.grub_device_label.setEnabled(grub_en)

    def return_to_partitioning (self):
        """If the install progress bar is up but still at the partitioning
        stage, then errors can safely return us to partitioning.
        """
        if self.installing and not self.installing_no_return:
            # Go back to the partitioner and try again.
            #self.live_installer.show()
            self.pagesindex = self.pages.index(partman.Partman)
            self.dbfilter = partman.Partman(self)
            self.set_current_page(self.previous_partitioning_page)
            self.ui.next.setText(self.get_string("next").replace('_', '&', 1))
            self.ui.next.setIcon(self.forwardIcon)
            self.translate_widget(self.ui.next, self.locale)
            self.backup = True
            self.installing = False

    def error_dialog (self, title, msg, fatal=True):
        self.run_automation_error_cmd()
        # TODO cjwatson 2009-04-16: We need to call allow_change_step here
        # to get a normal cursor, but that also enables the Back/Forward
        # buttons. Cursor handling should be controllable independently.
        saved_allowed_change_step = self.allowed_change_step
        self.allow_change_step(True)
        # TODO: cancel button as well if capb backup
        QMessageBox.warning(self.ui, title, msg, QMessageBox.Ok)
        self.allow_change_step(saved_allowed_change_step)
        if fatal:
            self.return_to_partitioning()

    def question_dialog (self, title, msg, options, use_templates=True):
        self.run_automation_error_cmd()
        # I doubt we'll ever need more than three buttons.
        assert len(options) <= 3, options

        # TODO cjwatson 2009-04-16: We need to call allow_change_step here
        # to get a normal cursor, but that also enables the Back/Forward
        # buttons. Cursor handling should be controllable independently.
        saved_allowed_change_step = self.allowed_change_step
        self.allow_change_step(True)
        buttons = {}
        messageBox = QMessageBox(QMessageBox.Question, title, msg, QMessageBox.NoButton, self.ui)
        for option in options:
            if use_templates:
                text = self.get_string(option)
            else:
                text = option
            if text is None:
                text = option
            # Convention for options is to have the affirmative action last; KDE
            # convention is to have it first.
            if option == options[-1]:
                button = messageBox.addButton(text, QMessageBox.AcceptRole)
            else:
                button = messageBox.addButton(text, QMessageBox.RejectRole)
            buttons[button] = option

        response = messageBox.exec_()
        self.allow_change_step(saved_allowed_change_step)

        if response < 0:
            return None
        else:
            return buttons[messageBox.clickedButton()]

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
      return self.ui.widgetStack.indexOf(self.ui.widgetStack.currentWidget())

    def on_fullname_changed(self):
        self.info_loop(self.ui.fullname)

    def on_username_changed(self):
        self.info_loop(self.ui.username)
        self.username_edited = (self.ui.username.text() != '')

    def on_password_changed(self):
        self.info_loop(self.ui.password)

    def on_verified_password_changed(self):
        self.info_loop(self.ui.verified_password)

    def on_hostname_changed(self):
        self.info_loop(self.ui.hostname)
        self.hostname_edited = (self.ui.hostname.text() != '')

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
		
