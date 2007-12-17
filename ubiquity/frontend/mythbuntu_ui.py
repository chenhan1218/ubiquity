# -*- coding: utf-8 -*-
#
# «mythbuntu-ui» - Mythbuntu user interface
#
# Copyright (C) 2005 Junta de Andalucía
# Copyright (C) 2005, 2006, 2007 Canonical Ltd.
# Copyright (C) 2007, Mario Limonciello, for Mythbuntu
# Copyright (C) 2007, Jared Greenwald, for Mythbuntu
#
# Authors:
#
# - Original gtk-ui.py that this is based upon:
#   - Javier Carranza <javier.carranza#interactors._coop>
#   - Juan Jesús Ojeda Croissier <juanje#interactors._coop>
#   - Antonio Olmo Titos <aolmo#emergya._info>
#   - Gumer Coronel Pérez <gcoronel#emergya._info>
#   - Colin Watson <cjwatson@ubuntu.com>
#   - Evan Dandrea <evand@ubuntu.com>
#   - Mario Limonciello <superm1@ubuntu.com>
#
# - This Document:
#   - Mario Limonciello <superm1@mythbuntu.org>
#   - Jared Greenwald <greenwaldjared@gmail.com>
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

import os
import re
import sys
import string
import subprocess
import syslog
import signal

import gtk
import MySQLdb

from ubiquity.misc import *
from ubiquity.components import console_setup, language, timezone, usersetup, \
                                partman, partman_commit, \
                                mythbuntu, mythbuntu_install, mythbuntu_summary
import ubiquity.frontend.gtk_ui
import ubiquity.components.mythbuntu_install
import ubiquity.components.mythbuntu_summary
ubiquity.frontend.gtk_ui.install = ubiquity.components.mythbuntu_install
ubiquity.frontend.gtk_ui.summary = ubiquity.components.mythbuntu_summary


BREADCRUMB_STEPS = {
    "stepLanguage": 1,
    "stepLocation": 2,
    "stepKeyboardConf": 3,
    "stepPartAuto": 4,
    "stepPartAdvanced": 4,
    "stepUserInfo": 5,
    "mythbuntu_stepInstallType": 6,
    "mythbuntu_stepCustomInstallType": 7,
    "mythbuntu_stepPlugins": 8,
    "mythbuntu_stepThemes": 9,
    "mythbuntu_stepServices": 10,
    "mythbuntu_stepPasswords": 11,
    "mythbuntu_stepLirc": 12,
    "mythbuntu_stepDrivers": 13,
    "stepReady": 14,
    "mythbuntu_stepBackendSetup": 15
}
BREADCRUMB_MAX_STEP = 15

# Define what pages of the UI we want to load.  Note that most of these pages
# are required for the install to complete successfully.
SUBPAGES = [
    "stepWelcome",
    "stepLanguage",
    "stepLocation",
    "stepKeyboardConf",
    "stepPartAuto",
    "stepPartAdvanced",
    "stepUserInfo",
    "mythbuntu_stepInstallType",
    "mythbuntu_stepCustomInstallType",
    "mythbuntu_stepPlugins",
    "mythbuntu_stepThemes",
    "mythbuntu_stepServices",
    "mythbuntu_stepPasswords",
    "mythbuntu_stepLirc",
    "mythbuntu_stepDrivers",
    "stepReady",
    "mythbuntu_stepBackendSetup"
]

ubiquity.frontend.gtk_ui.BREADCRUMB_STEPS = BREADCRUMB_STEPS
ubiquity.frontend.gtk_ui.BREADCRUMB_MAX_STEP = BREADCRUMB_MAX_STEP
ubiquity.frontend.gtk_ui.SUBPAGES = SUBPAGES

class Wizard(ubiquity.frontend.gtk_ui.Wizard):

#Overriden Methods
    def __init__(self, distro):
        del os.environ['UBIQUITY_MIGRATION_ASSISTANT']
        ubiquity.frontend.gtk_ui.Wizard.__init__(self,distro)
        self.populate_lirc()
        self.populate_video()
        self.backup=False

    def run(self):
        """run the interface."""
        def skip_pages(old_backup,old_name,new_name):
            """Skips a mythbuntu page if we should"""
            advanced=self.get_advanced()
            #advanced install conditionally skips a few pages
            if advanced:
                type = self.get_installtype()
                if (type == "Master Backend" or type == "Slave Backend") and \
                   (new_name == 'MythbuntuThemes' or new_name == 'MythbuntuRemote'):
                    if not old_backup:
                        self.dbfilter.ok_handler()
                    else:
                        self.dbfilter.cancel_handler()
                        self.backup=True
            #standard install should fly right through forward
            else:
                if new_name == 'MythbuntuInstallType' or \
                   new_name == 'MythbuntuPlugins' or \
                   new_name == 'MythbuntuThemes' or \
                   new_name == 'MythbuntuServices' or \
                   new_name == 'MythbuntuPasswords':
                    if not old_backup:
                        self.dbfilter.ok_handler()
                    else:
                        self.dbfilter.cancel_handler()
                        self.backup=True

        if os.getuid() != 0:
            title = ('This installer must be run with administrative '
                     'privileges, and cannot continue without them.')
            dialog = gtk.MessageDialog(self.live_installer, gtk.DIALOG_MODAL,
                                       gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
                                       title)
            dialog.run()
            sys.exit(1)

        self.disable_volume_manager()

        # show interface
        got_intro = self.show_intro()
        self.allow_change_step(True)

        # Declare SignalHandler
        self.glade.signal_autoconnect(self)

        # Some signals need to be connected by hand so that we have the
        # handler ids.
        self.username_changed_id = self.username.connect(
            'changed', self.on_username_changed)
        self.hostname_changed_id = self.hostname.connect(
            'changed', self.on_hostname_changed)

        # Start the interface
        if got_intro:
            global BREADCRUMB_STEPS, BREADCRUMB_MAX_STEP
            for step in BREADCRUMB_STEPS:
                BREADCRUMB_STEPS[step] += 1
            BREADCRUMB_STEPS["stepWelcome"] = 1
            BREADCRUMB_MAX_STEP += 1
            ubiquity.frontend.gtk_ui.BREADCRUMB_STEPS = BREADCRUMB_STEPS
            ubiquity.frontend.gtk_ui.BREADCRUMB_MAX_STEP = BREADCRUMB_MAX_STEP
            first_step = self.stepWelcome
        else:
            first_step = self.stepLanguage
        self.set_current_page(self.steps.page_num(first_step))
        if got_intro:
            # intro_label was the only focusable widget, but got can-focus
            # removed, so we end up with no input focus and thus pressing
            # Enter doesn't activate the default widget. Work around this.
            self.next.grab_focus()

        self.pages = [language.Language, timezone.Timezone,
            console_setup.ConsoleSetup, partman.Partman,
            usersetup.UserSetup, mythbuntu.MythbuntuAdvancedType,
            mythbuntu.MythbuntuInstallType, mythbuntu.MythbuntuPlugins,
            mythbuntu.MythbuntuThemes, mythbuntu.MythbuntuServices,
            mythbuntu.MythbuntuPasswords, mythbuntu.MythbuntuRemote,
            mythbuntu.MythbuntuDrivers, mythbuntu_summary.Summary]
        self.pagesindex = 0
        pageslen = len(self.pages)

        if got_intro:
            gtk.main()

        while(self.pagesindex < pageslen):
            if not self.installing:
                # Make sure any started progress bars are stopped.
                while self.progress_position.depth() != 0:
                    self.debconf_progress_stop()

            old_backup = self.backup
            self.backup = False
            old_dbfilter = self.dbfilter
            self.dbfilter = self.pages[self.pagesindex](self)

            # Non-debconf steps are no longer possible as the interface is now
            # driven by whether there is a question to ask.
            if self.dbfilter is not None and self.dbfilter != old_dbfilter:
                self.allow_change_step(False)
                self.dbfilter.start(auto_process=True)
                skip_pages(old_backup,old_dbfilter.__class__.__name__,self.dbfilter.__class__.__name__)
            gtk.main()

            if self.backup or self.dbfilter_handle_status():
                if self.installing:
                    self.progress_loop()
                elif self.current_page is not None and not self.backup:
                    self.process_step()
                    self.pagesindex = self.pagesindex + 1
                if self.backup:
                    if self.pagesindex > 0:
                        self.pagesindex = self.pagesindex - 1

            self.back.show()

            # TODO: Move this to after we're done processing GTK events, or is
            # that not worth the CPU time?
            if self.current_page == None:
                break

            while gtk.events_pending():
                gtk.main_iteration()

            # needed to be here for --automatic as there might not be any
            # current page in the event all of the questions have been
            # preseeded.
            if self.pagesindex == pageslen:
                # Ready to install
                self.live_installer.hide()
                self.current_page = None
                self.installing = True
                self.progress_loop()

        #After (and if) install is done, decide what to do
        if self.pagesindex == pageslen:
            self.run_success_cmd()
            if self.get_installtype() == "Frontend":
                if not self.get_reboot_seen():
                    self.finished_dialog.run()
                elif self.get_reboot():
                    self.reboot()
            else:
                self.live_installer.show()
                self.installing = False
                self.steps.next_page()
                self.back.hide()
                self.cancel.hide()
                self.next.set_label("Finish")
                gtk.main()
                self.live_installer.hide()
                self.finished_dialog.run()
        return self.returncode

    def process_step(self):
        """Process and validate the results of this step."""

        # setting actual step
        step_num = self.steps.get_current_page()
        step = self.step_name(step_num)

        #Figure out if this is a mythbuntu specific step
        if step == "mythbuntu_stepBackendSetup":
            syslog.syslog('Step_before = %s' % step)
            self.live_installer.hide()
            self.current_page = None
            self.finished_dialog.run()
        else:
            ubiquity.frontend.gtk_ui.Wizard.process_step(self)

    def progress_loop(self):
        """prepare, copy and config the system in the core install process."""

        syslog.syslog('progress_loop()')

        self.current_page = None

        self.debconf_progress_start(
            0, 100, self.get_string('ubiquity/install/title'))
        self.debconf_progress_region(0, 15)

        dbfilter = partman_commit.PartmanCommit(self)
        if dbfilter.run_command(auto_process=True) != 0:
            while self.progress_position.depth() != 0:
                self.debconf_progress_stop()
            self.debconf_progress_window.hide()
            self.return_to_partitioning()
            return

        # No return to partitioning from now on
        self.installing_no_return = True

        self.debconf_progress_region(15, 100)

        dbfilter = mythbuntu_install.Install(self)
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
        self.debconf_progress_window.hide()

        self.installing = False

    def set_page(self, n):
        gtk_ui_pages  = ['Language', 'ConsoleSetup', 'Timezone', 'Partman', 'UserSetup', 'Summary', 'MigrationAssistant']
        found = False
        for item in gtk_ui_pages:
            if n == item:
                found = True
                ubiquity.frontend.gtk_ui.Wizard.set_page(self,n)
                break
        if not found:
            self.live_installer.show()
            if n == 'MythbuntuAdvancedType':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepInstallType))
            elif n == 'MythbuntuRemote':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepLirc))
            elif n == 'MythbuntuDrivers':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepDrivers))
            if n == 'MythbuntuInstallType':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepCustomInstallType))
            elif n == 'MythbuntuPlugins':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepPlugins))
            elif n == 'MythbuntuThemes':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepThemes))
            elif n == 'MythbuntuPasswords':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepPasswords))
            elif n == 'MythbuntuServices':
                self.set_current_page(self.steps.page_num(self.mythbuntu_stepServices))

#Added Methods
    def populate_lirc(self):
        """Fills the lirc pages with the appropriate data"""
        #Note, this requires lirc >= 0.8.2-0ubuntu3
        hwdb = open('/usr/share/lirc/lirc.hwdb').readlines()
        hwdb.sort()
        #Filter out uncessary lines
        filter = "^\#|^\["
        #Filter out the /dev/input/eventX remote
        filter += "|http"
        pattern = re.compile(filter)
        for line in hwdb:
            if pattern.search(line) is None:
                list = string.split(line, ";")
                if len(list) > 1:
                    #Make sure we have a config file before including
                    if list[4] != "":
                        self.lirc_remote.append_text(list[0].translate(string.maketrans('',''),','))
                        self.lirc_driver.append_text(list[1])
                        self.lirc_modules.append_text(list[2])
                        self.lirc_rc.append_text(list[4])
        self.lirc_remote.append_text("Other Remote")

    def populate_video(self):
        """Finds the currently active video driver"""
        vid = open('/etc/X11/xorg.conf')
        start_filter = re.compile("Section \"Device\"")
        driver_filter = re.compile("Driver")
        section=False
        for line in vid:
            if not section and start_filter.search(line):
                section=True
            elif section and driver_filter.search(line):
                list = string.split(line, '"')
                if len(list) > 1:
                    self.video_driver.append_text("Open Source Driver: " + list[1])
                    self.video_driver.set_active(5)
                    self.tvoutstandard.set_active(0)
                    self.tvouttype.set_active(0)
                    break
        vid.close()

    def allow_go_backward(self, allowed):
        self.back.set_sensitive(allowed and self.allowed_change_step)
        self.allowed_go_backward = allowed

    def mythbuntu_password(self,widget):
        """Checks that certain passwords meet requirements"""
        #For the services page, the only password we have is the VNC
        if (widget is not None and widget.get_name() == 'vnc_password'):
            password= widget.get_text().split(' ')[0]
            if len(password) >= 6:
                self.allow_go_forward(True)
                self.allow_go_backward(True)
                self.vnc_error_image.hide()
            else:
                self.allow_go_forward(False)
                self.allow_go_backward(False)
                self.vnc_error_image.show()
        elif (widget is not None and widget.get_name() == 'mythweb_username'):
            username = widget.get_text().split(' ')[0]
            if len(username) >= 1:
                self.mythweb_user_error_image.hide()
            else:
                self.mythweb_user_error_image.show()
        elif (widget is not None and widget.get_name() == 'mythweb_password'):
            password = widget.get_text().split(' ')[0]
            if len(password) >= 1:
                self.mythweb_pass_error_image.hide()
            else:
                self.mythweb_pass_error_image.show()

        elif (widget is not None and widget.get_name() == 'mysql_root_password'):
            password = widget.get_text().split(' ')[0]
            if len(password) >= 1:
                self.mysql_root_error_image.hide()
            else:
                self.mysql_root_error_image.show()

        #The password check page is much more complex. Pieces have to be
        #done in a sequential order
        if (self.usemysqlrootpassword.get_active() or self.usemythwebpassword.get_active()):
            mysql_root_flag = self.mysql_root_error_image.flags() & gtk.VISIBLE
            mythweb_user_flag = self.mythweb_user_error_image.flags() & gtk.VISIBLE
            mythweb_pass_flag = self.mythweb_pass_error_image.flags() & gtk.VISIBLE
            result = not (mythweb_user_flag | mythweb_pass_flag | mysql_root_flag)
            self.allow_go_forward(result)
            self.allow_go_backward(result)

    def do_mythtv_setup(self,widget):
        """Spawn MythTV-Setup binary."""
        execute("/usr/share/ubiquity/mythbuntu-setup")

    def do_connection_test(self,widget):
        """Tests to make sure that the backend is accessible"""
        host = self.mysql_server.get_text()
        database = self.mysql_database.get_text()
        user = self.mysql_user.get_text()
        password = self.mysql_password.get_text()
        try:
            db = MySQLdb.connect(host=host, user=user, passwd=password,db=database)
            cursor = db.cursor()
            cursor.execute("SELECT NULL")
            result = cursor.fetchone()
            cursor.close()
            db.close()
            result = "Successful"
        except:
            result = "Failure"
        self.connection_results_label.show()
        self.connection_results.set_text(result)

    def toggle_installtype (self,widget):
        """Called whenever standard or full are toggled"""
        if self.standardinstall.get_active() :
            #Make sure that we have everything turned on in case they came back to this page
            #and changed their mind
            #Note: This will recursively handle changing the values on the pages
            self.master_be_fe.set_active(True)
            self.enablessh.set_active(True)
            self.enablevnc.set_active(False)
            self.enablenfs.set_active(False)
            self.enablesamba.set_active(True)
            self.enablemysql.set_active(False)

        else:
            self.master_backend_expander.hide()
            self.mythweb_expander.show()
            self.mysql_server_expander.show()

    def toggle_customtype (self,widget):
        """Called whenever a custom type is toggled"""

        def set_fe_drivers(self,enable):
            """Toggle Visible Frontend Applicable Drivers"""
            if enable:
                self.frontend_driver_list.show()
            else:
                self.frontend_driver_list.hide()

        def set_be_drivers(self,enable):
            """Toggles Visible Backend Applicable Drivers"""
            if enable:
                self.backend_driver_list.show()
                self.tuner0.set_active(0)
                self.tuner1.set_active(0)
                self.tuner2.set_active(0)
                self.tuner3.set_active(0)
                self.tuner4.set_active(0)
            else:
                self.backend_driver_list.hide()

        def set_all_services(self,enable):
            """Toggles visibility on all possible services"""
            if enable:
                self.ssh_option_hbox.show()
                self.samba_option_hbox.show()
                self.nfs_option_hbox.show()
                self.mysql_option_hbox.show()
            else:
                self.ssh_option_hbox.hide()
                self.samba_option_hbox.hide()
                self.nfs_option_hbox.hide()
                self.mysql_option_hbox.hide()

        def set_all_passwords(self,enable):
            """Toggles visibility on all password selection boxes"""
            if enable:
                self.master_backend_expander.show()
                self.mythweb_expander.show()
                self.mysql_server_expander.show()
            else:
                self.master_backend_expander.hide()
                self.mythweb_expander.hide()
                self.mysql_server_expander.hide()

        def set_all_themes(self,enable):
            """Enables all themes for defaults"""
            self.communitythemes.set_active(enable)
            self.officialthemes.set_active(enable)

        def set_all_fe_plugins(self,enable):
            """ Enables all frontend plugins for defaults"""
            self.mytharchive.set_active(enable)
            self.mythbrowser.set_active(enable)
            self.mythcontrols.set_active(enable)
            self.mythdvd.set_active(enable)
            self.mythflix.set_active(enable)
            self.mythgallery.set_active(enable)
            self.mythgame.set_active(enable)
            self.mythmusic.set_active(enable)
            self.mythnews.set_active(enable)
            self.mythphone.set_active(enable)
            self.mythstream.set_active(enable)
            self.mythvideo.set_active(enable)
            self.mythweather.set_active(enable)

        def set_all_be_plugins(self,enable):
            """ Enables all backend plugins for defaults"""
            self.mythweb.set_active(enable)

        if self.master_be_fe.get_active():
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,True)
            set_all_passwords(self,True)
            set_all_services(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Frontend / Backend Plugins")
            self.master_backend_expander.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
        elif self.slave_be_fe.get_active():
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Frontend / Backend Plugins")
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,True)
        elif self.master_be.get_active():
            set_all_themes(self,False)
            set_all_fe_plugins(self,False)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.hide()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Backend Plugins")
            self.master_backend_expander.hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
        elif self.slave_be.get_active():
            set_all_themes(self,False)
            set_all_fe_plugins(self,False)
            set_all_be_plugins(self,True)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(True)
            self.frontend_plugin_list.hide()
            self.backend_plugin_list.show()
            self.febe_heading_label.set_label("Choose Backend Plugins")
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            set_fe_drivers(self,False)
            set_be_drivers(self,True)
        else:
            set_all_themes(self,True)
            set_all_fe_plugins(self,True)
            set_all_be_plugins(self,False)
            set_all_services(self,True)
            set_all_passwords(self,True)
            self.enablessh.set_active(True)
            self.enablesamba.set_active(False)
            self.enablenfs.set_active(False)
            self.enablemysql.set_active(False)
            self.frontend_plugin_list.show()
            self.backend_plugin_list.hide()
            self.febe_heading_label.set_label("Choose Frontend Plugins")
            self.mythweb_expander.hide()
            self.mysql_server_expander.hide()
            self.mysql_option_hbox.hide()
            self.nfs_option_hbox.hide()
            self.samba_option_hbox.hide()
            set_fe_drivers(self,True)
            set_be_drivers(self,False)

    def lirc_toggled(self,widget):
        """Called when the checkbox to configure a remote is toggled"""
        if (self.lirc_enable.get_active()):
            self.lirc_middle_vbox.set_sensitive(True)
            self.lirc_remote.set_active(0)
        else:
            self.lirc_middle_vbox.set_sensitive(False)
            self.lirc_remote.set_active(0)

    def mythweb_toggled(self,widget):
        """Called when the checkbox to install Mythweb is toggled"""
        if (self.mythweb.get_active()):
            self.mythweb_expander.show()
        else:
            self.mythweb_expander.hide()

    def enablevnc_toggled(self,widget):
        """Called when the checkbox to turn on VNC is toggled"""
        if (self.enablevnc.get_active()):
            self.vnc_pass_hbox.set_sensitive(True)
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.vnc_error_image.show()
        else:
            self.vnc_pass_hbox.set_sensitive(False)
            self.vnc_password.set_text("")
            self.allow_go_forward(True)
            self.allow_go_backward(True)
            self.vnc_error_image.hide()

    def uselivemysqlinfo_toggled(self,widget):
        """Called when the checkbox to copy live mysql information is pressed"""
        if (self.uselivemysqlinfo.get_active()):
            self.master_backend_table.hide()
        else:
            self.master_backend_table.show()

    def usemythwebpassword_toggled(self,widget):
        """Called when the checkbox to set a mythweb password is pressed"""
        if (self.usemythwebpassword.get_active()):
            self.mythweb_table.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.mythweb_user_error_image.show()
            self.mythweb_pass_error_image.show()
        else:
            self.mythweb_table.hide()
            self.mythweb_password.set_text("")
            self.mythweb_username.set_text("")
            self.mythweb_user_error_image.hide()
            self.mythweb_pass_error_image.hide()
            if (not self.usemysqlrootpassword.get_active() or not self.mysql_root_error_image.flags() & gtk.VISIBLE):
                self.allow_go_forward(True)
                self.allow_go_backward(True)

    def usemysqlrootpassword_toggled(self,widget):
        """Called when the checkbox to set a MySQL root password is pressed"""
        if (self.usemysqlrootpassword.get_active()):
            self.mysql_server_hbox.show()
            self.allow_go_forward(False)
            self.allow_go_backward(False)
            self.mysql_root_error_image.show()
        else:
            self.mysql_server_hbox.hide()
            self.mysql_root_password.set_text("")
            self.mysql_root_error_image.hide()
            if (not self.usemythwebpassword.get_active() or ((not self.mythweb_pass_error_image.flags() & gtk.VISIBLE) and (not self.mythweb_user_error_image.flags() & gtk.VISIBLE))):
                self.allow_go_forward(True)
                self.allow_go_backward(True)

    def toggle_number_tuners (self,widget):
        """Called whenever a number of tuners is changed"""
        num = self.number_tuners.get_value()
        if num > 0:
            if num > 1:
                if num > 2:
                    if num > 3:
                        if num > 4:
                            self.tuner0.show()
                            self.tuner1.show()
                            self.tuner2.show()
                            self.tuner3.show()
                            self.tuner4.show()
                        else:
                            self.tuner0.show()
                            self.tuner1.show()
                            self.tuner2.show()
                            self.tuner3.show()
                            self.tuner4.hide()
                            self.tuner4.set_active(0)
                    else:
                        self.tuner0.show()
                        self.tuner1.show()
                        self.tuner2.show()
                        self.tuner3.hide()
                        self.tuner3.set_active(0)
                        self.tuner4.hide()
                        self.tuner4.set_active(0)
                else:
                    self.tuner0.show()
                    self.tuner1.show()
                    self.tuner2.hide()
                    self.tuner2.set_active(0)
                    self.tuner3.hide()
                    self.tuner3.set_active(0)
                    self.tuner4.hide()
                    self.tuner4.set_active(0)
            else:
                self.tuner0.show()
                self.tuner1.hide()
                self.tuner1.set_active(0)
                self.tuner2.hide()
                self.tuner2.set_active(0)
                self.tuner3.hide()
                self.tuner3.set_active(0)
                self.tuner4.hide()
                self.tuner4.set_active(0)
        else:
            self.tuner0.hide()
            self.tuner0.set_active(0)
            self.tuner1.hide()
            self.tuner1.set_active(0)
            self.tuner2.hide()
            self.tuner2.set_active(0)
            self.tuner3.hide()
            self.tuner3.set_active(0)
            self.tuner4.hide()
            self.tuner4.set_active(0)

    def toggle_tuners (self,widget):
        """Checks to make sure no tuner widgets have same value"""
        def return_tuner_val(self,num):
            if num == 0:
                return self.tuner0.get_active()
            elif num == 1:
                return self.tuner1.get_active()
            elif num == 2:
                return self.tuner2.get_active()
            elif num == 3:
                return self.tuner3.get_active()
            elif num == 4:
                return self.tuner4.get_active()

        number_tuners = self.number_tuners.get_value_as_int()
        enable_warning=False
        for i in range(number_tuners):
            #Check for the unknown Analogue or Digital Option
            if (return_tuner_val(self,i) == 19 or return_tuner_val(self,i) == 20):
                enable_warning=True
        if enable_warning == True:
            self.tunernotice.show()
        else:
            self.tunernotice.hide()

    def video_changed (self,widget):
        """Called whenever the modify video driver option is toggled or its kids"""
        if (widget is not None and widget.get_name() == 'modifyvideodriver'):
            if (widget.get_active()):
                self.videodrivers_hbox.set_sensitive(True)
            else:
                self.tvout_vbox.set_sensitive(False)
                self.videodrivers_hbox.set_sensitive(False)
                self.video_driver.set_active(5)
                self.tvoutstandard.set_active(0)
                self.tvouttype.set_active(0)
        elif (widget is not None and widget.get_name() == 'video_driver'):
            type = widget.get_active()
            if (type == 0 or type == 1 or type == 2 or type == 3):
                self.tvout_vbox.set_sensitive(True)
            else:
                self.tvout_vbox.set_sensitive(False)
                self.tvoutstandard.set_active(0)
                self.tvouttype.set_active(0)


    def toggle_tv_out (self,widget):
        """Called when the tv-out type is toggled"""
        if (self.tvouttype.get_active() == 0):
            self.tvoutstandard.set_active(0)
        elif ((self.tvouttype.get_active() == 1 or self.tvouttype.get_active() == 2) and (self.tvoutstandard.get_active() == 0 or self.tvoutstandard.get_active() >= 11 )):
            self.tvoutstandard.set_active(10)
        elif self.tvouttype.get_active() == 3:
            self.tvoutstandard.set_active(11)

    def toggle_tv_standard(self,widget):
        """Called when the tv standard is toggled"""
        if (self.tvoutstandard.get_active() >= 11):
            self.tvouttype.set_active(3)
        elif (self.tvoutstandard.get_active() < 11 and self.tvoutstandard.get_active() > 0 and self.tvouttype.get_active() == 0):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() < 11 and self.tvouttype.get_active() ==3):
            self.tvouttype.set_active(1)
        elif (self.tvoutstandard.get_active() == 0):
            self.tvouttype.set_active(0)

    def lirc_changed(self,widget):
        """Called when anything remote related is changed"""
        if (widget is not None and widget.get_name() == 'lirc_remote'):
            #If the remote type isn't other, don't
            #allow them to change any other settings
            if (widget.get_active_text() == "Other Remote"):
            #Please see bug 157233 for why "Other Remote" is disabled for now
            #    self.lirc_driver.set_sensitive(True)
            #    self.lirc_driver_label.set_sensitive(True)
            #    self.lirc_modules.set_sensitive(True)
            #    self.lirc_modules_label.set_sensitive(True)
            #    self.lirc_rc.set_sensitive(True)
            #    self.lirc_rc_label.set_sensitive(True)
                self.lirc_bug_vbox.show()
                self.allow_go_forward(False)
                self.allow_go_backward(False)
            else:
            #    self.lirc_driver.set_sensitive(False)
            #    self.lirc_driver_label.set_sensitive(False)
            #    self.lirc_modules.set_sensitive(False)
            #    self.lirc_modules_label.set_sensitive(False)
            #    self.lirc_rc.set_sensitive(False)
            #    self.lirc_rc_label.set_sensitive(False)
                self.lirc_bug_vbox.hide()
                self.allow_go_forward(True)
                self.allow_go_backward(True)

            self.lirc_driver.set_active(widget.get_active())
            self.lirc_modules.set_active(widget.get_active())
            self.lirc_rc.set_active(widget.get_active())

    def get_advanced(self):
        """Returns if this is an advanced install"""
        return self.custominstall.get_active()

    def get_installtype(self):
        """Returns the current custom installation type"""
        if self.master_be_fe.get_active():
                return "Master Backend/Frontend"
        elif self.slave_be_fe.get_active():
                return "Slave Backend/Frontend"
        elif self.master_be.get_active():
                return "Master Backend"
        elif self.slave_be.get_active():
                return "Slave Backend"
        elif self.fe.get_active():
                return "Frontend"

    def get_mytharchive(self):
        """Returns the status of the mytharchive plugin"""
        if self.mytharchive.get_active():
            return True
        else:
            return False

    def get_mythbrowser(self):
        """Returns the status of the mythbrowser plugin"""
        if self.mythbrowser.get_active():
            return True
        else:
            return False

    def get_mythcontrols(self):
        """Returns the status of the mythcontrols plugin"""
        if self.mythcontrols.get_active():
            return True
        else:
            return False

    def get_mythdvd(self):
        """Returns the status of the mythdvd plugin"""
        if self.mythdvd.get_active():
            return True
        else:
            return False

    def get_mythflix(self):
        """Returns the status of the mythflix plugin"""
        if self.mythflix.get_active():
            return True
        else:
            return False

    def get_mythgallery(self):
        """Returns the status of the mythgallery plugin"""
        if self.mythgallery.get_active():
            return True
        else:
            return False

    def get_mythgame(self):
        """Returns the status of the mythgame plugin"""
        if self.mythgame.get_active():
            return True
        else:
            return False

    def get_mythmusic(self):
        """Returns the status of the mythmusic plugin"""
        if self.mythmusic.get_active():
            return True
        else:
            return False

    def get_mythnews(self):
        """Returns the status of the mythnews plugin"""
        if self.mythnews.get_active():
            return True
        else:
            return False

    def get_mythphone(self):
        """Returns the status of the mythphone plugin"""
        if self.mythphone.get_active():
            return True
        else:
            return False

    def get_mythstream(self):
        """Returns the status of the mythstream plugin"""
        if self.mythstream.get_active():
            return True
        else:
            return False

    def get_mythvideo(self):
        """Returns the status of the mythvideo plugin"""
        if self.mythvideo.get_active():
            return True
        else:
            return False

    def get_mythweather(self):
        """Returns the status of the mythweather plugin"""
        if self.mythweather.get_active():
            return True
        else:
            return False

    def get_mythweb(self):
        """Returns the status of the mythweb plugin"""
        if self.mythweb.get_active():
            return True
        else:
            return False

    def get_officialthemes(self):
        """Returns the status of the official themes"""
        if self.officialthemes.get_active():
            return True
        else:
            return False

    def get_communitythemes(self):
        """Returns the status of the community themes"""
        if self.communitythemes.get_active():
            return True
        else:
            return False
    def get_video(self):
        """Returns the status of the video graphics drivers"""
        if (self.modifyvideodriver.get_active()):
            driver = self.video_driver.get_active()
            if driver == 0:
                return "fglrx"
            elif driver == 1:
                return "nvidia_legacy"
            elif driver == 2:
                return "nvidia"
            elif driver == 3:
                return "nvidia_new"
            elif driver == 4:
                return "openchrome"
            else:
                return "None"
        else:
            return "None"

    def get_tvout(self):
        """Returns the status of the TV Out type"""
        if (self.modifyvideodriver.get_active()):
            return self.tvouttype.get_active_text()
        else:
            return "TV Out Disabled"

    def get_tvstandard(self):
        """Returns the status of the TV Standard type"""
        if (self.modifyvideodriver.get_active()):
            return self.tvoutstandard.get_active_text()
        else:
            return "TV Out Disabled"

    def get_uselivemysqlinfo(self):
        if (self.uselivemysqlinfo.get_active()):
            return True
        else:
            return False

    def get_mysqluser(self):
        return self.mysql_user.get_text()

    def get_mysqlpass(self):
        return self.mysql_password.get_text()

    def get_mysqldatabase(self):
        return self.mysql_database.get_text()

    def get_mysqlserver(self):
        return self.mysql_server.get_text()

    def get_secure_mysql(self):
        if self.usemysqlrootpassword.get_active():
            return True
        else:
            return False

    def get_mysql_root_password(self):
        return self.mysql_root_password.get_text()

    def get_secure_mythweb(self):
        if self.usemythwebpassword.get_active():
            return True
        else:
            return False

    def get_mythweb_username(self):
        return self.mythweb_username.get_text()

    def get_mythweb_password(self):
        return self.mythweb_password.get_text()

    def get_vnc(self):
        if self.enablevnc.get_active():
            return True
        else:
            return False

    def get_vnc_password(self):
        return self.vnc_password.get_text()

    def get_ssh(self):
        if self.enablessh.get_active():
            return True
        else:
            return False

    def get_samba(self):
        if self.enablesamba.get_active():
            return True
        else:
            return False

    def get_nfs(self):
        if self.enablenfs.get_active():
            return True
        else:
            return False

    def get_mysql_port(self):
        if self.enablemysql.get_active():
            return True
        else:
            return False
    def get_lirc(self):
        if self.lirc_enable.get_active():
            return True
        else:
            return False

    def get_lirc_remote(self):
        return self.lirc_remote.get_active_text()

    def get_lirc_modules(self):
        return self.lirc_modules.get_active_text()

    def get_lirc_driver(self):
        return self.lirc_driver.get_active_text()

    def get_lirc_rc(self):
        return self.lirc_rc.get_active_text()

    def get_hdhomerun(self):
        return self.hdhomerun.get_active()

    def get_xmltv(self):
        return self.xmltv.get_active()
